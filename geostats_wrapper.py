# -*- coding: utf-8 -*-
"""
Created on Thu Jan 16 09:08:26 2020

@author: scott.mckean
"""
from gfracture import GeostatsDataFrame, Variogram
from scipy.stats import rankdata, norm
import scipy.spatial.distance as ssd
import matplotlib.pyplot as plt

# Initialize Geostats DataFrame
gs_df = GeostatsDataFrame(filepath = './data/windows_filtered_75_SouthWall_5+5.csv')
gs_df.set_coords(['x_coord','y_coord'])
gs_df.set_features(['p21_masked', 'p20_masked'])
gs_df.z_scale_feats()
gs_df.n_transform_feats()

# Initialize a Variogram Object and calculate lags for everything
vgm = Variogram(gs_df.output, 'p21_masked')
vgm.get_lags_wrapper()

# get omni semivariogram
vgm.calc_omni_variogram()
vgm.omni_variogram.plot('lag_bin','semivariance','scatter')
vgm.write_omni_variogram()

# get azimuth semivariogram for multiple azimuths
for azimuth in [0, 22.5, 45, 67.5, 90]:
    vgm.azimuth_cw_from_ns_deg = azimuth
    vgm.calc_azi_variogram()
    vgm.azi_variogram[
        vgm.azi_variogram.azimuth == azimuth
        ].plot('lag_bin','semivariance','scatter')
    plt.title(azimuth)
    plt.show()
    
vgm.write_azi_variogram()

# get variogram map
vgm.make_variogram_map()
vgm.filt_variogram_map(min_points = 1)
vgm.plot_variogram_map(lag_limit = 1)
vgm.plot_npairs_map(lag_limit = 1)
vgm.write_variogram_map()
