from multiprocessing import Process,Queue,Event,queues
import sys
import cv2
import signal
POISON_PILL = "EOF" # to terminate the processes.

class Streamer(Process):
    def __init__(self,video_path:str,out_queue:Queue,shutdown_event: Event):
        super().__init__()
        self.video_path = video_path
        self.out_queue = out_queue
        self.shutdown_event = shutdown_event
        
    def run(self) -> None:
        
        def local_sigint_handler(signum, frame):
            print("[Streamer] SIGINT intercepted. Cleaning up Streamer.")
            self.shutdown_event.set()
            sys.exit(0)

        signal.signal(signal.SIGINT, local_sigint_handler)
        
        cap = cv2.VideoCapture(self.video_path)
        if not cap.isOpened():
            print("[Streamer] Error: could not open video.")
            self.out_queue.put(POISON_PILL)
            return
        fps = cap.get(cv2.CAP_PROP_FPS)
        while not self.shutdown_event.is_set():
            ret, frame = cap.read()
            if not ret:
                print("[Streamer] Video file reached end of stream.")
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
        print("[Streamer] Stream completed, poison pill sent.")