# -*- coding: utf-8 -*-
"""
Wrapper for FractureImage workflow
"""
from gfracture.fractureimage import FractureImage

filename = 'AC1_02'

# load and set output flags
sample = FractureImage('./data/'+filename+'.TIF')

# Equalize exposure
sample.equalize_img_hist()

# Denoising filter w/ parameters
sample.denoise_spatial_sd = 1
sample.canny_threshold = (0.2,0.4)
sample.phough_min_line_length_px = 10
sample.phough_line_gap_px = 10
sample.phough_accumulator_threshold = 20

sample.denoise()

# edge detection w/ parameters 0.1, 0.3, 0.5, 0.7, 0.9
sample.canny_edges = 'horizontal'
sample.sigma_to_median_threshold(sigma=0.1)
sample.canny_threshold=tuple(map(lambda i, j: i - j, sample.canny_threshold, (0.2,0.2)))
sample.detect_edges(filename='./output/'+filename)
sample.gap_fill_px=5
sample.close_edge_gaps()

# label connected components
sample.label_edges()

# run the probabilistic hough transform

sample.run_phough_transform(filename='./output/hough_vert')

# create shapely linestrings and export
sample.convert_linestrings(filename='./output/lines_vert')
sample.export_linestrings(filename='./output/lines_vert')

