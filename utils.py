import cv2 as cv
from scipy.signal import argrelextrema, savgol_filter
import numpy as np
import matplotlib.pyplot as plt
from numba import njit, prange

def mask_image(img):
    """
    Takes image and creates an ROI of crop lane.

    Inputs:
        img: numpy array of image

    Returns:
        img:  image of same size, with non ROI pixels blacked out
    """

    height_f = img.shape[0]
    width_f = img.shape[1]
    middle_x = width_f // 2
    cv.line(img, (middle_x, 0), (middle_x, height_f), (255, 0, 0), 2)

    width = img.shape[1] 
    height = img.shape[0]
    roi_vertices = np.array([[
                (0.2*width, 0),
                (0.2*width, height),
                (0.8*width, height), 
                (0.8*width, 0)]], dtype=np.int32)
    

    mask = np.zeros_like(img)# Dynamic thresholding within ROIs_like(img)
    cv.fillPoly(mask, roi_vertices, (255, 255, 255))
    img = cv.bitwise_and(img, mask)
    return img

def binary_simple(img):
    """
    takes an image, converts to HSV, and then creates a binary image of green pixels

    Inputs:
        img: img

    Returns:
        MatLike: binary image (green sections of field)
    """

    h_low = 35
    h_upper = 85

    s_low = 50
    s_upper = 215

    v_low = 60
    v_upper = 200

    image = cv.cvtColor(img, cv.COLOR_BGR2HSV)

    binary_image = cv.inRange(
        image, (h_low, s_low, v_low), (h_upper, s_upper, v_upper))

    return binary_image

@njit(fastmath=True,cache=True)
def skidline(y1, x1, y2, x2):
    """
    given set of two points, return all points on line

    Inputs:
        y1, x1, y2, x2: points

    Returns:
        points: points on line
    """

    points = []
    dx = abs(x2 - x1)
    dy = abs(y2 - y1)
    sx = 1 if x1 < x2 else -1
    sy = 1 if y1 < y2 else -1
    err = dx - dy
    
    while True:
        points.append((y1, x1))
        if x1 == x2 and y1 == y2:

            break
        e2 = 2 * err
        if e2 > -dy:
            err -= dy
            x1 += sx
        if e2 < dx:
            err += dx
            y1 += sy
    
    return np.array(points).T

@njit(fastmath=True,cache=True,parallel=True)
def find_best_counts(binary_img):
    """
    Finds best lines for crop row detection.
    Args:
       binary_img: binarized image 

    Returns:
        best_top: top point of the best lines
        best_count: total count of all green pixels on line
    
    """
    height, width = binary_img.shape
    best_count = np.zeros(width)
    best_top = np.zeros(width)
    
    for bottom in prange(width):
        max_count = 0.0
        best_t = 0
        
        for top in range(width):
            rr, cc = skidline(height-1, bottom, 0, top)
            total = 0

            for i in range(len(rr)):
                y = int(rr[i])  
                x = int(cc[i])
                total += int(binary_img[y, x] > 0) 
            
            count = total / len(rr) if len(rr) > 0 else 0.0
            if count > max_count:
                max_count = count
                best_t = top
                
        best_count[bottom] = max_count
        best_top[bottom] = best_t
    
    return best_top, best_count


def draw_peak_lines(img, count, top, height,scale,img_original):
    """
    Filters the crop row lines to only the most relevant ones and draws the crop lines and the desired trajectory

    Inputs:
        img: resized image
        top: top point of the best lines
        count: total count of all green pixels on line
        height: height of image
        img_original: original image

    Returns:
        bottom_p: bottom point of the best lines
        top_p: top point of the best lines
    """

    peaks_array = argrelextrema(
        savgol_filter(count, 20, 5), np.greater, order=int(len(count) / 5))
    
    peaks = peaks_array[0]
    peaks_filtered = []

    if len(peaks)>=2:

        best_left = 0
        best_right = np.inf
        #filtering lines to only pick crop lines closest to robot heading
        for j in peaks:
            if j<img.shape[1]/2:
                if j>best_left:
                    best_left = j
            else:
                if j<best_right:
                    best_right = j
        peaks_filtered.append(best_left)
        peaks_filtered.append(best_right)

        #plotting crop lines
        
        for bottom_peak in peaks_filtered:
            if bottom_peak == np.inf:
                continue
            cv.line(img_original,
                (int(bottom_peak/scale), int((height - 1)/scale)),
                (int(top[int(bottom_peak)]/scale), 0),
                (0, 0, 255),
                2,)
        #plotting crop middle line
        if peaks_filtered[0] == np.inf or peaks_filtered[1] == np.inf:
            bottom_p = 0
            top_p = 0
            return bottom_p, top_p
        else:
            bottom_p_original = (((peaks_filtered[0]+peaks_filtered[1])/2))
            top_p_original = ((top[int(peaks_filtered[0])] + top[int(peaks_filtered[1])])/2)
            
            bottom_p = int(((peaks_filtered[0]+peaks_filtered[1])/2)/scale)
            top_p = int(((top[int(peaks_filtered[0])] + top[int(peaks_filtered[1])])/2)/scale)
            cv.line(img_original,(bottom_p,int((height-1)/scale)), 
            (top_p,0),(255,0,0),2)

            return bottom_p_original, top_p_original
    else:
        return 0,0
        

def calculate_error(img, bottom_p, top_p,height,scale):
    """
    Calculates the cross track error and heading error.
    Args:
       img: image
        bottom_p: bottom point of the best lines
        top_p: top point of the best lines
        height: height of image
        scale: scale of resized image

    Returns:
        cross_track_error: cross track error
        heading_error: heading error
    
    """
    cross_track_error = (img.shape[1]/2 - bottom_p/scale)
    

    height_f = img.shape[0]
    width_f = img.shape[1]
    middle_x = width_f // 2

    m1 = 0
    try:
        m2 = slope_from_points((bottom_p/scale, (height-1)/scale), (top_p/scale, 0))
    except:
        m2 = 0
    # m2 = slope_from_points((bottom_p, height-1), (top_p, 0))
    angle = angle_lines(m2,m1)
   
    heading_error = 90.0 - angle
    cross_track_error = cross_track_error
    cv.putText(img, f"Cross Track Error: {(cross_track_error):.2f}", (10, height - 30), cv.FONT_HERSHEY_SIMPLEX, 0.6, (0,0,0), 2)
    cv.putText(img, f"Heading Error: {heading_error:.2f}", (10, height - 10), cv.FONT_HERSHEY_SIMPLEX, 0.6, (0,0,0), 2)
    return cross_track_error, (90-angle)

def angle_lines(m1,m2):
    """
    Calculates the angle between two lines given their slopes.

    Inputs:
        m1: Slope of the first line.
        m2: Slope of the second line.

    Returns:
        The angle between the lines in degrees.
    """
    angle_rad = np.arctan(abs((m2 - m1) / (1 + m1 * m2)))
    angle_deg = np.degrees(angle_rad)
    return angle_deg


def slope_from_points(point1, point2):
    """Calculates the slope of a line given two points."""
    x1, y1 = point1
    x2, y2 = point2
    return (y2 - y1) / (x2 - x1)


