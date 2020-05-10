# -*- coding: utf-8 -*-
"""
Wrapper for FractureImage workflow
"""
from gfracture.fractureimage import FractureImage
import glob

files = glob.glob('./data/AC*.tif')

for filename in files:
    name = str.replace(filename,'./data\\',"")
    name = str.replace(name,".TIF","")
    # load and set output flags
    sample = FractureImage(filename)

    # Parameters
    sample.denoise_spatial_sd = 1
    sample.show_figures=False
    sample.canny_threshold = (0.2,0.4)
    sample.phough_min_line_length_px = 10
    sample.phough_line_gap_px = 10
    sample.phough_accumulator_threshold = 20
    sample.gap_fill_px=5

    sample.equalize_img_hist()
    sample.denoise()

    sample.canny_edges = 'horizontal'
    sample.detect_edges(filename='./output/'+name+'_edges_horiz')
    sample.close_edge_gaps()
    sample.label_edges()
    sample.run_phough_transform(filename='./output/'+name+'_hough_horiz')
    sample.convert_linestrings(filename='./output/'+name+'_lines_horiz')
    sample.export_linestrings(filename='./output/'+name+'_lines_horiz')

    sample.canny_edges = 'vertical'
    sample.detect_edges(filename='./output/'+name+'_edges_vert')
    sample.close_edge_gaps()
    sample.label_edges()
    sample.run_phough_transform(filename='./output/'+name+'_hough_vert')
    sample.convert_linestrings(filename='./output/'+name+'_lines_vert')
    sample.export_linestrings(filename='./output/'+name+'_lines_vert')