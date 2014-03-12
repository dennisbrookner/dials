/*
 * flex_reflection_table.cc
 *
 *  Copyright (C) 2013 Diamond Light Source
 *
 *  Author: James Parkhurst
 *
 *  This code is distributed under the BSD license, a copy of which is
 *  included in the root directory of this package.
 */
#include <boost/python.hpp>
#include <boost/python/def.hpp>
#include <dials/array_family/boost_python/flex_table_suite.h>
#include <dials/array_family/reflection_table.h>
#include <dials/model/data/shoebox.h>
#include <dials/model/data/observation.h>
#include <scitbx/array_family/tiny_types.h>
#include <scitbx/array_family/ref_reductions.h>
#include <scitbx/vec3.h>
#include <scitbx/vec2.h>
#include <cctbx/miller.h>

namespace dials { namespace af { namespace boost_python {

  using namespace boost::python;
  using scitbx::vec2;
  using scitbx::vec3;
  using scitbx::af::int6;
  using flex_table_suite::flex_table_wrapper;
  using dials::model::Shoebox;
  using dials::model::Observation;

  /**
   * Construct a reflection table from a list of observations and shoeboxes
   * @param o The observation
   * @param s The shoeboxes
   * @returns A reflection table
   */
  template <typename T>
  T* make_from_observation_and_shoebox(
      const af::const_ref<Observation> &o,
      const af::const_ref< Shoebox<double> > &s) {
    DIALS_ASSERT(o.size() == s.size());

    // The reflection table
    T result(o.size());
    af::shared<std::size_t>    panel  = result["panel"];
    af::shared< vec3<double> > xyzval = result["xyzobs.px.value"];
    af::shared< vec3<double> > xyzvar = result["xyzobs.px.variance"];
    af::shared<double>         iraw   = result["intensity.raw.value"];
    af::shared<double>         irawv  = result["intensity.raw.variance"];
    af::shared<double>         icor   = result["intensity.cor.value"];
    af::shared<double>         icorv  = result["intensity.cor.variance"];
    af::shared<int6>           bbox   = result["bbox"];
    af::shared< Shoebox<> >    sbox   = result["shoebox"];

    // Copy all the values
    for (std::size_t i = 0; i < result.nrows(); ++i) {

      // Check panel numbers
      DIALS_ASSERT(o[i].panel == s[i].panel);
      panel[i] = o[i].panel;

      // Copy observation info
      xyzval[i] = o[i].centroid.px.position;
      xyzvar[i] = o[i].centroid.px.std_err_sq;
      iraw[i]   = o[i].intensity.observed.value;
      irawv[i]  = o[i].intensity.observed.variance;
      icor[i]   = o[i].intensity.corrected.value;
      icorv[i]  = o[i].intensity.corrected.variance;

      // Copy shoebox info
      bbox[i] = s[i].bbox;
      sbox[i].bbox = s[i].bbox;
      sbox[i].data = s[i].data;
      sbox[i].mask = s[i].mask;
      sbox[i].background = s[i].background;
    }

    // Return the new reflection table
    return new T(result);
  }

  /**
   * A function to print some help about keys
   */
  template <typename T>
  std::string help_keys(const T &self) {
    std::string result =
      "Standard column names:\n"
      "======================\n"
      "\n"
      " Columns in the reflection table can have any name and type;\n"
      " however, it is helpful to have a set of standard data columns\n"
      " which can be used by different algorithms. These are shown below.\n"
      "\n"
      " General properties\n"
      " ------------------\n"
      "\n"
      "  flags:                  bit mask status flags\n"
      "  id:                     experiment id\n"
      "  panel:                  the detector panel index\n"
      "\n"
      " Predicted properties\n"
      " --------------------\n"
      "\n"
      "  miller_index:           miller indices\n"
      "  entering:               reflection entering/exiting\n"
      "  s1:                     the diffracted beam vector\n"
      "  xyzcal.mm:              the predicted location (mm, mm, rad)\n"
      "  xyzcal.px:              the predicted location (px, px, frame)\n"
      "  ub_matrix:              predicted crystal setting\n"
      "\n"
      " Observed properties\n"
      " -------------------\n"
      "\n"
      "  xyzobs.px.value:        centroid pixel position\n"
      "  xyzobs.px.variance:     centroid pixel variance\n"
      "  xyzobs.mm.value:        centroid millimetre position\n"
      "  xyzobs.mm.variance:     centroid millimetre variance\n"
      "  intensity.raw.value:    raw intensity value\n"
      "  intensity.raw.variance: raw intensity variance\n"
      "  intensity.cor.value:    corrected intensity value\n"
      "  intensity.cor.variance: corrected intensity variance\n"
      "\n"
      " Shoebox properties\n"
      " ------------------\n"
      "\n"
      "  bbox:                   bounding box\n"
      "  shoebox:                shoebox data/mask/background struct\n"
      "\n"
      ;
    return result;
  }

  /**
   * Do ray intersections for all items
   */
  template <typename T>
  af::shared< vec2<double> > compute_ray_intersections(
      const T &self, const model::Detector &detector) {
    af::shared< vec2<double> > result(self.nrows());
    af::const_ref< vec3<double> > s1 =
      self.template get< vec3<double> >("s1").const_ref();
    af::const_ref< std::size_t > panel =
      self.template get< std::size_t >("panel").const_ref();
    for (std::size_t i = 0; i < result.size(); ++i) {
      result[i] = detector[panel[i]].get_ray_intersection(s1[i]);
    }
    return result;
  }

  /**
   * Get where the flag value is set
   */
  template <typename T>
  af::shared<bool> get_flags(const T &self, std::size_t value) {
    af::shared<bool> result(self.nrows());
    af::shared<std::size_t> flags = self.template get<std::size_t>("flags");
    for (std::size_t i = 0; i < result.size(); ++i) {
      result[i] = (flags[i] & value) == value;
    }
    return result;
  }

  /**
   * Set the flags.
   */
  template <typename T>
  void set_flags(T self, const af::const_ref<bool> mask, std::size_t value) {
    DIALS_ASSERT(mask.size() == self.nrows());
    af::shared<std::size_t> flags = self.template get<std::size_t>("flags");
    for (std::size_t i = 0; i < mask.size(); ++i) {
      if (mask[i]) {
        flags[i] |= value;
      }
    }
  }

  /**
   * Unset the flags.
   */
  template <typename T>
  void unset_flags(T self, const af::const_ref<bool> mask, std::size_t value) {
    DIALS_ASSERT(mask.size() == self.nrows());
    af::shared<std::size_t> flags = self.template get<std::size_t>("flags");
    for (std::size_t i = 0; i < mask.size(); ++i) {
      if (mask[i]) {
        flags[i] &= ~value;
      }
    }
  }

  /**
   * Struct to facilitate wrapping reflection table type
   */
  template <typename T>
  struct flex_reflection_table_wrapper : public flex_table_wrapper<T> {

    typedef flex_table_wrapper<T> base_type;
    typedef typename base_type::flex_types flex_types;
    typedef typename base_type::flex_table_type flex_table_type;
    typedef typename base_type::class_type class_type;

    /**
     * Wrap the reflection table class
     */
    static
    class_type wrap(const char *name) {

      // Wrap with flex table bindings
      class_type result = base_type::wrap(name);

      // Add functions
      result
        .def("__init__", make_constructor(
          &make_from_observation_and_shoebox<flex_table_type>))
        .def("help_keys",
          &help_keys<flex_table_type>)
        .def("compute_ray_intersections",
          &compute_ray_intersections<flex_table_type>)
        .def("get_flags",
          &get_flags<flex_table_type>)
        .def("set_flags",
          &set_flags<flex_table_type>)
        .def("unset_flags",
          &unset_flags<flex_table_type>)
        ;

      // Create the flags enum in the reflection table scope
      scope in_table = result;
      enum_<Flags>("flags")
        .value("predicted", Predicted)
        .value("observed", Observed)
        .value("indexed", Indexed)
        .value("used_in_refinement", UsedInRefinement)
        .value("reference_spot", ReferenceSpot)
        .value("integrated", Integrated);

      // return the wrapped class
      return result;
    }
  };

  void export_flex_reflection_table() {

    // Define all the types we want to support in the table
    typedef reflection_table::mapped_type flex_types;

    // Export the reflection table
    flex_reflection_table_wrapper<flex_types>::wrap("reflection_table");
  }

}}} // namespace dials::af::boost_python
