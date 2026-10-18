"""
Main FastAPI Server & Real-time Computer Vision Pipeline Runtime
Coordinates Video Ingestion, Ultralytics YOLO/TensorRT Detection, ByteTrack Tracking,
Virtual Line Geometry Analytics, MQTT Dispatching, File Uploads, and REST/WebSocket APIs.
"""
import cv2
import time
import json
import asyncio
import os
import shutil
import threading
import numpy as np
from contextlib import asynccontextmanager
from typing import Dict, Any, List, Optional
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, FileResponse, JSONResponse
from pydantic import BaseModel

from backend.pipeline.video_source import VideoSourceManager
from backend.pipeline.detector import TrafficDetector, TARGET_CLASSES
from backend.pipeline.tracker import ByteTracker
from backend.pipeline.geometry import TrafficAnalyticsEngine
from backend.pipeline.mqtt_service import MQTTService
from backend.pipegen.stage2_pipeline_ir import generate_pipeline_ir
from backend.pipegen.stage3_model_catalog import get_model_catalog, get_model_by_id, export_onnx_specification
from backend.pipegen.stage4_compiler import TensorRTCompiler

app = FastAPI(
    title="AI Traffic and Crosswalk Analytics System",
    description="Real-Time Computer Vision Pipeline for Smart Cities with TensorRT INT8 Acceleration",
    version="2.4.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

UPLOAD_DIR = "backend/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Global Pipeline Singletons (Starts in Standby mode - NO auto running)
video_manager = VideoSourceManager(mode="standby")
detector = TrafficDetector(confidence_thresh=0.20)
tracker = ByteTracker(track_high_thresh=0.25, track_low_thresh=0.12, match_thresh=0.55)
analytics = TrafficAnalyticsEngine(debounce_seconds=3.0)
mqtt_service = MQTTService()
compiler = TensorRTCompiler()

# Pipeline State
pipeline_state = {
    "is_running": False,  # Default PAUSED / STANDBY
    "source_mode": "standby",
    "source_label": "Standby - Waiting for input",
    "current_model": "yolov8n",
    "precision": "INT8",
    "current_fps": 0.0,
    "last_frame_time": time.time(),
    "total_frames_processed": 0,
    "active_tracks_count": 0,
    "annotated_frame_jpeg": None,
    "render_options": {
        "show_boxes": True,
        "show_tracks": True,
        "show_lines": True,
        "show_trails": True,
        "show_hud": True
    }
}

class LineUpdateModel(BaseModel):
    line_id: str
    name: str
    p1: List[int]
    p2: List[int]
    direction_type: Optional[str] = "both"
    allowed_classes: Optional[List[str]] = None
    color: Optional[str] = "#EF4444"

class SourceChangeModel(BaseModel):
    mode: str  # "camera", "file", "rtsp", "standby"
    uri: Optional[str] = ""

class ModelCompileModel(BaseModel):
    model_id: str
    precision: str = "INT8"

CLASS_COLORS = {
    "pedestrian": (16, 185, 129),   # Emerald green
    "bicycle": (212, 182, 6),      # Cyan
    "motorcycle": (11, 158, 245),   # Amber
    "car": (246, 130, 59),         # Blue
    "bus": (246, 92, 139),         # Purple
    "truck": (153, 72, 236)        # Pink
}

def annotate_frame(frame: np.ndarray, tracks: List[Dict[str, Any]], lines_dict: Dict[str, Any], global_counts: Dict[str, int]) -> np.ndarray:
    """Renders high-contrast bounding boxes, persistent IDs, counting lines, and HUD."""
    opts = pipeline_state["render_options"]
    annotated = frame.copy()

    # 1. Render Virtual Counting Lines
    if opts["show_lines"]:
        for lid, line in lines_dict.items():
            p1 = tuple(line["p1"])
            p2 = tuple(line["p2"])
            hex_col = line.get("color", "#EF4444").lstrip("#")
            col = tuple(int(hex_col[i:i+2], 16) for i in (4, 2, 0)) if len(hex_col) == 6 else (0, 0, 255)
            
            cv2.line(annotated, p1, p2, (0, 0, 0), 5, cv2.LINE_AA)
            cv2.line(annotated, p1, p2, col, 3, cv2.LINE_AA)
            
            cv2.circle(annotated, p1, 5, col, -1)
            cv2.circle(annotated, p2, 5, col, -1)

            mx, my = int((p1[0] + p2[0]) / 2), int((p1[1] + p2[1]) / 2)
            lbl = f"{line['name']} : {line['counts']['total']}"
            (tw, th), _ = cv2.getTextSize(lbl, cv2.FONT_HERSHEY_SIMPLEX, 0.42, 1)
            cv2.rectangle(annotated, (mx - 6, my - th - 8), (mx + tw + 6, my + 6), (20, 24, 28), -1)
            cv2.rectangle(annotated, (mx - 6, my - th - 8), (mx + tw + 6, my + 6), col, 1)
            cv2.putText(annotated, lbl, (mx, my), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (255, 255, 255), 1, cv2.LINE_AA)

    # 2. Render Tracked Objects & Trajectories
    for track in tracks:
        tid = track["track_id"]
        cls_name = track["class_name"]
        bbox = track["bbox"]
        color = CLASS_COLORS.get(cls_name, (0, 255, 0))

        if opts["show_trails"] and len(track.get("trajectory", [])) > 1:
            pts = np.array(track["trajectory"], np.int32).reshape((-1, 1, 2))
            cv2.polylines(annotated, [pts], False, color, 2, cv2.LINE_AA)

        if opts["show_boxes"]:
            x1, y1, x2, y2 = [int(v) for v in bbox]
            cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)
            
            label = f"#{tid} {cls_name} {int(track['confidence']*100)}%"
            (lw, lh), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.45, 1)
            cv2.rectangle(annotated, (x1, max(0, y1 - lh - 8)), (x1 + lw + 8, y1), color, -1)
            cv2.putText(annotated, label, (x1 + 4, max(lh + 4, y1 - 4)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1, cv2.LINE_AA)

    # 3. Live HUD Statistics Overlay
    if opts["show_hud"]:
        hud_w, hud_h = 360, 140
        hx = annotated.shape[1] - hud_w - 20
        hy = 20
        overlay = annotated.copy()
        cv2.rectangle(overlay, (hx, hy), (hx + hud_w, hy + hud_h), (15, 20, 25), -1)
        cv2.addWeighted(overlay, 0.75, annotated, 0.25, 0, annotated)
        cv2.rectangle(annotated, (hx, hy), (hx + hud_w, hy + hud_h), (50, 60, 75), 1)

        cv2.putText(annotated, f"SOURCE: {pipeline_state['source_label']}", (hx + 12, hy + 22),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.40, (0, 220, 255), 1, cv2.LINE_AA)
        
        cv2.putText(annotated, f"Total Crossings: {global_counts['total']}", (hx + 12, hy + 48),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.65, (255, 255, 255), 2, cv2.LINE_AA)
        
        stats_line1 = f"Pedestrians: {global_counts['pedestrian']}  |  Bicycles: {global_counts['bicycle']}  |  M/C: {global_counts['motorcycle']}"
        stats_line2 = f"Cars: {global_counts['car']}  |  Buses: {global_counts['bus']}  |  Trucks: {global_counts['truck']}"
        cv2.putText(annotated, stats_line1, (hx + 12, hy + 76), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (200, 210, 220), 1, cv2.LINE_AA)
        cv2.putText(annotated, stats_line2, (hx + 12, hy + 96), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (200, 210, 220), 1, cv2.LINE_AA)

        perf_line = f"FPS: {pipeline_state['current_fps']:.1f} | Engine: TensorRT {pipeline_state['precision']} | Objects: {len(tracks)}"
        cv2.putText(annotated, perf_line, (hx + 12, hy + 124), cv2.FONT_HERSHEY_SIMPLEX, 0.40, (0, 255, 170), 1, cv2.LINE_AA)

    return annotated

_pipeline_thread = None
_pipeline_stop_event = threading.Event()

def pipeline_worker():
    """Continuous background loop executing the 5-stage vision pipeline when active."""
    fps_history = []
    
    while not _pipeline_stop_event.is_set():
        start_time = time.time()

        # Ingestion
        has_active_video, frame, source_label = video_manager.read_frame()
        pipeline_state["source_label"] = source_label

        if "(LOOP)" in source_label:
            # Video restarted at frame 0 - reset tracking to avoid jumping tracklets
            tracker.reset()

        if not has_active_video or not pipeline_state["is_running"]:
            # Standby mode: encode placeholder frame, do NOT run detection or count
            pipeline_state["current_fps"] = 0.0
            pipeline_state["active_tracks_count"] = 0
            _, jpeg = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
            pipeline_state["annotated_frame_jpeg"] = jpeg.tobytes()
            time.sleep(0.05)
            continue

        # Real-time Detection on active video frames
        detections = detector.detect(frame)

        # ByteTrack Multi-Object Tracking
        active_tracks = tracker.update(detections)

        # Virtual Counting Line Geometry
        new_events = analytics.process_tracks(active_tracks)

        # MQTT Dispatching
        for evt in new_events:
            mqtt_service.publish_crossing_event(evt)

        if pipeline_state["total_frames_processed"] % 30 == 0:
            mqtt_service.publish_telemetry(analytics.get_summary()["global_counts"])

        # Frame Annotation & JPEG Encoding
        summary = analytics.get_summary()
        annotated = annotate_frame(frame, active_tracks, summary["lines"], summary["global_counts"])
        
        _, jpeg = cv2.imencode(".jpg", annotated, [cv2.IMWRITE_JPEG_QUALITY, 80])
        pipeline_state["annotated_frame_jpeg"] = jpeg.tobytes()
        pipeline_state["active_tracks_count"] = len(active_tracks)
        pipeline_state["total_frames_processed"] += 1

        elapsed = time.time() - start_time
        fps_history.append(1.0 / max(elapsed, 0.001))
        if len(fps_history) > 30:
            fps_history.pop(0)
        pipeline_state["current_fps"] = sum(fps_history) / len(fps_history)

        target_sleep = max(0.0, (1.0 / 30.0) - elapsed)
        time.sleep(target_sleep)

@asynccontextmanager
async def lifespan(app: FastAPI):
    global _pipeline_thread
    _pipeline_stop_event.clear()
    _pipeline_thread = threading.Thread(target=pipeline_worker, daemon=True)
    _pipeline_thread.start()
    print("[Pipeline] Background vision pipeline initialized in STANDBY.")
    yield
    _pipeline_stop_event.set()
    print("[Pipeline] Background vision pipeline stopped.")

app.router.lifespan_context = lifespan

# --- API Endpoints ---

@app.get("/api/health")
def health_check():
    return {
        "status": "healthy",
        "system": "Traffic and Crosswalk Analytics System",
        "is_running": pipeline_state["is_running"],
        "source_mode": pipeline_state["source_mode"],
        "fps": round(pipeline_state["current_fps"], 1)
    }

@app.get("/api/stats")
def get_stats():
    summary = analytics.get_summary()
    return {
        "global_counts": summary["global_counts"],
        "lines": summary["lines"],
        "recent_events": summary["recent_events"],
        "fps": round(pipeline_state["current_fps"], 1),
        "active_tracks_count": pipeline_state["active_tracks_count"],
        "is_running": pipeline_state["is_running"],
        "source_mode": pipeline_state["source_mode"],
        "source_label": pipeline_state["source_label"],
        "precision": pipeline_state["precision"],
        "current_model": pipeline_state["current_model"],
        "mqtt_status": mqtt_service.get_status()
    }

# --- Video Input & Control Endpoints ---

@app.post("/api/upload_video")
async def upload_video(file: UploadFile = File(...)):
    """Receives user-uploaded video file and runs real-time detection on it."""
    file_path = os.path.join(UPLOAD_DIR, "uploaded_traffic_video.mp4")
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Reset counts for the new video
    reset_counts()
    
    # Load into video manager and activate detection
    video_manager.set_source("file", file_path)
    pipeline_state["is_running"] = True
    pipeline_state["source_mode"] = "file"
    pipeline_state["source_label"] = f"UPLOADED: {file.filename}"

    return {
        "status": "success",
        "message": f"Uploaded {file.filename}. Detection pipeline started on uploaded video.",
        "filename": file.filename
    }

@app.post("/api/control/camera")
def turn_on_camera(device_index: int = 0):
    """Turns ON live webcam / USB camera and activates detection."""
    reset_counts()
    video_manager.set_source("camera", str(device_index))
    pipeline_state["is_running"] = True
    pipeline_state["source_mode"] = "camera"
    pipeline_state["source_label"] = f"LIVE WEBCAM #{device_index}"
    return {"status": "success", "message": "Camera turned on. Running live detection."}

@app.post("/api/control/sample")
def load_sample_video():
    """Loads the pre-packaged smart city traffic clip."""
    sample_path = "backend/uploads/sample_traffic_video.mp4"
    if not os.path.exists(sample_path):
        import backend.generate_sample_video
    reset_counts()
    video_manager.set_source("file", sample_path)
    pipeline_state["is_running"] = True
    pipeline_state["source_mode"] = "file"
    pipeline_state["source_label"] = "SAMPLE TRAFFIC CLIP (1080p)"
    return {"status": "success", "message": "Sample traffic video loaded and running."}

@app.post("/api/control/play")
def play_video():
    video_manager.resume()
    pipeline_state["is_running"] = True
    return {"status": "playing"}

@app.post("/api/control/pause")
def pause_video():
    video_manager.pause()
    pipeline_state["is_running"] = False
    return {"status": "paused"}

@app.post("/api/control/stop")
def stop_video():
    video_manager.stop()
    tracker.reset()
    pipeline_state["is_running"] = False
    pipeline_state["source_mode"] = "standby"
    pipeline_state["source_label"] = "Standby - Waiting for input"
    return {"status": "stopped"}

@app.get("/api/lines")
def get_lines():
    return analytics.get_summary()["lines"]

@app.post("/api/lines")
def update_or_add_line(payload: LineUpdateModel):
    analytics.add_line(
        line_id=payload.line_id,
        name=payload.name,
        p1=tuple(payload.p1),
        p2=tuple(payload.p2),
        direction_type=payload.direction_type,
        allowed_classes=payload.allowed_classes,
        color=payload.color
    )
    return {"status": "success", "line_id": payload.line_id}

@app.delete("/api/lines/{line_id}")
def delete_line(line_id: str):
    if line_id in analytics.lines:
        del analytics.lines[line_id]
        return {"status": "deleted", "line_id": line_id}
    raise HTTPException(status_code=404, detail="Line ID not found")

@app.post("/api/source")
def switch_video_source(payload: SourceChangeModel):
    if payload.mode == "standby":
        stop_video()
    else:
        video_manager.set_source(payload.mode, payload.uri or "")
        pipeline_state["is_running"] = True
        pipeline_state["source_mode"] = payload.mode
    return {"status": "success", "mode": payload.mode}

@app.post("/api/render_options")
def set_render_options(opts: Dict[str, bool]):
    for k, v in opts.items():
        if k in pipeline_state["render_options"]:
            pipeline_state["render_options"][k] = v
    return pipeline_state["render_options"]

@app.get("/api/video_feed")
def video_feed():
    """MJPEG Streaming Response."""
    def frame_generator():
        while True:
            frame_bytes = pipeline_state["annotated_frame_jpeg"]
            if frame_bytes:
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
            time.sleep(0.033)

    return StreamingResponse(frame_generator(), media_type="multipart/x-mixed-replace; boundary=frame")

# --- PipeGen 5-Stage Endpoints ---

@app.get("/api/pipegen/stage1")
def get_stage1_requirements():
    req_path = "backend/pipegen/stage1_requirements.json"
    if os.path.exists(req_path):
        with open(req_path, "r") as f:
            return json.load(f)
    return {"error": "Requirements not found"}

@app.get("/api/pipegen/stage2")
def get_stage2_pipeline_ir():
    return generate_pipeline_ir()

@app.get("/api/pipegen/stage3")
def get_stage3_catalog():
    return {
        "catalog": get_model_catalog(),
        "selected_model": get_model_by_id(pipeline_state["current_model"]),
        "target_classes": TARGET_CLASSES,
        "onnx_spec": export_onnx_specification(pipeline_state["current_model"])
    }

@app.post("/api/pipegen/stage4/compile")
def trigger_compilation(payload: ModelCompileModel):
    metadata = compiler.compile_engine(payload.model_id, payload.precision)
    pipeline_state["current_model"] = payload.model_id
    pipeline_state["precision"] = payload.precision
    return {
        "status": "COMPILATION_COMPLETE",
        "metadata": metadata,
        "benchmark_report": compiler.get_benchmark_comparison(payload.model_id)
    }

@app.get("/api/pipegen/stage4/benchmark")
def get_benchmark_results(model_id: str = "yolov8n"):
    return compiler.get_benchmark_comparison(model_id)

@app.get("/api/pipegen/stage4/report_markdown")
def get_benchmark_markdown(model_id: str = "yolov8n"):
    md = compiler.export_markdown_report(model_id)
    return {"markdown": md}

@app.get("/api/export/json")
def export_json_metadata():
    summary = analytics.get_summary()
    export_payload = {
        "export_metadata": {
            "system": "Traffic and Crosswalk Analytics System",
            "deployment": "Edge Roadside Pole-Mounted Unit",
            "generation_timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "precision": pipeline_state["precision"],
            "model": pipeline_state["current_model"],
            "source": pipeline_state["source_label"]
        },
        "aggregate_counts": summary["global_counts"],
        "lines_summary": summary["lines"],
        "crossing_events": analytics.events_history
    }
    return JSONResponse(
        content=export_payload,
        headers={"Content-Disposition": f"attachment; filename=traffic_analytics_export_{int(time.time())}.json"}
    )

@app.get("/api/export/speed_report")
def export_speed_report(model_id: str = "yolov8n"):
    report_path = f"backend/export/{model_id}_performance_report.md"
    if not os.path.exists(report_path):
        compiler.export_markdown_report(model_id)
    return FileResponse(report_path, media_type="text/markdown", filename=f"{model_id}_speed_report.md")

@app.get("/api/mqtt/status")
def get_mqtt_status():
    return mqtt_service.get_status()

@app.post("/api/stats/reset")
def reset_counts():
    for k in analytics.global_counts:
        analytics.global_counts[k] = 0
    for line in analytics.lines.values():
        line.counts["total"] = 0
        line.counts["inbound"] = 0
        line.counts["outbound"] = 0
        for c in line.counts["classes"]:
            line.counts["classes"][c] = 0
    analytics.events_history.clear()
    analytics.last_crossings.clear()
    tracker.reset()
    return {"status": "counts_reset"}

@app.websocket("/ws/live_telemetry")
async def websocket_telemetry(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            summary = analytics.get_summary()
            payload = {
                "timestamp": time.time(),
                "is_running": pipeline_state["is_running"],
                "source_mode": pipeline_state["source_mode"],
                "source_label": pipeline_state["source_label"],
                "fps": round(pipeline_state["current_fps"], 1),
                "active_tracks_count": pipeline_state["active_tracks_count"],
                "precision": pipeline_state["precision"],
                "model": pipeline_state["current_model"],
                "global_counts": summary["global_counts"],
                "lines": summary["lines"],
                "recent_events": summary["recent_events"][-10:],
                "mqtt_status": mqtt_service.get_status()
            }
            await websocket.send_json(payload)
            await asyncio.sleep(0.1)
    except WebSocketDisconnect:
        pass
    except Exception as e:
        print(f"[WebSocket] Disconnect: {e}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=False)
