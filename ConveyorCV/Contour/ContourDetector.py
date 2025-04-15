import cv2

class ContourDetector:
    @staticmethod
    def draw_contours(cam):

        cam.connect()

        # Create Background Subtractor MOG2 object
        back_sub = cv2.createBackgroundSubtractorMOG2()

        while True:
            try:
                frame = cam.get_frame()
                # Apply background subtraction
                fg_mask = back_sub.apply(frame)

                # apply global threshold to remove shadows
                retval, mask_thresh = cv2.threshold(fg_mask, 180, 255, cv2.THRESH_BINARY)

                        # set the kernel
                kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
                        # Apply erosion
                mask_eroded = cv2.morphologyEx(mask_thresh, cv2.MORPH_OPEN, kernel)

                    # Find contours
                contours, hierarchy = cv2.findContours(mask_eroded, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

                min_contour_area = 10000  # Define your minimum area threshold
                    # filtering contours using list comprehension
                large_contours = [cnt for cnt in contours if cv2.contourArea(cnt) > min_contour_area]
                frame_out = frame.copy()

                for cnt in large_contours:
                    x, y, w, h = cv2.boundingRect(cnt)
                    frame_out = cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 0, 200), 3)

                        # Display the resulting frame
                cv2.imshow("Frame_final", frame_out)

                #Press Q on keyboard to exit
                if cv2.waitKey(30) & 0xFF == ord("q"):
                    break

            except Exception as e:
                print("Exception: ", e)

        # Closes all the frames
        cv2.destroyAllWindows()
