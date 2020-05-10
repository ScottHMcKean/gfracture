import numpy as np
import pandas as pd
from scipy.stats import norm, rankdata
from scipy import spatial

class GeostatsDataFrame(object):
    """A class to load an transform a table of xy + feature values into
    a compliant dataframe for variogram calculations"""
    
    coord_cols = {'x':'x', 'y':'y'}
    random_seed = np.random.seed(73073)
    nscore_epsilon = 1.0e-20
    
    def __init__(self, filepath = None, pd_df = None):
        if filepath is not None:
            self.input = pd.read_csv(filepath)
        
        if pd_df is not None:
            self.input = pd_df
        
        self.input.columns = (
            self.input.columns
            .str.strip()
            .str.lower()
            .str.replace(' ', '_')
            .str.replace('(', '')
            .str.replace(')', '')
            )

        print(self.input.head())
        
    def set_coords(self, coord_tuple):
        """
        Input a string tuple to set the coord_cols dictionary with 
        a minimum value of zero for 'x' and 'y'
        """
        self.coord_cols['x'] = coord_tuple[0]
        self.input['x'] = self.input[coord_tuple[0]] - self.input[coord_tuple[0]].min() 
        self.coord_cols['y'] = coord_tuple[1]
        self.input['y'] = self.input[coord_tuple[1]] - self.input[coord_tuple[1]].min() 
        print('Coordinate Columns:')
        print(self.input[['x','y']].head())
        
    def set_features(self, feature_list):
        """Input a list of strings corresponding to desired feature columns"""
        self.feature_cols = feature_list
        print('Feature Columns')
        print(self.input.loc[:,self.feature_cols].head())
        
    def z_scale_feats(self):
        feat_df = self.input[self.feature_cols].dropna()
        
        # z-score transform
        scaled_df = (feat_df - feat_df.mean())/feat_df.std()
        scaled_df.columns = 'z_' + scaled_df.columns
        self.zscore_cols = list(scaled_df.columns)
        self.zscore_mean = np.array(feat_df.mean())
        self.zscore_sd = np.array(feat_df.std())
        
        try:
            self.output = pd.merge(
                self.output, scaled_df, how='left', 
                left_index = True, right_index = True
                )
        except:
            self.output = pd.merge(
                self.input, scaled_df, how='left', 
                left_index = True, right_index = True
                )
        
        print('Created Z-score scaled features')
        print(self.output[self.zscore_cols].head())
        
    def n_transform_feats(self):
        """ N-score transform using van der Waerden's method (Conover, 1999)"""
        feat_df = self.input[self.feature_cols].dropna()
        
        norm_df = feat_df.apply(lambda x : norm.ppf(rankdata(x)/(len(x) + 1)))     
        norm_df.columns = 'n_' + norm_df.columns
        self.nscore_cols = list(norm_df.columns)
        self.nscore_scores = feat_df.apply(lambda x : rankdata(x)/(len(x) + 1))
        self.nscore_factor = np.array(
            feat_df.apply(lambda x: x/norm_df['n_' + x.name])
            )
        try:
            self.output = pd.merge(
                self.output, norm_df, how='left', 
                left_index = True, right_index = True
                )
        except:
            self.output = pd.merge(
                self.input, norm_df, how='left', 
                left_index = True, right_index = True
                )
        
        print('Created N-score transformed features')
        print(self.output[self.nscore_cols].head())