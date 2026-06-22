import cv2
from multiprocessing import Process,Queue
import time

POISON_PILL = "EOF"

class Viewer(Process):
    def __init__(self, in_queue: Queue):
        super().__init__()
        self.in_queue = in_queue

    def run(self):
        cv2.namedWindow("Pipeline Output", cv2.WINDOW_NORMAL)
        
        while True:
            data = self.in_queue.get()
            if data == POISON_PILL:
                break
                
            frame, detections, fps = data
            delay_ms = max(1, int(1000 / fps))
                
            # drawing bounding boxes.
            for (x, y, w, h) in detections:
                cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
                
            # render current Time.
            current_time = time.strftime("%H:%M:%S", time.localtime())
            cv2.putText(frame, current_time, (20, 40), 
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
            
            cv2.imshow("Pipeline Output", frame)
            if cv2.waitKey(delay_ms) & 0xFF == ord('q'):
                print("[Viewer] User interrupted playback.")
                break
                
        cv2.destroyAllWindows()
        print("[Viewer] Exited cleanly.")