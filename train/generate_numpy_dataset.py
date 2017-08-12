#!/usr/bin/env python3

import cv2
import numpy as np
import os
import pickle
import sys
import srperm as srp

def main():
    target_size = (128, 32)

    # Output labels
    thumbs_out = []
    labels_out = []
    
    name = sys.argv[1]
    perturb = not (name[0] == '_')
    folders = sys.argv[2:]
    for folder in folders:

        # Prepare timestamps and labels
        timestamps = []
        labels = []
        csv_path = os.path.join(folder, 'video.csv')
        with open(csv_path) as f:
            headers = f.readline()
            for row in f:
                timestamp, speed, nn_speed, steer, nn_steer = row.split(",")
                timestamps.append([float(timestamp)])
                labels.append((float(speed), float(steer)))
        timestamps = np.array(timestamps, dtype=np.double)
        labels = np.array(labels, dtype=np.float32)

        # Prepare video frames by extracting the patch and thumbnail for training
        video_path = os.path.join(folder, 'video.mp4')
        video_cap = cv2.VideoCapture(video_path)
        counter = 0
        while video_cap.isOpened() and counter < len(labels):

            # Get the frame
            ret, frame = video_cap.read()
            if not ret: break

            # Handle multiple video sizes
            frame_height, frame_width, frame_depth = frame.shape
            if frame_width == 1920 and frame_height == 1080:
                frame = cv2.resize(frame, (240, 135))
                frame_height, frame_width, frame_depth = frame.shape
                crop_size = frame_width * 3 // 4, frame_height * 1 // 3
            elif frame_width == 640 and frame_height == 480:
                frame = cv2.resize(frame, (160, 120))
                frame_height, frame_width, frame_depth = frame.shape
                crop_size = frame_width, frame_height * 1 // 3
            else:
                print("Unknown frame size", frame.size)
                return
            crop_x = (frame_width - crop_size[0]) // 2
            crop_y = frame_height - crop_size[1]
            
            # Perturb if we got a wide enough image
            if perturb and frame_width / frame_height > 1.5:
                drot = max(min(np.random.normal(0, 3), 10), -10)
                mshift = max(min(np.random.normal(0, 0.1), 1), -1)
                pframe = srp.shiftimg(frame, drot, mshift)
                patch = pframe[crop_y : crop_y + crop_size[1], crop_x : crop_x + crop_size[0], :]
                thumb = cv2.resize(patch, target_size)
                speed = labels[counter][0]
                steer = srp.shiftsteer(labels[counter][1], drot, mshift)
                labels_out.append([speed, steer])
                thumbs_out.append(thumb)

            # Store original too
            patch = frame[crop_y : crop_y + crop_size[1], crop_x : crop_x + crop_size[0], :]
            thumb = cv2.resize(patch, target_size)
            speed = labels[counter][0]
            steer = labels[counter][1]
            labels_out.append([speed, steer])
            thumbs_out.append(thumb)
            
            counter += 1
            print("%.2f\r" % (100.0 * counter / len(labels)), end='')
        print("Done [%i] %s"  % (counter, folder))

        # Clean up
        video_cap.release()

    # Store output
    thumbs_out = np.array(thumbs_out, dtype=np.uint8)
    labels_out = np.array(labels_out, dtype=np.float32)

    # store pickles
    print("Storing ", thumbs_out.shape, labels_out.shape)
    with open("../data/%s.pkl" % name, 'wb') as f:
        pickle.dump((thumbs_out, labels_out), f, protocol=pickle.HIGHEST_PROTOCOL)
        
if __name__ == "__main__":
    main()
