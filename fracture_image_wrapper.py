# -*- coding: utf-8 -*-
"""
Wrapper for FractureImage workflow
"""
import gfracture
from gfracture.fractureimage import FractureImage

# load and set output flags
sample = FractureImage('./data/handsample1.jpg')
sample.show_img()
sample.list_params()
sample.show_figures = True
sample.save_figures = True

# Denoising filter w/ parameters
sample.denoise_spatial_sd = 1
sample.denoise()

# edge detection w/ parameters
sample.sig_canny = 0.9
sample.canny_method = 'standard'
sample.detect_edges()
sample.close_gaps()

# label connected components
sample.label_edges()
sample.count_edges()

# find large edges above a minimum threshold
sample.min_large_edge_px = 10
sample.find_large_edges()

# run the probabilistic hough transform
sample.phough_min_line_length_px = 50
sample.phough_line_gap_px = 10
sample.phough_accumulator_threshold = 20
sample.run_phough_transform()

# create shapely linestrings and export
sample.convert_linestrings()
sample.export_linestrings()

