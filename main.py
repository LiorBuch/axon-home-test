import time
from pipeline_components import Streamer, Detector, Viewer
from multiprocessing import Queue, Event
import signal


def main():
    streamer_to_detector = Queue(maxsize=30)
    detector_to_viewer = Queue(maxsize=30)
    
    shutdown_event = Event()
    
    def sigint_handler(signum, frame):
        print("[Main] SIGINT (Ctrl+C) detected! Signaling shutdown...")
        shutdown_event.set()
        
    signal.signal(signal.SIGINT, sigint_handler)
    
    # pipeline
    processes = [
        Streamer("People - 6387.mp4", streamer_to_detector,shutdown_event),
        Detector(streamer_to_detector, detector_to_viewer,shutdown_event),
        Viewer(detector_to_viewer,shutdown_event)
    ]
    
    print("[Main] Starting pipeline...")
    for p in processes:
        p.start() 

    while any(p.is_alive() for p in processes) and not shutdown_event.is_set():
        time.sleep(0.1)

    if shutdown_event.is_set():
        print("[Main] Shutdown event active. Terminating lingering processes...")
        for p in processes:
            if p.is_alive():
                p.terminate()

    for q in (streamer_to_detector, detector_to_viewer):
        q.cancel_join_thread()
        q.close()

    for p in processes:
        p.join(timeout=2)
        if p.is_alive():
            print(f"[Main] {p.name} did not exit, killing it.")
            p.kill()
            p.join()

    print("[Main] Pipeline completely shutting down.")


if __name__ == "__main__":
    main()
