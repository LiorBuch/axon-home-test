from multiprocessing import Event, Process, Queue, queues
import signal
import sys
import imutils
import cv2

POISON_PILL = "EOF"


class Detector(Process):
    def __init__(self, in_queue: Queue, out_queue: Queue, shutdown_event: Event):
        super().__init__()
        self.in_queue = in_queue
        self.out_queue = out_queue
        self.shutdown_event = shutdown_event

    def run(self):

        def local_sigint_handler(signum, frame):
            print("[Detector] SIGINT intercepted. Cleaning up Detector.")
            self.shutdown_event.set()
            sys.exit(0)

        signal.signal(signal.SIGINT, local_sigint_handler)

        counter = 0
        prev_frame = None

        while not self.shutdown_event.is_set():
            try:
                data = self.in_queue.get(timeout=0.1)
            except queues.Empty:
                continue

            # graceful shutdown hook.
            if data == POISON_PILL:
                try:
                    self.out_queue.put(POISON_PILL, timeout=0.5)
                except queues.Full:
                    pass
                break

            frame, fps = data
            detections = []  # bounding box tuples: (x, y, w, h).
            gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

            if counter == 0:
                prev_frame = gray_frame
                counter += 1
            else:
                diff = cv2.absdiff(gray_frame, prev_frame)
                thresh = cv2.threshold(diff, 25, 255, cv2.THRESH_BINARY)[1]
                thresh = cv2.dilate(thresh, None, iterations=2)
                cnts = cv2.findContours(
                    thresh.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
                )
                cnts = imutils.grab_contours(cnts)

                # extract coordinates from contours for bounding boxes.
                for c in cnts:
                    # Optional optimization: filter out tiny noise contours if desired.
                    # if cv2.contourArea(c) < 500: continue
                    (x, y, w, h) = cv2.boundingRect(c)
                    detections.append((x, y, w, h))

                prev_frame = gray_frame
                counter += 1

            # send the unmodified frame, detections list, and fps to the viewer.
            try:
                self.out_queue.put((frame, detections, fps), timeout=0.1)
            except queues.Full:
                continue

        print("[Detector] Exited cleanly.")
