import cv2 as cv
import random
from utils import binary_simple, find_best_counts, draw_peak_lines, mask_image, calculate_error
import numpy as np
import time
import os

scale = 0.1
file_dir = "Data/Videos/"  # Directory containing video files

def process_frame(frame):
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

def main(video_filename):
    cap = cv.VideoCapture(f"{file_dir}/{video_filename}")

    if not cap.isOpened():
        print(f"Error: Could not open video file {video_filename}")
        return

    frame_width = int(cap.get(cv.CAP_PROP_FRAME_WIDTH))
    frame_height = int(cap.get(cv.CAP_PROP_FRAME_HEIGHT))

    out = cv.VideoWriter(f'output_{video_filename}', cv.VideoWriter_fourcc(*'XVID'), 20.0, (frame_width, frame_height))

    count = 0
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        a = time.time()
        frame, binary_frame = process_frame(frame)
        fps = 1 / (time.time() - a)
        print(f"fps: {fps}")
        count = 0

        cv.putText(frame, f"FPS: {fps:.2f}", (10, 30), cv.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2, cv.LINE_AA)

        cv.imshow("Processed Frame", frame)
        # cv.imshow("Binary Frame", binary_frame)

        out.write(frame)

        if cv.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    out.release()
    cv.destroyAllWindows()

if __name__ == "__main__":
    video_list = os.listdir(file_dir)
    for video_filename in video_list:
        print(video_filename)
        main(video_filename)
