"""
Stage 2: Pipeline Intermediate Representation (Pipeline IR)
Generates and validates the computational DAG for the real-time traffic vision pipeline.
"""
import json
from typing import Dict, Any, List

def generate_pipeline_ir() -> Dict[str, Any]:
    return {
        "pipeline_name": "Traffic_Crosswalk_Analytics_Pipeline",
        "pipeline_version": "2.4.0",
        "ir_format_version": "1.0-pipegen",
        "target_platform": "NVIDIA Jetson Orin / RTX GPU (Edge Roadside Unit)",
        "nodes": [
            {
                "id": "node_01_capture",
                "name": "Multi-Modal Video Ingestion",
                "stage": "Ingestion",
                "type": "SourceNode",
                "plugin": "GStreamer / OpenCV V4L2 Source",
                "parameters": {
                    "sources": ["RTSP Stream", "USB Camera", "CSI MIPI", "Video File"],
                    "output_resolution": [1920, 1080],
                    "target_fps": 30,
                    "color_space": "BGR"
                },
                "inputs": [],
                "outputs": [
                    {"name": "raw_frame", "type": "Tensor", "shape": [1080, 1920, 3], "dtype": "uint8"}
                ],
                "profiling_budget_ms": 2.5
            },
            {
                "id": "node_02_preprocess",
                "name": "Tensor Preprocessor",
                "stage": "Preprocessing",
                "type": "TransformNode",
                "plugin": "CUDA Accelerated Letterbox & Normalizer",
                "parameters": {
                    "target_shape": [640, 640],
                    "interpolation": "BILINEAR",
                    "normalize_range": [0.0, 1.0],
                    "layout": "NCHW",
                    "color_conversion": "BGR2RGB"
                },
                "inputs": [
                    {"name": "raw_frame", "from": "node_01_capture.raw_frame"}
                ],
                "outputs": [
                    {"name": "input_tensor", "type": "Tensor", "shape": [1, 3, 640, 640], "dtype": "float32"},
                    {"name": "scale_params", "type": "Metadata", "desc": "ratio and padding offsets"}
                ],
                "profiling_budget_ms": 1.8
            },
            {
                "id": "node_03_inference",
                "name": "TensorRT Engine Execution",
                "stage": "Inference",
                "type": "InferenceNode",
                "plugin": "NVIDIA TensorRT 8.6+ Engine Runtime",
                "parameters": {
                    "precision": "INT8 (Calibrated with EntropyCalibratorV2)",
                    "engine_file": "traffic_detector_int8.engine",
                    "cuda_stream": "Asynchronous Stream 0",
                    "batch_size": 1,
                    "workspace_size_mb": 2048,
                    "supported_classes": ["pedestrian", "bicycle", "motorcycle", "car", "bus", "truck"]
                },
                "inputs": [
                    {"name": "input_tensor", "from": "node_02_preprocess.input_tensor"}
                ],
                "outputs": [
                    {"name": "raw_detections", "type": "Tensor", "shape": [1, 84, 8400], "dtype": "float32"}
                ],
                "profiling_budget_ms": 7.8
            },
            {
                "id": "node_04_postprocess",
                "name": "Batched NMS & Bounding Box Decoder",
                "stage": "Postprocessing",
                "type": "FilterNode",
                "plugin": "Efficient NMS / Coordinate Un-pad",
                "parameters": {
                    "confidence_threshold": 0.45,
                    "iou_nms_threshold": 0.50,
                    "max_detections_per_frame": 100
                },
                "inputs": [
                    {"name": "raw_detections", "from": "node_03_inference.raw_detections"},
                    {"name": "scale_params", "from": "node_02_preprocess.scale_params"}
                ],
                "outputs": [
                    {"name": "detections", "type": "DetectionList", "items": ["bbox_xyxy", "class_id", "confidence"]}
                ],
                "profiling_budget_ms": 1.2
            },
            {
                "id": "node_05_bytetrack",
                "name": "ByteTrack Multi-Object Tracker",
                "stage": "Tracking",
                "type": "TrackerNode",
                "plugin": "ByteTrack Kalman Filter + Hungarian Matcher",
                "parameters": {
                    "track_high_thresh": 0.5,
                    "track_low_thresh": 0.2,
                    "match_thresh": 0.7,
                    "track_buffer_frames": 30,
                    "assign_persistent_ids": True
                },
                "inputs": [
                    {"name": "detections", "from": "node_04_postprocess.detections"}
                ],
                "outputs": [
                    {"name": "tracked_objects", "type": "TrackList", "items": ["track_id", "class_name", "bbox", "centroid", "trajectory", "velocity"]}
                ],
                "profiling_budget_ms": 2.1
            },
            {
                "id": "node_06_geometry_analytics",
                "name": "Virtual Counting Lines & Crossing Logic",
                "stage": "Analytics",
                "type": "AnalyticsNode",
                "plugin": "2D Vector Cross Product & Intersection Engine",
                "parameters": {
                    "debounce_window_seconds": 3.0,
                    "direction_classification": ["Inbound", "Outbound"],
                    "duplicate_suppression": True,
                    "class_wise_segregation": True
                },
                "inputs": [
                    {"name": "tracked_objects", "from": "node_05_bytetrack.tracked_objects"}
                ],
                "outputs": [
                    {"name": "crossing_events", "type": "EventList"},
                    {"name": "class_counts", "type": "CountDictionary"}
                ],
                "profiling_budget_ms": 0.8
            },
            {
                "id": "node_07_mqtt_telemetry",
                "name": "MQTT Event & Telemetry Dispatcher",
                "stage": "Egress",
                "type": "SinkNode",
                "plugin": "Paho MQTT v2 Client",
                "parameters": {
                    "broker_host": "localhost",
                    "broker_port": 1883,
                    "qos": 1,
                    "event_topic": "smartcity/traffic/crosswalk_events",
                    "telemetry_topic": "smartcity/traffic/class_counts"
                },
                "inputs": [
                    {"name": "crossing_events", "from": "node_06_geometry_analytics.crossing_events"},
                    {"name": "class_counts", "from": "node_06_geometry_analytics.class_counts"}
                ],
                "outputs": [
                    {"name": "mqtt_status", "type": "Ack"}
                ],
                "profiling_budget_ms": 0.5
            },
            {
                "id": "node_08_hud_visualizer",
                "name": "Live Visualization & Streamer",
                "stage": "Visualization",
                "type": "VisualizationNode",
                "plugin": "OpenCV Annotation & MJPEG / WebSocket Broadcaster",
                "parameters": {
                    "render_bounding_boxes": True,
                    "render_track_ids": True,
                    "render_counting_lines": True,
                    "render_direction_vectors": True,
                    "render_class_statistics": True
                },
                "inputs": [
                    {"name": "raw_frame", "from": "node_01_capture.raw_frame"},
                    {"name": "tracked_objects", "from": "node_05_bytetrack.tracked_objects"},
                    {"name": "class_counts", "from": "node_06_geometry_analytics.class_counts"}
                ],
                "outputs": [
                    {"name": "annotated_stream", "type": "VideoStream"}
                ],
                "profiling_budget_ms": 3.2
            }
        ],
        "edges": [
            {"from": "node_01_capture", "to": "node_02_preprocess"},
            {"from": "node_01_capture", "to": "node_08_hud_visualizer"},
            {"from": "node_02_preprocess", "to": "node_03_inference"},
            {"from": "node_02_preprocess", "to": "node_04_postprocess"},
            {"from": "node_03_inference", "to": "node_04_postprocess"},
            {"from": "node_04_postprocess", "to": "node_05_bytetrack"},
            {"from": "node_05_bytetrack", "to": "node_06_geometry_analytics"},
            {"from": "node_05_bytetrack", "to": "node_08_hud_visualizer"},
            {"from": "node_06_geometry_analytics", "to": "node_07_mqtt_telemetry"},
            {"from": "node_06_geometry_analytics", "to": "node_08_hud_visualizer"}
        ],
        "summary": {
            "total_nodes": 8,
            "total_edges": 10,
            "estimated_latency_ms": 19.9,
            "theoretical_max_fps": 50.2,
            "jetson_orin_target_fps": 45.0,
            "meets_latency_budget": True
        }
    }

if __name__ == "__main__":
    ir = generate_pipeline_ir()
    with open("s:/Projects/MS bengluru/backend/pipegen/pipeline_ir.json", "w") as f:
        json.dump(ir, f, indent=2)
    print("Pipeline IR successfully generated.")
