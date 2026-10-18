import React from 'react';
import { 
  Activity, 
  Cpu, 
  Radio, 
  RotateCcw, 
  ShieldCheck, 
  Video, 
  Sliders
} from 'lucide-react';

export default function Navbar({ 
  activeTab, 
  setActiveTab, 
  stats, 
  onResetCounts
}) {
  const fps = stats?.fps || 30.0;
  const mqttConnected = stats?.mqtt_status?.connected || false;

  return (
    <header className="app-header">
      <div className="brand-section">
        <div className="brand-icon-box">
          <Activity size={24} />
        </div>
        <div>
          <div className="brand-title">AURA-CROSSWALK // EDGE VISION</div>
          <div className="brand-subtitle">
            <span className="live-pulse"></span>
            POLE-MOUNTED UNIT #042 &bull; NVIDIA JETSON ORIN NANO
          </div>
        </div>
      </div>

      <nav className="nav-tabs">
        <button 
          className={`nav-tab-btn ${activeTab === 'analytics' ? 'active' : ''}`}
          onClick={() => setActiveTab('analytics')}
        >
          <Video size={16} />
          Live Vision & Hub
        </button>
        <button 
          className={`nav-tab-btn ${activeTab === 'pipegen' ? 'active' : ''}`}
          onClick={() => setActiveTab('pipegen')}
        >
          <Sliders size={16} />
          PipeGen 5-Stages
        </button>
        <button 
          className={`nav-tab-btn ${activeTab === 'mqtt' ? 'active' : ''}`}
          onClick={() => setActiveTab('mqtt')}
        >
          <Radio size={16} />
          MQTT Telemetry
        </button>
        <button 
          className={`nav-tab-btn ${activeTab === 'safety' ? 'active' : ''}`}
          onClick={() => setActiveTab('safety')}
        >
          <ShieldCheck size={16} />
          Safety & Insights
        </button>
      </nav>

      <div className="telemetry-pills">

        <div className="stat-pill">
          <Cpu size={14} color="#3b82f6" />
          <span className="label">FPS:</span>
          <span className="value">{fps.toFixed(1)}</span>
        </div>

        <div className="stat-pill">
          <Radio size={14} color={mqttConnected ? '#10b981' : '#f59e0b'} />
          <span className="label">MQTT:</span>
          <span className="value" style={{ color: mqttConnected ? '#10b981' : '#f59e0b' }}>
            {mqttConnected ? 'ONLINE' : 'STANDBY'}
          </span>
        </div>

        <button 
          className="btn-secondary" 
          onClick={onResetCounts}
          title="Reset traffic counters"
          style={{ padding: '8px' }}
        >
          <RotateCcw size={14} />
        </button>
      </div>
    </header>
  );
}
