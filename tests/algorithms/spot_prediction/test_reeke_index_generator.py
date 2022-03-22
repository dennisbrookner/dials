from __future__ import annotations

import math
import random

from cctbx.sgtbx import space_group, space_group_info, space_group_symbols
from cctbx.uctbx import unit_cell
from rstbx.diffraction import full_sphere_indices, rotation_angles
from scitbx import matrix
from scitbx.math import r3_rotation_axis_and_angle_as_matrix

from dials.algorithms.spot_prediction import ReekeIndexGenerator


class Test:
    def setup_method(self):

        # cubic, 50A cell, 1A radiation, 1 deg osciillation, everything ideal
        a = 50.0
        self.ub = matrix.sqr((1.0 / a, 0.0, 0.0, 0.0, 1.0 / a, 0.0, 0.0, 0.0, 1.0 / a))

        self.axis = matrix.col((0, 1, 0))
        self.s0 = matrix.col((0, 0, 1))

        self.dmin = 1.5
        self.margin = 1

    def test_varying_s0(self):

        space_group_type = space_group_info("P 1").group().type()
        ub_beg, ub_end = self._get_ub(0)

        hkl_sets = []
        # loop over random beam changes and ensure we can generate indices
        us0 = self.s0.normalize()
        for i in range(100):
            # find a random axis orthogonal to the beam about which to rotate it
            axis = (us0.ortho()).rotate_around_origin(
                axis=us0, angle=random.uniform(0, 2 * math.pi)
            )

            # apply small angle of rotation (up to ~1mrad) to perturb the beam direction
            s0_2 = self.s0.rotate_around_origin(
                axis=axis, angle=random.uniform(0, 0.057), deg=True
            )

            # alter the wavelength by up to about 0.1%
            s0_2 = s0_2 * random.uniform(0.999, 1.001)

            # now try to generate indices
            r = ReekeIndexGenerator(
                ub_beg,
                ub_end,
                space_group_type,
                self.axis,
                self.s0,
                s0_2,
                self.dmin,
                self.margin,
            )
            hkl = r.to_array()
            hkl_sets.append(set(hkl))

        # count common reflections in every set. For this example let's say we are
        # satisfied if 98% of the smallest set of generated indices are common
        # to every set. It is unclear how optimal this requirement is, but it at
        # least shows that beam changes across one image that are much larger than
        # we'd expect in normal processing do not hugely alter the generated list
        # of HKLs.
        min_set_len = min(len(e) for e in hkl_sets)
        common = set.intersection(*hkl_sets)
        # print "{0:.3f}% common".format(len(common) / min_set_len)
        assert len(common) >= 0.98 * min_set_len

    def _get_ub(self, frame):

        angle_beg = frame * 1
        angle_end = (frame + 1) * 1

        r_osc_beg = matrix.sqr(
            r3_rotation_axis_and_angle_as_matrix(
                axis=self.axis, angle=angle_beg, deg=True
            )
        )

        r_osc_end = matrix.sqr(
            r3_rotation_axis_and_angle_as_matrix(
                axis=self.axis, angle=angle_end, deg=True
            )
        )

        ub_beg = r_osc_beg * self.ub
        ub_end = r_osc_end * self.ub
        return ub_beg, ub_end


def test_versus_brute_force():
    """Perform a regression test by comparing to indices generated by the brute
    force method"""

    # cubic, 50A cell, 1A radiation, 1 deg osciillation, everything ideal
    a = 50.0
    ub_beg = matrix.sqr((1.0 / a, 0.0, 0.0, 0.0, 1.0 / a, 0.0, 0.0, 0.0, 1.0 / a))
    axis = matrix.col((0, 1, 0))
    r_osc = matrix.sqr(
        r3_rotation_axis_and_angle_as_matrix(axis=axis, angle=1.0, deg=True)
    )
    ub_end = r_osc * ub_beg
    uc = unit_cell((a, a, a, 90, 90, 90))
    sg = space_group(space_group_symbols("P23").hall())
    s0 = matrix.col((0, 0, 1))
    wavelength = 1.0
    dmin = 1.5

    # get the full set of indices
    indices = full_sphere_indices(unit_cell=uc, resolution_limit=dmin, space_group=sg)

    # find the observed indices
    ra = rotation_angles(dmin, ub_beg, wavelength, axis)
    obs_indices, obs_angles = ra.observed_indices_and_angles_from_angle_range(
        phi_start_rad=0.0 * math.pi / 180.0,
        phi_end_rad=1.0 * math.pi / 180.0,
        indices=indices,
    )

    # r = reeke_model(ub_beg, ub_end, axis, s0, dmin, 1.0)
    # reeke_indices = r.generate_indices()

    # now try the Reeke method to generate indices
    r = ReekeIndexGenerator(ub_beg, ub_end, sg.type(), axis, s0, dmin, margin=1)
    reeke_indices = r.to_array()

    for oi in obs_indices:
        assert tuple(map(int, oi)) in reeke_indices
