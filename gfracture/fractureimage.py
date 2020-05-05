from skimage import io, measure, util
from skimage.restoration import denoise_bilateral
from skimage.feature import canny
from skimage.filters import sobel, sobel_h, sobel_v, apply_hysteresis_threshold
from skimage.exposure import equalize_hist, rescale_intensity, cumulative_distribution
from skimage.morphology import binary_closing, square
from skimage.transform import probabilistic_hough_line
from skimage.segmentation import clear_border
from shapely.geometry import LineString
import matplotlib.pyplot as plt
import geopandas as gpd
import numpy as np

class FractureImage(object):
    """A class to contain the results of fracture segmentation on 
    a core or outcrop image"""
    
    denoise_spatial_sd = 0.33
    canny_edges = None
    canny_threshold = (0,1)
    gap_fill_px = 3
    min_large_edge_px = 50
    phough_min_line_length_px = 50
    phough_line_gap_px = 10
    phough_accumulator_threshold = 100
    show_figures = True
    save_figures = True
    
    def __init__(self, filepath):
        self.img_orig = io.imread(filepath, as_gray = True)
        self.img = self.img_orig.copy()
    
    def list_params(self):
        """ Print a list of object parameters """
        print('denoise_spatial_sd: ' + str(self.denoise_spatial_sd))
        print('canny_edges: ' + str(self.canny_method))
        print('canny_threshold: ' + str(self.canny_threshold))
        print('gap_fill_px: ' + str(self.gap_fill_px)) 
        print('show_figures: ' + str(self.show_figures))
        print('save_figures: ' + str(self.save_figures))
        print('min_large_edge_px: ' + str(self.min_large_edge_px))
        print('phough_min_line_length_px: ' + str(self.phough_min_line_length_px))
        print('phough_line_gap_px: ' + str(self.phough_line_gap_px))
        print('phough_accumulator_threshold: ' + str(self.phough_accumulator_threshold))
        
    def show_img(self):
        """ Show image using io.imshow and matplotlib """
        io.imshow(self.img_orig)
        plt.show(block=False)

    def equalize_img_hist(self, method = 'equalize'):
        """ Equalize or rescale image histogram """
        if method == 'rescale':
            print('Rescaling image histogram')
            self.img = rescale_intensity(
                self.img, in_range=np.percentile(self.img, (2, 98))
                )
        else:
            print('Equalizing image histogram')
            self.img = equalize_hist(self.img)

        if self.show_figures:
            self.plot_img_hist()
            plt.show(block=False)
            io.imshow(self.img)
            plt.show(block=False)

    def plot_img_hist(self, num_bins=256):
        """Plot an image along with its histogram and cumulative histogram."""
        fig,ax1 = plt.subplots()
        ax1.hist(
            self.img[(self.img>self.img.min()) & ((self.img<self.img.max()))].ravel(), 
            bins=num_bins, histtype='step', color='black'
            )
        ax2=ax1.twinx()
        img_cdf, bins = cumulative_distribution(self.img, num_bins)
        ax2.plot(bins, img_cdf, 'r')
        plt.show()

    def denoise(self):
        """ Run a bilateral denoise on the raw image """
        print('Denoising Image')

        if self.denoise_spatial_sd <= 0.15:
            print('setting denoise_spatial_sd to 0.15 (minimum value')
            self.denoise_spatial_sd = 0.15
        
        self.img = denoise_bilateral(
                self.img, sigma_spatial = self.denoise_spatial_sd, 
                multichannel=False)
        
        if self.show_figures:
            io.imshow(self.img)
            plt.show(block=False)

    def detect_edges(self, filename=None):
        """Edge filter an image using the Canny algorithm."""
        if filename is None:
            filename='./output/phough_transform'

        low = self.canny_threshold[0]*(self.img.max()-self.img.min())
        high = self.canny_threshold[1]*(self.img.max()-self.img.min())

        if self.canny_edges =='horizontal':
            print('Running One-Way Horizontal Edge Detector')
            magnitude = sobel_h(self.img).clip(min=0)
        elif self.canny_edges == 'vertical':
            print('Running One-Way Vertical Edge Detector')
            magnitude = sobel_v(self.img).clip(min=0)
        else:
            print('Running One-Way Multidirectional Edge Detector')
            magnitude = sobel(self.img).clip(min=0)
        
        self.edges = apply_hysteresis_threshold(magnitude,low,high)

        if self.show_figures:
            io.imshow(self.edges)
            plt.show(block=False)
        
        if self.save_figures:
            io.imsave(filename+'.tif',util.img_as_ubyte(self.edges))
    
    def sigma_to_mean_threshold(self, sigma):
        mean = np.mean(self.img)
        print(f"Mean: {mean:.3f}")
        lower_threshold = max(self.img.min(), mean-sigma)
        upper_threshold = min(self.img.max(), mean+sigma)
        print(f"Mean Threshold: {lower_threshold:.2f} {upper_threshold:.2f}")
        self.canny_threshold = (lower_threshold,upper_threshold)

    def sigma_to_median_threshold(self, sigma):
        median = np.median(self.img[np.nonzero(self.img)])
        print(f"Median: {median:.3f}")
        lower_threshold = max(self.img.min(), median-sigma)
        upper_threshold = min(self.img.max(), median+sigma)
        print(f"Median Threshold: {lower_threshold:.2f} {upper_threshold:.2f}")
        self.canny_threshold = (lower_threshold,upper_threshold)
        
    def close_edge_gaps(self):
        """ Close small holes with binary closing to within x pixels """
        print('Closing binary edge gaps')
        
        self.edges = binary_closing(self.edges, square(self.gap_fill_px))
        
        if self.show_figures:
            io.imshow(self.edges)
            plt.show(block=False)
        
        if self.save_figures:
            io.imsave('./output/closededges.tif',util.img_as_ubyte(self.edges))
    
    def label_edges(self):
        """ Label connected edges/components using skimage wrapper """
        print('Labelling connected edges')
        
        self.edge_labels = measure.label(
            self.edges, connectivity=2, background=0
            )
        
        print(str(len(np.unique(self.edge_labels))-1) + ' components identified')
        self.count_edges()

        if self.show_figures:
            io.imshow(self.edge_labels)
            plt.show(block=False)
        
    def count_edges(self):
        """ Get a unique count of edges, omitting zero values  """       
        unique, counts = np.unique(self.edge_labels, return_counts=True)
        self.edge_dict = dict(zip(unique, counts))
        self.edge_dict.pop(0)
        
        edge_cov = sum(self.edge_dict.values()) / self.edge_labels.size * 100
        
        print(str(edge_cov) + '% edge coverage')
            
    def run_phough_transform(self, filename=None):
        """ Run the Probabilistic Hough Transform """
        print('Running Probabilistic Hough Transform')
        if filename is None:
            filename='./output/phough_transform'
        
        self.lines = probabilistic_hough_line(
                self.edge_labels,    
                line_length=self.phough_min_line_length_px,
                line_gap=self.phough_line_gap_px,
                threshold = self.phough_accumulator_threshold)
        
        if self.show_figures | self.save_figures:
            fig, ax = plt.subplots(1, 1)
            for line in self.lines:
                p0, p1 = line
                ax.plot((p0[0], p1[0]), (p0[1], p1[1]))
            ax.set_xlim((0, self.edge_labels.shape[1]))
            ax.set_ylim((self.edge_labels.shape[0], 0))
            ax.set_aspect('equal')
            if self.save_figures:
                fig.savefig(filename+'.pdf')
                fig.savefig(filename+'.tif')
            if self.show_figures:
                plt.show(block=False)
            
    def convert_linestrings(self, filename=None):
        """ Convert lines to geopandas linestrings """
        print('Converting linestrings')
        if filename is None:
            filename='./output/linestrings'
                
        self.linestrings = (gpd.GeoSeries(map(LineString, self.lines)).
                            affine_transform([1,0,0,-1,0,0])
                            )
        
        if self.show_figures:
            self.linestrings.plot()
            if self.save_figures:
                plt.savefig(filename+'.pdf')
                plt.savefig(filename+'.tif')
            plt.show(block=False)
            
    def export_linestrings(self, filename=None):
        """ Save geopandas linestrings as shapefile """
        print('Exporting linestrings')
        if filename is None:
            filename='./output/linestrings'
        
        self.linestrings.to_file(
            filename+".shp",
            driver='ESRI Shapefile')