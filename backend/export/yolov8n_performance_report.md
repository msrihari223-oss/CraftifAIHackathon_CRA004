# PipeGen Stage 4: TensorRT Compiler & Performance Benchmark Report
**Target System:** Smart City Crosswalk & Roadside Pole-Mounted Unit  
**Hardware Platform:** NVIDIA Jetson Orin Nano (6-Core ARM, 1024-core NVIDIA Ampere GPU, 8GB LPDDR5)  
**Model Architecture:** yolov8n (Input: 640x640x3)  
**Date:** 2026-10-18T11:00:00Z

---

## 1. Executive Summary
The traffic vision pipeline was compiled to NVIDIA TensorRT using FP32, FP16, and INT8 precision with **IInt8EntropyCalibrator2** calibration on roadside traffic datasets. **INT8 precision achieved 78.1 FPS** end-to-end (a **2.47x speedup** over FP32) with a power envelope of only **8.6 Watts**, comfortably fitting the 15W roadside unit constraint while retaining **99.1% of base detection accuracy**.

---

## 2. Performance & Precision Comparison Table

| Metric | FP32 (Baseline) | FP16 (Half) | INT8 (Calibrated) | Improvement / Delta |
|---|---|---|---|---|
| **Inference Latency** | 26.2 ms | 13.4 ms | **7.8 ms** | **3.35x faster** |
| **End-to-End Latency** | 31.6 ms | 18.6 ms | **12.8 ms** | **Sub-13 ms (< 33.3ms budget)** |
| **Throughput (FPS)** | 31.6 FPS | 53.7 FPS | **78.1 FPS** | **+147% Throughput** |
| **VRAM Consumption** | 1280 MB | 720 MB | **430 MB** | **-66.4% Memory Footprint** |
| **Power Draw** | 14.8 W | 11.4 W | **8.6 W** | **-41.8% Power Reduction** |
| **Thermal Temperature** | 58.4 °C | 52.1 °C | **46.2 °C** | **-12.2 °C Cooler** |
| **Detection mAP@50** | 67.8 | 67.7 | **67.2** | **-0.6% (Negligible drop)** |
| **Detection mAP@50-95**| 37.3 | 37.2 | **36.8** | **-0.5%** |

---

## 3. Class-Wise Detection Accuracy (AP@50)

| Object Class | FP32 AP@50 | FP16 AP@50 | INT8 AP@50 | Quantization Delta |
|---|---|---|---|---|
| **Pedestrian** | 71.4% | 71.3% | **70.9%** | -0.5% |
| **Bicycle** | 62.8% | 62.6% | **62.1%** | -0.7% |
| **Motorcycle** | 65.2% | 65.0% | **64.7%** | -0.5% |
| **Car** | 79.5% | 79.4% | **78.9%** | -0.6% |
| **Bus** | 72.1% | 72.0% | **71.5%** | -0.6% |
| **Truck** | 70.3% | 70.2% | **69.8%** | -0.5% |

---

## 4. Compilation Artifacts
1. **Engine Binary:** `backend/export/yolov8n_int8.engine`
2. **Calibration Cache:** `backend/export/yolov8n_int8_calib.cache`
3. **Execution Flags:** `trtexec --onnx=yolov8n_traffic.onnx --int8 --fp16 --calib=calib.cache --workspace=2048`

---
*Report generated automatically by PipeGen Stage 4 Compiler.*
