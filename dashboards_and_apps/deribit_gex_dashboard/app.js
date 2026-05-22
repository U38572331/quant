// app.js

// Configuration
const API_URL = '/api/data';
const REFRESH_RATE = 10000; // 10 seconds

// State
let charts = {
    gex: null,
    oi: null
};

// Main Entry Point
document.addEventListener('DOMContentLoaded', () => {
    initCharts();
    fetchData();
    setInterval(fetchData, REFRESH_RATE);
});

async function fetchData() {
    updateStatus('Fetching...');
    try {
        const response = await fetch(API_URL);
        if (!response.ok) throw new Error('Network response was not ok');

        const data = await response.json();
        const processed = processData(data.result || []);

        updateDashboard(processed);
        updateStatus('Connected', true);
    } catch (error) {
        console.error('Fetch error:', error);
        updateStatus('Error', false);
    }
}

// Data Processing Logic
function processData(rawData) {
    // 1. Group by Strike for 2D charts, and by (Expiry, Strike) for 3D Heatmap
    const strikeData = {};
    const heatmapData = {}; // { expiryDate: { strike: { netGex, iv } } }

    let currentPrice = 0;
    let totalCallIv = 0, totalPutIv = 0, callCount = 0, putCount = 0;

    rawData.forEach(item => {
        if (!item.instrument_name.startsWith('BTC')) return;
        if (currentPrice === 0) currentPrice = item.underlying_price;

        const parts = item.instrument_name.split('-');
        if (parts.length < 4) return;

        const expiryStr = parts[1];
        const strike = parseInt(parts[2]);
        const type = parts[3];

        // --- GEX Logic (Approx) ---
        let gamma = item.greeks?.gamma;
        if (!gamma && item.mark_iv > 0) {
            const now = Date.now();
            const expiryDate = parseExpiry(expiryStr);
            const t = Math.max(0.001, (expiryDate - now) / (365 * 24 * 3600 * 1000));
            const K = strike;
            const S = item.underlying_price;
            const v = item.mark_iv / 100;
            const r = 0;

            if (v > 0) {
                const d1 = (Math.log(S / K) + (r + v * v / 2) * t) / (v * Math.sqrt(t));
                const pdf = Math.exp(-0.5 * d1 * d1) / Math.sqrt(2 * Math.PI);
                gamma = pdf / (S * v * Math.sqrt(t));
            }
        }
        const gexValue = (gamma || 0) * item.open_interest * item.underlying_price;

        // 2D Aggregation
        if (!strikeData[strike]) {
            strikeData[strike] = { strike, callGex: 0, putGex: 0, callOi: 0, putOi: 0, netGex: 0 };
        }

        strikeData[strike].callOi += (type === 'C' ? item.open_interest : 0);
        strikeData[strike].putOi += (type === 'P' ? item.open_interest : 0);

        if (type === 'C') {
            strikeData[strike].callGex += gexValue;
            strikeData[strike].netGex += gexValue;
            if (item.mark_iv) { totalCallIv += item.mark_iv; callCount++; }
        } else {
            strikeData[strike].putGex += gexValue;
            strikeData[strike].netGex -= gexValue;
            if (item.mark_iv) { totalPutIv += item.mark_iv; putCount++; }
        }

        // 3D Aggregation
        if (!heatmapData[expiryStr]) heatmapData[expiryStr] = {};
        if (!heatmapData[expiryStr][strike]) heatmapData[expiryStr][strike] = { netGex: 0, iv: 0, count: 0 };

        if (type === 'C') {
            heatmapData[expiryStr][strike].netGex += gexValue;
        } else {
            heatmapData[expiryStr][strike].netGex -= gexValue;
        }
        heatmapData[expiryStr][strike].iv += item.mark_iv || 0;
        heatmapData[expiryStr][strike].count++;
    });

    // Process 2D Ticks
    const ticks = Object.values(strikeData).sort((a, b) => a.strike - b.strike);
    const activeTicks = ticks.filter(t => (t.callOi + t.putOi) > 10);

    return {
        ticks: activeTicks,
        heatmapData,
        currentPrice,
        avgCallIv: callCount ? (totalCallIv / callCount).toFixed(1) : 0,
        avgPutIv: putCount ? (totalPutIv / putCount).toFixed(1) : 0
    };
}

function parseExpiry(str) {
    const months = { JAN: 0, FEB: 1, MAR: 2, APR: 3, MAY: 4, JUN: 5, JUL: 6, AUG: 7, SEP: 8, OCT: 9, NOV: 10, DEC: 11 };
    const day = parseInt(str.slice(0, 2));
    const mon = str.slice(2, 5);
    const yr = 2000 + parseInt(str.slice(5));
    return new Date(Date.UTC(yr, months[mon], day));
}

function updateDashboard(data) {
    const { ticks, heatmapData, currentPrice, avgCallIv, avgPutIv } = data;

    document.getElementById('btc-price').innerText = currentPrice.toLocaleString('en-US', { style: 'currency', currency: 'USD' });
    document.getElementById('date-range').innerText = new Date().toISOString().split('T')[0];

    // 1. Calculate Metrics
    const totalCallGex = ticks.reduce((acc, t) => acc + t.callGex, 0);
    const totalPutGex = ticks.reduce((acc, t) => acc + t.putGex, 0);
    const netGex = ticks.reduce((acc, t) => acc + t.netGex, 0);

    // Zero Gamma
    let zeroGamma = 'N/A';
    for (let i = 0; i < ticks.length - 1; i++) {
        if (ticks[i].netGex > 0 && ticks[i + 1].netGex < 0 || ticks[i].netGex < 0 && ticks[i + 1].netGex > 0) {
            zeroGamma = ticks[i + 1].strike;
            break;
        }
    }

    // Max Levels
    const maxCallOi = ticks.reduce((max, t) => t.callOi > max.callOi ? t : max, ticks[0] || { callOi: 0, strike: '-' });
    const maxPutOi = ticks.reduce((max, t) => t.putOi > max.putOi ? t : max, ticks[0] || { putOi: 0, strike: '-' });
    const maxPosGex = ticks.reduce((max, t) => t.netGex > max.netGex ? t : max, ticks[0] || { netGex: 0, strike: '-' });
    const maxNegGex = ticks.reduce((min, t) => t.netGex < min.netGex ? t : min, ticks[0] || { netGex: 0, strike: '-' });

    // Update DOM
    document.getElementById('gex-ratio').innerText = totalPutGex > 0 ? (totalCallGex / totalPutGex).toFixed(2) : '-';
    document.getElementById('net-gex').innerText = `$${(netGex / 1000000).toFixed(1)}M`;
    document.getElementById('net-gex').className = `value ${netGex >= 0 ? 'green' : 'red'}`;

    document.getElementById('call-oi-max').innerHTML = `${(maxCallOi.callOi / 1000).toFixed(1)}K <span class="label">@ ${maxCallOi.strike}</span>`;
    document.getElementById('call-oi-max').className = 'value green';

    document.getElementById('put-oi-max').innerHTML = `${(maxPutOi.putOi / 1000).toFixed(1)}K <span class="label">@ ${maxPutOi.strike}</span>`;
    document.getElementById('put-oi-max').className = 'value red';

    document.getElementById('pos-gex-max').innerHTML = `${(maxPosGex.netGex / 1000000).toFixed(1)}M <span class="label">@ ${maxPosGex.strike}</span>`;
    document.getElementById('neg-gex-max').innerHTML = `${(maxNegGex.netGex / 1000000).toFixed(1)}M <span class="label">@ ${maxNegGex.strike}</span>`;

    document.getElementById('zero-gamma').innerText = zeroGamma;
    document.getElementById('call-iv').innerText = `${avgCallIv}%`;
    document.getElementById('put-iv').innerText = `${avgPutIv}%`;

    // Charts
    updateGexChart(charts.gex, ticks, currentPrice);
    updateOiChart(charts.oi, ticks, currentPrice);

    renderHeatmaps(heatmapData);
}

function renderHeatmaps(data) {
    if (!window.Plotly) return;

    const expiries = Object.keys(data).sort((a, b) => parseExpiry(a) - parseExpiry(b));
    const allStrikes = new Set();
    Object.values(data).forEach(d => Object.keys(d).forEach(k => allStrikes.add(parseInt(k))));
    const strikes = Array.from(allStrikes).sort((a, b) => a - b);

    // Build Z Matrix
    const zGex = [];
    const zIv = [];

    expiries.forEach(exp => {
        const rowGex = [];
        const rowIv = [];
        strikes.forEach(str => {
            const cell = data[exp][str];
            rowGex.push(cell ? cell.netGex : 0);
            rowIv.push(cell ? (cell.iv / cell.count) : 0);
        });
        zGex.push(rowGex);
        zIv.push(rowIv);
    });

    const commonLayout = {
        autosize: true,
        margin: { l: 0, r: 0, b: 0, t: 0 },
        paper_bgcolor: 'rgba(0,0,0,0)',
        plot_bgcolor: 'rgba(0,0,0,0)',
        scene: {
            xaxis: { title: '', color: '#888', gridcolor: '#444' },
            yaxis: { title: '', color: '#888', gridcolor: '#444', ticktext: expiries, tickvals: expiries.map((_, i) => i) },
            zaxis: { title: '', color: '#888', gridcolor: '#444' },
            camera: { eye: { x: 1.5, y: 1.5, z: 1.2 } },
            aspectmode: 'cube'
        },
        font: { color: '#e0e0e0', size: 9 },
        showlegend: false
    };

    Plotly.react('gex-heatmap', [{
        type: 'surface',
        z: zGex,
        x: strikes,
        y: expiries.map((_, i) => i),
        colorscale: [[0, 'red'], [0.5, 'white'], [1, 'lime']],
        showscale: false,
        name: 'GEX'
    }], commonLayout);

    Plotly.react('iv-heatmap', [{
        type: 'surface',
        z: zIv,
        x: strikes,
        y: expiries.map((_, i) => i),
        colorscale: 'Viridis',
        showscale: false,
        name: 'IV'
    }], commonLayout);
}

function initCharts() {
    Chart.defaults.color = '#888';
    Chart.defaults.borderColor = '#333';

    const ctxGex = document.getElementById('gexChart').getContext('2d');
    charts.gex = new Chart(ctxGex, {
        type: 'bar',
        data: { labels: [], datasets: [] },
        options: {
            indexAxis: 'y', // Horizontal bars
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                title: { display: false }
            },
            scales: {
                x: { grid: { color: '#333' } },
                y: { grid: { color: '#333' }, ticks: { color: '#e0e0e0' } }
            }
        }
    });

    const ctxOi = document.getElementById('oiChart').getContext('2d');
    charts.oi = new Chart(ctxOi, {
        type: 'bar',
        data: { labels: [], datasets: [] },
        options: {
            indexAxis: 'y',
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                x: { stacked: true },
                y: { stacked: true, grid: { display: false } }
            }
        }
    });
}

function updateGexChart(chart, ticks, price) {
    const labels = ticks.map(t => t.strike);
    const data = ticks.map(t => t.netGex);
    const bgColors = data.map(v => v >= 0 ? '#00ff00' : '#ff0000');

    chart.data.labels = labels;
    chart.data.datasets = [{
        label: 'Net GEX',
        data: data,
        backgroundColor: bgColors,
        barThickness: 'flex',
        maxBarThickness: 20
    }];

    chart.update();
}

function updateOiChart(chart, ticks, price) {
    const labels = ticks.map(t => t.strike);
    const callData = ticks.map(t => t.callOi);
    const putData = ticks.map(t => -t.putOi);

    chart.data.labels = labels;
    chart.data.datasets = [
        {
            label: 'Calls',
            data: callData,
            backgroundColor: '#00ff00',
            barThickness: 'flex',
            maxBarThickness: 20
        },
        {
            label: 'Puts',
            data: putData,
            backgroundColor: '#ff0000',
            barThickness: 'flex',
            maxBarThickness: 20
        }
    ];
    chart.update();
}

function updateStatus(msg, isSuccess) {
    const el = document.getElementById('api-status');
    el.innerText = msg;
    el.style.color = isSuccess === true ? '#00ff00' : (isSuccess === false ? '#ff0000' : '#888');
}
