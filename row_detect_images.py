from multiprocessing import process
import cv2 as cv
import random
from utils import binary_simple, find_best_counts, draw_peak_lines, mask_image, calculate_error
import numpy as np
import time
import os

scale = 0.1

file_dir = "Data/Images/"

results_dir = os.path.join("Data", "Results")
if not os.path.exists(results_dir):
    os.makedirs(results_dir)



def process_image(frame):
    img = cv.resize(frame, (0, 0), fx=scale, fy=scale)
    img_resize = img
    img = mask_image(img)
    binary_img = binary_simple(img)
    
    
    (height, width) = binary_img.shape[:2]

    
    top, count = find_best_counts(binary_img)

    if top.size != 0 or count.size != 0:
        bottom_p, top_p = draw_peak_lines(img_resize, count, top, height, scale,frame)
        cross_track_error, heading_error = calculate_error(frame, bottom_p, top_p, height,scale)
        print(f"Cross Track Error: {cross_track_error}, Heading Error: {heading_error}")


    middle_x = frame.shape[1] // 2
    cv.line(frame, (middle_x, 0), (middle_x, frame.shape[0]), (0, 255, 0), 2)

    return frame, binary_img

def main(filename,display = True):
    img_original = cv.imread(f"{file_dir}/{filename}")
    img_original,binary_img = process_image(img_original)
    if display==True:
        cv.imshow("Display window", img_original)



        k = cv.waitKey(0)
    else:
        cv.imwrite(f"Data/Results/{filename}",img_original)

if __name__ == "__main__":
    image_list = os.listdir(file_dir)
    #uncomment this line if you want to process only one image

    # main("Reference.png",display=True)


    #comment this loop if you want to process only one image
    
    for filename in image_list:
        print(filename)
        main(filename,display=False)

    
    