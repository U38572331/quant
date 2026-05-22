import React, { useEffect, useRef } from 'react';
import * as LW from 'lightweight-charts';

export default function KLineChart({ data, tradeDate, type }) {
  const chartContainerRef = useRef();

  useEffect(() => {
    if (!data || data.length === 0) return;

    const container = chartContainerRef.current;
    if (!container || container.clientWidth <= 0) return;

    const { createChart, ColorType, CandlestickSeries, createSeriesMarkers } = LW;

    const chart = createChart(container, {
      layout: {
        background: { type: ColorType ? ColorType.Solid : 'Solid', color: 'transparent' },
        textColor: '#94a3b8',
      },
      grid: {
        vertLines: { color: 'rgba(255, 255, 255, 0.05)' },
        horzLines: { color: 'rgba(255, 255, 255, 0.05)' },
      },
      width: container.clientWidth,
      height: 400,
      timeScale: {
        borderColor: 'rgba(255, 255, 255, 0.1)',
      },
    });

    let candlestickSeries;
    
    // Compatibility check for v4 and v5
    if (chart.addCandlestickSeries) {
      candlestickSeries = chart.addCandlestickSeries({
        upColor: '#10b981',
        downColor: '#ef4444',
        borderVisible: false,
        wickUpColor: '#10b981',
        wickDownColor: '#ef4444',
      });
    } else if (chart.addSeries && CandlestickSeries) {
      candlestickSeries = chart.addSeries(CandlestickSeries, {
        upColor: '#10b981',
        downColor: '#ef4444',
        borderVisible: false,
        wickUpColor: '#10b981',
        wickDownColor: '#ef4444',
      });
    }

    if (!candlestickSeries) return;

    candlestickSeries.setData(data);

    if (tradeDate) {
      const markers = [
        {
          time: tradeDate,
          position: type === 'Purchase' ? 'belowBar' : 'aboveBar',
          color: type === 'Purchase' ? '#10b981' : '#ef4444',
          shape: type === 'Purchase' ? 'arrowUp' : 'arrowDown',
          text: `${type} @ ${tradeDate}`,
        },
      ];

      // Try v4 way first, then v5 primitive way
      if (candlestickSeries.setMarkers) {
        candlestickSeries.setMarkers(markers);
      } else if (createSeriesMarkers && candlestickSeries.attachPrimitive) {
        // v5 requires the series as the first argument to createSeriesMarkers
        const markersPrimitive = createSeriesMarkers(candlestickSeries, markers);
        candlestickSeries.attachPrimitive(markersPrimitive);
      }
    }

    chart.timeScale().fitContent();

    const resizeObserver = new ResizeObserver(entries => {
      if (entries.length === 0 || entries[0].target !== container) return;
      const newRect = entries[0].contentRect;
      if (newRect.width > 0) {
        chart.applyOptions({ width: newRect.width });
      }
    });

    resizeObserver.observe(container);

    return () => {
      resizeObserver.disconnect();
      chart.remove();
    };
  }, [data, tradeDate, type]);

  return <div ref={chartContainerRef} style={{ width: '100%', height: '400px' }} />;
}
