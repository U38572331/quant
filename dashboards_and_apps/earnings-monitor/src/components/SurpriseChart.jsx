import React from 'react';
import { 
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, 
  Cell, Legend, ReferenceLine 
} from 'recharts';

export default function SurpriseChart({ history, ticker }) {
  if (!history) return null;

  return (
    <div className="glass-card" style={{ height: '400px', width: '100%' }}>
      <div style={{ marginBottom: '1.5rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h3 style={{ margin: 0 }}>{ticker} Historical Performance</h3>
        <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Actual vs Estimate EPS</div>
      </div>
      
      <ResponsiveContainer width="100%" height="80%">
        <BarChart data={history} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" vertical={false} />
          <XAxis 
            dataKey="quarter" 
            axisLine={false} 
            tickLine={false} 
            tick={{ fill: 'var(--text-muted)', fontSize: 12 }} 
          />
          <YAxis 
            axisLine={false} 
            tickLine={false} 
            tick={{ fill: 'var(--text-muted)', fontSize: 12 }} 
          />
          <Tooltip 
            contentStyle={{ 
              backgroundColor: 'rgba(15, 15, 20, 0.9)', 
              border: '1px solid var(--border-glass)',
              borderRadius: '8px',
              backdropFilter: 'blur(10px)'
            }}
            itemStyle={{ color: 'var(--text-main)' }}
          />
          <Legend iconType="circle" />
          <Bar dataKey="estimate" fill="rgba(255,255,255,0.1)" radius={[4, 4, 0, 0]} name="Estimated EPS" />
          <Bar dataKey="actual" radius={[4, 4, 0, 0]} name="Actual EPS">
            {history.map((entry, index) => (
              <Cell key={`cell-${index}`} fill={entry.actual >= entry.estimate ? 'var(--success)' : 'var(--error)'} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
