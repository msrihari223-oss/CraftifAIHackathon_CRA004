import React, { useState } from 'react';
import { Radio, Terminal, Copy, Check, Send, CheckCircle2, AlertTriangle } from 'lucide-react';

export default function MqttConsole({ mqttStatus }) {
  const [copiedIdx, setCopiedIdx] = useState(null);
  const status = mqttStatus || { connected: false, total_messages_published: 0, recent_messages: [] };

  const handleCopy = (payload, idx) => {
    navigator.clipboard.writeText(JSON.stringify(payload, null, 2));
    setCopiedIdx(idx);
    setTimeout(() => setCopiedIdx(null), 2000);
  };

  return (
    <div className="glass-panel" style={{ padding: 28 }}>
      <div className="panel-header">
        <div>
          <h2 style={{ fontFamily: 'var(--font-heading)', fontSize: 20, display: 'flex', alignItems: 'center', gap: 10 }}>
            <Radio size={22} color={status.connected ? '#10B981' : '#F59E0B'} />
            MQTT Telemetry &amp; External Monitoring Bridge
          </h2>
          <p style={{ color: 'var(--text-muted)', fontSize: 13, marginTop: 4 }}>
            Publishes live crossing events and class aggregations to city traffic control centers.
          </p>
        </div>

        <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
          <div className="stat-pill">
            <span className="label">BROKER:</span>
            <span className="value">{status.broker_host}:{status.broker_port}</span>
          </div>

          <div className="stat-pill">
            <span className="label">STATUS:</span>
            <span className="value" style={{ color: status.connected ? '#10b981' : '#f59e0b' }}>
              {status.connected ? 'CONNECTED (QoS 1)' : 'STANDBY / BUFFERING'}
            </span>
          </div>

          <div className="stat-pill">
            <span className="label">SENT:</span>
            <span className="value">{status.total_messages_published}</span>
          </div>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20, marginTop: 20 }}>
        {/* Active Topics */}
        <div style={{ background: 'rgba(255,255,255,0.02)', padding: 18, borderRadius: 12, border: '1px solid var(--border-subtle)' }}>
          <h3 style={{ fontSize: 14, color: 'var(--color-cyan)', marginBottom: 12 }}>
            Configured MQTT Topics
          </h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div style={{ padding: 12, background: 'rgba(0,0,0,0.3)', borderRadius: 8, border: '1px solid var(--border-subtle)' }}>
              <div style={{ fontFamily: 'var(--font-mono)', fontSize: 13, color: '#38bdf8' }}>
                smartcity/traffic/crosswalk_events
              </div>
              <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 4 }}>
                Instant payload upon line crossing: Track ID, class, direction, timestamp, updated counts.
              </div>
            </div>

            <div style={{ padding: 12, background: 'rgba(0,0,0,0.3)', borderRadius: 8, border: '1px solid var(--border-subtle)' }}>
              <div style={{ fontFamily: 'var(--font-mono)', fontSize: 13, color: 'var(--color-emerald)' }}>
                smartcity/traffic/class_counts
              </div>
              <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 4 }}>
                1 Hz periodic telemetry broadcast of cumulative pedestrians, cyclists, cars, buses, trucks.
              </div>
            </div>
          </div>
        </div>

        {/* MQTT Specification Accordion */}
        <div style={{ background: 'rgba(255,255,255,0.02)', padding: 18, borderRadius: 12, border: '1px solid var(--border-subtle)' }}>
          <h3 style={{ fontSize: 14, color: 'var(--text-secondary)', marginBottom: 12 }}>
            Smart City Ingestion Contract
          </h3>
          <div style={{ fontSize: 12, color: 'var(--text-secondary)', lineHeight: 1.6 }}>
            The roadside unit acts as an autonomous MQTT publisher. Traffic management centers can subscribe with standard MQTT clients (e.g., Mosquitto, HiveMQ, AWS IoT Core) to dynamically update traffic light timings, detect crosswalk demand, and log modal split statistics.
          </div>
        </div>
      </div>

      {/* Live Stream Terminal */}
      <div style={{ marginTop: 24 }}>
        <h3 style={{ fontSize: 14, color: 'var(--text-secondary)', marginBottom: 10, display: 'flex', alignItems: 'center', gap: 6 }}>
          <Terminal size={16} />
          Live Published MQTT Messages
        </h3>

        <div className="code-preview-box" style={{ maxHeight: 360 }}>
          {status.recent_messages.length === 0 ? (
            <div style={{ color: 'var(--text-muted)', textAlign: 'center', padding: 20 }}>
              No messages dispatched yet. Waiting for crossing triggers...
            </div>
          ) : (
            status.recent_messages.map((msg, i) => (
              <div key={i} style={{ borderBottom: '1px solid rgba(255,255,255,0.05)', paddingBottom: 10, marginBottom: 10 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', color: '#38bdf8', fontSize: 11 }}>
                  <span>[{msg.timestamp}] TOPIC: {msg.topic} &bull; {msg.broker_status}</span>
                  <button 
                    onClick={() => handleCopy(msg.payload, i)}
                    style={{ background: 'transparent', border: 'none', color: 'var(--text-muted)', cursor: 'pointer' }}
                  >
                    {copiedIdx === i ? <Check size={12} color="#10b981" /> : <Copy size={12} />}
                  </button>
                </div>
                <pre style={{ marginTop: 4, color: '#e2e8f0', fontSize: 11 }}>
                  {JSON.stringify(msg.payload, null, 2)}
                </pre>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
