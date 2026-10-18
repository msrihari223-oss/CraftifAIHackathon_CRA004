import React from 'react';
import { History, ArrowDownRight, ArrowUpRight, Clock, Gauge } from 'lucide-react';

const CLASS_COLORS = {
  pedestrian: '#10B981',
  bicycle: '#06B6D4',
  motorcycle: '#F59E0B',
  car: '#3B82F6',
  bus: '#8B5CF6',
  truck: '#EC4899'
};

export default function EventsFeed({ events }) {
  const eventsList = (events || []).slice().reverse();

  return (
    <div className="glass-panel events-panel">
      <div className="panel-header">
        <div className="panel-title">
          <History size={18} color="#10B981" />
          Real-Time Crossing Events Feed
        </div>
        <div style={{ fontSize: 11, color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
          LIVE DEBOUNCED TELEMETRY
        </div>
      </div>

      <div className="events-list">
        {eventsList.length === 0 ? (
          <div style={{ padding: 28, textAlign: 'center', color: 'var(--text-muted)', fontSize: 13 }}>
            Waiting for objects to cross configured virtual lines...
          </div>
        ) : (
          eventsList.map((evt) => {
            const timeStr = evt.timestamp ? evt.timestamp.split('T')[1].replace('Z', '') : '--:--:--';
            const color = CLASS_COLORS[evt.object_class] || '#38bdf8';
            const isInbound = evt.crossing_direction === 'Inbound';

            return (
              <div key={evt.event_id} className="event-row">
                <div className="event-left">
                  <div className="event-time">
                    <Clock size={11} style={{ display: 'inline', marginRight: 4 }} />
                    {timeStr}
                  </div>

                  <span className="event-track-id">
                    #{evt.tracked_object_id}
                  </span>

                  <span 
                    className="event-class-badge" 
                    style={{ 
                      backgroundColor: `${color}20`, 
                      color: color,
                      border: `1px solid ${color}40`
                    }}
                  >
                    {evt.object_class}
                  </span>

                  <div className="event-direction-badge">
                    {isInbound ? (
                      <ArrowDownRight size={13} color="#10B981" />
                    ) : (
                      <ArrowUpRight size={13} color="#3B82F6" />
                    )}
                    <span>{evt.crossing_direction}</span>
                  </div>

                  <span style={{ color: 'var(--text-muted)', fontSize: 11 }}>
                    on {evt.line_name}
                  </span>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
                  {evt.speed_kmh && (
                    <span style={{ fontSize: 11, color: 'var(--text-secondary)', fontFamily: 'var(--font-mono)' }}>
                      <Gauge size={11} style={{ display: 'inline', marginRight: 3 }} />
                      {evt.speed_kmh} km/h
                    </span>
                  )}

                  <div className="event-count-badge">
                    T: {evt.updated_count?.total || 0}
                  </div>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
