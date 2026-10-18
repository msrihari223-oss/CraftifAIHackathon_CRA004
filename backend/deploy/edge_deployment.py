"""
Edge Roadside Unit Deployment Artifacts Generator
Creates production Dockerfile, systemd service, NVIDIA DeepStream config, and shell runners.
"""
import os
import json

DEPLOY_DIR = "backend/deploy"
os.makedirs(DEPLOY_DIR, exist_ok=True)

DOCKERFILE_JETSON = """# NVIDIA Jetson Edge Roadside Unit Container (JetPack 5.1 / 6.0)
FROM nvcr.io/nvidia/l4t-tensorrt:r8.6.1-runtime

WORKDIR /opt/traffic-analytics

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \\
    python3-pip \\
    python3-opencv \\
    libgstreamer1.0-0 \\
    gstreamer1.0-plugins-base \\
    gstreamer1.0-plugins-good \\
    gstreamer1.0-plugins-bad \\
    mosquitto-clients \\
    curl && \\
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

COPY . .

# Run edge pipeline with INT8 TensorRT engine
ENV JETSON_CLOCKS=1
ENV TRT_PRECISION=INT8
ENV RTSP_STREAM_URL=rtsp://localhost:8554/live

CMD ["python3", "-m", "backend.main", "--mode", "rtsp", "--precision", "INT8"]
"""

SYSTEMD_SERVICE = """[Unit]
Description=AI Traffic and Crosswalk Analytics System - Roadside Unit
After=network.target docker.service mosquitto.service
Wants=network-online.target

[Service]
Type=simple
User=jetson
WorkingDirectory=/opt/traffic-analytics
ExecStartPre=/usr/bin/jetson_clocks
ExecStart=/usr/bin/python3 -m backend.main --host 0.0.0.0 --port 8000 --precision INT8
Restart=always
RestartSec=5s
StandardOutput=journal
StandardError=journal
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
"""

DEEPSTREAM_CONFIG = """[application]
enable-perf-measurement=1
perf-measurement-interval-sec=5

[source0]
enable=1
# Type 1=Camera (V4L2), 2=URI/RTSP, 3=File
type=2
uri=rtsp://edge-unit.city.gov:554/live/cam01
num-sources=1
gpu-id=0
nvbuf-memory-type=0

[sink0]
enable=1
# Type 1=Fakesink, 2=EGL, 3=File, 4=RTSP Streaming
type=2
sync=0
gpu-id=0

[osd]
enable=1
gpu-id=0
border-width=2
text-size=12
text-color=1;1;1;1
text-bg-color=0.3;0.3;0.3;1

[primary-gie]
enable=1
gpu-id=0
batch-size=1
interval=0
gie-unique-id=1
nvbuf-memory-type=0
model-engine-file=backend/export/yolov8n_traffic_int8.engine
config-file=config_infer_primary_yolo.txt

[tracker]
enable=1
tracker-width=640
tracker-height=640
ll-lib-file=/opt/nvidia/deepstream/deepstream/lib/libnvds_nvmultiobjecttracker.so
ll-config-file=config_tracker_bytetrack.yml
enable-batch-process=1
"""

RUN_SCRIPT = """#!/bin/bash
echo "=== Starting AI Traffic & Crosswalk Analytics Edge Pipeline ==="
echo "Target Platform: NVIDIA Jetson / Edge Roadside Unit"
echo "Active Precision: INT8 (Calibrated with Entropy v2)"

# Lock clocks for consistent edge FPS
if command -v jetson_clocks &> /dev/null; then
    sudo jetson_clocks
    echo "[OK] Jetson Clocks Max Performance Enabled"
fi

# Run backend server
python3 -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --workers 1
"""

def generate_deployment_files():
    with open(os.path.join(DEPLOY_DIR, "Dockerfile.jetson"), "w") as f:
        f.write(DOCKERFILE_JETSON)
    with open(os.path.join(DEPLOY_DIR, "crosswalk-analytics.service"), "w") as f:
        f.write(SYSTEMD_SERVICE)
    with open(os.path.join(DEPLOY_DIR, "deepstream_app_config.txt"), "w") as f:
        f.write(DEEPSTREAM_CONFIG)
    with open(os.path.join(DEPLOY_DIR, "run_edge_unit.sh"), "w") as f:
        f.write(RUN_SCRIPT)
    print("Edge deployment files generated successfully.")

if __name__ == "__main__":
    generate_deployment_files()
