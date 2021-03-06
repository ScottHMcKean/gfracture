# -*- coding: utf-8 -*-
import math
import numpy as np
import pandas as pd
import scipy.spatial.distance as ssd
import matplotlib.pyplot as plt
from pathlib import Path

def calc_row_idx(k, n):
    return int(math.ceil((1/2.) * (- (-8*k + 4 *n**2 -4*n - 7)**0.5 + 2*n -1) - 1))

def elem_in_i_rows(i, n):
    return i * (n - 1 - i) + (i*(i + 1))/2
    
def calc_col_idx(k, i, n):
    return int(n - elem_in_i_rows(i + 1, n) + k)

class Variogram(object):
    """A class to analyze and model experimental variograms of a 
    GeostatsDataFrame object. Based on GSLIB (Deutsch and
    Journel, 1998) and Micheal Pyrcz's GeostatsPy package"""
    
    azimuth_cw_from_ns_deg = 90
    azimuth_tolerance_deg = 45
    epsilon = 1.0e-5
    standardize_sill=False
    save_figures = True
    show_figures = True
    output_path = './output/'
    
    def __init__(self, geostats_df, val_col_str):
        self.gs_df = geostats_df
        self.val_col = val_col_str
        self.val_col_var = self.gs_df.loc[:,self.val_col].std()**2
        self.n_lags = round(self.gs_df.shape[0]/10)
        self.max_dist = max(self.gs_df.x.max(), self.gs_df.y.max())
        self.bandwidth_tolerance = self.max_dist/2
    
        self.convert_azi_tol()

    def set_output_path(self, path):
        self.output_path = path
        Path(self.output_path).mkdir(parents=True, exist_ok=True)

    def convert_azimuth(self):
        """ Mathematical azimuth is measured counterclockwise from EW and
        not clockwise from NS as the conventional azimuth """
        self.azimuth_ccw_ew_rad = (
                (90.0 - self.azimuth_cw_from_ns_deg) * math.pi / 180.0
                )
    
    def convert_azi_tol(self): 
        if self.azimuth_tolerance_deg <= 0.0:
            self.azi_tol_rad = math.cos(45.0 * math.pi / 180.0)
        else:
            self.azi_tol_rad = math.cos(self.azimuth_tolerance_deg * math.pi / 180.0)

    def set_default_lag_tolerance(self):
        self.lag_tolerance = np.diff(self.lag_bins).min()/2

    def condensed_to_square(self, k):
        i = calc_row_idx(k, len(self.gs_df))
        j = calc_col_idx(k, i, len(self.gs_df))
        return i, j

    def get_lags_wrapper(self):
        self.calculate_lags()
        self.map_values_to_lags()
        self.filter_lags_distance()
        self.lags_orig = self.lags.copy()
        
    def calculate_lags(self):
        h = ssd.squareform(ssd.pdist(self.gs_df[['x','y']])).flatten()
        x = ssd.squareform(ssd.pdist(self.gs_df[['x']], lambda u,v : u-v)).flatten()
        y = ssd.squareform(ssd.pdist(self.gs_df[['y']], lambda u,v : u-v)).flatten()
        self.lags = pd.DataFrame({'xy_dist': h, 'x_dist': x, 'y_dist': y})

    def map_values_to_lags(self):
        pairs = pd.DataFrame(
            np.transpose(np.unravel_index(list(range(0,len(self.lags))),
                (len(self.gs_df),len(self.gs_df)))
                ), columns=('pt_1','pt_2')
            )
        
        self.lags = pd.concat([self.lags.reset_index(drop=True), pairs], axis=1)
        
        self.lags['pt_1_val'] = [
                self.gs_df.loc[pt,self.val_col] for pt in self.lags.pt_1
                ]
        
        self.lags['pt_2_val'] = [
                self.gs_df.loc[pt,self.val_col] for pt in self.lags.pt_2
                ]
        
        self.lags['sq_val_diff'] = (
                (self.lags['pt_1_val'] - self.lags['pt_2_val'])**2
                )

    def filter_lags_distance(self):
        self.lags = self.lags[self.lags.xy_dist <= self.max_dist]
        self.lags = self.lags[self.lags.xy_dist > self.epsilon]
        
    def bin_lags(self):
        self.lag_bins = np.linspace(
                self.lags.xy_dist.min(), 
                self.lags.xy_dist.max(), 
                self.n_lags+2
                )[1:-1]
    
    def calculate_azimuth(self):
        self.lags['azimuth_dist'] = (
                self.lags.x_dist * math.cos(self.azimuth_ccw_ew_rad) 
                + self.lags.y_dist * math.sin(self.azimuth_ccw_ew_rad)
                ) / self.lags.xy_dist
        
        self.lags['bandwidth_dist'] = (
                math.cos(self.azimuth_ccw_ew_rad) * self.lags.y_dist 
                - math.sin(self.azimuth_ccw_ew_rad) * self.lags.x_dist
                )
    
    def filter_lags_azimuth(self):
        self.lags = self.lags[
                abs(self.lags.azimuth_dist) <= self.azi_tol_rad
                ]
        
        self.lags = self.lags[
                abs(self.lags.bandwidth_dist) <= self.bandwidth_tolerance
                ]
    
    def calc_lag_semivariance(self, lag_bin):
        lag_df = self.lags[
                    (self.lags.xy_dist >= lag_bin - self.lag_tolerance) 
                    & (self.lags.xy_dist <= lag_bin + self.lag_tolerance)
                    ]
        
        n_pairs = len(lag_df)
        
        if n_pairs == 0:
            return np.nan, 0
        
        semivariance = lag_df.sq_val_diff.sum()/(2*n_pairs)
        
        return semivariance, n_pairs
    
    def calc_omni_variogram(self):
        self.lags = self.lags_orig.copy()
        self.bin_lags()
        self.set_default_lag_tolerance()
        
        self.omni_variogram = pd.DataFrame([
                self.calc_lag_semivariance(lag_bin) 
                for lag_bin 
                in self.lag_bins
                ], columns = ('semivariance', 'n_pairs'))
        
        if self.standardize_sill:
            self.omni_variogram['semivariance'] = (
               self.omni_variogram['semivariance']
               /self.val_col_var
               )

        self.omni_variogram['lag_bin'] = self.lag_bins

    def write_omni_variogram(self):
        self.omni_variogram.to_csv(self.output_path+'omni_variogram.csv')
        
    def calc_azi_variogram(self):
        self.lags = self.lags_orig.copy()
        self.convert_azimuth()
        self.calculate_azimuth()
        self.filter_lags_azimuth()
        self.bin_lags()
        self.set_default_lag_tolerance()
        
        azi_variogram = pd.DataFrame([
                self.calc_lag_semivariance(lag_bin) 
                for lag_bin 
                in self.lag_bins
                ], columns = ('semivariance', 'n_pairs'))
        
        if self.standardize_sill:
           azi_variogram = azi_variogram/self.val_col_var

        azi_variogram['lag_bin'] = self.lag_bins
        azi_variogram['azimuth'] = self.azimuth_cw_from_ns_deg
        
        if hasattr(self, 'azi_variogram'):
            self.azi_variogram = self.azi_variogram.append(
                    azi_variogram, ignore_index=True
                    )
        else:
            self.azi_variogram = azi_variogram
    
    def write_azi_variogram(self):
        self.azi_variogram.to_csv(self.output_path+'azi_variogram.csv')
    
    def make_variogram_map(self):
        self.lags = self.lags_orig.copy()
        self.map_bin_lags()
        self.set_map_lag_tolerance()
        
        self.variogram_map = pd.DataFrame([
                self.calc_map_semivariance(x,y) 
                for x in self.map_xx[0,:] 
                for y in self.map_yy[:,0]
                ], columns = ('x','y','semivariance', 'n_pairs')).dropna()
                  
    def map_bin_lags(self):
        x_lags = np.linspace(
                self.lags.x_dist.min(), 
                self.lags.x_dist.max(), 
                self.n_lags+2
                )[1:-1]
        
        y_lags = np.linspace(
                self.lags.y_dist.min(), 
                self.lags.y_dist.max(), 
                self.n_lags+2
                )[1:-1]
        
        self.map_xx, self.map_yy = np.meshgrid(x_lags, y_lags, sparse = True)
        
    def set_map_lag_tolerance(self):
        self.map_lag_x_tol = np.diff(self.map_xx).mean()/2*1.02
        self.map_lag_y_tol = np.diff(np.transpose(self.map_yy)).mean()/2*1.02

    def calc_map_semivariance(self, x, y):
        lag_df = self.lags[
                    (self.lags.x_dist >= x - self.map_lag_x_tol) 
                    & (self.lags.x_dist <= x + self.map_lag_x_tol)
                    & (self.lags.y_dist >= y - self.map_lag_y_tol)
                    & (self.lags.y_dist <= y + self.map_lag_y_tol)
                    ]
        
        n_pairs = len(lag_df.index)
        
        if n_pairs == 0:
            return (x,y, np.nan, 0)
        
        semivariance = lag_df.sq_val_diff.sum()/(2*n_pairs)
        
        return (x, y, semivariance, n_pairs)
    
    def filt_variogram_map(self, min_points):
        self.variogram_map = self.variogram_map[
                self.variogram_map['n_pairs'] >= min_points
                ]
    
    def write_variogram_map(self):
        self.variogram_map.to_csv(self.output_path+'variogram_map.csv')
    
    def plot_variogram_map(self, lag_limit=None):

        x = self.variogram_map[['x']]
        y = self.variogram_map[['y']]
        z = self.variogram_map[['semivariance']]
        
        x_vals, x_idx = np.unique(x, return_inverse=True)
        y_vals, y_idx = np.unique(y, return_inverse=True)
        vals_array = np.empty(x_vals.shape + y_vals.shape)
        vals_array.fill(np.nan)
        vals_array[x_idx, y_idx] = np.array(z.iloc[:,0])
        z_vals = vals_array.T

        plt.contourf(x_vals,y_vals,z_vals, cmap = plt.get_cmap('plasma'))
        plt.axes().set_aspect('equal')
        plt.xlabel(r'x lag (m)')
        plt.ylabel(r'y lag (m)')
        plt.title('Variogram Map: ' + self.val_col)
        if lag_limit is not None: 
            plt.xlim([-lag_limit,lag_limit])
            plt.ylim([-lag_limit,lag_limit])
        if self.save_figures:
            plt.savefig(self.output_path+'variogram_map.pdf')
            plt.savefig(self.output_path+'variogram_map.png')
        if self.show_figures:
            plt.show()
        else:
            plt.close()
        
    def plot_npairs_map(self, lag_limit = None):

        x = self.variogram_map[['x']]
        y = self.variogram_map[['y']]
        z = self.variogram_map[['n_pairs']]
        
        x_vals, x_idx = np.unique(x, return_inverse=True)
        y_vals, y_idx = np.unique(y, return_inverse=True)
        vals_array = np.empty(x_vals.shape + y_vals.shape)
        vals_array.fill(np.nan)
        vals_array[x_idx, y_idx] = np.array(z.iloc[:,0])
        z_vals = vals_array.T
        
        plt.contourf(x_vals,y_vals,z_vals, cmap = plt.get_cmap('plasma'))
        plt.axes().set_aspect('equal')
        plt.xlabel(r'x lag (m)')
        plt.ylabel(r'y lag (m)')
        plt.title('Pairs Plot: ' + self.val_col)
        if lag_limit is not None: 
            plt.xlim([-lag_limit,lag_limit])
            plt.ylim([-lag_limit,lag_limit])
        if self.save_figures:
            plt.savefig(self.output_path+'pairs_plot.pdf')
            plt.savefig(self.output_path+'pairs_plot.png')
        if self.show_figures:
            plt.show()
        else:
            plt.close()