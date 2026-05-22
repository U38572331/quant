import React, { useState, useEffect } from 'react';
import { Search, Bell, TrendingUp, Info, RefreshCcw, Landmark, LineChart } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { getEarningsData } from './data/dataSource';
import EarningsGrid from './components/EarningsGrid';
import SurpriseChart from './components/SurpriseChart';
import CongressDashboard from './components/CongressDashboard';
import './App.css';

function App() {
  const [activeTab, setActiveTab] = useState('congress'); 
  const [searchTerm, setSearchTerm] = useState('');
  const [stocks, setStocks] = useState([]);
  const [selectedStock, setSelectedStock] = useState(null);
  const [loading, setLoading] = useState(true);
  const [isLive, setIsLive] = useState(false);
  const [filterCategory, setFilterCategory] = useState('all'); 

  useEffect(() => {
    getEarningsData().then(data => {
      setStocks(data);
      setSelectedStock(data[0]);
      setLoading(false);
      // Simple check to see if local API is reachable
      fetch('/api/earnings', { method: 'HEAD' })
        .then(() => setIsLive(true))
        .catch(() => setIsLive(false));
    });
  }, []);

  const filteredStocks = stocks.filter(stock => {
    const matchesSearch = stock.ticker.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         stock.name.toLowerCase().includes(searchTerm.toLowerCase());
    
    if (filterCategory === 'beat') return matchesSearch && parseFloat(stock.epsSurprise) > 10;
    if (filterCategory === 'miss') return matchesSearch && parseFloat(stock.epsSurprise) < -10;
    return matchesSearch;
  });

  return (
    <div className="app-container">
      <header className="header">
        <div className="logo-section">
          <div className="logo-icon">
            <TrendingUp size={24} color="white" />
          </div>
          <div style={{ display: 'flex', flexDirection: 'column' }}>
            <h1 style={{ lineHeight: 1 }}>Surprise<span className="gradient-text">Monitor</span></h1>
            {isLive && (
              <span style={{ 
                fontSize: '0.65rem', 
                color: '#10b981', 
                display: 'flex', 
                alignItems: 'center', 
                gap: '4px',
                fontWeight: 'bold',
                textTransform: 'uppercase',
                letterSpacing: '1px',
                marginTop: '4px'
              }}>
                <div className="live-dot"></div>
                Live Data Active
              </span>
            )}
          </div>
        </div>
        
        <div className="search-bar">
          <Search size={18} className="search-icon" />
          <input 
            type="text" 
            placeholder="Search tickers or company names..." 
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
        </div>

        <nav className="main-nav">
          <button 
            className={`nav-item ${activeTab === 'earnings' ? 'active' : ''}`}
            onClick={() => setActiveTab('earnings')}
          >
            <LineChart size={18} /> Earnings
          </button>
          <button 
            className={`nav-item ${activeTab === 'congress' ? 'active' : ''}`}
            onClick={() => setActiveTab('congress')}
          >
            <Landmark size={18} /> Capitol
          </button>
        </nav>

        <div className="actions">
          <button 
            className="icon-btn" 
            onClick={() => {
                setLoading(true);
                getEarningsData().then(data => {
                    setStocks(data);
                    setLoading(false);
                });
            }}
            title="Refresh Data"
          >
            <RefreshCcw size={20} className={loading ? 'spin' : ''} />
          </button>
          <button className="icon-btn"><Bell size={20} /></button>
          <div className="user-avatar"></div>
        </div>
      </header>

      <main className="content">
        {loading ? (
          <div className="empty-state">
            <RefreshCcw size={48} className="spin" />
            <p>Fetching latest data from Yahoo Finance...</p>
          </div>
        ) : (
          activeTab === 'earnings' ? (
            <div className="dashboard-grid">
              <section className="left-panel">
                <div className="section-header">
                  <h2>Recent Surprises</h2>
                  <div className="filter-tabs">
                    <button 
                      className={`tab ${filterCategory === 'all' ? 'active' : ''}`}
                      onClick={() => setFilterCategory('all')}
                    >All</button>
                    <button 
                      className={`tab ${filterCategory === 'beat' ? 'active' : ''}`}
                      onClick={() => setFilterCategory('beat')}
                    >Strong Beat (&gt;10%)</button>
                    <button 
                      className={`tab ${filterCategory === 'miss' ? 'active' : ''}`}
                      onClick={() => setFilterCategory('miss')}
                    >Strong Miss (&lt;-10%)</button>
                  </div>
                  <span className="badge">{filteredStocks.length} Results</span>
                </div>
                <EarningsGrid 
                  stocks={filteredStocks} 
                  onSelect={setSelectedStock} 
                  selectedTicker={selectedStock?.ticker}
                />
              </section>

              <section className="right-panel">
                <AnimatePresence mode="wait">
                  {selectedStock ? (
                    <motion.div
                      key={selectedStock.ticker}
                      initial={{ opacity: 0, x: 20 }}
                      animate={{ opacity: 1, x: 0 }}
                      exit={{ opacity: 0, x: -20 }}
                      transition={{ duration: 0.3 }}
                    >
                      <div className="detail-header glass-card" style={{ marginBottom: '1.5rem' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                          <div>
                            <h1 style={{ margin: 0, fontSize: '2.5rem' }}>{selectedStock.ticker}</h1>
                            <p style={{ color: 'var(--text-muted)', fontSize: '1.1rem' }}>{selectedStock.name}</p>
                          </div>
                          <div style={{ textAlign: 'right' }}>
                            <div className={selectedStock.epsSurprise > 0 ? 'beat' : 'miss'} style={{ fontSize: '1.5rem', fontWeight: 'bold' }}>
                              {selectedStock.epsSurprise > 0 ? '+' : ''}{selectedStock.epsSurprise}% Surprise
                            </div>
                            <p style={{ color: 'var(--text-muted)' }}>Reported on {selectedStock.reportDate}</p>
                          </div>
                        </div>
                        
                        <div className="stats-row" style={{ display: 'flex', gap: '3rem', marginTop: '2rem' }}>
                          <div className="stat-item">
                            <label>Revenue Actual</label>
                            <div className="value">
                              {selectedStock.revActual && !isNaN(selectedStock.revActual) ? `$${selectedStock.revActual}B` : 'N/A'}
                            </div>
                            <div className={`sub-value ${selectedStock.revSurprise > 0 ? 'beat' : 'miss'}`}>
                              ({selectedStock.revSurprise && !isNaN(selectedStock.revSurprise) ? `${selectedStock.revSurprise > 0 ? '+' : ''}${selectedStock.revSurprise}%` : 'N/A'})
                            </div>
                          </div>
                          <div className="stat-item">
                            <label>Consensus Est.</label>
                            <div className="value">
                              {selectedStock.revEstimate && !isNaN(selectedStock.revEstimate) ? `$${selectedStock.revEstimate}B` : 'N/A'}
                            </div>
                          </div>
                        </div>
                      </div>

                      <SurpriseChart history={selectedStock.history} ticker={selectedStock.ticker} />
                    </motion.div>
                  ) : (
                    <div className="empty-state glass-card">
                      <Info size={48} color="var(--text-muted)" />
                      <p>Select a stock to view detailed performance</p>
                    </div>
                  )}
                </AnimatePresence>
              </section>
            </div>
          ) : (
            <CongressDashboard />
          )
        )}
      </main>
    </div>
  );
}

export default App;
