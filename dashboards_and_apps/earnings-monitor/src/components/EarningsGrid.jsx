import React from 'react';
import { motion } from 'framer-motion';
import { TrendingUp, TrendingDown, Minus } from 'lucide-react';

const EarningsCard = ({ data, onSelect, isSelected }) => {
  const isBeat = data.epsSurprise > 0;
  
  return (
    <motion.div
      layout
      onClick={() => onSelect(data)}
      className={`glass-card ${isSelected ? 'selected' : ''}`}
      style={{
        cursor: 'pointer',
        border: isSelected ? '1px solid var(--accent-primary)' : '1px solid var(--border-glass)',
        background: isSelected ? 'rgba(99, 102, 241, 0.05)' : 'var(--bg-card)'
      }}
      whileHover={{ scale: 1.02 }}
      whileTap={{ scale: 0.98 }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '1rem' }}>
        <div>
          <h3 style={{ margin: 0, fontSize: '1.25rem' }}>{data.ticker}</h3>
          <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>{data.name}</span>
        </div>
        <div className={isBeat ? 'beat' : 'miss'} style={{ display: 'flex', alignItems: 'center', gap: '4px', fontWeight: 'bold' }}>
          {isBeat ? <TrendingUp size={18} /> : <TrendingDown size={18} />}
          {Math.abs(data.epsSurprise).toFixed(2)}%
        </div>
      </div>
      
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
        <div>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>EPS Actual</div>
          <div style={{ fontSize: '1.1rem', fontWeight: '600' }}>${data.epsActual}</div>
        </div>
        <div>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Estimate</div>
          <div style={{ fontSize: '1.1rem', fontWeight: '600', color: 'var(--text-muted)' }}>${data.epsEstimate}</div>
        </div>
      </div>
      
      <div style={{ marginTop: '1rem', paddingTop: '1rem', borderTop: '1px solid var(--border-glass)', display: 'flex', justifyContent: 'space-between' }}>
        <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>{data.period}</span>
        <span style={{ fontSize: '0.8rem', color: data.priceChange > 0 ? 'var(--success)' : 'var(--error)' }}>
          Price: {data.priceChange > 0 ? '+' : ''}{data.priceChange}%
        </span>
      </div>
    </motion.div>
  );
};

export default function EarningsGrid({ stocks, onSelect, selectedTicker }) {
  return (
    <div style={{ 
      display: 'grid', 
      gridTemplateColumns: '1fr', 
      gap: '1.5rem',
      '@media (min-width: 768px)': { gridTemplateColumns: '1fr 1fr' },
      '@media (min-width: 1024px)': { gridTemplateColumns: '1fr 1fr 1fr' }
    }} className="grid-container">
      {stocks.map(stock => (
        <EarningsCard 
          key={stock.ticker} 
          data={stock} 
          onSelect={onSelect}
          isSelected={selectedTicker === stock.ticker}
        />
      ))}
    </div>
  );
}
