from multiprocessing import Process, Queue, Event, queues
import logging
import sys
import cv2
import signal

from pipeline_components.logging_config import configure_logging

POISON_PILL = "EOF"  # to terminate the processes.
DEFAULT_FPS = 30.0  # fallback when the source does not report a valid frame rate.

log = logging.getLogger(__name__)


class Streamer(Process):
    def __init__(self, video_path: str, out_queue: Queue, shutdown_event: Event):
        super().__init__()
        self.video_path = video_path
        self.out_queue = out_queue
        self.shutdown_event = shutdown_event

    def run(self) -> None:
        configure_logging()

        def local_sigint_handler(signum, frame):
            log.info("SIGINT intercepted. Cleaning up Streamer.")
            self.shutdown_event.set()
            sys.exit(0)

        signal.signal(signal.SIGINT, local_sigint_handler)

        cap = cv2.VideoCapture(self.video_path)
        if not cap.isOpened():
            log.error("Could not open video: %s", self.video_path)
            self.out_queue.put(POISON_PILL)
            return

        # fall back to a sane default so the Viewer's timing math never divides by zero.
        fps = cap.get(cv2.CAP_PROP_FPS)
        if not fps or fps <= 0:
            log.warning("Source reported invalid fps (%s); falling back to %s.", fps, DEFAULT_FPS)
            fps = DEFAULT_FPS

        while not self.shutdown_event.is_set():
            ret, frame = cap.read()
            if not ret:
                log.info("Video file reached end of stream.")
                break
            try:
                self.out_queue.put((frame, fps), timeout=0.1)
            except queues.Full:
                continue

        cap.release()
        try:
            self.out_queue.put(POISON_PILL, timeout=0.5)
        except queues.Full:
            pass
        log.info("Stream completed, poison pill sent.")
