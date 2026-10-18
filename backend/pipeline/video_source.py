"""
Multi-Modal Video Source Ingestion Module
Supports Standby mode, Uploaded Video File, USB / CSI Webcam, RTSP stream, and Sample Video.
"""
import cv2
import numpy as np
import time
import os
import threading
from typing import Tuple, Optional

class VideoSourceManager:
    def __init__(self, mode: str = "standby", source_uri: str = "", width: int = 1280, height: int = 720):
        self.mode = mode  # "standby", "camera", "file", "rtsp"
        self.source_uri = source_uri
        self.width = width
        self.height = height
        self.cap: Optional[cv2.VideoCapture] = None
        self.is_paused = False
        self.lock = threading.Lock()
        self.frame_count = 0
        self.fps = 30.0
        self.current_filename = ""
        
        # Standby graphic placeholder
        self._standby_frame = self._generate_standby_canvas()
        if self.mode != "standby" and self.source_uri:
            self._init_source()

    def _generate_standby_canvas(self) -> np.ndarray:
        """Renders a sleek standby display awaiting user video activation or upload."""
        canvas = np.zeros((self.height, self.width, 3), dtype=np.uint8)
        # Deep space dark slate
        canvas[:] = (18, 22, 28)

        # Subtle grid pattern
        for x in range(0, self.width, 40):
            cv2.line(canvas, (x, 0), (x, self.height), (26, 32, 42), 1)
        for y in range(0, self.height, 40):
            cv2.line(canvas, (0, y), (self.width, y), (26, 32, 42), 1)

        # Central monitor box
        cx, cy = self.width // 2, self.height // 2
        box_w, box_h = 720, 260
        x1, y1 = cx - box_w // 2, cy - box_h // 2
        x2, y2 = cx + box_w // 2, cy + box_h // 2
        
        cv2.rectangle(canvas, (x1, y1), (x2, y2), (30, 41, 59), -1)
        cv2.rectangle(canvas, (x1, y1), (x2, y2), (6, 182, 212), 2)

        # Top title badge
        cv2.rectangle(canvas, (x1, y1), (x2, y1 + 45), (15, 23, 42), -1)
        cv2.putText(canvas, "AI TRAFFIC & CROSSWALK ANALYTICS // STANDBY", (x1 + 24, y1 + 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.65, (6, 182, 212), 2, cv2.LINE_AA)

        # Standby instructions
        cv2.putText(canvas, "Video stream paused. Real-time detection is on standby.", (x1 + 30, y1 + 90),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.60, (255, 255, 255), 1, cv2.LINE_AA)
        
        cv2.putText(canvas, "1. Click 'Turn On Live Camera' to run detection on your webcam", (x1 + 30, y1 + 130),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.50, (148, 163, 184), 1, cv2.LINE_AA)
        
        cv2.putText(canvas, "2. Click 'Upload Traffic Video' to detect from any MP4 / AVI file", (x1 + 30, y1 + 165),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.50, (148, 163, 184), 1, cv2.LINE_AA)
        
        cv2.putText(canvas, "3. Click 'Load Sample Video' for instant pre-packaged smart city clip", (x1 + 30, y1 + 200),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.50, (16, 185, 129), 1, cv2.LINE_AA)

        # Footer timestamp
        t_str = time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())
        cv2.putText(canvas, f"POLE UNIT #042 - SYSTEM READY - {t_str}", (30, self.height - 25),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (100, 116, 139), 1, cv2.LINE_AA)

        return canvas

    def _init_source(self):
        with self.lock:
            if self.cap:
                self.cap.release()
                self.cap = None

            if self.mode == "camera":
                try:
                    dev_idx = int(self.source_uri) if self.source_uri.isdigit() else 0
                    self.cap = cv2.VideoCapture(dev_idx, cv2.CAP_DSHOW)
                    if not self.cap.isOpened():
                        self.cap = cv2.VideoCapture(dev_idx)
                    self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
                    self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
                except Exception as e:
                    print(f"[VideoSource] Error opening camera: {e}")
            elif self.mode in ["file", "rtsp"]:
                try:
                    if os.path.exists(self.source_uri) or self.source_uri.startswith("rtsp://") or self.source_uri.startswith("http://"):
                        self.cap = cv2.VideoCapture(self.source_uri)
                        self.current_filename = os.path.basename(self.source_uri)
                    else:
                        print(f"[VideoSource] File not found: {self.source_uri}")
                except Exception as e:
                    print(f"[VideoSource] Error opening video file: {e}")

    def read_frame(self) -> Tuple[bool, np.ndarray, str]:
        """
        Returns:
            (has_active_video: bool, frame: np.ndarray, source_info: str)
        """
        self.frame_count += 1

        if self.mode == "standby" or self.is_paused:
            frame = self._generate_standby_canvas()
            return False, frame, "STANDBY"

        if self.cap and self.cap.isOpened():
            ret, frame = self.cap.read()
            if ret:
                frame = cv2.resize(frame, (self.width, self.height))
                source_label = f"FILE: {self.current_filename}" if self.mode == "file" else f"CAM: {self.source_uri or '0'}"
                return True, frame, source_label
            elif self.mode == "file":
                # Loop video file continuously
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                ret, frame = self.cap.read()
                if ret:
                    frame = cv2.resize(frame, (self.width, self.height))
                    return True, frame, f"FILE: {self.current_filename} (LOOP)"

        # Fallback to standby if source couldn't be read
        frame = self._generate_standby_canvas()
        return False, frame, "NO SIGNAL / STANDBY"

    def set_source(self, mode: str, uri: str = ""):
        self.mode = mode
        self.source_uri = uri
        self.is_paused = False
        self._init_source()

    def pause(self):
        self.is_paused = True

    def resume(self):
        self.is_paused = False

    def stop(self):
        self.mode = "standby"
        self.is_paused = False
        with self.lock:
            if self.cap:
                self.cap.release()
                self.cap = None

    def release(self):
        with self.lock:
            if self.cap:
                self.cap.release()
                self.cap = None
