# Axon-Vision Home Assignment: Multi Process Pipeline

Dear Axon-Vision interviewer, I hope you have as much fun checking my work as I had working on it!

---

## ▶️ How to Run

This project requires **Python 3.11+**.

### Option 1: Normal Python

Create and activate a virtual environment:

```bash
python -m venv .venv
```

On Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

On macOS/Linux:

```bash
source .venv/bin/activate
```

Install dependencies and run the pipeline:

```bash
pip install -r requirements.txt
python main.py
```

To run with a custom video file:

```bash
python main.py path/to/video.mp4
```

### Option 2: uv

Install dependencies and run the pipeline:

```bash
uv sync
uv run python main.py
```

To run with a custom video file:

```bash
uv run python main.py path/to/video.mp4
```

By default, the project looks for `People - 6387.mp4` in the project root.

---

## 🏗️ Architecture Overview

The system is designed as a classic **Producer Consumer pipeline** split across three decoupled processes by subclassing `multiprocessing.Process`. 

1. **Streamer:** Decodes the video using `cv2.VideoCapture` and pushes raw frames alongside frame rate metadata down the pipeline.
2. **Detector:** Consumes frames, processes them through the provided frame differencing motion detector, extracts contour bounding boxes, and passes them along. **Constraint Check:** This component never modifies or draws on the image matrix.
3. **Viewer:** Consumes frames and bounding boxes, handles the heavy visual blurring, draws UI overlays, and renders the output seamlessly at the video's native frame rate.

---

## 💡 Key Design & Engineering Decisions

### 1. IPC Choice: `multiprocessing.Queue`
* **Why:** I used bounded queues (`maxsize=30`) between the processes. This acts as a thread/process safe FIFO mechanism. 
* **Backpressure Management:** The bounding size ensures that if the Viewer or Detector experiences a temporary CPU spike, memory consumption does not balloon infinitely; instead, upstream processes naturally block until the pipeline clears.

#### Trade off Considered: `Queue` vs. `Shared Memory`
I deliberately chose `Queue` over a `multiprocessing.shared_memory` buffer pool. A shared memory design would avoid serializing each frame (a few MB) twice as it travels Streamer → Detector → Viewer, lowering CPU and latency. I decided against it here for the following reasons:

* **Isolation & correctness:** With a `Queue`, each process receives its **own private copy** of the frame. This *physically guarantees* the "Detector must not draw on the image" constraint and makes the Viewer's in place blur completely safe. Shared memory shares the same physical buffer, reintroducing race conditions (torn frames if a buffer is recycled while still being read) that the `Queue` eliminates for free.
* **Complexity:** Shared memory would turn a simple FIFO into a fixed size **buffer pool protocol** with a return/credit channel so the Streamer knows when a buffer is safe to reuse, plus explicit `close()`/`unlink()` cleanup on every shutdown path more code and more ways to leak OS level segments.
* **No measured benefit for this scope:** The input is a single fixed file, and the pipeline already sustains the video's native FPS with smooth playback. The real bottleneck was the blur (addressed in section 3), not IPC throughput. The assignment also emphasizes correct architecture and smooth playback over raw throughput.

For a higher resolution or higher throughput production system, shared memory (or zero copy frame handles) would be the natural next optimization.

### 2. Smooth Playback & Timing Optimization
* To prevent stuttering or unnatural playback speeds, frame rate synchronization is managed entirely in the **Viewer** process based on the source metadata.
* **Drift compensation:** A naive fixed `wait = 1000 / fps` per frame plays back too slowly, because the per frame processing cost (blur, drawing, rendering) is *added on top of* the wait. Instead, the Viewer keeps an absolute playback clock and only sleeps for the time remaining until the next frame's target, subtracting the work already done:

```python
next_frame_target += 1.0 / fps
wait_ms = max(1, int((next_frame_target - time.perf_counter()) * 1000))
cv2.waitKey(wait_ms)
```

* Because the target advances by an exact frame period each iteration (rather than resetting), small per frame timing errors do not accumulate, keeping playback locked to the source frame rate.

### 3. Stage B Optimization: `cv2.blur` (Normalized Box Filter)
* **The Problem:** At the beggining i used Gaussian Blurring but Heavy Gaussian Blurring on large motion contours originally introduced a massive computational bottleneck, degrading playback FPS.
* **The Solution:** I replaced it with `cv2.blur`. Because OpenCV optimizes box filtering using integral images, its computation time is independent of kernel size. This ensures the Viewer easily sustains full video speed while keeping target regions perfectly obscured.

### 4. Stage C: Bidirectional Lifecycle & Robust Shutdown
* **The Foresight Choice:** I implemented the shutdown infrastructure alongside Stage A. In multi process programming, omitting a lifecycle strategy leads to zombie processes and memory leaks.
* **Mechanism:** The pipeline utilizes a shared `multiprocessing.Event` alongside a downstream "Poison Pill" (`"EOF"`). 
* **Signal Handling:** Each process overrides its local `SIGINT` (Ctrl+C) handler inside its `run()` context. This ensures that if a process is blocked on a `Queue.get()`, it is forcefully interrupted, destroys its native UI windows cleanly, and exits without throwing messy stack traces.
* **Design Note** I partially implemented stage C with stage A, the poision pill part. The reason for that is that while developing and testing the project at stage A, I wanted all the processes to close without leaving leaked resources and zombie processes.

---