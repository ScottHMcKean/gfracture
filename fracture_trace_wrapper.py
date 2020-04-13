# -*- coding: utf-8 -*-
"""
Created on Thu Jan 16 09:08:26 2020

@author: scott.mckean
"""
from gfracture.fracturetrace import FractureTrace

# Initialize and load
trace = FractureTrace()
trace.show_figures = True
trace.save_figures = True
trace.limit_direction_to = 'none'
trace.load_traces('./data/linestrings.shp')
trace.load_masks('./data/side_mask.shp')
trace.scale(scale_m_px = 0.001)
trace.mask_traces()

# Generate scanlines
trace.scanline_distance_m = 0.05
trace.make_scanlines()
trace.mask_scanlines()
trace.hull_scanlines()
trace.intersect_scanlines()
trace.make_scanline_spacing_dfs()
trace.calc_scanline_stats()
trace.write_scanline_tables()

# make rolling segments along scanlines
trace.segment_width_m = 0.05
trace.segment_step_increment_m = 0.05
trace.make_segments()
trace.mask_segments()
trace.intersect_segments()
trace.calc_segment_stats()
trace.write_segment_tables()

# make rolling windows
trace.window_width_m = 0.1
trace.window_step_increment_m = 0.1
trace.make_windows()
trace.mask_windows()
trace.intersect_windows()
trace.calc_window_stats()
trace.write_window_table()