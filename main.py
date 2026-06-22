from pipeline_components import Streamer, Detector, Viewer
from multiprocessing import Queue
def main():
    streamer_to_detector = Queue(maxsize=30)
    detector_to_viewer = Queue(maxsize=30)
    
    # pipeline
    processes = [
        Streamer("People - 6387.mp4", streamer_to_detector),
        Detector(streamer_to_detector, detector_to_viewer),
        Viewer(detector_to_viewer)
    ]
    
    print("[Main] Starting pipeline...")
    for p in processes:
        p.start() 
        
    for p in processes:
        p.join() # all of them will shut down once the poision pill will be sent.
        
    print("[Main] Pipeline completely shutting down.")


if __name__ == "__main__":
    main()
