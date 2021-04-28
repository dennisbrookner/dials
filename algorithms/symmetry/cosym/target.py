"""Target function for cosym analysis."""

import copy
import logging
import warnings

import numpy as np
import scipy.sparse
import scipy.stats
from orderedset import OrderedSet

import cctbx.sgtbx.cosets
from cctbx import miller, sgtbx
from cctbx.array_family import flex
from libtbx import easy_mp

logger = logging.getLogger(__name__)


class Target:
    """Target function for cosym analysis.

    Attributes:
      dim (int): The number of dimensions used in the analysis.
    """

    def __init__(
        self,
        intensities,
        lattice_ids,
        weights=None,
        min_pairs=3,
        lattice_group=None,
        dimensions=None,
        nproc=1,
    ):
        r"""Intialise a Target object.

        Args:
          intensities (cctbx.miller.array): The intensities on which to perform
            cosym anaylsis.
          lattice_ids (np.ndarray): An array of equal size to
            `intensities` which maps each reflection to a given lattice (dataset).
          weights (str): Optionally include weights in the target function.
            Allowed values are `None`, "count" and "standard_error". The default
            is to use no weights. If "count" is set, then weights are equal to the
            number of pairs of reflections used in calculating each value of the
            rij matrix. If "standard_error" is used, then weights are defined as
            :math:`w_{ij} = 1/s`, where :math:`s = \sqrt{(1-r_{ij}^2)/(n-2)}`.
            See also http://www.sjsu.edu/faculty/gerstman/StatPrimer/correlation.pdf.
          min_pairs (int): Only calculate the correlation coefficient between two
            datasets if they have more than `min_pairs` of common reflections.
          lattice_group (cctbx.sgtbx.space_group): Optionally set the lattice
            group to be used in the analysis.
          dimensions (int): Optionally override the number of dimensions to be used
            in the analysis. If not set, then the number of dimensions used is
            equal to the greater of 2 or the number of symmetry operations in the
            lattice group.
          nproc (int): number of processors to use for computing the rij matrix.
        """
        if weights is not None:
            assert weights in ("count", "standard_error")
        self._weights = weights
        self._min_pairs = min_pairs
        self._nproc = nproc

        data = intensities.customized_copy(anomalous_flag=False)
        cb_op_to_primitive = data.change_of_basis_op_to_primitive_setting()
        data = data.change_basis(cb_op_to_primitive).map_to_asu()

        # Convert to uint64 avoids crashes on Windows when later constructing
        # flex.size_t (https://github.com/cctbx/cctbx_project/issues/591)
        order = lattice_ids.argsort().astype(np.uint64)
        sorted_data = data.data().select(flex.size_t(order))
        sorted_indices = data.indices().select(flex.size_t(order))
        self._lattice_ids = lattice_ids[order]
        self._data = data.customized_copy(indices=sorted_indices, data=sorted_data)
        assert isinstance(self._data.indices(), type(flex.miller_index()))
        assert isinstance(self._data.data(), type(flex.double()))

        # construct a lookup for the separate lattices
        self._lattices = np.array(
            [
                np.where(self._lattice_ids == i)[0][0]
                for i in np.unique(self._lattice_ids)
            ]
        )

        self.sym_ops = OrderedSet(["x,y,z"])
        self._lattice_group = lattice_group
        self.sym_ops.update(op.as_xyz() for op in self._generate_twin_operators())
        if dimensions is None:
            dimensions = max(2, len(self.sym_ops))
        self.set_dimensions(dimensions)

        self._lattice_group = copy.deepcopy(self._data.space_group())
        for sym_op in self.sym_ops:
            self._lattice_group.expand_smx(sym_op)
        self._patterson_group = self._lattice_group.build_derived_patterson_group()

        logger.debug(
            "Lattice group: %s (%i symops)",
            self._lattice_group.info().symbol_and_number(),
            len(self._lattice_group),
        )
        logger.debug(
            "Patterson group: %s", self._patterson_group.info().symbol_and_number()
        )

        self.rij_matrix, self.wij_matrix = self._compute_rij_wij()

    def set_dimensions(self, dimensions):
        """Set the number of dimensions for analysis.

        Args:
          dimensions (int): The number of dimensions to be used.
        """
        self.dim = dimensions

    def _generate_twin_operators(self, lattice_symmetry_max_delta=5.0):
        # see also mmtbx.scaling.twin_analyses.twin_laws
        if self._lattice_group is None:
            cb_op_to_minimum_cell = self._data.change_of_basis_op_to_minimum_cell()
            minimum_cell_symmetry = self._data.crystal_symmetry().change_basis(
                cb_op=cb_op_to_minimum_cell
            )
            self._lattice_group = sgtbx.lattice_symmetry.group(
                reduced_cell=minimum_cell_symmetry.unit_cell(),
                max_delta=lattice_symmetry_max_delta,
            )
            intensity_symmetry = minimum_cell_symmetry.reflection_intensity_symmetry(
                anomalous_flag=self._data.anomalous_flag()
            )
            cb_op = cb_op_to_minimum_cell.inverse()
        else:
            cb_op = sgtbx.change_of_basis_op()
            intensity_symmetry = self._data.reflection_intensity_symmetry()

        operators = []
        for partition in cctbx.sgtbx.cosets.left_decomposition(
            g=self._lattice_group,
            h=intensity_symmetry.space_group()
            .build_derived_acentric_group()
            .make_tidy(),
        ).partitions[1:]:
            if partition[0].r().determinant() > 0:
                operators.append(cb_op.apply(partition[0]))

        return operators

    def _lattice_lower_upper_index(self, lattice_id):
        lower_index = int(self._lattices[lattice_id])
        upper_index = None
        if lattice_id < len(self._lattices) - 1:
            upper_index = int(self._lattices[lattice_id + 1])
        else:
            assert lattice_id == len(self._lattices) - 1
        return lower_index, upper_index

    def _compute_rij_wij(self, use_cache=True):
        """Compute the rij_wij matrix.

        Rij is a symmetric matrix of size (n x m, n x m), where n is the number of
        datasets and m is the number of symmetry operations.

        It is composed of (m, m) blocks of size (n, n), where each block contains the
        correlation coefficients between cb_op_k applied to datasets 1..N with
        cb_op_kk applied to datasets 1.. N.

        If `use_cache=True`, then an optimisation is made to reflect the fact some elements
        of the matrix are equivalent, i.e.:
            CC[(a, cb_op_k), (b, cb_op_kk)] == CC[(a,), (b, cb_op_k.inverse() * cb_op_kk)]

        """
        n_lattices = len(self._lattices)

        # Pre-calculate miller indices after application of each cb_op. Only calculate
        # this once per cb_op instead of on-the-fly every time we need it.
        indices = {}
        epsilons = {}
        space_group_type = self._data.space_group().type()
        for cb_op in self.sym_ops:
            cb_op = sgtbx.change_of_basis_op(cb_op)
            indices_reindexed = cb_op.apply(self._data.indices())
            miller.map_to_asu(space_group_type, False, indices_reindexed)
            indices[cb_op.as_xyz()] = np.array(
                [
                    h.iround().as_numpy_array()
                    for h in indices_reindexed.as_vec3_double().parts()
                ]
            ).transpose()
            epsilons[cb_op.as_xyz()] = self._patterson_group.epsilon(
                indices_reindexed
            ).as_numpy_array()
        intensities = self._data.data().as_numpy_array()

        def _compute_rij_matrix_one_row_block(i):
            rij_cache = {}

            n_sym_ops = len(self.sym_ops)
            NN = n_lattices * n_sym_ops

            rij_row = []
            rij_col = []
            rij_data = []
            if self._weights:
                wij_row = []
                wij_col = []
                wij_data = []
            else:
                wij = None

            i_lower, i_upper = self._lattice_lower_upper_index(i)
            intensities_i = intensities[i_lower:i_upper]

            for j in range(n_lattices):

                j_lower, j_upper = self._lattice_lower_upper_index(j)
                intensities_j = intensities[j_lower:j_upper]

                for k, cb_op_k in enumerate(self.sym_ops):
                    cb_op_k = sgtbx.change_of_basis_op(cb_op_k)

                    indices_i = indices[cb_op_k.as_xyz()][i_lower:i_upper]
                    epsilons_i = epsilons[cb_op_k.as_xyz()][i_lower:i_upper]

                    for kk, cb_op_kk in enumerate(self.sym_ops):
                        if i == j and k == kk:
                            # don't include correlation of dataset with itself
                            continue
                        cb_op_kk = sgtbx.change_of_basis_op(cb_op_kk)

                        ik = i + (n_lattices * k)
                        jk = j + (n_lattices * kk)

                        key = (i, j, str(cb_op_k.inverse() * cb_op_kk))
                        if use_cache and key in rij_cache:
                            cc, n = rij_cache[key]
                        else:
                            indices_j = indices[cb_op_kk.as_xyz()][j_lower:j_upper]
                            epsilons_j = epsilons[cb_op_k.as_xyz()][j_lower:j_upper]

                            def match_miller_indices(indices_0, indices_1):
                                offset = -np.min(
                                    np.concatenate([indices_0, indices_1]), axis=0
                                )
                                dims = (
                                    np.max(
                                        np.concatenate([indices_0, indices_1]), axis=0
                                    )
                                    + offset
                                    + 1
                                )
                                a = np.ravel_multi_index((indices_0 + offset).T, dims)
                                b = np.ravel_multi_index((indices_1 + offset).T, dims)
                                _, p0, p1 = np.intersect1d(a, b, return_indices=True)
                                return p0, p1

                            isel_i, isel_j = match_miller_indices(indices_i, indices_j)

                            isel_i = isel_i[epsilons_i[isel_i] == 1]
                            isel_j = isel_j[epsilons_j[isel_j] == 1]

                            n = isel_i.size
                            if n < self._min_pairs:
                                n = None
                                cc = None
                            else:
                                cc, _ = scipy.stats.pearsonr(
                                    intensities_i[isel_i],
                                    intensities_j[isel_j],
                                )
                            if np.isnan(cc):
                                cc = None
                                n = None

                            rij_cache[key] = (cc, n)

                        if (
                            n is None
                            or cc is None
                            or (self._min_pairs is not None and n < self._min_pairs)
                        ):
                            continue
                        if self._weights:
                            wij_row.append(ik)
                            wij_col.append(jk)
                            wij_data.append(n)
                        rij_row.append(ik)
                        rij_col.append(jk)
                        rij_data.append(cc)

            rij = scipy.sparse.coo_matrix(
                (rij_data, (rij_row, rij_col)), shape=(NN, NN)
            )
            if self._weights:
                wij = scipy.sparse.coo_matrix(
                    (wij_data, (wij_row, wij_col)), shape=(NN, NN)
                )

            return rij, wij

        args = [(i,) for i in range(n_lattices)]
        results = easy_mp.parallel_map(
            _compute_rij_matrix_one_row_block,
            args,
            processes=self._nproc,
            iterable_type=easy_mp.posiargs,
            method="multiprocessing",
        )

        rij_matrix = None
        wij_matrix = None
        for i, (rij, wij) in enumerate(results):
            if rij_matrix is None:
                rij_matrix = rij
            else:
                rij_matrix += rij
            if wij is not None:
                if wij_matrix is None:
                    wij_matrix = wij
                else:
                    wij_matrix += wij

        rij_matrix = rij_matrix.toarray().astype(np.float64)
        if wij_matrix is not None:
            wij_matrix = wij_matrix.toarray().astype(np.float64)
            if self._weights == "standard_error":
                # http://www.sjsu.edu/faculty/gerstman/StatPrimer/correlation.pdf
                sel = np.where(wij_matrix > 2)
                se = np.sqrt((1 - np.square(rij_matrix[sel])) / (wij_matrix[sel] - 2))
                wij_matrix = np.zeros_like(rij_matrix)
                wij_matrix[sel] = 1 / se

        return rij_matrix, wij_matrix

    def compute_functional(self, x: np.ndarray) -> float:
        """Compute the target function at coordinates `x`.

        Args:
          x (np.ndarray):
            a flattened list of the N-dimensional vectors, i.e. coordinates in
            the first dimension are stored first, followed by the coordinates in
            the second dimension, etc.

        Returns:
          f (float): The value of the target function at coordinates `x`.
        """
        assert (x.size // self.dim) == (len(self._lattices) * len(self.sym_ops))
        x = x.reshape((self.dim, x.size // self.dim))
        elements = np.square(self.rij_matrix - x.T @ x)
        if self.wij_matrix is not None:
            np.multiply(self.wij_matrix, elements, out=elements)
        f = 0.5 * elements.sum()
        return f

    def compute_gradients_fd(self, x: np.ndarray, eps=1e-6) -> np.ndarray:
        """Compute the gradients at coordinates `x` using finite differences.

        Args:
          x (np.ndarray):
            a flattened list of the N-dimensional vectors, i.e. coordinates in
            the first dimension are stored first, followed by the coordinates in
            the second dimension, etc.
          eps (float):
            The value of epsilon to use in finite difference calculations.

        Returns:
          grad (np.ndarray):
          The gradients of the target function with respect to the parameters.
        """
        x = copy.deepcopy(x)
        grad = np.zeros(x.shape)
        for i in range(x.size):
            x[i] += eps  # x + eps
            fp = self.compute_functional(x)
            x[i] -= 2 * eps  # x - eps
            fm = self.compute_functional(x)
            x[i] += eps  # reset to original values
            grad[i] += (fp - fm) / (2 * eps)
        return grad

    def compute_gradients(self, x: np.ndarray) -> np.ndarray:
        """Compute the gradients of the target function at coordinates `x`.

        Args:
          x (np.ndarray):
            a flattened list of the N-dimensional vectors, i.e. coordinates in
            the first dimension are stored first, followed by the coordinates in
            the second dimension, etc.

        Returns:
          Tuple[float, np.ndarray]:
          f: The value of the target function at coordinates `x`.
          grad: The gradients of the target function with respect to the parameters.
        """
        x = x.reshape((self.dim, x.size // self.dim))
        if self.wij_matrix is not None:
            wrij_matrix = np.multiply(self.wij_matrix, self.rij_matrix)
            grad = -2 * x @ (wrij_matrix - np.multiply(self.wij_matrix, x.T @ x))
        else:
            grad = -2 * x @ (self.rij_matrix - x.T @ x)
        return grad.flatten()

    def curvatures(self, x: np.ndarray) -> np.ndarray:
        """Compute the curvature of the target function at coordinates `x`.

        Args:
          x (np.ndarray):
            a flattened list of the N-dimensional vectors, i.e. coordinates in
            the first dimension are stored first, followed by the coordinates in
            the second dimension, etc.

        Returns:
          curvs (np.ndarray):
          The curvature of the target function with respect to the parameters.
        """
        if self.wij_matrix is not None:
            wij = self.wij_matrix
        else:
            wij = np.ones(self.rij_matrix.shape)
        x = x.reshape((self.dim, x.size // self.dim))
        curvs = 2 * np.square(x) @ wij
        return curvs.flatten()

    def curvatures_fd(self, x: np.ndarray, eps=1e-6) -> np.ndarray:
        """Compute the curvatures at coordinates `x` using finite differences.

        Args:
          x (np.ndarray):
            a flattened list of the N-dimensional vectors, i.e. coordinates in
            the first dimension are stored first, followed by the coordinates in
            the second dimension, etc.
          eps (float):
            The value of epsilon to use in finite difference calculations.

        Returns:
          curvs (np.ndarray):
          The curvature of the target function with respect to the parameters.
        """
        x = copy.deepcopy(x)
        f = self.compute_functional(x)
        curvs = np.zeros(x.shape)
        for i in range(x.size):
            x[i] += eps  # x + eps
            fp = self.compute_functional(x)
            x[i] -= 2 * eps  # x - eps
            fm = self.compute_functional(x)
            x[i] += eps  # reset to original values
            curvs[i] += (fm - 2 * f + fp) / (eps ** 2)
        return curvs

    def get_sym_ops(self):
        """Get the list of symmetry operations used in the analysis.

        Returns:
          List[cctbx.sgtbx.rt_mx]: The list of symmetry operations.
        """
        warnings.warn(
            "get_sym_ops() is deprecated, use sym_ops property instead",
            DeprecationWarning,
        )
        return self.sym_ops
