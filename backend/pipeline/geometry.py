"""
Virtual Counting Lines & Geometric Intersection Engine
Provides 2D line-segment intersection, directional vector orientation,
debounce logic to prevent duplicate counting, and class-wise traffic statistics.
"""
import time
import math
from typing import List, Dict, Tuple, Optional, Any

def ccw(A: Tuple[float, float], B: Tuple[float, float], C: Tuple[float, float]) -> bool:
    """Tests if 3 points are in counter-clockwise order."""
    return (C[1] - A[1]) * (B[0] - A[0]) > (B[1] - A[1]) * (C[0] - A[0])

def intersect(A: Tuple[float, float], B: Tuple[float, float], C: Tuple[float, float], D: Tuple[float, float]) -> bool:
    """Returns True if line segment AB and CD intersect."""
    return ccw(A, C, D) != ccw(B, C, D) and ccw(A, B, C) != ccw(A, B, D)

class VirtualCountingLine:
    def __init__(self, line_id: str, name: str, p1: Tuple[int, int], p2: Tuple[int, int], 
                 direction_type: str = "both", allowed_classes: Optional[List[str]] = None,
                 color: str = "#EF4444"):
        self.line_id = line_id
        self.name = name
        self.p1 = p1
        self.p2 = p2
        self.direction_type = direction_type  # "both", "inbound", "outbound"
        self.allowed_classes = allowed_classes or ["pedestrian", "bicycle", "motorcycle", "car", "bus", "truck"]
        self.color = color
        self.counts = {
            "total": 0,
            "inbound": 0,
            "outbound": 0,
            "classes": {
                "pedestrian": 0,
                "bicycle": 0,
                "motorcycle": 0,
                "car": 0,
                "bus": 0,
                "truck": 0
            }
        }

    def check_crossing(self, prev_pos: Tuple[float, float], curr_pos: Tuple[float, float]) -> Optional[str]:
        """
        Checks if the segment from prev_pos to curr_pos intersects the line.
        Returns crossing direction ('Inbound' or 'Outbound') if crossing occurs, else None.
        """
        if not intersect(prev_pos, curr_pos, self.p1, self.p2):
            return None
        
        # Determine direction via 2D cross product:
        # Vector L: P1 -> P2
        # Vector T: prev_pos -> curr_pos
        lx = self.p2[0] - self.p1[0]
        ly = self.p2[1] - self.p1[1]
        tx = curr_pos[0] - prev_pos[0]
        ty = curr_pos[1] - prev_pos[1]
        
        cross_product = (lx * ty) - (ly * tx)
        direction = "Inbound" if cross_product > 0 else "Outbound"
        
        if self.direction_type == "inbound" and direction != "Inbound":
            return None
        if self.direction_type == "outbound" and direction != "Outbound":
            return None
            
        return direction

class TrafficAnalyticsEngine:
    def __init__(self, debounce_seconds: float = 3.0):
        self.debounce_seconds = debounce_seconds
        self.lines: Dict[str, VirtualCountingLine] = {}
        self.last_crossings: Dict[Tuple[int, str], float] = {}  # (track_id, line_id) -> timestamp
        self.events_history: List[Dict[str, Any]] = []
        self.global_counts = {
            "total": 0,
            "pedestrian": 0,
            "bicycle": 0,
            "motorcycle": 0,
            "car": 0,
            "bus": 0,
            "truck": 0
        }
        self.hourly_throughput: Dict[str, int] = {}
        self.setup_default_lines()

    def setup_default_lines(self):
        """Sets up default virtual counting lines for crosswalks and traffic lanes."""
        self.add_line(
            line_id="crosswalk_north",
            name="Crosswalk North (Pedestrian / Cyclist)",
            p1=(340, 480),
            p2=(940, 480),
            direction_type="both",
            allowed_classes=["pedestrian", "bicycle"],
            color="#10B981"
        )
        self.add_line(
            line_id="intersection_inbound",
            name="Main Ave Inbound (Vehicular)",
            p1=(200, 680),
            p2=(700, 680),
            direction_type="both",
            allowed_classes=["car", "motorcycle", "bus", "truck", "bicycle"],
            color="#3B82F6"
        )
        self.add_line(
            line_id="intersection_outbound",
            name="Main Ave Outbound (Vehicular)",
            p1=(720, 680),
            p2=(1220, 680),
            direction_type="both",
            allowed_classes=["car", "motorcycle", "bus", "truck", "bicycle"],
            color="#F59E0B"
        )
        self.add_line(
            line_id="crosswalk_south",
            name="Crosswalk South (Mid-Block)",
            p1=(380, 240),
            p2=(880, 240),
            direction_type="both",
            allowed_classes=["pedestrian", "bicycle"],
            color="#EC4899"
        )

    def add_line(self, line_id: str, name: str, p1: Tuple[int, int], p2: Tuple[int, int],
                 direction_type: str = "both", allowed_classes: Optional[List[str]] = None,
                 color: str = "#EF4444"):
        self.lines[line_id] = VirtualCountingLine(
            line_id=line_id,
            name=name,
            p1=p1,
            p2=p2,
            direction_type=direction_type,
            allowed_classes=allowed_classes,
            color=color
        )

    def update_line_coordinates(self, line_id: str, p1: Tuple[int, int], p2: Tuple[int, int]):
        if line_id in self.lines:
            self.lines[line_id].p1 = p1
            self.lines[line_id].p2 = p2

    def process_tracks(self, tracks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Evaluates active track trajectories against all counting lines.
        Generates structured event metadata when a valid crossing is detected.
        """
        now = time.time()
        new_events = []

        for track in tracks:
            track_id = track.get("track_id")
            cls_name = track.get("class_name", "car")
            trajectory = track.get("trajectory", [])
            confidence = track.get("confidence", 0.85)

            if len(trajectory) < 2:
                continue

            prev_pt = trajectory[-2]
            curr_pt = trajectory[-1]

            for line_id, line in self.lines.items():
                if cls_name not in line.allowed_classes:
                    continue

                # Check duplicate crossing debounce
                debounce_key = (track_id, line_id)
                last_time = self.last_crossings.get(debounce_key, 0)
                if now - last_time < self.debounce_seconds:
                    continue

                direction = line.check_crossing(prev_pt, curr_pt)
                if direction:
                    # Valid Crossing Event!
                    self.last_crossings[debounce_key] = now
                    
                    # Update line counts
                    line.counts["total"] += 1
                    if direction == "Inbound":
                        line.counts["inbound"] += 1
                    else:
                        line.counts["outbound"] += 1
                    line.counts["classes"][cls_name] = line.counts["classes"].get(cls_name, 0) + 1

                    # Update global counts
                    self.global_counts["total"] += 1
                    self.global_counts[cls_name] = self.global_counts.get(cls_name, 0) + 1

                    # Estimate speed in km/h based on pixel movement & geometry
                    dx = curr_pt[0] - prev_pt[0]
                    dy = curr_pt[1] - prev_pt[1]
                    pixel_dist = math.sqrt(dx*dx + dy*dy)
                    # Calibration scale: approx 15 pixels/meter at 30 fps
                    speed_kmh = round((pixel_dist / 15.0) * 30.0 * 3.6, 1)
                    if cls_name == "pedestrian":
                        speed_kmh = min(speed_kmh, 8.5)
                    elif cls_name == "bicycle":
                        speed_kmh = min(speed_kmh, 28.0)

                    # Build structured event JSON
                    event = {
                        "event_id": f"EVT-{int(now * 1000)}-{track_id}",
                        "tracked_object_id": track_id,
                        "object_class": cls_name,
                        "crossing_direction": direction,
                        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S.", time.gmtime(now)) + f"{int((now % 1)*1000):03d}Z",
                        "unix_timestamp": now,
                        "line_id": line.line_id,
                        "line_name": line.name,
                        "confidence": round(float(confidence), 2),
                        "speed_kmh": speed_kmh,
                        "updated_count": dict(self.global_counts)
                    }

                    new_events.append(event)
                    self.events_history.append(event)
                    if len(self.events_history) > 200:
                        self.events_history.pop(0)

        return new_events

    def get_summary(self) -> Dict[str, Any]:
        return {
            "global_counts": self.global_counts,
            "lines": {
                lid: {
                    "line_id": line.line_id,
                    "name": line.name,
                    "p1": line.p1,
                    "p2": line.p2,
                    "color": line.color,
                    "direction_type": line.direction_type,
                    "allowed_classes": line.allowed_classes,
                    "counts": line.counts
                }
                for lid, line in self.lines.items()
            },
            "recent_events": self.events_history[-20:]
        }
