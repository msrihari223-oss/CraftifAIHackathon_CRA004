import React, { useState, useRef } from 'react';
import { 
  Eye, 
  Hash, 
  GitCommit, 
  Navigation, 
  LayoutDashboard, 
  Camera, 
  Upload, 
  Play, 
  Pause, 
  Square, 
  Film,
  CheckCircle2,
  AlertCircle
} from 'lucide-react';

export default function LiveVideoCanvas({ 
  renderOptions, 
  onToggleRenderOption, 
  backendUrl,
  stats,
  onRefreshStats
}) {
  const [isUploading, setIsUploading] = useState(false);
  const [uploadMessage, setUploadMessage] = useState(null);
  const fileInputRef = useRef(null);

  const isRunning = stats?.is_running || false;
  const sourceLabel = stats?.source_label || 'Standby';

  const handleFileUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setIsUploading(true);
    setUploadMessage('Uploading video to edge pipeline...');

    const formData = new FormData();
    formData.append('file', file);

    try {
      const res = await fetch(`${backendUrl}/api/upload_video`, {
        method: 'POST',
        body: formData,
      });
      const data = await res.json();
      setUploadMessage(`Loaded: ${file.name}. Real-time detection active!`);
      setTimeout(() => setUploadMessage(null), 4000);
      onRefreshStats();
    } catch (err) {
      setUploadMessage('Upload failed. Please check file format.');
      setTimeout(() => setUploadMessage(null), 4000);
    } finally {
      setIsUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  const handleTurnOnCamera = async () => {
    try {
      await fetch(`${backendUrl}/api/control/camera`, { method: 'POST' });
      onRefreshStats();
    } catch (err) {
      console.error(err);
    }
  };

  const handleLoadSample = async () => {
    try {
      await fetch(`${backendUrl}/api/control/sample`, { method: 'POST' });
      onRefreshStats();
    } catch (err) {
      console.error(err);
    }
  };

  const handlePlay = async () => {
    try {
      await fetch(`${backendUrl}/api/control/play`, { method: 'POST' });
      onRefreshStats();
    } catch (err) {
      console.error(err);
    }
  };

  const handlePause = async () => {
    try {
      await fetch(`${backendUrl}/api/control/pause`, { method: 'POST' });
      onRefreshStats();
    } catch (err) {
      console.error(err);
    }
  };

  const handleStop = async () => {
    try {
      await fetch(`${backendUrl}/api/control/stop`, { method: 'POST' });
      onRefreshStats();
    } catch (err) {
      console.error(err);
    }
  };

  const videoStreamUrl = `${backendUrl}/api/video_feed`;

  return (
    <div className="video-section">
      {/* Primary Control Bar */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '12px 18px',
        background: 'var(--bg-card)',
        border: '1px solid var(--border-subtle)',
        borderRadius: 'var(--radius-md)',
        flexWrap: 'wrap',
        gap: 12
      }}>
        {/* Source Action Buttons */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <button 
            className="btn-primary"
            onClick={handleTurnOnCamera}
            title="Start live detection on Webcam / USB Camera"
            style={{ background: 'linear-gradient(135deg, #10b981, #059669)' }}
          >
            <Camera size={15} />
            Turn On Live Camera
          </button>

          <input 
            type="file" 
            ref={fileInputRef} 
            onChange={handleFileUpload} 
            accept="video/*" 
            style={{ display: 'none' }} 
          />

          <button 
            className="btn-primary"
            onClick={() => fileInputRef.current?.click()}
            title="Upload MP4, AVI or MKV traffic video to detect objects"
            disabled={isUploading}
          >
            <Upload size={15} />
            {isUploading ? 'Uploading Video...' : 'Upload Traffic Video'}
          </button>

          <button 
            className="btn-secondary"
            onClick={handleLoadSample}
            title="Load sample 1080p smart city traffic clip"
          >
            <Film size={15} />
            Load Sample Video
          </button>
        </div>

        {/* Video Playback Controls */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          {isRunning ? (
            <button 
              className="btn-secondary"
              onClick={handlePause}
              title="Pause detection"
              style={{ color: '#f59e0b' }}
            >
              <Pause size={14} />
              Pause
            </button>
          ) : (
            <button 
              className="btn-secondary"
              onClick={handlePlay}
              title="Resume detection"
              style={{ color: '#10b981' }}
            >
              <Play size={14} />
              Play
            </button>
          )}

          <button 
            className="btn-secondary"
            onClick={handleStop}
            title="Stop detection and return to standby"
            style={{ color: '#f43f5e' }}
          >
            <Square size={14} />
            Stop
          </button>
        </div>
      </div>

      {uploadMessage && (
        <div style={{
          padding: '8px 16px',
          borderRadius: 8,
          background: 'rgba(6, 182, 212, 0.15)',
          border: '1px solid rgba(6, 182, 212, 0.3)',
          color: '#38bdf8',
          fontSize: 12,
          display: 'flex',
          alignItems: 'center',
          gap: 8
        }}>
          <CheckCircle2 size={14} />
          {uploadMessage}
        </div>
      )}

      {/* Video Container Canvas */}
      <div className="video-container">
        <img 
          src={videoStreamUrl} 
          alt="Live Roadside Camera Vision Stream" 
          className="video-stream-img"
          onError={(e) => {
            setTimeout(() => {
              e.target.src = `${videoStreamUrl}?t=${Date.now()}`;
            }, 2000);
          }}
        />
      </div>

      {/* Toggles Toolbar */}
      <div className="video-toolbar">
        <div className="toggle-group">
          <button 
            className={`toggle-btn ${renderOptions.show_boxes ? 'active' : ''}`}
            onClick={() => onToggleRenderOption('show_boxes', !renderOptions.show_boxes)}
          >
            <Eye size={14} />
            Bounding Boxes
          </button>

          <button 
            className={`toggle-btn ${renderOptions.show_tracks ? 'active' : ''}`}
            onClick={() => onToggleRenderOption('show_tracks', !renderOptions.show_tracks)}
          >
            <Hash size={14} />
            Persistent IDs
          </button>

          <button 
            className={`toggle-btn ${renderOptions.show_lines ? 'active' : ''}`}
            onClick={() => onToggleRenderOption('show_lines', !renderOptions.show_lines)}
          >
            <GitCommit size={14} />
            Counting Lines
          </button>

          <button 
            className={`toggle-btn ${renderOptions.show_trails ? 'active' : ''}`}
            onClick={() => onToggleRenderOption('show_trails', !renderOptions.show_trails)}
          >
            <Navigation size={14} />
            Trajectories
          </button>

          <button 
            className={`toggle-btn ${renderOptions.show_hud ? 'active' : ''}`}
            onClick={() => onToggleRenderOption('show_hud', !renderOptions.show_hud)}
          >
            <LayoutDashboard size={14} />
            Live HUD
          </button>
        </div>

        <div style={{ fontSize: 12, color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
          ACTIVE: <span style={{ color: isRunning ? '#10b981' : '#f59e0b', fontWeight: 600 }}>{sourceLabel}</span>
        </div>
      </div>
    </div>
  );
}
