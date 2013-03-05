#!/usr/bin/env python
#
# predict_spots.py
#
#  Copyright (C) 2013 Diamond Light Source
#
#  Author: James Parkhurst
#
#  This code is distributed under the BSD license, a copy of which is
#  included in the root directory of this package.
from __future__ import division

def print_ub_matrix(UB):
    '''Print the UB matrix to stdout.'''
    print "UB Matrix:"
    print "    (({0}, {1}, {2}),".format(UB[0], UB[1], UB[2])
    print "     ({0}, {1}, {2}),".format(UB[3], UB[4], UB[5])
    print "     ({0}, {1}, {2}))".format(UB[6], UB[7], UB[8])

def print_call_info(callback, info, result_type):
    '''Call a function and print basic info about the time it took to run the
    function and the number of output elements.'''
    from time import time
    print ""
    print info + ":"
    start_time = time()
    result = callback()
    time_taken = time() - start_time
    print "{0} {1} in {2} s".format(len(result), result_type, time_taken)
    return result

def print_reflection_stats(reflections):
    '''Print some reflection statistics.'''
    import numpy

    # Get the stats
    num_reflections = len(reflections)
    shoeboxes = [r.shoebox for r in reflections]

    # Calculate the min, max, mean pixels in shoebox
    shoebox_count = [(s[1]-s[0])*(s[3]-s[2])*(s[5]-s[4]) for s in shoeboxes]
    min_shoebox_size = numpy.min(shoebox_count)
    max_shoebox_size = numpy.max(shoebox_count)
    med_shoebox_size = int(numpy.median(shoebox_count))

    # Calculate the mib, max, mean fast range of shoebox
    shoebox_fast_range = [s[1] - s[0] for s in shoeboxes]
    min_shoebox_fast_range = numpy.min(shoebox_fast_range)
    max_shoebox_fast_range = numpy.max(shoebox_fast_range)
    med_shoebox_fast_range = int(numpy.median(shoebox_fast_range))

    # Calculate the mib, max, mean slow range of shoebox
    shoebox_slow_range = [s[3] - s[2] for s in shoeboxes]
    min_shoebox_slow_range = numpy.min(shoebox_slow_range)
    max_shoebox_slow_range = numpy.max(shoebox_slow_range)
    med_shoebox_slow_range = int(numpy.median(shoebox_slow_range))

    # Calculate the mib, max, mean frame range of shoebox
    shoebox_frame_range = [s[5] - s[4] for s in shoeboxes]
    min_shoebox_frame_range = numpy.min(shoebox_frame_range)
    max_shoebox_frame_range = numpy.max(shoebox_frame_range)
    med_shoebox_frame_range = int(numpy.median(shoebox_frame_range))

    # Print the stats
    print "Num reflections:", num_reflections
    print "Max shoebox element count: ", max_shoebox_size
    print "Min shoebox element count: ", min_shoebox_size
    print "Median shoebox element count: ", med_shoebox_size
    print "Max shoebox fast range: ", max_shoebox_fast_range
    print "Min shoebox fast range: ", min_shoebox_fast_range
    print "Median shoebox fast range: ", med_shoebox_fast_range
    print "Max shoebox slow range: ", max_shoebox_slow_range
    print "Min shoebox slow range: ", min_shoebox_slow_range
    print "Median shoebox slow range: ", med_shoebox_slow_range
    print "Max shoebox frame range: ", max_shoebox_frame_range
    print "Min shoebox frame range: ", min_shoebox_frame_range
    print "Median shoebox frame range: ", med_shoebox_frame_range

def predict_spots(input_filename, num_frames, verbose):
    """Read the required data from the file, predict the spots and display."""

    from dials.algorithms.spot_prediction import IndexGenerator
    from dials.algorithms.spot_prediction import RayPredictor
    from dials.algorithms.spot_prediction import ray_intersection
    from dials.algorithms.spot_prediction import reflection_frames
    from dials.algorithms.integration import ShoeboxCalculator
    from iotbx.xds import xparm
    from dials.util import io
    from math import pi
    import dxtbx

    # Read the models from the input file
    print "Reading: \"{0}\"".format(input_filename)
    models = dxtbx.load(input_filename)
    beam = models.get_beam()
    detector = models.get_detector()
    gonio = models.get_goniometer()
    scan = models.get_scan()
    first_image = scan.get_image_range()[0]
    image_range = (first_image, first_image + num_frames)
    scan.set_image_range(image_range)

    # Read other data (need to assume an XPARM file
    xparm_handle = xparm.reader()
    xparm_handle.read_file(input_filename)
    UB = io.get_ub_matrix_from_xparm(xparm_handle)
    unit_cell = io.get_unit_cell_from_xparm(xparm_handle)
    space_group = io.get_space_group_type_from_xparm(xparm_handle)
    d_min = detector.get_max_resolution_at_corners(
        beam.get_direction(), beam.get_wavelength())
    # Load the image volume from the CBF files and set the number of frames
#    if cbf_path:
#        print "Loading CBF files"
#        image_volume = pycbf_extra.search_for_image_volume(cbf_search_path)
#        scan.image_range = (scan.image_range[0],
#            scan.image_range[0] + image_volume.shape[0] - 1)

    # Print the model data
    print ""
    print beam
    print detector
    print gonio
    print scan
    print "Resolution: ", d_min
    print ""
    print_ub_matrix(UB)

    # Create the index generator
    generate_indices = IndexGenerator(unit_cell, space_group, d_min)

    # Create the spot predictor
    predict_rays = RayPredictor(beam.get_s0(), gonio.get_rotation_axis(), UB,
                                scan.get_oscillation_range())

    # Generate Indices
    miller_indices = print_call_info(generate_indices.to_array,
        "Generating miller indices", "miller indices")

    # Predict reflections
    reflections = print_call_info(lambda: predict_rays(miller_indices),
        "Predicting rays", "reflections")

    # Get detector coordinates (mm)
    reflections = print_call_info(
        lambda: ray_intersection(detector, reflections),
        "Calculating detector coordinates", "coordinates")

    # Calculate the frame numbers of all the reflections
    reflections = print_call_info(
        lambda: reflection_frames(scan, reflections),
        "Calculating frame numbers", "frames")

    # Set the divergence and mosaicity
    n_sigma = 5.0
    delta_divergence = n_sigma * 0.016 * pi / 180.0
    delta_mosaicity = n_sigma * 0.008 * pi / 180.0

    # Create the shoebox calculator
    calculate_shoebox = ShoeboxCalculator(beam, detector, gonio, scan,
        delta_divergence, delta_mosaicity)

    # Calculate the frame numbers of all the reflections
    reflections = print_call_info(
        lambda: (calculate_shoebox(reflections), reflections)[1],
        "Calculating shoeboxes", "shoeboxes")

    # Print some reflection statistics
    print_reflection_stats(reflections)

if __name__ == '__main__':

    from optparse import OptionParser

    # Specify the command line options
    usage = "usage: %prog [options] /path/to/GXPARM.XDS"
    parser = OptionParser(usage)

    # Add a verbose option (False by default)
    parser.add_option('-v', action="store_true", dest="verbose", default=False,
                      help='Print out reflection details (default = False)')

    # Parse the arguments
    (options, args) = parser.parse_args()

    # Print help if no arguments specified, otherwise call spot prediction
    if len(args) == 0:
        print parser.print_help()
    else:
        predict_spots(args[0], 4000, options.verbose)
