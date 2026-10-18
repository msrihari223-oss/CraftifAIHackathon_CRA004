import React from 'react';
import { User, Bike, Car, Truck, Bus } from 'lucide-react';

const CLASS_CONFIG = [
  { key: 'pedestrian', label: 'Pedestrians', icon: User, color: '#10B981', category: 'VRU' },
  { key: 'bicycle', label: 'Cyclists', icon: Bike, color: '#06B6D4', category: 'VRU' },
  { key: 'motorcycle', label: 'Motorcycles', icon: Bike, color: '#F59E0B', category: 'Motorized' },
  { key: 'car', label: 'Cars', icon: Car, color: '#3B82F6', category: 'Motorized' },
  { key: 'bus', label: 'Buses', icon: Bus, color: '#8B5CF6', category: 'Transit' },
  { key: 'truck', label: 'Trucks', icon: Truck, color: '#EC4899', category: 'Commercial' },
];

export default function ClassStatsCards({ globalCounts }) {
  const counts = globalCounts || {};
  const total = counts.total || 0;

  return (
    <div className="stats-overview-grid">
      {CLASS_CONFIG.map((item) => {
        const count = counts[item.key] || 0;
        const percentage = total > 0 ? ((count / total) * 100).toFixed(1) : '0.0';
        const IconComponent = item.icon;

        return (
          <div 
            key={item.key} 
            className="glass-panel class-stat-card"
            style={{ '--accent-color': item.color }}
          >
            <div className="stat-card-header">
              <span className="stat-card-title">{item.label}</span>
              <div className="stat-card-icon">
                <IconComponent size={18} />
              </div>
            </div>

            <div className="stat-card-count">
              {count.toLocaleString()}
            </div>

            <div className="stat-card-footer">
              <span>{item.category}</span>
              <span style={{ color: item.color, fontWeight: 600 }}>{percentage}%</span>
            </div>
          </div>
        );
      })}
    </div>
  );
}
