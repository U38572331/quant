const API_URL = "/api/v1/snapshot/BTC";

async function refreshData() {
    try {
        const response = await fetch(API_URL);
        const data = await response.json();
        if (!data || !data.metrics) return;

        updateStats(data);
        renderGammaChart(data);
        renderInventoryChart(data);
        render3DSurface(data);

        document.getElementById('date-display').textContent = new Date().toLocaleDateString();

    } catch (e) {
        console.error("Refresh failed:", e);
    }
}

function updateStats(data) {
    const fmt = (n) => n ? new Intl.NumberFormat('en-US', { notation: "compact" }).format(n) : '-';

    document.getElementById('gex-ratio').textContent = (data.metrics.pcr_oi || 0).toFixed(2);
    document.getElementById('net-gex-val').textContent = fmt(data.metrics.total_gex);
    document.getElementById('call-oi-val').textContent = fmt(data.metrics.total_oi * 0.6); // Approx estimate if not avail
    document.getElementById('put-oi-val').textContent = fmt(data.metrics.total_oi * 0.4);
    document.getElementById('spot-price').textContent = data.spot_price.toLocaleString(undefined, { maximumFractionDigits: 0 });

    document.getElementById('ai-content').innerHTML = data.summary_html;
}

function renderGammaChart(data) {
    const container = document.getElementById('gamma-chart');
    if (!data.curve || !data.curve.x) return;

    const x = data.curve.y; // GEX Values
    const y = data.curve.x; // Strikes

    const colors = x.map(v => v > 0 ? '#00e676' : '#ff1744');

    const trace = {
        x: x,
        y: y,
        type: 'bar',
        orientation: 'h',
        marker: { color: colors },
        hoverinfo: 'x+y'
    };

    const spot = data.spot_price;
    const shape = {
        type: 'line',
        x0: Math.min(...x), x1: Math.max(...x),
        y0: spot, y1: spot,
        line: { color: '#ffd700', width: 1, dash: 'dot' }
    };

    const layout = {
        paper_bgcolor: 'transparent',
        plot_bgcolor: 'transparent',
        margin: { t: 5, r: 10, b: 20, l: 40 },
        font: { family: 'Roboto Mono', color: '#666', size: 10 },
        xaxis: { gridcolor: '#333', zerolinecolor: '#555' },
        yaxis: { gridcolor: '#333', range: [spot * 0.8, spot * 1.2] }, // Zoom near spot
        shapes: [shape],
        showlegend: false
    };

    Plotly.react(container, [trace], layout, { displayModeBar: false, responsive: true });
}

function renderInventoryChart(data) {
    const container = document.getElementById('inventory-chart');
    const profile = data.oi_profile;
    if (!profile || profile.length === 0) return;

    // Sort logic? Usually provided sorted by strike.

    const strikes = profile.map(p => p.strike);
    const calls = profile.map(p => p.call_oi);
    const puts = profile.map(p => -p.put_oi); // Negative for Left Side spine

    const traceCalls = {
        x: calls, y: strikes, name: 'Calls', type: 'bar', orientation: 'h',
        marker: { color: '#00e676' }
    };

    const tracePuts = {
        x: puts, y: strikes, name: 'Puts', type: 'bar', orientation: 'h',
        marker: { color: '#ff1744' }
    };

    const spot = data.spot_price;
    const shape = {
        type: 'line',
        x0: Math.min(...puts), x1: Math.max(...calls),
        y0: spot, y1: spot,
        line: { color: '#ffd700', width: 1, dash: 'dot' }
    };

    const layout = {
        paper_bgcolor: 'transparent',
        plot_bgcolor: 'transparent',
        margin: { t: 5, r: 10, b: 20, l: 40 },
        font: { family: 'Roboto Mono', color: '#666', size: 10 },
        xaxis: { gridcolor: '#333', zerolinecolor: '#555' },
        yaxis: { gridcolor: '#333', range: [spot * 0.8, spot * 1.2] },
        shapes: [shape],
        barmode: 'overlay', // or relative
        showlegend: false
    };

    Plotly.react(container, [tracePuts, traceCalls], layout, { displayModeBar: false, responsive: true });
}

function render3DSurface(data) {
    const container = document.getElementById('heatmap-3d');
    const surf = data.gex_surface;
    if (!surf || !surf.z) return;

    const trace = {
        z: surf.z,
        x: surf.x,
        y: surf.y,
        type: 'surface',
        colorscale: [
            [0, 'rgb(255, 23, 68)'],
            [0.5, 'rgb(30,30,30)'],
            [1, 'rgb(0, 230, 118)']
        ],
        contours: {
            z: { show: true, usecolormap: true, highlightcolor: "#42f462", project: { z: true } }
        }
    };

    const layout = {
        paper_bgcolor: 'transparent',
        plot_bgcolor: 'transparent',
        margin: { t: 0, r: 0, b: 0, l: 0 },
        font: { family: 'Roboto', color: '#ccc', size: 9 },
        scene: {
            xaxis: { title: 'Expiry', gridcolor: '#444' },
            yaxis: { title: 'Strike', gridcolor: '#444' },
            zaxis: { title: 'GEX', gridcolor: '#444' },
            camera: { eye: { x: 1.5, y: 1.5, z: 1.2 } }
        }
    };

    Plotly.react(container, [trace], layout, { displayModeBar: false, responsive: true });
}

// Init
refreshData();
setInterval(refreshData, 15000);
