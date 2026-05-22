import React, { useRef, useEffect, useState, useCallback } from 'react';

const FootprintChart = ({ data, largeOrders }) => {
    const canvasRef = useRef(null);
    const containerRef = useRef(null);

    // Viewport & Scale
    const [offsetY, setOffsetY] = useState(0);
    const [scaleY, setScaleY] = useState(40);
    const [candleWidth, setCandleWidth] = useState(140);
    const [tickSize, setTickSize] = useState(1.0);
    const [autoFollow, setAutoFollow] = useState(true);

    // Interaction State
    const [mousePos, setMousePos] = useState({ x: -1, y: -1 });
    const [isDragging, setIsDragging] = useState(false);
    const [dragMode, setDragMode] = useState(null);
    const [lastDragPos, setLastDragPos] = useState({ x: 0, y: 0 });

    const [initialized, setInitialized] = useState(false);

    const formatQty = (q) => {
        if (q >= 1000) return (q / 1000).toFixed(1) + 'k';
        return q.toFixed(2);
    };

    useEffect(() => {
        const canvas = canvasRef.current;
        const ctx = canvas.getContext('2d');
        let frameId;

        const render = () => {
            if (!canvas || !containerRef.current) return;
            const { clientWidth, clientHeight } = containerRef.current;
            if (canvas.width !== clientWidth || canvas.height !== clientHeight) {
                canvas.width = clientWidth; canvas.height = clientHeight;
            }

            const latestCandle = data[data.length - 1];
            if (!initialized && latestCandle) {
                setOffsetY(latestCandle.close);
                setInitialized(true);
            }

            const centerPrice = autoFollow && latestCandle ? latestCandle.close : offsetY;
            const centerY = (canvas.height - 60) / 2;

            // Clear Background
            ctx.fillStyle = '#0b0e11'; ctx.fillRect(0, 0, canvas.width, canvas.height);

            if (!data || data.length === 0) return;

            // --- Grid & Axis ---
            ctx.strokeStyle = '#1e2329'; ctx.lineWidth = 0.5;
            const minP = centerPrice - centerY / scaleY;
            const maxP = centerPrice + centerY / scaleY;
            for (let p = Math.floor(minP / tickSize) * tickSize; p <= maxP; p += tickSize) {
                const y = centerY + (centerPrice - p) * scaleY;
                ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(canvas.width - 70, y); ctx.stroke();
            }

            // Price Labels (Right Axis)
            ctx.fillStyle = '#161a1e'; ctx.fillRect(canvas.width - 70, 0, 70, canvas.height);
            ctx.fillStyle = '#848e9c'; ctx.font = '10px monospace'; ctx.textAlign = 'right';
            for (let p = Math.floor(minP / (tickSize * 5)) * (tickSize * 5); p <= maxP; p += tickSize * 5) {
                const y = centerY + (centerPrice - p) * scaleY;
                if (y < canvas.height - 60) ctx.fillText(p.toFixed(2), canvas.width - 5, y + 3);
            }

            // Bottom Axis
            ctx.fillStyle = '#161a1e'; ctx.fillRect(0, canvas.height - 60, canvas.width, 60);

            // --- Candles ---
            const maxVisible = Math.ceil((canvas.width - 70) / candleWidth) + 1;
            const visible = data.slice(Math.max(0, data.length - maxVisible));

            visible.forEach((candle, i) => {
                const x = (canvas.width - 70) - ((visible.length - i) * candleWidth);

                // Candle Base Structure
                ctx.strokeStyle = 'rgba(255, 255, 255, 0.03)'; ctx.strokeRect(x, 0, candleWidth, canvas.height - 60);

                // Levels Aggregation
                const agg = {};
                Object.entries(candle.levels).forEach(([p, v]) => {
                    const k = (Math.floor(parseFloat(p) / tickSize) * tickSize).toFixed(1);
                    if (!agg[k]) agg[k] = { b: 0, s: 0, poc: false };
                    agg[k].b += v.buy; agg[k].s += v.sell;
                    if (Math.abs(parseFloat(k) - Math.floor(candle.poc / tickSize) * tickSize) < 0.01) agg[k].poc = true;
                });

                const cellH = scaleY * tickSize;
                const showText = cellH > 14;

                Object.entries(agg).forEach(([pStr, v]) => {
                    const price = parseFloat(pStr);
                    const y = centerY + (centerPrice - price) * scaleY;
                    if (y < -cellH || y > canvas.height - 60) return;

                    const maxV = candle.maxLevelVolume * tickSize || 1;
                    const sOp = Math.min((v.s / maxV) * 0.75 + 0.1, 0.85);
                    const bOp = Math.min((v.b / maxV) * 0.75 + 0.1, 0.85);

                    // Footprint Blocks
                    ctx.fillStyle = `rgba(246, 70, 93, ${sOp})`;
                    ctx.fillRect(x + 2, y - cellH / 2 + 0.5, candleWidth / 2 - 3, cellH - 1);
                    ctx.fillStyle = `rgba(29, 191, 115, ${bOp})`;
                    ctx.fillRect(x + candleWidth / 2 + 1, y - cellH / 2 + 0.5, candleWidth / 2 - 3, cellH - 1);

                    if (showText) {
                        ctx.fillStyle = '#ffffff'; ctx.font = '8px monospace';
                        ctx.textAlign = 'right'; ctx.fillText(v.s.toFixed(1), x + candleWidth / 2 - 3, y + 3);
                        ctx.textAlign = 'left'; ctx.fillText(v.b.toFixed(1), x + candleWidth / 2 + 4, y + 3);
                    }

                    if (v.poc) {
                        ctx.fillStyle = 'rgba(250, 204, 21, 0.2)'; ctx.fillRect(x + 1, y - cellH / 2, candleWidth - 2, cellH);
                        ctx.strokeStyle = '#facc15'; ctx.lineWidth = 1; ctx.strokeRect(x + 1, y - cellH / 2, candleWidth - 2, cellH);
                    }
                });

                // --- Professional Delta & Volume Ribbons ---
                const ribbonY = canvas.height - 50;
                const vH = Math.min(candle.volume / 50, 15); // Dynamic height
                const dH = Math.min(Math.abs(candle.delta) / 25, 15);

                ctx.fillStyle = '#1e2329'; ctx.fillRect(x + 5, ribbonY - 20, candleWidth - 10, 20);
                ctx.fillStyle = 'rgba(132, 142, 156, 0.3)'; ctx.fillRect(x + 5, ribbonY - vH, candleWidth - 10, vH);
                ctx.fillStyle = candle.delta >= 0 ? 'rgba(29, 191, 115, 0.6)' : 'rgba(246, 70, 93, 0.6)';
                ctx.fillRect(x + 5, ribbonY + 2, candleWidth - 10, dH);

                // Stats Labels
                ctx.fillStyle = '#848e9c'; ctx.font = '9px monospace'; ctx.textAlign = 'center';
                ctx.fillText(`V ${formatQty(candle.volume)}`, x + candleWidth / 2, canvas.height - 25);
                ctx.fillStyle = candle.delta >= 0 ? '#1dbf73' : '#f6465d';
                ctx.fillText(`D ${formatQty(candle.delta)}`, x + candleWidth / 2, canvas.height - 10);

                // Time
                ctx.fillStyle = '#4a5568';
                const tS = new Date(candle.time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
                ctx.fillText(tS, x + candleWidth / 2, canvas.height - 45);
            });

            // --- Crosshair ---
            if (mousePos.x > 0 && mousePos.x < canvas.width - 70 && mousePos.y < canvas.height - 60) {
                ctx.setLineDash([4, 4]); ctx.strokeStyle = 'rgba(132, 142, 156, 0.4)';
                ctx.beginPath(); ctx.moveTo(mousePos.x, 0); ctx.lineTo(mousePos.x, canvas.height - 60); ctx.stroke();
                ctx.beginPath(); ctx.moveTo(0, mousePos.y); ctx.lineTo(canvas.width - 70, mousePos.y); ctx.stroke();
                ctx.setLineDash([]);

                const hoverPrice = centerPrice + (centerY - mousePos.y) / scaleY;
                ctx.fillStyle = '#1e2329'; ctx.fillRect(canvas.width - 70, mousePos.y - 10, 70, 20);
                ctx.fillStyle = '#fff'; ctx.textAlign = 'right'; ctx.fillText(hoverPrice.toFixed(2), canvas.width - 5, mousePos.y + 4);
            }

            // Live Price Line
            const lY = centerY + (centerPrice - latestCandle.close) * scaleY;
            ctx.strokeStyle = '#22d3ee'; ctx.lineWidth = 1; ctx.beginPath(); ctx.moveTo(0, lY); ctx.lineTo(canvas.width - 70, lY); ctx.stroke();
            ctx.fillStyle = '#22d3ee'; ctx.fillRect(canvas.width - 70, lY - 10, 70, 20);
            ctx.fillStyle = '#0b0e11'; ctx.font = 'bold 11px monospace';
            ctx.fillText(latestCandle.close.toFixed(2), canvas.width - 5, lY + 4);

            frameId = requestAnimationFrame(render);
        };
        render();
        return () => cancelAnimationFrame(frameId);
    }, [data, offsetY, scaleY, candleWidth, tickSize, mousePos, autoFollow, initialized]);

    const handleWheel = (e) => {
        e.preventDefault();
        const factor = 1.1;
        const centerX = canvasRef.current.width / 2;
        const centerY = (canvasRef.current.height - 60) / 2;
        const currentPriceCenter = autoFollow ? data[data.length - 1]?.close : offsetY;

        if (e.ctrlKey) {
            // Precise Vertical Zoom centered on mouse
            const dy = e.deltaY > 0 ? 1 / factor : factor;
            const mousePrice = currentPriceCenter + (centerY - mousePos.y) / scaleY;

            const newScaleY = Math.max(1, Math.min(400, scaleY * dy));
            setScaleY(newScaleY);

            if (!autoFollow) {
                // Adjust offsetY so mouse stays over same price
                const newOffsetY = mousePrice - (centerY - mousePos.y) / newScaleY;
                setOffsetY(newOffsetY);
            }
        } else if (e.shiftKey) {
            // Horizontal Zoom
            const dx = e.deltaY > 0 ? 1 / factor : factor;
            setCandleWidth(p => Math.max(40, Math.min(1000, p * dx)));
        } else {
            // Pan
            setOffsetY(p => p - e.deltaY * (0.005 / (scaleY / 20)));
            setAutoFollow(false);
        }
    };

    const handleMouseDown = (e) => {
        const { offsetX, offsetY } = e.nativeEvent;
        setLastDragPos({ x: offsetX, y: offsetY });
        setIsDragging(true);
        if (offsetX > containerRef.current.clientWidth - 70) setDragMode('scaleY');
        else if (offsetY > containerRef.current.clientHeight - 60) setDragMode('scaleX');
        else { setDragMode('pan'); setAutoFollow(false); }
    };

    const handleMouseMove = (e) => {
        const { offsetX, offsetY } = e.nativeEvent;
        setMousePos({ x: offsetX, y: offsetY });
        if (isDragging) {
            const dx = offsetX - lastDragPos.x; const dy = offsetY - lastDragPos.y;
            if (dragMode === 'pan') setOffsetY(p => p + dy / scaleY);
            else if (dragMode === 'scaleY') setScaleY(p => Math.max(1, Math.min(500, p - dy * 0.8)));
            else if (dragMode === 'scaleX') setCandleWidth(p => Math.max(40, Math.min(1000, p + dx * 0.8)));
            setLastDragPos({ x: offsetX, y: offsetY });
        }
    };

    return (
        <div ref={containerRef} className="w-full h-full relative overflow-hidden bg-dark-bg select-none cursor-crosshair">
            <canvas ref={canvasRef} onMouseDown={handleMouseDown} onMouseMove={handleMouseMove} onMouseUp={() => setIsDragging(false)} onMouseLeave={() => { setIsDragging(false); setMousePos({ x: -1, y: -1 }); }} onWheel={handleWheel} />

            <div className="absolute top-4 right-24 flex space-x-2">
                <button onClick={() => setAutoFollow(!autoFollow)} className={`px-2 py-1 rounded text-[10px] font-bold border transition-all ${autoFollow ? 'bg-buy-green text-dark-bg border-buy-green shadow-[0_0_10px_rgba(29,191,115,0.4)]' : 'bg-dark-bg text-text-secondary border-grid-line'}`}>
                    {autoFollow ? '● LIVE SYNC' : '○ MANUAL MODE'}
                </button>
                <select value={tickSize} onChange={e => setTickSize(parseFloat(e.target.value))} className="bg-dark-bg text-[10px] border border-grid-line text-buy-green outline-none px-2 rounded font-bold shadow-lg">
                    <option value="0.1">0.1 PRECISION</option><option value="0.5">0.5 TICK</option><option value="1.0">1.0 STEP</option><option value="5.0">5.0 AGG</option>
                </select>
            </div>

            {!autoFollow && (
                <button onClick={() => setAutoFollow(true)} className="absolute bottom-20 right-24 bg-accent-blue/20 hover:bg-accent-blue/40 text-accent-blue border border-accent-blue/40 px-3 py-1.5 rounded-full text-[10px] font-bold shadow-xl transition-all">
                    ↑ BACK TO LIVE
                </button>
            )}

            <div className="absolute bottom-12 left-4 px-2 py-1 bg-dark-bg/40 rounded text-[9px] text-text-secondary opacity-30 hover:opacity-100 transition-opacity">
                SCROLL: PAN | CTRL+SCROLL: ZOOM Y | SHIFT+SCROLL: ZOOM X | DRAG AXIS: SCALE
            </div>
        </div>
    );
};

export default FootprintChart;
