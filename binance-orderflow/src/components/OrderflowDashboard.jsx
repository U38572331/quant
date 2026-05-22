import React, { useEffect, useState, useRef } from 'react';
import { DataManager } from '../services/DataManager';
import FootprintChart from './FootprintChart';
import DOMLadder from './DOMLadder';
import VolumeProfile from './VolumeProfile';

const OrderflowDashboard = () => {
    const [marketData, setMarketData] = useState({ candles: [], orderBook: { bids: [], asks: [] }, sessionProfile: {} });
    const [largeOrders, setLargeOrders] = useState([]);
    const [isConnected, setIsConnected] = useState(false);
    const [symbol, setSymbol] = useState('BTCUSDT');
    const [threshold, setThreshold] = useState(10);

    const managerRef = useRef(null);

    useEffect(() => {
        const manager = new DataManager(
            symbol,
            (newState) => {
                setMarketData(newState);
                setIsConnected(true);
            },
            (largeOrder) => {
                setLargeOrders(prev => [...prev, largeOrder]);
            }
        );

        manager.connect();
        manager.setThreshold(threshold);
        managerRef.current = manager;

        return () => {
            manager.disconnect();
        };
    }, [symbol]);

    useEffect(() => {
        if (managerRef.current) {
            managerRef.current.setThreshold(threshold);
        }
    }, [threshold]);

    return (
        <div className="flex flex-col h-screen w-screen bg-dark-bg text-text-primary overflow-hidden font-mono">
            {/* Professional Header */}
            <header className="h-14 border-b border-grid-line flex items-center px-4 justify-between bg-card-bg shadow-lg z-20">
                <div className="flex items-center space-x-6">
                    <div className="flex items-center space-x-2">
                        <div className="w-8 h-8 bg-buy-green rounded-lg flex items-center justify-center shadow-neon">
                            <span className="text-dark-bg font-black italic">G</span>
                        </div>
                        <h1 className="text-xl font-black tracking-tighter text-white">
                            GEX<span className="text-buy-green">STREAM</span>
                            <span className="text-[10px] ml-1 text-text-secondary font-normal uppercase tracking-widest border border-grid-line px-1 rounded">Pro</span>
                        </h1>
                    </div>

                    <div className="h-8 w-[1px] bg-grid-line"></div>

                    <div className="flex items-center space-x-4">
                        <div className="flex flex-col">
                            <span className="text-[10px] text-text-secondary uppercase">Instrument</span>
                            <select
                                value={symbol}
                                onChange={(e) => setSymbol(e.target.value)}
                                className="bg-dark-bg text-sm font-bold outline-none border border-grid-line rounded px-2 py-0.5 text-neon-blue"
                            >
                                <option value="BTCUSDT">BTCUSDT.P</option>
                                <option value="ETHUSDT">ETHUSDT.P</option>
                                <option value="SOLUSDT">SOLUSDT.P</option>
                            </select>
                        </div>

                        <div className="flex flex-col">
                            <span className="text-[10px] text-text-secondary uppercase">Whale Alert</span>
                            <div className="flex items-center space-x-2 bg-dark-bg border border-grid-line rounded px-2 py-0.5">
                                <input
                                    type="number"
                                    value={threshold}
                                    onChange={(e) => setThreshold(Number(e.target.value))}
                                    className="bg-transparent text-sm font-bold w-12 outline-none text-poc-yellow"
                                />
                                <span className="text-[10px] text-text-secondary">BTC</span>
                            </div>
                        </div>
                    </div>
                </div>

                <div className="flex items-center space-x-6">
                    <div className="flex flex-col items-end">
                        <span className="text-[10px] text-text-secondary uppercase">Status</span>
                        <div className="flex items-center space-x-2">
                            <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-buy-green shadow-[0_0_8px_#1dbf73]' : 'bg-sell-red animate-pulse'}`}></div>
                            <span className="text-xs font-bold">{isConnected ? 'LIVE' : 'RECONNECTING'}</span>
                        </div>
                    </div>
                </div>
            </header>

            {/* Main Application Area */}
            <main className="flex-1 flex overflow-hidden">
                {/* Left Sidebar: DOM Ladder */}
                <aside className="w-80 border-r border-grid-line bg-card-bg flex flex-col">
                    <div className="p-2 border-b border-grid-line bg-dark-bg/50 flex justify-between items-center">
                        <span className="text-xs font-bold text-text-secondary uppercase tracking-widest">DOM Ladder</span>
                        <span className="text-[10px] text-buy-green bg-buy-green/10 px-1 rounded">Real-time</span>
                    </div>
                    <div className="flex-1 overflow-hidden relative">
                        <DOMLadder orderBook={marketData.orderBook} />
                    </div>
                </aside>

                {/* Center: Footprint Chart */}
                <section className="flex-1 relative bg-dark-bg">
                    <FootprintChart
                        data={marketData.candles}
                        largeOrders={largeOrders}
                    />

                    {!isConnected && (
                        <div className="absolute inset-0 flex items-center justify-center bg-dark-bg/80 backdrop-blur-sm z-50">
                            <div className="flex flex-col items-center">
                                <div className="w-12 h-12 border-4 border-buy-green border-t-transparent rounded-full animate-spin mb-4"></div>
                                <div className="text-text-secondary font-bold tracking-widest uppercase">Initializing Stream...</div>
                            </div>
                        </div>
                    )}
                </section>

                {/* Right Sidebar: Volume Profile */}
                <aside className="w-64 border-l border-grid-line bg-card-bg flex flex-col">
                    <div className="p-2 border-b border-grid-line bg-dark-bg/50">
                        <span className="text-xs font-bold text-text-secondary uppercase tracking-widest">Volume Profile</span>
                    </div>
                    <div className="flex-1 overflow-hidden relative">
                        <VolumeProfile data={marketData.sessionProfile} />
                    </div>
                </aside>
            </main>

            {/* Sub-footer / Ticker Info */}
            <div className="h-6 bg-dark-bg border-t border-grid-line flex items-center px-4 justify-between text-[10px] text-text-secondary">
                <div className="flex items-center space-x-4">
                    <span>SERVER: BINANCE-FUTURES-WSS</span>
                    <span>LATENCY: 42ms</span>
                </div>
                <div>
                    &copy; 2026 GEXSTREAM TERMINAL v2.0
                </div>
            </div>
        </div>
    );
};

export default OrderflowDashboard;
