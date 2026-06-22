from multiprocessing import Process,Queue
import cv2
POISON_PILL = "EOF" # to terminate the processes.

class Streamer(Process):
    def __init__(self,video_path:str,out_queue:Queue):
        super().__init__()
        self.video_path = video_path
        self.out_queue = out_queue
        
    def run(self) -> None:
        cap = cv2.VideoCapture(self.video_path)
        if not cap.isOpened():
            print("[Streamer] Error: could not open video.")
            self.out_queue.put(POISON_PILL)
            return
        fps = cap.get(cv2.CAP_PROP_FPS)
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            self.out_queue.put((frame, fps))
            
        cap.release()
        self.out_queue.put(POISON_PILL)
        print("[Streamer] Stream completed, poison pill sent.")