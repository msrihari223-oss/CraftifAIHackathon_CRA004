import React, { useState } from 'react';
import { Plus, Trash2, ArrowUpDown, Shield, CheckSquare } from 'lucide-react';

const ALL_CLASSES = ['pedestrian', 'bicycle', 'motorcycle', 'car', 'bus', 'truck'];

export default function CountingLinesPanel({ lines, onSaveLine, onDeleteLine }) {
  const [showAddModal, setShowAddModal] = useState(false);
  const [newLine, setNewLine] = useState({
    line_id: '',
    name: '',
    p1: [350, 300],
    p2: [850, 300],
    direction_type: 'both',
    allowed_classes: [...ALL_CLASSES],
    color: '#10B981'
  });

  const handleOpenAdd = () => {
    const id = `line_${Date.now().toString().slice(-4)}`;
    setNewLine({
      line_id: id,
      name: `Virtual Gate ${id.toUpperCase()}`,
      p1: [320, 360],
      p2: [920, 360],
      direction_type: 'both',
      allowed_classes: [...ALL_CLASSES],
      color: '#06B6D4'
    });
    setShowAddModal(true);
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!newLine.name.trim()) return;
    onSaveLine(newLine);
    setShowAddModal(false);
  };

  const toggleClass = (cls) => {
    if (newLine.allowed_classes.includes(cls)) {
      setNewLine({
        ...newLine,
        allowed_classes: newLine.allowed_classes.filter((c) => c !== cls)
      });
    } else {
      setNewLine({
        ...newLine,
        allowed_classes: [...newLine.allowed_classes, cls]
      });
    }
  };

  const linesList = Object.values(lines || {});

  return (
    <div className="glass-panel lines-panel">
      <div className="panel-header">
        <div className="panel-title">
          <ArrowUpDown size={18} color="#06B6D4" />
          Virtual Counting Lines ({linesList.length})
        </div>
        <button className="btn-primary" onClick={handleOpenAdd}>
          <Plus size={14} />
          Add Line
        </button>
      </div>

      <div className="line-card-list">
        {linesList.map((line) => (
          <div key={line.line_id} className="line-item-card">
            <div className="line-info-left">
              <div 
                className="line-color-dot" 
                style={{ backgroundColor: line.color, boxShadow: `0 0 8px ${line.color}` }}
              />
              <div>
                <div className="line-name">{line.name}</div>
                <div className="line-coords">
                  P1: ({line.p1[0]}, {line.p1[1]}) &rarr; P2: ({line.p2[0]}, {line.p2[1]}) &bull;{' '}
                  <span style={{ textTransform: 'capitalize' }}>{line.direction_type}</span>
                </div>
              </div>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
              <div className="line-count-badge" title="Total crossings on this gate">
                {line.counts?.total || 0}
              </div>
              <button 
                onClick={() => onDeleteLine(line.line_id)}
                style={{ 
                  background: 'transparent', 
                  border: 'none', 
                  color: 'var(--text-muted)', 
                  cursor: 'pointer' 
                }}
                title="Remove Virtual Line"
              >
                <Trash2 size={15} />
              </button>
            </div>
          </div>
        ))}
      </div>

      {showAddModal && (
        <div className="modal-backdrop" onClick={() => setShowAddModal(false)}>
          <div className="modal-dialog" onClick={(e) => e.stopPropagation()}>
            <h3 style={{ marginBottom: 16, fontFamily: 'var(--font-heading)', fontSize: 18 }}>
              Configure New Virtual Counting Line
            </h3>

            <form onSubmit={handleSubmit}>
              <div className="form-group">
                <label className="form-label">Gate Name / Location</label>
                <input 
                  type="text" 
                  className="form-input" 
                  value={newLine.name} 
                  onChange={(e) => setNewLine({ ...newLine, name: e.target.value })}
                  required
                />
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
                <div className="form-group">
                  <label className="form-label">Start Point P1 (X, Y)</label>
                  <div style={{ display: 'flex', gap: 6 }}>
                    <input 
                      type="number" 
                      className="form-input"
                      value={newLine.p1[0]}
                      onChange={(e) => setNewLine({ ...newLine, p1: [parseInt(e.target.value) || 0, newLine.p1[1]] })}
                    />
                    <input 
                      type="number" 
                      className="form-input"
                      value={newLine.p1[1]}
                      onChange={(e) => setNewLine({ ...newLine, p1: [newLine.p1[0], parseInt(e.target.value) || 0] })}
                    />
                  </div>
                </div>

                <div className="form-group">
                  <label className="form-label">End Point P2 (X, Y)</label>
                  <div style={{ display: 'flex', gap: 6 }}>
                    <input 
                      type="number" 
                      className="form-input"
                      value={newLine.p2[0]}
                      onChange={(e) => setNewLine({ ...newLine, p2: [parseInt(e.target.value) || 0, newLine.p2[1]] })}
                    />
                    <input 
                      type="number" 
                      className="form-input"
                      value={newLine.p2[1]}
                      onChange={(e) => setNewLine({ ...newLine, p2: [newLine.p2[0], parseInt(e.target.value) || 0] })}
                    />
                  </div>
                </div>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
                <div className="form-group">
                  <label className="form-label">Direction Filter</label>
                  <select 
                    className="form-select"
                    value={newLine.direction_type}
                    onChange={(e) => setNewLine({ ...newLine, direction_type: e.target.value })}
                  >
                    <option value="both">Bidirectional (Inbound + Outbound)</option>
                    <option value="inbound">Inbound Only (A &rarr; B)</option>
                    <option value="outbound">Outbound Only (B &rarr; A)</option>
                  </select>
                </div>

                <div className="form-group">
                  <label className="form-label">Highlight Color</label>
                  <input 
                    type="color" 
                    className="form-input"
                    value={newLine.color}
                    onChange={(e) => setNewLine({ ...newLine, color: e.target.value })}
                    style={{ height: 42, padding: 4 }}
                  />
                </div>
              </div>

              <div className="form-group">
                <label className="form-label">Target Classes Counted</label>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 8 }}>
                  {ALL_CLASSES.map((cls) => {
                    const isChecked = newLine.allowed_classes.includes(cls);
                    return (
                      <label 
                        key={cls} 
                        style={{ 
                          display: 'flex', 
                          alignItems: 'center', 
                          gap: 6, 
                          fontSize: 12, 
                          cursor: 'pointer',
                          textTransform: 'capitalize' 
                        }}
                      >
                        <input 
                          type="checkbox" 
                          checked={isChecked} 
                          onChange={() => toggleClass(cls)} 
                        />
                        {cls}
                      </label>
                    );
                  })}
                </div>
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 10, marginTop: 24 }}>
                <button type="button" className="btn-secondary" onClick={() => setShowAddModal(false)}>
                  Cancel
                </button>
                <button type="submit" className="btn-primary">
                  Save Counting Line
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
