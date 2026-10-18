#!/bin/bash
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
