# -*- coding: utf-8 -*-
"""
Wrapper for FractureImage workflow
"""
from gfracture.fractureimage import FractureImage
import numpy as np
import skimage.exposure as exposure

# load and set output flags
sample = FractureImage('./data/pavement2.png')
sample.show_img()
sample.list_params()
sample.show_figures = False
sample.save_figures = True

# Denoising filter w/ parameters
sample.denoise_spatial_sd = 1
sample.denoise()

# edge detection w/ parameters 0.1, 0.3, 0.5, 0.7, 0.9
sample.canny_method = 'horizontal'
sample.sigma_to_mean_threshold(sigma=0.1)
sample.sigma_to_median_threshold(sigma=0.1)
sample.canny_threshold = (0.21,0.31)
sample.detect_edges()
sample.close_gaps()

# label connected components
sample.label_edges()
sample.count_edges()

# run the probabilistic hough transform
sample.show_figures = True
sample.save_figures = True
sample.phough_min_line_length_px = 25
sample.phough_line_gap_px = 50
sample.phough_accumulator_threshold = 500
sample.run_phough_transform()

# create shapely linestrings and export
sample.convert_linestrings()
sample.export_linestrings()

