import React, { useState, useEffect, useRef } from 'react';
import Navbar from './components/Navbar';
import ClassStatsCards from './components/ClassStatsCards';
import LiveVideoCanvas from './components/LiveVideoCanvas';
import CountingLinesPanel from './components/CountingLinesPanel';
import EventsFeed from './components/EventsFeed';
import PipeGenExplorer from './components/PipeGenExplorer';
import MqttConsole from './components/MqttConsole';
import SafetyInsights from './components/SafetyInsights';

const BACKEND_URL = 'http://localhost:8000';
const WS_URL = 'ws://localhost:8000/ws/live_telemetry';

export default function App() {
  const [activeTab, setActiveTab] = useState('analytics');
  const [stats, setStats] = useState({
    global_counts: { total: 0, pedestrian: 0, bicycle: 0, motorcycle: 0, car: 0, bus: 0, truck: 0 },
    lines: {},
    recent_events: [],
    fps: 30.0,
    precision: 'INT8',
    mqtt_status: { connected: false, total_messages_published: 0, recent_messages: [] }
  });

  const [renderOptions, setRenderOptions] = useState({
    show_boxes: true,
    show_tracks: true,
    show_lines: true,
    show_trails: true,
    show_hud: true
  });

  const wsRef = useRef(null);

  // Initialize WebSocket and polling fallback
  useEffect(() => {
    let isSubscribed = true;

    const connectWebSocket = () => {
      try {
        const ws = new WebSocket(WS_URL);
        wsRef.current = ws;

        ws.onopen = () => {
          console.log('[Telemetry WS] Connected to live pipeline stream.');
        };

        ws.onmessage = (event) => {
          if (!isSubscribed) return;
          try {
            const data = JSON.parse(event.data);
            setStats((prev) => ({
              ...prev,
              global_counts: data.global_counts || prev.global_counts,
              lines: data.lines || prev.lines,
              recent_events: data.recent_events || prev.recent_events,
              fps: data.fps ?? prev.fps,
              precision: data.precision || prev.precision,
              mqtt_status: data.mqtt_status || prev.mqtt_status
            }));
          } catch (e) {
            console.error('WS Parse Error', e);
          }
        };

        ws.onclose = () => {
          // Reconnect after 2 seconds if still mounted
          if (isSubscribed) {
            setTimeout(connectWebSocket, 2000);
          }
        };

        ws.onerror = () => {
          ws.close();
        };
      } catch (e) {
        console.warn('WS Init Error, falling back to HTTP polling');
      }
    };

    connectWebSocket();

    // Secondary HTTP Poller ensuring state freshness even if WebSocket is disconnected
    const interval = setInterval(() => {
      fetch(`${BACKEND_URL}/api/stats`)
        .then((r) => r.json())
        .then((data) => {
          if (isSubscribed && (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN)) {
            setStats(data);
          }
        })
        .catch(() => {});
    }, 1000);

    return () => {
      isSubscribed = false;
      clearInterval(interval);
      if (wsRef.current) wsRef.current.close();
    };
  }, []);

  const fetchLatestStats = async () => {
    try {
      const res = await fetch(`${BACKEND_URL}/api/stats`);
      const data = await res.json();
      setStats(data);
    } catch (e) {}
  };

  const handleToggleRenderOption = async (key, val) => {
    const updated = { ...renderOptions, [key]: val };
    setRenderOptions(updated);
    try {
      await fetch(`${BACKEND_URL}/api/render_options`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(updated)
      });
    } catch (e) {
      console.error(e);
    }
  };

  const handleSwitchSource = async (mode, uri) => {
    try {
      await fetch(`${BACKEND_URL}/api/source`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ mode, uri })
      });
    } catch (e) {
      console.error(e);
    }
  };

  const handleSaveLine = async (lineData) => {
    try {
      await fetch(`${BACKEND_URL}/api/lines`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(lineData)
      });
      // Refresh lines
      const res = await fetch(`${BACKEND_URL}/api/lines`);
      const updatedLines = await res.json();
      setStats((prev) => ({ ...prev, lines: updatedLines }));
    } catch (e) {
      console.error(e);
    }
  };

  const handleDeleteLine = async (lineId) => {
    try {
      await fetch(`${BACKEND_URL}/api/lines/${lineId}`, { method: 'DELETE' });
      const updatedLines = { ...stats.lines };
      delete updatedLines[lineId];
      setStats((prev) => ({ ...prev, lines: updatedLines }));
    } catch (e) {
      console.error(e);
    }
  };

  const handleResetCounts = async () => {
    try {
      await fetch(`${BACKEND_URL}/api/stats/reset`, { method: 'POST' });
    } catch (e) {
      console.error(e);
    }
  };

  return (
    <div className="app-container">
      <Navbar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        stats={stats}
        onResetCounts={handleResetCounts}
      />

      <main className="main-content">
        {activeTab === 'analytics' && (
          <>
            <ClassStatsCards globalCounts={stats.global_counts} />

            <div className="workspace-grid">
              <LiveVideoCanvas
                renderOptions={renderOptions}
                onToggleRenderOption={handleToggleRenderOption}
                backendUrl={BACKEND_URL}
                stats={stats}
                onRefreshStats={fetchLatestStats}
              />

              <div className="side-analytics-panel">
                <CountingLinesPanel
                  lines={stats.lines}
                  onSaveLine={handleSaveLine}
                  onDeleteLine={handleDeleteLine}
                />

                <EventsFeed events={stats.recent_events} />
              </div>
            </div>
          </>
        )}

        {activeTab === 'pipegen' && <PipeGenExplorer backendUrl={BACKEND_URL} />}

        {activeTab === 'mqtt' && <MqttConsole mqttStatus={stats.mqtt_status} />}

        {activeTab === 'safety' && <SafetyInsights globalCounts={stats.global_counts} />}
      </main>
    </div>
  );
}
