#!/usr/bin/env python
# -*- mode: python; coding: utf-8; indent-tabs-mode: nil; python-indent: 2 -*-
#

from __future__ import absolute_import, division, print_function

import math
import logging

import libtbx
from dxtbx.model.experiment_list import Experiment, ExperimentList
from dials.array_family import flex
from dials.util import log
from dials.algorithms.indexing.indexer import Indexer
from dials.algorithms.indexing.known_orientation import IndexerKnownOrientation
from dials.algorithms.indexing.lattice_search import BasisVectorSearch
from dials.algorithms.indexing.nave_parameters import NaveParameters
from dials.algorithms.indexing import DialsIndexError, DialsIndexRefineError

logger = logging.getLogger(__name__)
debug_handle = log.debug_handle(logger)
info_handle = log.info_handle(logger)


def calc_2D_rmsd_and_displacements(reflections):

    displacements = flex.vec2_double(
        reflections["xyzobs.px.value"].parts()[0],
        reflections["xyzobs.px.value"].parts()[1],
    ) - flex.vec2_double(
        reflections["xyzcal.px"].parts()[0], reflections["xyzcal.px"].parts()[1]
    )
    rmsd = math.sqrt(flex.mean(displacements.dot(displacements)))

    return rmsd, displacements


def plot_displacements(reflections, predictions, experiments):
    rmsd, displacements = calc_2D_rmsd_and_displacements(predictions)

    if True:  # params.refinement.plot_residual_scatter:
        from matplotlib import pyplot as plt

        plt.figure()
        for cv in displacements:
            plt.plot([cv[0]], [-cv[1]], "r.")
        plt.title(" %d spots, r.m.s.d. %5.2f pixels" % (len(displacements), rmsd))
        plt.axes().set_aspect("equal")
        plt.show()
        plt.close()

    if True:  # params.refinement.plot_residual_map:
        from matplotlib import pyplot as plt

        plt.figure()
        sz1, sz2 = experiments[0].detector[0].get_image_size()
        for item, cv in zip(predictions, displacements):
            plt.plot([item["xyzcal.px"][0]], [sz1 - item["xyzcal.px"][1]], "r.")
            plt.plot(
                [item["xyzobs.px.value"][0]], [sz1 - item["xyzobs.px.value"][1]], "g."
            )
            plt.plot(
                [item["xyzcal.px"][0], item["xyzcal.px"][0] + 10.0 * cv[0]],
                [sz1 - item["xyzcal.px"][1], sz1 - item["xyzcal.px"][1] - 10.0 * cv[1]],
                "r-",
            )

        plt.xlim([0, experiments[0].detector[0].get_image_size()[0]])
        plt.ylim([0, experiments[0].detector[0].get_image_size()[1]])
        plt.title(" %d spots, r.m.s.d. %5.2f pixels" % (len(displacements), rmsd))
        plt.axes().set_aspect("equal")
        plt.show()
        plt.close()


def e_refine(params, experiments, reflections, graph_verbose=False):
    # Stills-specific parameters we always want
    assert params.refinement.reflections.outlier.algorithm in (
        None,
        "null",
    ), (
        "Cannot index, set refinement.reflections.outlier.algorithm=null"
    )  # we do our own outlier rejection

    from dials.algorithms.refinement.refiner import RefinerFactory

    refiner = RefinerFactory.from_parameters_data_experiments(
        params, reflections, experiments, verbosity=1
    )

    refiner.run()

    ref_sel = refiner.selection_used_for_refinement()
    assert ref_sel.count(True) == len(reflections)

    if not graph_verbose:
        return refiner

    RR = refiner.predict_for_reflection_table(reflections)
    plot_displacements(reflections, RR, experiments)

    return refiner


class StillsIndexer(Indexer):
    """ Class for indexing stills """

    def __init__(self, reflections, experiments, params=None):
        if params.refinement.reflections.outlier.algorithm in ("auto", libtbx.Auto):
            # The stills_indexer provides its own outlier rejection
            params.refinement.reflections.outlier.algorithm = "null"
        super(StillsIndexer, self).__init__(reflections, experiments, params)

    def index(self):
        # most of this is the same as dials.algorithms.indexing.indexer.indexer_base.index(), with some stills
        # specific modifications (don't re-index after choose best orientation matrix, but use the indexing from
        # choose best orientation matrix, also don't use macrocycles) of refinement after indexing.
        # 2017 update: do accept multiple lattices per shot

        experiments = ExperimentList()

        had_refinement_error = False
        have_similar_crystal_models = False

        while True:
            self.d_min = self.params.refinement_protocol.d_min_start
            if had_refinement_error or have_similar_crystal_models:
                break
            max_lattices = self.params.multiple_lattice_search.max_lattices
            if max_lattices is not None and len(experiments) >= max_lattices:
                break
            if len(experiments) > 0:
                cutoff_fraction = (
                    self.params.multiple_lattice_search.recycle_unindexed_reflections_cutoff
                )
                d_spacings = 1 / self.reflections["rlp"].norms()
                d_min_indexed = flex.min(d_spacings.select(self.indexed_reflections))
                min_reflections_for_indexing = cutoff_fraction * len(
                    self.reflections.select(d_spacings > d_min_indexed)
                )
                crystal_ids = self.reflections.select(d_spacings > d_min_indexed)["id"]
                if (crystal_ids == -1).count(True) < min_reflections_for_indexing:
                    logger.info(
                        "Finish searching for more lattices: %i unindexed reflections remaining."
                        % (min_reflections_for_indexing)
                    )
                    break

            n_lattices_previous_cycle = len(experiments)

            # index multiple lattices per shot
            if len(experiments) == 0:
                experiments.extend(self.find_lattices())
                if len(experiments) == 0:
                    raise DialsIndexError("No suitable lattice could be found.")
            else:
                try:
                    new = self.find_lattices()
                    experiments.extend(new)
                except Exception as e:
                    logger.info("Indexing remaining reflections failed")
                    logger.debug(
                        "Indexing remaining reflections failed, exception:\n" + str(e)
                    )

            # reset reflection lattice flags
            # the lattice a given reflection belongs to: a value of -1 indicates
            # that a reflection doesn't belong to any lattice so far
            self.reflections["id"] = flex.int(len(self.reflections), -1)

            self.index_reflections(experiments, self.reflections)

            if len(experiments) == n_lattices_previous_cycle:
                # no more lattices found
                break

            if (
                not self.params.stills.refine_candidates_with_known_symmetry
                and self.params.known_symmetry.space_group is not None
            ):
                self._apply_symmetry_post_indexing(
                    experiments, self.reflections, n_lattices_previous_cycle
                )

            # discard nearly overlapping lattices on the same shot
            if self._check_have_similar_crystal_models(experiments):
                break

            self.indexed_reflections = self.reflections["id"] > -1
            if self.d_min is None:
                sel = self.reflections["id"] <= -1
            else:
                sel = flex.bool(len(self.reflections), False)
                lengths = 1 / self.reflections["rlp"].norms()
                isel = (lengths >= self.d_min).iselection()
                sel.set_selected(isel, True)
                sel.set_selected(self.reflections["id"] > -1, False)
            self.unindexed_reflections = self.reflections.select(sel)

            reflections_for_refinement = self.reflections.select(
                self.indexed_reflections
            )

            if len(self.params.stills.isoforms) > 0:
                logger.info("")
                logger.info("#" * 80)
                logger.info("Starting refinement")
                logger.info("#" * 80)
                logger.info("")

                import copy

                isoform_experiments = ExperimentList()
                isoform_reflections = flex.reflection_table()
                # Note, changes to params after initial indexing. Cannot use tie to target when fixing the unit cell.
                self.all_params.refinement.reflections.outlier.algorithm = "null"
                self.all_params.refinement.parameterisation.crystal.fix = "cell"
                self.all_params.refinement.parameterisation.crystal.unit_cell.restraints.tie_to_target = (
                    []
                )

                for expt_id, experiment in enumerate(experiments):
                    reflections = reflections_for_refinement.select(
                        reflections_for_refinement["id"] == expt_id
                    )
                    reflections["id"] = flex.int(len(reflections), 0)
                    refiners = []
                    for isoform in self.params.stills.isoforms:
                        iso_experiment = copy.deepcopy(experiment)
                        crystal = iso_experiment.crystal
                        if (
                            isoform.lookup_symbol
                            != crystal.get_space_group().type().lookup_symbol()
                        ):
                            logger.info(
                                "Crystal isoform lookup_symbol %s does not match isoform %s lookup_symbol %s"
                                % (
                                    crystal.get_space_group().type().lookup_symbol(),
                                    isoform.name,
                                    isoform.lookup_symbol,
                                )
                            )
                            continue
                        crystal.set_B(isoform.cell.fractionalization_matrix())

                        logger.info("Refining isoform %s" % isoform.name)
                        refiners.append(
                            e_refine(
                                params=self.all_params,
                                experiments=ExperimentList([iso_experiment]),
                                reflections=reflections,
                                graph_verbose=False,
                            )
                        )

                    if len(refiners) == 0:
                        raise DialsIndexError(
                            "No isoforms had a lookup symbol that matched"
                        )
                    positional_rmsds = [
                        math.sqrt(P.rmsds()[0] ** 2 + P.rmsds()[1] ** 2)
                        for P in refiners
                    ]
                    logger.info(
                        "Positional rmsds for all isoforms:" + str(positional_rmsds)
                    )
                    minrmsd_mm = min(positional_rmsds)
                    minindex = positional_rmsds.index(minrmsd_mm)
                    logger.info(
                        "The smallest rmsd is %5.1f um from isoform %s"
                        % (
                            1000.0 * minrmsd_mm,
                            self.params.stills.isoforms[minindex].name,
                        )
                    )
                    if self.params.stills.isoforms[minindex].rmsd_target_mm is not None:
                        logger.info(
                            "Asserting %f < %f"
                            % (
                                minrmsd_mm,
                                self.params.stills.isoforms[minindex].rmsd_target_mm,
                            )
                        )
                        assert (
                            minrmsd_mm
                            < self.params.stills.isoforms[minindex].rmsd_target_mm
                        )
                    logger.info(
                        "Acceptable rmsd for isoform %s."
                        % (self.params.stills.isoforms[minindex].name)
                    )
                    if len(self.params.stills.isoforms) == 2:
                        logger.info(
                            "Rmsd gain over the other isoform %5.1f um."
                            % (1000.0 * abs(positional_rmsds[0] - positional_rmsds[1]))
                        )
                    R = refiners[minindex]
                    # Now one last check to see if direct beam is out of bounds
                    if self.params.stills.isoforms[minindex].beam_restraint is not None:
                        from scitbx import matrix

                        refined_beam = matrix.col(
                            R.get_experiments()[0]
                            .detector[0]
                            .get_beam_centre_lab(experiments[0].beam.get_s0())[0:2]
                        )
                        known_beam = matrix.col(
                            self.params.stills.isoforms[minindex].beam_restraint
                        )
                        logger.info(
                            "Asserting difference in refined beam center and expected beam center %f < %f"
                            % (
                                (refined_beam - known_beam).length(),
                                self.params.stills.isoforms[minindex].rmsd_target_mm,
                            )
                        )
                        assert (
                            (refined_beam - known_beam).length()
                            < self.params.stills.isoforms[minindex].rmsd_target_mm
                        )
                        # future--circle of confusion could be given as a separate length in mm instead of reusing rmsd_target

                    experiment = R.get_experiments()[0]
                    experiment.crystal.identified_isoform = self.params.stills.isoforms[
                        minindex
                    ].name

                    isoform_experiments.append(experiment)
                    reflections["id"] = flex.int(len(reflections), expt_id)
                    isoform_reflections.extend(reflections)
                experiments = isoform_experiments
                reflections_for_refinement = isoform_reflections

            if self.params.refinement_protocol.mode == "repredict_only":

                from dials.algorithms.indexing.nave_parameters import NaveParameters
                from dials.algorithms.refinement.prediction.managed_predictors import (
                    ExperimentsPredictorFactory,
                )

                refined_experiments, refined_reflections = (
                    experiments,
                    reflections_for_refinement,
                )
                ref_predictor = ExperimentsPredictorFactory.from_experiments(
                    experiments,
                    force_stills=True,
                    spherical_relp=self.all_params.refinement.parameterisation.spherical_relp_model,
                )
                ref_predictor(refined_reflections)
                refined_reflections["delpsical2"] = (
                    refined_reflections["delpsical.rad"] ** 2
                )
                for expt_id in range(len(refined_experiments)):
                    refls = refined_reflections.select(
                        refined_reflections["id"] == expt_id
                    )
                    nv = NaveParameters(
                        params=self.all_params,
                        experiments=refined_experiments[expt_id : expt_id + 1],
                        reflections=refls,
                        refinery=None,
                        graph_verbose=False,
                    )
                    experiments[expt_id].crystal = nv()
                ref_predictor = ExperimentsPredictorFactory.from_experiments(
                    experiments,
                    force_stills=True,
                    spherical_relp=self.all_params.refinement.parameterisation.spherical_relp_model,
                )
                ref_predictor(refined_reflections)

            else:
                try:
                    refined_experiments, refined_reflections = self.refine(
                        experiments, reflections_for_refinement
                    )
                except Exception as e:
                    s = str(e)
                    if len(experiments) == 1:
                        raise DialsIndexRefineError(e.message)
                    had_refinement_error = True
                    logger.info("Refinement failed:")
                    logger.info(s)
                    del experiments[-1]
                    break

            self._unit_cell_volume_sanity_check(experiments, refined_experiments)

            self.refined_reflections = refined_reflections.select(
                refined_reflections["id"] > -1
            )

            for i, expt in enumerate(self.experiments):
                ref_sel = self.refined_reflections.select(
                    self.refined_reflections["imageset_id"] == i
                )
                ref_sel = ref_sel.select(ref_sel["id"] >= 0)
                for i_expt in set(ref_sel["id"]):
                    refined_expt = refined_experiments[i_expt]
                    expt.detector = refined_expt.detector
                    expt.beam = refined_expt.beam
                    expt.goniometer = refined_expt.goniometer
                    expt.scan = refined_expt.scan
                    refined_expt.imageset = expt.imageset

            if not (
                self.all_params.refinement.parameterisation.beam.fix == "all"
                and self.all_params.refinement.parameterisation.detector.fix == "all"
            ):
                # Experimental geometry may have changed - re-map centroids to
                # reciprocal space
                self.reflections = self._map_centroids_to_reciprocal_space(
                    self.experiments, self.reflections
                )

            # update for next cycle
            experiments = refined_experiments
            self.refined_experiments = refined_experiments

        if self.refined_experiments is None:
            raise DialsIndexRefineError("None of the experiments could refine.")

        # discard experiments with zero reflections after refinement
        id_set = set(self.refined_reflections["id"])
        if len(id_set) < len(self.refined_experiments):
            filtered_refined_reflections = flex.reflection_table()
            for i in xrange(len(self.refined_experiments)):
                if i not in id_set:
                    del self.refined_experiments[i]
            for old, new in zip(sorted(id_set), range(len(id_set))):
                subset = self.refined_reflections.select(
                    self.refined_reflections["id"] == old
                )
                subset["id"] = flex.int(len(subset), new)
                filtered_refined_reflections.extend(subset)
            self.refined_reflections = filtered_refined_reflections

        if len(self.refined_experiments) > 1:
            from dials.algorithms.indexing.compare_orientation_matrices import (
                rotation_matrix_differences,
            )

            logger.info(
                rotation_matrix_differences(self.refined_experiments.crystals())
            )

        logger.info("Final refined crystal models:")
        for i, crystal_model in enumerate(self.refined_experiments.crystals()):
            n_indexed = 0
            for i_expt in experiments.where(crystal=crystal_model):
                n_indexed += (self.reflections["id"] == i).count(True)
            logger.info("model %i (%i reflections):" % (i + 1, n_indexed))
            logger.info(crystal_model)

        if (
            "xyzcal.mm" in self.refined_reflections
        ):  # won't be there if refine_all_candidates = False and no isoforms

            self._xyzcal_mm_to_px(self.experiments, self.refined_reflections)

    def experiment_list_for_crystal(self, crystal):
        experiments = ExperimentList()
        for imageset in self.experiments.imagesets():
            experiments.append(
                Experiment(
                    imageset=imageset,
                    beam=imageset.get_beam(),
                    detector=imageset.get_detector(),
                    goniometer=imageset.get_goniometer(),
                    scan=imageset.get_scan(),
                    crystal=crystal,
                )
            )
        return experiments

    def choose_best_orientation_matrix(self, candidate_orientation_matrices):
        import copy

        logger.info("*" * 80)
        logger.info("Selecting the best orientation matrix")
        logger.info("*" * 80)

        from libtbx import group_args

        class CandidateInfo(group_args):
            pass

        candidates = []

        params = copy.deepcopy(self.all_params)

        candidate_orientation_matrices = list(candidate_orientation_matrices)

        for icm, cm in enumerate(candidate_orientation_matrices):
            if icm >= self.params.basis_vector_combinations.max_refine:
                break
            # Index reflections in P1
            sel = self.reflections["id"] == -1
            refl = self.reflections.select(sel)
            experiments = self.experiment_list_for_crystal(cm)
            self.index_reflections(experiments, refl)
            indexed = refl.select(refl["id"] >= 0)
            indexed = indexed.select(indexed.get_flags(indexed.flags.indexed))

            # If target symmetry supplied, try to apply it.  Then, apply the change of basis to the reflections
            # indexed in P1 to the target setting
            if (
                self.params.stills.refine_candidates_with_known_symmetry
                and self.params.known_symmetry.space_group is not None
            ):
                new_crystal, cb_op_to_primitive = self._symmetry_handler.apply_symmetry(
                    cm
                )
                if new_crystal is None:
                    print("Cannot convert to target symmetry, candidate %d" % (icm))
                    continue
                new_crystal = new_crystal.change_basis(
                    self._symmetry_handler.cb_op_primitive_inp
                )
                cm = candidate_orientation_matrices[icm] = new_crystal
                experiments = self.experiment_list_for_crystal(cm)

                if not cb_op_to_primitive.is_identity_op():
                    indexed["miller_index"] = cb_op_to_primitive.apply(
                        indexed["miller_index"]
                    )
                if self._symmetry_handler.cb_op_primitive_inp is not None:
                    indexed[
                        "miller_index"
                    ] = self._symmetry_handler.cb_op_primitive_inp.apply(
                        indexed["miller_index"]
                    )

            if params.indexing.stills.refine_all_candidates:
                try:
                    print(
                        "$$$ stills_indexer::choose_best_orientation_matrix, candidate %d initial outlier identification"
                        % (icm)
                    )
                    acceptance_flags = self.identify_outliers(
                        params, experiments, indexed
                    )
                    # create a new "indexed" list with outliers thrown out:
                    indexed = indexed.select(acceptance_flags)

                    print(
                        "$$$ stills_indexer::choose_best_orientation_matrix, candidate %d refinement before outlier rejection"
                        % (icm)
                    )
                    R = e_refine(
                        params=params,
                        experiments=experiments,
                        reflections=indexed,
                        graph_verbose=False,
                    )
                    ref_experiments = R.get_experiments()

                    # try to improve the outcome with a second round of outlier rejection post-initial refinement:
                    acceptance_flags = self.identify_outliers(
                        params, ref_experiments, indexed
                    )

                    # insert a round of Nave-outlier rejection on top of the r.m.s.d. rejection
                    nv0 = NaveParameters(
                        params=params,
                        experiments=ref_experiments,
                        reflections=indexed,
                        refinery=R,
                        graph_verbose=False,
                    )
                    nv0()
                    acceptance_flags_nv0 = nv0.nv_acceptance_flags
                    indexed = indexed.select(acceptance_flags & acceptance_flags_nv0)

                    print(
                        "$$$ stills_indexer::choose_best_orientation_matrix, candidate %d after positional and delta-psi outlier rejection"
                        % (icm)
                    )
                    R = e_refine(
                        params=params,
                        experiments=ref_experiments,
                        reflections=indexed,
                        graph_verbose=False,
                    )
                    ref_experiments = R.get_experiments()

                    nv = NaveParameters(
                        params=params,
                        experiments=ref_experiments,
                        reflections=indexed,
                        refinery=R,
                        graph_verbose=False,
                    )
                    crystal_model = nv()

                    # Drop candidates that after refinement can no longer be converted to the known target space group
                    if (
                        not self.params.stills.refine_candidates_with_known_symmetry
                        and self.params.known_symmetry.space_group is not None
                    ):
                        new_crystal, cb_op_to_primitive = self._symmetry_handler.apply_symmetry(
                            crystal_model
                        )
                        if new_crystal is None:
                            print(
                                "P1 refinement yielded model diverged from target, candidate %d"
                                % (icm)
                            )
                            continue

                    rmsd, _ = calc_2D_rmsd_and_displacements(
                        R.predict_for_reflection_table(indexed)
                    )
                except Exception as e:
                    print("Couldn't refine candiate %d, %s" % (icm, str(e)))
                else:
                    print(
                        "$$$ stills_indexer::choose_best_orientation_matrix, candidate %d done"
                        % (icm)
                    )
                    candidates.append(
                        CandidateInfo(
                            crystal=crystal_model,
                            green_curve_area=nv.green_curve_area,
                            ewald_proximal_volume=nv.ewald_proximal_volume(),
                            n_indexed=len(indexed),
                            rmsd=rmsd,
                            indexed=indexed,
                            experiments=ref_experiments,
                        )
                    )
            else:
                from dials.algorithms.refinement.prediction.managed_predictors import (
                    ExperimentsPredictorFactory,
                )

                ref_predictor = ExperimentsPredictorFactory.from_experiments(
                    experiments,
                    force_stills=True,
                    spherical_relp=params.refinement.parameterisation.spherical_relp_model,
                )
                rmsd, _ = calc_2D_rmsd_and_displacements(ref_predictor(indexed))
                candidates.append(
                    CandidateInfo(
                        crystal=cm,
                        n_indexed=len(indexed),
                        rmsd=rmsd,
                        indexed=indexed,
                        experiments=experiments,
                    )
                )
        if len(candidates) == 0:
            raise DialsIndexError("No suitable indexing solution found")

        print("**** ALL CANDIDATES:")
        for i, XX in enumerate(candidates):
            print("\n****Candidate %d" % i, XX)
            cc = XX.crystal
            if hasattr(cc, "get_half_mosaicity_deg"):
                print("  half mosaicity %5.2f deg." % (cc.get_half_mosaicity_deg()))
                print("  domain size %.0f Ang." % (cc.get_domain_size_ang()))
        print("\n**** BEST CANDIDATE:")

        results = flex.double([c.rmsd for c in candidates])
        best = candidates[flex.min_index(results)]
        print(best)

        if params.indexing.stills.refine_all_candidates:
            if best.rmsd > params.indexing.stills.rmsd_min_px:
                raise DialsIndexError("RMSD too high, %f" % best.rmsd)

            if (
                best.ewald_proximal_volume
                > params.indexing.stills.ewald_proximal_volume_max
            ):
                raise DialsIndexError(
                    "Ewald proximity volume too high, %f" % best.ewald_proximal_volume
                )

            if len(candidates) > 1:
                for i in xrange(len(candidates)):
                    if i == flex.min_index(results):
                        continue
                    if best.ewald_proximal_volume > candidates[i].ewald_proximal_volume:
                        print(
                            "Couldn't figure out which candidate is best; picked the one with the best RMSD."
                        )

        best.indexed["entering"] = flex.bool(best.n_indexed, False)

        return best.crystal, best.n_indexed

    def identify_outliers(self, params, experiments, indexed):
        if not params.indexing.stills.candidate_outlier_rejection:
            return flex.bool(len(indexed), True)

        print("$$$ stills_indexer::identify_outliers")
        refiner = e_refine(params, experiments, indexed, graph_verbose=False)

        RR = refiner.predict_for_reflection_table(indexed)

        px_sz = experiments[0].detector[0].get_pixel_size()

        class Match(object):
            pass

        matches = []
        for item in RR:
            m = Match()
            m.x_obs = item["xyzobs.px.value"][0] * px_sz[0]
            m.y_obs = item["xyzobs.px.value"][1] * px_sz[1]
            m.x_calc = item["xyzcal.px"][0] * px_sz[0]
            m.y_calc = item["xyzcal.px"][1] * px_sz[1]
            m.miller_index = item["miller_index"]
            matches.append(m)

        from rstbx.phil.phil_preferences import indexing_api_defs
        import iotbx.phil

        hardcoded_phil = iotbx.phil.parse(input_string=indexing_api_defs).extract()

        from rstbx.indexing_api.outlier_procedure import OutlierPlotPDF

        # comment this in if PDF graph is desired:
        # hardcoded_phil.indexing.outlier_detection.pdf = "outlier.pdf"
        # new code for outlier rejection inline here
        if hardcoded_phil.indexing.outlier_detection.pdf is not None:
            hardcoded_phil.__inject__(
                "writer", OutlierPlotPDF(hardcoded_phil.indexing.outlier_detection.pdf)
            )

        # execute Sauter and Poon (2010) algorithm
        from rstbx.indexing_api import outlier_detection

        od = outlier_detection.find_outliers_from_matches(
            matches, verbose=True, horizon_phil=hardcoded_phil
        )

        if hardcoded_phil.indexing.outlier_detection.pdf is not None:
            od.make_graphs(canvas=hardcoded_phil.writer.R.c, left_margin=0.5)
            hardcoded_phil.writer.R.c.showPage()
            hardcoded_phil.writer.R.c.save()

        return od.get_cache_status()

    def refine(self, experiments, reflections):
        acceptance_flags = self.identify_outliers(
            self.all_params, experiments, reflections
        )
        # create a new "reflections" list with outliers thrown out:
        reflections = reflections.select(acceptance_flags)

        R = e_refine(
            params=self.all_params,
            experiments=experiments,
            reflections=reflections,
            graph_verbose=False,
        )
        ref_experiments = R.get_experiments()

        # try to improve the outcome with a second round of outlier rejection post-initial refinement:
        acceptance_flags = self.identify_outliers(
            self.all_params, ref_experiments, reflections
        )

        # insert a round of Nave-outlier rejection on top of the r.m.s.d. rejection
        nv0 = NaveParameters(
            params=self.all_params,
            experiments=ref_experiments,
            reflections=reflections,
            refinery=R,
            graph_verbose=False,
        )
        nv0()
        acceptance_flags_nv0 = nv0.nv_acceptance_flags
        reflections = reflections.select(acceptance_flags & acceptance_flags_nv0)

        R = e_refine(
            params=self.all_params,
            experiments=ref_experiments,
            reflections=reflections,
            graph_verbose=False,
        )
        ref_experiments = R.get_experiments()

        nv = NaveParameters(
            params=self.all_params,
            experiments=ref_experiments,
            reflections=reflections,
            refinery=R,
            graph_verbose=False,
        )
        nv()
        rmsd, _ = calc_2D_rmsd_and_displacements(
            R.predict_for_reflection_table(reflections)
        )

        matches = R.get_matches()
        xyzcal_mm = flex.vec3_double(len(reflections))
        xyzcal_mm.set_selected(matches["iobs"], matches["xyzcal.mm"])
        reflections["xyzcal.mm"] = xyzcal_mm
        reflections.set_flags(matches["iobs"], reflections.flags.used_in_refinement)
        reflections["entering"] = flex.bool(len(reflections), False)
        return ref_experiments, reflections


""" Mixin class definitions that override the dials indexing class methods specific to stills """


class StillsIndexerKnownOrientation(IndexerKnownOrientation, StillsIndexer):
    pass


class StillsIndexerBasisVectorSearch(StillsIndexer, BasisVectorSearch):
    pass
