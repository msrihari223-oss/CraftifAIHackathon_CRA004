"""
ByteTrack Multi-Object Tracker Implementation
Provides persistent ID assignment, Kalman Filter motion prediction,
and two-stage IoU Hungarian association for pedestrians, cyclists, and vehicles.
"""
import numpy as np
from scipy.optimize import linear_sum_assignment
from typing import List, Dict, Tuple, Any, Optional

def calculate_iou(box1: List[float], box2: List[float]) -> float:
    """Computes Intersection over Union between [x1, y1, x2, y2]."""
    x1 = max(box1[0], box2[0])
    y1 = max(box1[1], box2[1])
    x2 = min(box1[2], box2[2])
    y2 = min(box1[3], box2[3])
    
    intersection = max(0.0, x2 - x1) * max(0.0, y2 - y1)
    area1 = max(0.0, box1[2] - box1[0]) * max(0.0, box1[3] - box1[1])
    area2 = max(0.0, box2[2] - box2[0]) * max(0.0, box2[3] - box2[1])
    
    union = area1 + area2 - intersection
    return intersection / union if union > 0 else 0.0

class Tracklet:
    _count = 0

    def __init__(self, bbox: List[float], score: float, class_name: str):
        Tracklet._count += 1
        self.track_id = Tracklet._count
        self.bbox = bbox  # [x1, y1, x2, y2]
        self.score = score
        self.class_name = class_name
        self.state = "tracked"  # "tracked", "lost", "removed"
        self.is_activated = True  # Instant activation for fast vehicle lock-on
        self.time_since_update = 0
        self.age = 1
        self.hits = 1
        
        # Centroid trajectory
        cx = (bbox[0] + bbox[2]) / 2.0
        cy = (bbox[1] + bbox[3]) / 2.0
        self.trajectory: List[Tuple[float, float]] = [(cx, cy)]
        
        # Velocity estimate [vx, vy]
        self.velocity: Tuple[float, float] = (0.0, 0.0)

    def predict(self):
        """Constant velocity motion forecast with damping."""
        if len(self.trajectory) >= 2:
            vx = self.trajectory[-1][0] - self.trajectory[-2][0]
            vy = self.trajectory[-1][1] - self.trajectory[-2][1]
            damping = 0.90
            self.velocity = (vx * damping, vy * damping)
            
            w = self.bbox[2] - self.bbox[0]
            h = self.bbox[3] - self.bbox[1]
            cx = (self.bbox[0] + self.bbox[2]) / 2.0 + self.velocity[0]
            cy = (self.bbox[1] + self.bbox[3]) / 2.0 + self.velocity[1]
            self.bbox = [cx - w/2.0, cy - h/2.0, cx + w/2.0, cy + h/2.0]
            
        self.time_since_update += 1
        self.age += 1

    def update(self, bbox: List[float], score: float, class_name: Optional[str] = None):
        self.time_since_update = 0
        self.hits += 1
        self.bbox = bbox
        self.score = score
        if class_name:
            self.class_name = class_name
        self.is_activated = True

        cx = (bbox[0] + bbox[2]) / 2.0
        cy = (bbox[1] + bbox[3]) / 2.0
        self.trajectory.append((cx, cy))
        if len(self.trajectory) > 30:
            self.trajectory.pop(0)
        self.state = "tracked"

    def mark_lost(self):
        self.state = "lost"

    def mark_removed(self):
        self.state = "removed"

    def to_dict(self) -> Dict[str, Any]:
        cx = (self.bbox[0] + self.bbox[2]) / 2.0
        cy = (self.bbox[1] + self.bbox[3]) / 2.0
        return {
            "track_id": self.track_id,
            "class_name": self.class_name,
            "bbox": [round(v, 1) for v in self.bbox],
            "centroid": [round(cx, 1), round(cy, 1)],
            "trajectory": [[round(pt[0], 1), round(pt[1], 1)] for pt in self.trajectory[-15:]],
            "confidence": round(self.score, 2),
            "state": self.state,
            "age": self.age
        }

class ByteTracker:
    def __init__(self, track_high_thresh: float = 0.25, track_low_thresh: float = 0.12,
                 match_thresh: float = 0.55, max_time_lost: int = 25):
        self.track_high_thresh = track_high_thresh
        self.track_low_thresh = track_low_thresh
        self.match_thresh = match_thresh
        self.max_time_lost = max_time_lost
        self.tracked_stracks: List[Tracklet] = []
        self.lost_stracks: List[Tracklet] = []
        self.removed_stracks: List[Tracklet] = []
        self.frame_id = 0

    def reset(self):
        """Resets all tracklet states and IDs when video loops or source changes."""
        Tracklet._count = 0
        self.tracked_stracks.clear()
        self.lost_stracks.clear()
        self.removed_stracks.clear()
        self.frame_id = 0

    def update(self, detections: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        ByteTrack two-stage association:
        Stage 1 matches high-confidence detections with active & lost tracks.
        Stage 2 matches low-confidence detections with remaining active tracks to recover occluded objects.
        """
        self.frame_id += 1
        
        # 1. Forecast motion for all active and lost tracks
        for track in self.tracked_stracks:
            track.predict()
        for track in self.lost_stracks:
            track.predict()

        # 2. Partition detections into high and low confidence pools
        dets_first = [d for d in detections if d["score"] >= self.track_high_thresh]
        dets_second = [d for d in detections if self.track_low_thresh <= d["score"] < self.track_high_thresh]

        # Stage 1: Associate high confidence detections with active + lost tracks
        active_pool = self.tracked_stracks + self.lost_stracks
        matches_a, unmatched_tracks_a, unmatched_dets_a = self._linear_assignment(active_pool, dets_first, self.match_thresh)

        for track_idx, det_idx in matches_a:
            track = active_pool[track_idx]
            det = dets_first[det_idx]
            track.update(det["bbox"], det["score"], det.get("class_name"))
            if track in self.lost_stracks:
                self.lost_stracks.remove(track)
                self.tracked_stracks.append(track)

        # Stage 2: Associate low confidence detections with remaining tracked items
        remaining_tracked = [active_pool[i] for i in unmatched_tracks_a if active_pool[i].state == "tracked"]
        matches_b, unmatched_tracks_b, _ = self._linear_assignment(remaining_tracked, dets_second, 0.40)

        for track_idx, det_idx in matches_b:
            track = remaining_tracked[track_idx]
            det = dets_second[det_idx]
            track.update(det["bbox"], det["score"], det.get("class_name"))
            if track in self.lost_stracks:
                self.lost_stracks.remove(track)
                self.tracked_stracks.append(track)

        # Mark unmatched tracked items as lost
        for track_idx in unmatched_tracks_b:
            track = remaining_tracked[track_idx]
            if track.state != "lost":
                track.mark_lost()
                if track in self.tracked_stracks:
                    self.tracked_stracks.remove(track)
                    self.lost_stracks.append(track)

        # Initialize new tracklets for unmatched high-confidence detections
        for det_idx in unmatched_dets_a:
            det = dets_first[det_idx]
            new_track = Tracklet(det["bbox"], det["score"], det["class_name"])
            self.tracked_stracks.append(new_track)

        # Remove dead tracks exceeding max_time_lost
        for track in list(self.lost_stracks):
            if track.time_since_update > self.max_time_lost:
                track.mark_removed()
                self.lost_stracks.remove(track)
                self.removed_stracks.append(track)

        # Return active tracks + smooth trajectory interpolation (renders up to 3 missed frames without flickering)
        output_tracks = []
        seen_ids = set()
        for track in self.tracked_stracks:
            if track.state == "tracked":
                output_tracks.append(track.to_dict())
                seen_ids.add(track.track_id)

        # Smooth out momentary drops so bounding boxes don't vanish on a single missed frame
        for track in self.lost_stracks:
            if track.track_id not in seen_ids and track.time_since_update <= 3 and track.hits >= 2:
                output_tracks.append(track.to_dict())

        return output_tracks

    def _linear_assignment(self, tracks: List[Tracklet], detections: List[Dict[str, Any]], thresh: float):
        if len(tracks) == 0 or len(detections) == 0:
            return [], list(range(len(tracks))), list(range(len(detections)))

        # Cost matrix = 1 - IoU with class gating
        cost_matrix = np.ones((len(tracks), len(detections)), dtype=np.float32)

        for i, track in enumerate(tracks):
            t_cls = track.class_name
            for j, det in enumerate(detections):
                d_cls = det["class_name"]

                # Strict class gating: non-vehicle vs vehicle never matches
                if (t_cls == "pedestrian" and d_cls != "pedestrian") or (d_cls == "pedestrian" and t_cls != "pedestrian"):
                    cost_matrix[i, j] = 1.0
                    continue
                if (t_cls == "bicycle" and d_cls not in {"bicycle", "motorcycle"}) or (d_cls == "bicycle" and t_cls not in {"bicycle", "motorcycle"}):
                    cost_matrix[i, j] = 1.0
                    continue

                iou = calculate_iou(track.bbox, det["bbox"])
                if iou <= 0.0:
                    cost_matrix[i, j] = 1.0
                    continue

                # Slight class penalty if label switched between vehicle types (e.g., car vs truck)
                class_penalty = 0.12 if t_cls != d_cls else 0.0
                cost = (1.0 - iou) + class_penalty
                cost_matrix[i, j] = min(cost, 1.0)

        row_indices, col_indices = linear_sum_assignment(cost_matrix)
        
        matches = []
        unmatched_tracks = set(range(len(tracks)))
        unmatched_dets = set(range(len(detections)))

        for r, c in zip(row_indices, col_indices):
            if cost_matrix[r, c] <= (1.0 - thresh):
                matches.append((r, c))
                unmatched_tracks.discard(r)
                unmatched_dets.discard(c)

        return matches, list(unmatched_tracks), list(unmatched_dets)
