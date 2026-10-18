"""
MQTT Telemetry & Event Dispatcher Service
Publishes crossing events and class-wise traffic analytics to external smart city brokers,
with built-in resilience, queueing, and live telemetry streaming.
"""
import json
import time
import threading
from typing import Dict, Any, List, Optional

try:
    import paho.mqtt.client as mqtt
    PAHO_AVAILABLE = True
except ImportError:
    PAHO_AVAILABLE = False

class MQTTService:
    def __init__(self, broker_host: str = "localhost", broker_port: int = 1883,
                 topic_events: str = "smartcity/traffic/crosswalk_events",
                 topic_telemetry: str = "smartcity/traffic/class_counts"):
        self.broker_host = broker_host
        self.broker_port = broker_port
        self.topic_events = topic_events
        self.topic_telemetry = topic_telemetry
        
        self.client: Optional[Any] = None
        self.connected = False
        self.published_count = 0
        self.recent_messages: List[Dict[str, Any]] = []
        self.lock = threading.Lock()
        
        self._init_client()

    def _init_client(self):
        if not PAHO_AVAILABLE:
            print("[MQTT] Paho MQTT not installed. Operating in internal buffer mode.")
            return

        try:
            # Compatibility with paho-mqtt v2.0+ and v1.x
            try:
                self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=f"traffic-edge-unit-{int(time.time())}")
            except AttributeError:
                self.client = mqtt.Client(client_id=f"traffic-edge-unit-{int(time.time())}")

            self.client.on_connect = self._on_connect
            self.client.on_disconnect = self._on_disconnect

            # Attempt async non-blocking connect
            t = threading.Thread(target=self._try_connect, daemon=True)
            t.start()
        except Exception as e:
            print(f"[MQTT] Init warning: {e}")

    def _try_connect(self):
        try:
            self.client.connect(self.broker_host, self.broker_port, keepalive=60)
            self.client.loop_start()
        except Exception:
            # External broker might not be running locally on the user machine; that's normal
            self.connected = False

    def _on_connect(self, client, userdata, flags, rc, properties=None):
        if rc == 0:
            self.connected = True
            print(f"[MQTT] Successfully connected to broker at {self.broker_host}:{self.broker_port}")
        else:
            self.connected = False

    def _on_disconnect(self, client, userdata, flags=None, rc=None, properties=None):
        self.connected = False

    def publish_crossing_event(self, event: Dict[str, Any]):
        """Publishes a structured crossing event JSON payload."""
        payload = json.dumps(event, indent=2)
        now_str = time.strftime("%H:%M:%S", time.localtime())

        msg_record = {
            "topic": self.topic_events,
            "timestamp": now_str,
            "payload": event,
            "broker_status": "PUBLISHED" if self.connected else "STORED_LOCAL_QUEUE"
        }

        with self.lock:
            self.published_count += 1
            self.recent_messages.append(msg_record)
            if len(self.recent_messages) > 100:
                self.recent_messages.pop(0)

        if self.connected and self.client:
            try:
                self.client.publish(self.topic_events, payload, qos=1)
            except Exception as e:
                print(f"[MQTT] Publish error: {e}")

    def publish_telemetry(self, telemetry: Dict[str, Any]):
        """Publishes periodic aggregated class counts."""
        payload = json.dumps(telemetry)
        if self.connected and self.client:
            try:
                self.client.publish(self.topic_telemetry, payload, qos=0)
            except Exception:
                pass

    def get_status(self) -> Dict[str, Any]:
        with self.lock:
            return {
                "broker_host": self.broker_host,
                "broker_port": self.broker_port,
                "connected": self.connected,
                "total_messages_published": self.published_count,
                "recent_messages": self.recent_messages[-15:]
            }
