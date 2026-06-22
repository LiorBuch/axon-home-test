import logging
import signal
import sys
import cv2
from multiprocessing import Event, Process, Queue, queues
import time

from pipeline_components.logging_config import configure_logging

POISON_PILL = "EOF"

log = logging.getLogger(__name__)


class Viewer(Process):
    def __init__(self, in_queue: Queue, shutdown_event: Event):
        super().__init__()
        self.in_queue = in_queue
        self.shutdown_event = shutdown_event

    def run(self):
        configure_logging()

        def local_sigint_handler(signum, frame):
            log.info("SIGINT intercepted, destroying UI windows.")
            cv2.destroyAllWindows()
            self.shutdown_event.set()
            sys.exit(0)

        signal.signal(signal.SIGINT, local_sigint_handler)

        cv2.namedWindow("Pipeline Output", cv2.WINDOW_NORMAL)

        # Absolute playback clock. We advance it by one frame period each frame
        # and only sleep for the time remaining until that target, so the per
        # frame processing cost (blur/draw/render) does not accumulate into drift.
        next_frame_target = None

        while not self.shutdown_event.is_set():
            try:
                data = self.in_queue.get(timeout=0.1)
            except queues.Empty:
                continue
            if data == POISON_PILL:
                break

            frame, detections, fps = data
            if next_frame_target is None:
                next_frame_target = time.perf_counter()

            # blurring stage (done before drawing so boxes stay crisp on top).
            height, width, _ = frame.shape

            for x, y, w, h in detections:
                # defensive boundaries to prevent out of bounds NumPy indexing crashes.
                x1, y1 = max(0, x), max(0, y)
                x2, y2 = min(width, x + w), min(height, y + h)

                if x2 > x1 and y2 > y1:
                    roi = frame[y1:y2, x1:x2]

                    # we use cv2 blur for efficency.
                    blurred_roi = cv2.blur(roi, (45, 45))

                    # paste the blurred block back into the frame.
                    frame[y1:y2, x1:x2] = blurred_roi

            # drawing bounding boxes on top of the blurred regions.
            for x, y, w, h in detections:
                cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)

            # render current Time.
            current_time = time.strftime("%H:%M:%S", time.localtime())
            cv2.putText(
                frame,
                current_time,
                (20, 40),
                cv2.FONT_HERSHEY_SIMPLEX,
                1,
                (0, 0, 255),
                2,
            )

            cv2.imshow("Pipeline Output", frame)

            # Pace to the source frame rate by sleeping only the time left until
            # the next target, compensating for the time already spent processing.
            next_frame_target += 1.0 / fps
            wait_ms = max(1, int((next_frame_target - time.perf_counter()) * 1000))
            if (cv2.waitKey(wait_ms) & 0xFF == ord("q")) or cv2.getWindowProperty(
                "Pipeline Output", cv2.WND_PROP_VISIBLE
            ) < 1:
                log.info("User closed playback via window UI.")
                self.shutdown_event.set()
                break

        cv2.destroyAllWindows()
        log.info("Exited cleanly.")
