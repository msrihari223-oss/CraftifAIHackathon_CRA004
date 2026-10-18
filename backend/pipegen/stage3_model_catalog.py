"""
Stage 3: Model Catalog and Selection
Manages compatible pretrained vision models, class index mappings, and ONNX export routines.
"""
import json
from typing import Dict, Any, List

TARGET_CLASSES = {
    0: "pedestrian",
    1: "bicycle",
    2: "car",
    3: "motorcycle",
    5: "bus",
    7: "truck"
}

MODEL_CATALOG = [
    {
        "id": "yolov8n",
        "name": "YOLOv8 Nano (Roadside Optimized)",
        "family": "YOLOv8",
        "parameters_millions": 3.2,
        "flops_g": 8.7,
        "input_resolution": [640, 640],
        "default_precision": "INT8",
        "supported_precisions": ["FP32", "FP16", "INT8"],
        "recommended_for": "Edge Roadside Pole-Mounted Unit (Jetson Orin Nano 15W)",
        "classes_count": 6,
        "map50_95_traffic": 37.3,
        "map50_traffic": 67.8,
        "onnx_filename": "yolov8n_traffic.onnx",
        "trt_engine_filename": "yolov8n_traffic_int8.engine"
    },
    {
        "id": "yolov8s",
        "name": "YOLOv8 Small (High Accuracy)",
        "family": "YOLOv8",
        "parameters_millions": 11.2,
        "flops_g": 28.6,
        "input_resolution": [640, 640],
        "default_precision": "INT8",
        "supported_precisions": ["FP32", "FP16", "INT8"],
        "recommended_for": "Jetson AGX Xavier / Jetson Orin NX (25W)",
        "classes_count": 6,
        "map50_95_traffic": 44.9,
        "map50_traffic": 74.2,
        "onnx_filename": "yolov8s_traffic.onnx",
        "trt_engine_filename": "yolov8s_traffic_int8.engine"
    },
    {
        "id": "yolo11n",
        "name": "YOLO11 Nano (Next-Gen Small-Object Attn)",
        "family": "YOLO11",
        "parameters_millions": 2.6,
        "flops_g": 6.5,
        "input_resolution": [640, 640],
        "default_precision": "INT8",
        "supported_precisions": ["FP32", "FP16", "INT8"],
        "recommended_for": "Extreme low-power IoT / Pole units (7W-15W)",
        "classes_count": 6,
        "map50_95_traffic": 39.5,
        "map50_traffic": 70.1,
        "onnx_filename": "yolo11n_traffic.onnx",
        "trt_engine_filename": "yolo11n_traffic_int8.engine"
    },
    {
        "id": "rt_detr_l",
        "name": "RT-DETR Large (Transformer NMS-Free)",
        "family": "RT-DETR",
        "parameters_millions": 32.0,
        "flops_g": 110.0,
        "input_resolution": [640, 640],
        "default_precision": "FP16",
        "supported_precisions": ["FP32", "FP16"],
        "recommended_for": "High-throughput Smart Intersection Gateway",
        "classes_count": 6,
        "map50_95_traffic": 53.1,
        "map50_traffic": 81.6,
        "onnx_filename": "rt_detr_traffic.onnx",
        "trt_engine_filename": "rt_detr_traffic_fp16.engine"
    }
]

def get_model_catalog() -> List[Dict[str, Any]]:
    return MODEL_CATALOG

def get_model_by_id(model_id: str) -> Dict[str, Any]:
    for model in MODEL_CATALOG:
        if model["id"] == model_id:
            return model
    return MODEL_CATALOG[0]

def export_onnx_specification(model_id: str) -> Dict[str, Any]:
    model = get_model_by_id(model_id)
    return {
        "status": "READY_FOR_COMPILATION",
        "model_id": model["id"],
        "model_name": model["name"],
        "input_tensor_name": "images",
        "input_shape": [1, 3, model["input_resolution"][0], model["input_resolution"][1]],
        "output_tensor_name": "output0",
        "output_shape": [1, 84, 8400],
        "opset_version": 17,
        "dynamic_axes": {
            "images": {0: "batch"},
            "output0": {0: "batch"}
        },
        "quantization_nodes_inserted": True,
        "calibration_dataset": "traffic_crosswalk_calibration_set_500img.tar.gz"
    }

if __name__ == "__main__":
    catalog = get_model_catalog()
    print(f"Loaded {len(catalog)} models from PipeGen Model Catalog.")
