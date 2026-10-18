"""
Generates a realistic sample traffic video (sample_traffic_video.mp4)
for immediate testing of file upload and video detection.
"""
import cv2
import numpy as np
import os
import random

os.makedirs("backend/uploads", exist_ok=True)
output_path = "backend/uploads/sample_traffic_video.mp4"

width, height = 1280, 720
fps = 30
duration_sec = 15
total_frames = fps * duration_sec

fourcc = cv2.VideoWriter_fourcc(*'mp4v')
out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

# Build background
bg = np.zeros((height, width, 3), dtype=np.uint8)
bg[:] = (45, 48, 52)

# Sidewalks
cv2.rectangle(bg, (0, 0), (320, 260), (165, 170, 175), -1)
cv2.rectangle(bg, (960, 0), (width, 260), (165, 170, 175), -1)
cv2.rectangle(bg, (0, 460), (320, height), (165, 170, 175), -1)
cv2.rectangle(bg, (960, 460), (width, height), (165, 170, 175), -1)

# Bike lanes
cv2.rectangle(bg, (330, 0), (370, height), (40, 110, 50), -1)
cv2.rectangle(bg, (910, 0), (950, height), (40, 110, 50), -1)

# Double yellow lines
cv2.line(bg, (636, 0), (636, height), (0, 215, 255), 2)
cv2.line(bg, (644, 0), (644, height), (0, 215, 255), 2)

# Crosswalk stripes
for x in range(380, 900, 32):
    cv2.rectangle(bg, (x, 210), (x + 18, 255), (240, 240, 245), -1)
    cv2.rectangle(bg, (x, 465), (x + 18, 510), (240, 240, 245), -1)

# Vehicles & Pedestrians with realistic shapes
vehicles = [
    {"type": "car", "color": (220, 60, 50), "w": 70, "h": 120, "x": 520, "y": -150, "speed": 6.5},
    {"type": "car", "color": (50, 140, 240), "w": 68, "h": 115, "x": 740, "y": height + 100, "speed": -7.0},
    {"type": "bus", "color": (180, 50, 180), "w": 95, "h": 220, "x": 550, "y": -500, "speed": 4.5},
    {"type": "truck", "color": (50, 180, 200), "w": 90, "h": 180, "x": 760, "y": height + 400, "speed": -5.0},
    {"type": "motorcycle", "color": (20, 200, 100), "w": 32, "h": 65, "x": 480, "y": -250, "speed": 8.0},
    {"type": "bicycle", "color": (220, 200, 20), "w": 28, "h": 60, "x": 350, "y": -80, "speed": 3.8},
    {"type": "bicycle", "color": (20, 220, 220), "w": 28, "h": 60, "x": 930, "y": height + 50, "speed": -4.0},
]

pedestrians = [
    {"x": 360, "y": 232, "vx": 2.2, "vy": 0, "color": (240, 240, 240), "w": 22, "h": 22},
    {"x": 860, "y": 485, "vx": -1.9, "vy": 0, "color": (250, 230, 200), "w": 22, "h": 22},
    {"x": 420, "y": 485, "vx": 2.0, "vy": 0, "color": (200, 250, 220), "w": 22, "h": 22},
    {"x": 800, "y": 232, "vx": -2.1, "vy": 0, "color": (255, 200, 220), "w": 22, "h": 22},
]

print("Rendering realistic sample traffic video...")
for frame_idx in range(total_frames):
    frame = bg.copy()

    # Draw pedestrians
    for p in pedestrians:
        p["x"] += p["vx"]
        if p["x"] > 910 or p["x"] < 340:
            p["vx"] = -p["vx"]
        cx, cy = int(p["x"]), int(p["y"])
        # Head & body circle / shadow
        cv2.circle(frame, (cx + 2, cy + 3), 12, (20, 20, 25), -1)
        cv2.circle(frame, (cx, cy), 11, p["color"], -1)
        cv2.circle(frame, (cx, cy), 5, (50, 50, 50), -1)

    # Draw vehicles
    for v in vehicles:
        v["y"] += v["speed"]
        if v["speed"] > 0 and v["y"] > height + 200:
            v["y"] = -random.randint(150, 350)
        elif v["speed"] < 0 and v["y"] < -200:
            v["y"] = height + random.randint(150, 350)

        vx, vy = int(v["x"]), int(v["y"])
        w, h = v["w"], v["h"]
        # Vehicle shadow
        cv2.rectangle(frame, (vx - w//2 + 4, vy - h//2 + 6), (vx + w//2 + 4, vy + h//2 + 6), (20, 22, 26), -1)
        # Vehicle body
        cv2.rectangle(frame, (vx - w//2, vy - h//2), (vx + w//2, vy + h//2), v["color"], -1)
        # Windshield
        if v["speed"] > 0:
            cv2.rectangle(frame, (vx - w//2 + 6, vy + h//4), (vx + w//2 - 6, vy + h//4 + 18), (30, 40, 50), -1)
            cv2.rectangle(frame, (vx - w//2 + 6, vy - h//4), (vx + w//2 - 6, vy - h//4 + 14), (30, 40, 50), -1)
        else:
            cv2.rectangle(frame, (vx - w//2 + 6, vy - h//4), (vx + w//2 - 6, vy - h//4 + 18), (30, 40, 50), -1)
            cv2.rectangle(frame, (vx - w//2 + 6, vy + h//4), (vx + w//2 - 6, vy + h//4 + 14), (30, 40, 50), -1)

    # Time code overlay on top-left of video
    tc = f"RAW TRAFFIC FOOTAGE - FRAME {frame_idx:04d} / {total_frames}"
    cv2.putText(frame, tc, (20, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1, cv2.LINE_AA)

    out.write(frame)

out.release()
print(f"Sample traffic video generated at {output_path} ({total_frames} frames).")
