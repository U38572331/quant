import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { User, Calendar, DollarSign, TrendingUp, TrendingDown } from 'lucide-react';
import KLineChart from './KLineChart';
import ErrorBoundary from './ErrorBoundary';

export default function CongressDashboard() {
  const [trades, setTrades] = useState([]);
  const [selectedTrade, setSelectedTrade] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch('/api/congress')
      .then(res => res.json())
      .then(data => {
        setTrades(data);
        setSelectedTrade(data[0]);
        setLoading(false);
      })
      .catch(() => {
        // Fallback to local JSON if API fails
        fetch('/src/data/congressData.json')
          .then(res => res.json())
          .then(data => {
            setTrades(data);
            setSelectedTrade(data[0]);
            setLoading(false);
          });
      });
  }, []);

  if (loading) return (
    <div className="empty-state" style={{ height: '70vh' }}>
      <div className="spin" style={{ width: '48px', height: '48px', border: '4px solid var(--accent-primary)', borderTopColor: 'transparent', borderRadius: '50%' }}></div>
      <h3 style={{ marginTop: '1.5rem' }}>Fetching Real-time Capitol Data...</h3>
      <p style={{ color: 'var(--text-muted)' }}>Analyzing 30+ recent trades and generating K-line charts.</p>
    </div>
  );

  return (
    <div className="dashboard-grid">
      <section className="left-panel">
        <div className="section-header">
          <h2>Congressional Insider Trades</h2>
          <span className="badge">{trades.length} Recent Trades</span>
        </div>
        
        <div style={{ display: 'grid', gap: '1rem' }}>
          {trades.map((trade, idx) => (
            <motion.div
              key={`${trade.ticker}-${idx}`}
              onClick={() => setSelectedTrade(trade)}
              className="glass-card"
              style={{ 
                cursor: 'pointer',
                border: selectedTrade === trade ? '1px solid var(--accent-primary)' : '1px solid var(--border-glass)',
                background: selectedTrade === trade ? 'rgba(99, 102, 241, 0.05)' : 'var(--bg-card)'
              }}
              whileHover={{ x: 5 }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
                  <div className="user-avatar" style={{ width: '32px', height: '32px' }}>
                    <User size={16} />
                  </div>
                  <div>
                    <div style={{ fontWeight: '600' }}>{trade.politician}</div>
                    <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>{trade.ticker} • {trade.type}</div>
                  </div>
                </div>
                <div className={trade.type === 'Purchase' ? 'beat' : 'miss'}>
                  {trade.type === 'Purchase' ? <TrendingUp size={16} /> : <TrendingDown size={16} />}
                </div>
              </div>
            </motion.div>
          ))}
        </div>
      </section>

      <section className="right-panel">
        <AnimatePresence mode="wait">
          {selectedTrade && (
            <motion.div
              key={selectedTrade.ticker + selectedTrade.date}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
            >
              <div className="glass-card" style={{ marginBottom: '1.5rem' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '1.5rem' }}>
                  <div>
                    <h1 style={{ margin: 0 }}>{selectedTrade.ticker}</h1>
                    <p style={{ color: 'var(--text-muted)' }}>{selectedTrade.politician}'s {selectedTrade.type}</p>
                  </div>
                  <div style={{ textAlign: 'right' }}>
                    <div style={{ fontSize: '1.25rem', fontWeight: 'bold' }}>{selectedTrade.amount}</div>
                    <div style={{ color: 'var(--text-muted)', fontSize: '0.85rem', marginTop: '4px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '4px', justifyContent: 'flex-end' }}>
                        <Calendar size={12} /> <span style={{ color: 'var(--accent-primary)' }}>Trade: {selectedTrade.date}</span>
                      </div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '4px', justifyContent: 'flex-end', marginTop: '2px' }}>
                        <Calendar size={12} /> <span>Filed: {selectedTrade.disclosureDate}</span>
                      </div>
                    </div>
                  </div>
                </div>

                <ErrorBoundary>
                  <KLineChart 
                    data={selectedTrade.klineData} 
                    tradeDate={selectedTrade.date} 
                    type={selectedTrade.type} 
                  />
                </ErrorBoundary>
              </div>
              
              <div className="glass-card">
                <h3>Trade Analysis</h3>
                <p style={{ color: 'var(--text-muted)' }}>
                  This transaction occurred on <strong>{selectedTrade.date}</strong> and was officially disclosed on <strong>{selectedTrade.disclosureDate}</strong>. The marker on the K-line chart reflects the <strong>Transaction Date</strong> to show the exact market price at the time of the trade.
                </p>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </section>
    </div>
  );
}
