import matplotlib.pyplot as plt
from skimage import io, measure, util
from skimage.restoration import denoise_bilateral
from skimage.feature import canny
from skimage.morphology import binary_closing, square
from skimage.transform import probabilistic_hough_line
from shapely.geometry import LineString
import geopandas as gpd
from gfracture.canny import canny_std, canny_horiz
import numpy as np

class FractureImage(object):
    """A class to contain the results of fracture segmentation on 
    a core or outcrop image"""
    
    denoise_spatial_sd = 1
    canny_method = None
    sig_threshold = 0.5
    gap_fill_px = 3
    show_figures = False
    save_figures = False

    min_large_edge_px = 50
    phough_min_line_length_px = 50
    phough_line_gap_px = 10
    phough_accumulator_threshold = 100
    
    def __init__(self, filepath):
        self.img = io.imread(filepath, as_gray = True)
    
    def list_params(self):
        """ Print a list of object parameters """
        print('denoise_spatial_sd: ' + str(self.denoise_spatial_sd))
        print('sig_threshold: ' + str(self.sig_threshold))
        print('gap_fill_px: ' + str(self.gap_fill_px)) 
        print('show_figures: ' + str(self.show_figures))
        print('save_figures: ' + str(self.save_figures))
        print('canny_method: ' + str(self.canny_method))
        print('min_large_edge_px: ' + str(self.min_large_edge_px))
        print('phough_min_line_length_px: ' + str(self.phough_min_line_length_px))
        print('phough_line_gap_px: ' + str(self.phough_line_gap_px))
        print('phough_accumulator_threshold: ' + str(self.phough_accumulator_threshold))
        
    def show_img(self):
        """ Show image using io.imshow and matplotlib """
        io.imshow(self.img)
        plt.show()
    
    def denoise(self):
        """ Run a bilateral denoise on the raw image """
        print('Denoising Image')
        
        self.img_denoised = denoise_bilateral(
                self.img, sigma_spatial = self.denoise_spatial_sd, 
                multichannel=False)
        
        if self.show_figures:
            io.imshow(self.img_denoised)
            plt.show()
        
        if self.save_figures:
            io.imsave('./output/img_denoised.png',util.img_as_ubyte(self.img_denoised))
    
    def detect_edges(self):
        """ Run one of several modified Canny edge detectors on the denoised
            image.    
        """
        if self.canny_method == 'horizontal':
            print('Running Horizontal One-Way Gradient Canny Detector')
            self.img_edges = canny_horiz(self.img_denoised, self.sig_threshold)
        else: 
            print('Running Standard Canny Detector')
            self.img_edges = canny_std(self.img_denoised, self.sig_threshold)
        
        if self.show_figures:
            io.imshow(self.img_edges)
            plt.show()
        
        if self.save_figures:
            io.imsave('./output/img_edges.png',util.img_as_ubyte(self.img_edges))
            io.imsave('./output/img_edges.eps',util.img_as_ubyte(self.img_edges))
            
    def close_gaps(self):
        """ Close small holes with binary closing to within x pixels """
        
        print('Closing binary gaps')
        
        self.img_closededges = binary_closing(self.img_edges, square(self.gap_fill_px))
        
        if self.show_figures:
            io.imshow(self.img_closededges)
            plt.show()
        
        if self.save_figures:
            io.imsave('./output/img_closededges.png',util.img_as_ubyte(self.img_closededges))
            io.imsave('./output/img_closededges.eps',util.img_as_ubyte(self.img_closededges))
    
    def label_edges(self):
        """ Label connected edges/components using skimage wrapper """
        
        print('Labelling connected edges')
        
        self.img_labelled = measure.label(self.img_closededges, 
                                          connectivity=2, background=0)
        
        print(str(len(np.unique(self.img_labelled))-1) + ' components identified')
             
        if self.show_figures:
            io.imshow(self.img_labelled)
            plt.show()

        if self.save_figures:
            io.imsave('./output/img_labelled.png',util.img_as_ubyte(self.img_labelled))
            io.imsave('./output/img_labelled.eps',util.img_as_ubyte(self.img_labelled))
        
    def count_edges(self):
        """ Get a unique count of edges, omitting zero values  """       
        unique, counts = np.unique(self.img_labelled, return_counts=True)
        self.edge_dict = dict(zip(unique, counts))
        self.edge_dict.pop(0)
        
        edge_cov = sum(self.edge_dict.values()) / self.img_labelled.size * 100
        
        print(str(edge_cov) + '% edge coverage')
        
    def find_large_edges(self):
        """ Label connected edges/components using skimage wrapper """ 
        self.large_edge_dict = {k: v for k, v 
                                in self.edge_dict.items()
                                if v >= self.min_large_edge_px}
        
        large_edge_cov = len(self.large_edge_dict) / len(self.edge_dict) * 100
        
        print(str(large_edge_cov) + '% large edges')
        
        large_edge_bool = np.isin(self.img_labelled, list(self.large_edge_dict.keys()))
        
        self.img_large_edges = self.img_labelled.copy()
        self.img_large_edges[np.invert(large_edge_bool)] = 0

        if self.show_figures:
            io.imshow(self.img_large_edges)
            plt.show()

        if self.save_figures:
            io.imsave('./output/img_large_edges.png',util.img_as_ubyte(self.img_large_edges > 0))
            
    def run_phough_transform(self):
        """ Run the Probabilistic Hough Transform """
        print('Running Probabilistic Hough Transform')
        
        self.lines = probabilistic_hough_line(
                self.img_large_edges,    
                line_length=self.phough_min_line_length_px,
                line_gap=self.phough_line_gap_px,
                threshold = self.phough_accumulator_threshold)
        
        if self.show_figures:
            fig, ax = plt.subplots(1, 1)
            io.imshow(self.img_large_edges * 0)
            for line in self.lines:
                p0, p1 = line
                ax.plot((p0[0], p1[0]), (p0[1], p1[1]))
            ax.set_xlim((0, self.img_large_edges.shape[1]))
            ax.set_ylim((self.img_large_edges.shape[0], 0))
            if self.save_figures:
                plt.savefig('./output/phough_transform.pdf')
                plt.savefig('./output/phough_transform.png')
            plt.show()
            
    def convert_linestrings(self):
        """ Convert lines to geopandas linestrings """
        print('Converting linestrings')
                
        self.linestrings = (gpd.GeoSeries(map(LineString, self.lines)).
                            affine_transform([1,0,0,-1,0,0])
                            )
        
        if self.show_figures:
            self.linestrings.plot()
            if self.save_figures:
                plt.savefig('./output/linestrings.pdf')
                plt.savefig('./output/linestrings.png')
            plt.show()
            
    def export_linestrings(self):
        """ Save geopandas linestrings as shapefile """
        print('Exporting linestrings')
        
        self.linestrings.to_file("./output/linestrings.shp")
    

