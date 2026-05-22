
const API_BASE = 'http://127.0.0.1:8000/api';

const state = {
    markets: [],
    activeCode: null,
    chart: null,
    series: {}
};

// Start
document.addEventListener('DOMContentLoaded', init);

async function init() {
    console.log("Hyper-Terminal v5 Starting...");
    await loadMarkets();
}

async function loadMarkets() {
    try {
        const res = await fetch(`${API_BASE}/markets`);
        const data = await res.json();
        state.markets = data;

        renderMarketSelect();

        // Auto-select S&P
        const sp = data.find(m => m.market_and_exchange_names.includes('S&P 500') && m.market_and_exchange_names.includes('E-MINI'));
        if (sp) loadMarket(sp);
        else if (data.length > 0) loadMarket(data[0]);

    } catch (e) {
        console.error("Init failed", e);
    }
}

function renderMarketSelect() {
    const sel = document.getElementById('market-select');
    sel.innerHTML = '<option value="" disabled selected>Select a Market...</option>';

    // Sort roughly
    const sorted = state.markets.sort((a, b) => a.market_and_exchange_names.localeCompare(b.market_and_exchange_names));

    sorted.forEach(m => {
        const opt = document.createElement('option');
        opt.value = m.cftc_contract_market_code;
        opt.textContent = m.market_and_exchange_names;
        sel.appendChild(opt);
    });

    sel.onchange = (e) => {
        const m = state.markets.find(x => x.cftc_contract_market_code === e.target.value);
        if (m) loadMarket(m);
    };
}

async function loadMarket(market) {
    if (state.activeCode === market.cftc_contract_market_code) return;
    state.activeCode = market.cftc_contract_market_code;

    // UI Update
    const sel = document.getElementById('market-select');
    sel.value = state.activeCode;
    document.getElementById('mkt-code').textContent = state.activeCode;

    // Fetch Data
    try {
        const res = await fetch(`${API_BASE}/data/${state.activeCode}`);
        const data = await res.json();

        console.log(`Loaded ${data.length} rows`);
        // Render
        renderChart(data);
        renderDataGrid(data);

    } catch (e) {
        console.error("Data load failed", e);
    }
}

function renderChart(data) {
    const container = document.getElementById('chart-container');

    // Init Chart if needed
    if (!state.chart) {
        state.chart = LightweightCharts.createChart(container, {
            layout: { background: { type: 'solid', color: 'transparent' }, textColor: '#888' },
            grid: { vertLines: { color: '#222' }, horzLines: { color: '#222' } },
            timeScale: { borderColor: '#444' },
            rightPriceScale: { borderColor: '#444', scaleMargins: { top: 0.1, bottom: 0.1 } },
        });

        // Series 1: Net Positions (Histogram)
        state.series.net = state.chart.addHistogramSeries({
            color: '#00f0ff',
            priceFormat: { type: 'volume' },
            priceScaleId: 'right'
        });

        // Series 2: Open Interest (Line) - Force White
        state.series.oi = state.chart.addLineSeries({
            color: '#ffffff',
            lineWidth: 2,
            priceScaleId: 'right', // Overlay on right to ensure visibility
            lineStyle: 0
        });

        // Resize
        new ResizeObserver(entries => {
            if (entries.length === 0 || !entries[0].contentRect) return;
            const { width, height } = entries[0].contentRect;
            state.chart.resize(width, height);
            state.chart.timeScale().fitContent();
        }).observe(container);
    }

    // Process Data
    const sorted = [...data].sort((a, b) => new Date(a.report_date_as_yyyy_mm_dd) - new Date(b.report_date_as_yyyy_mm_dd));

    const histData = sorted.map(d => ({
        time: d.report_date_as_yyyy_mm_dd.split('T')[0],
        value: d.net_noncomm,
        color: d.net_noncomm >= 0 ? '#00f0ff' : '#ff3366'
    }));

    const lineData = sorted.map(d => ({
        time: d.report_date_as_yyyy_mm_dd.split('T')[0],
        value: d.open_interest_all
    }));

    state.series.net.setData(histData);
    state.series.oi.setData(lineData);

    setTimeout(() => state.chart.timeScale().fitContent(), 100);
}

function renderDataGrid(data) {
    const grid = document.getElementById('data-grid');
    if (!data || data.length === 0) {
        grid.innerHTML = '<div class="empty-msg">No Data Available</div>';
        document.getElementById('last-date').textContent = "--/--/----";
        return;
    }

    // Sort latest first
    const sorted = [...data].sort((a, b) => new Date(b.report_date_as_yyyy_mm_dd) - new Date(a.report_date_as_yyyy_mm_dd));
    const d = sorted[0];

    document.getElementById('last-date').textContent = d.report_date_as_yyyy_mm_dd.split('T')[0];

    const row = (label, l, s, net) => {
        const total = (l || 0) + (s || 0);
        const lPct = total ? (l / total) * 100 : 50;
        return `
            <div class="data-row">
                <div class="dr-label">${label}</div>
                <div class="dr-bar">
                    <div class="bar-track">
                        <div class="bar-fill" style="width:${lPct}%; background:var(--green)"></div>
                        <div class="bar-fill" style="width:${100 - lPct}%; background:var(--red)"></div>
                    </div>
                </div>
                <div class="dr-val pos">${(l || 0).toLocaleString()}</div>
                <div class="dr-val neg">${(s || 0).toLocaleString()}</div>
                <div class="dr-val ${net >= 0 ? 'pos' : 'neg'}">${(net || 0).toLocaleString()}</div>
            </div>
        `;
    };

    grid.innerHTML = `
        <div class="data-row" style="opacity:0.5; font-size:10px;">
            <div class="dr-label">GROUP</div>
            <div class="dr-bar">L/S RATIO</div>
            <div class="dr-val">LONG</div>
            <div class="dr-val">SHORT</div>
            <div class="dr-val">NET</div>
        </div>
        ${row('Large Specs (Managed Money)', d.noncomm_positions_long_all, d.noncomm_positions_short_all, d.net_noncomm)}
        ${row('Commercials (Hedgers)', d.comm_positions_long_all, d.comm_positions_short_all, d.net_comm)}
        ${row('Small Traders', d.nonrept_positions_long_all, d.nonrept_positions_short_all, (d.nonrept_positions_long_all - d.nonrept_positions_short_all))}
        
        <div style="margin-top:20px; text-align:right; font-family:var(--font-code); color:#666;">
            OPEN INTEREST: <span style="color:#fff">${(d.open_interest_all || 0).toLocaleString()}</span>
        </div>
    `;
}

window.app = {
    sync: async () => {
        const btn = document.querySelector('.btn-sync');
        btn.textContent = "SYNCING...";
        document.getElementById('db-status').textContent = "PULLING CFTC...";

        await fetch(`${API_BASE}/update`);

        btn.textContent = "FORCE SYNC";
        document.getElementById('db-status').textContent = "READY";

        // Reload current
        if (state.activeCode && state.markets.length > 0) {
            const m = state.markets.find(x => x.cftc_contract_market_code === state.activeCode);
            if (m) loadMarket(m);
        } else {
            loadMarkets();
        }
    }
};
