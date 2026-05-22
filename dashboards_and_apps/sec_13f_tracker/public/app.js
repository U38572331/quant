// 13F Terminal Logic - Master Edition (Fixed Scaling)

let dataStore = [];
let changeStore = null;
let macroStore = null;
let portfolioSnapshotChart = null;
let sectorSnapshotChart = null;
let globalSectorChart = null;
let rotationChart = null;

// Chart Instances for Macro
let chartRates = null;
let chartMacro = null;

const SECTOR_MAP = {
    "APPLE": "Technology", "MICROSOFT": "Technology", "NVIDIA": "Technology", "BROADCOM": "Technology",
    "ALPHABET": "Communication", "META PLATFORMS": "Communication", "NETFLIX": "Communication",
    "BERKSHIRE HATHAWAY": "Financials", "JPMORGAN CHASE": "Financials", "VISA": "Financials", "MASTERCARD": "Financials",
    "BANK OF AMERICA": "Financials", "WELLS FARGO": "Financials", "GOLDMAN SACHS": "Financials",
    "AMAZON": "Consumer Disc", "TESLA": "Consumer Disc", "HOME DEPOT": "Consumer Disc",
    "ELI LILLY": "Healthcare", "UNITEDHEALTH": "Healthcare", "NOVO NORDISK": "Healthcare",
    "EXXON MOBIL": "Energy", "CHEVRON": "Energy", "WALMART": "Consumer Staples",
    "COSTCO": "Consumer Staples", "PROCTER & GAMBLE": "Consumer Staples", "COCA-COLA": "Consumer Staples",
    "PEPSICO": "Consumer Staples"
};

const getSector = (n) => {
    n = (n || '').toUpperCase();
    for (const [k, s] of Object.entries(SECTOR_MAP)) if (n.includes(k)) return s;
    return "Others";
};

document.addEventListener('DOMContentLoaded', bootstrap);

async function bootstrap() {
    try {
        const ts = new Date().getTime();
        const [hR, cR, mR] = await Promise.all([
            fetch(`holdings.json?v=${ts}`), fetch(`change_summary.json?v=${ts}`).catch(() => null), fetch(`macro.json?v=${ts}`).catch(() => null)
        ]);
        if (!hR.ok) throw new Error('System Offline');
        dataStore = await hR.json();
        if (cR && cR.ok) changeStore = await cR.json();
        if (mR && mR.ok) macroStore = await mR.json();

        initMarketOverview();
        initFundDropdown();
        setupSearch();
        if (changeStore) renderMomentum();
        if (macroStore) renderMacro();
    } catch (e) { console.error(e); }
}

function switchView(v) {
    ['overview', 'momentum', 'funds', 'macro'].forEach(n => {
        const el = document.getElementById(`view-${n}`);
        if (el) el.style.display = n === v ? 'block' : 'none';
        const nav = document.getElementById(`nav-${n}`);
        if (nav) nav.classList.toggle('active', n === v);
    });
    if (v === 'momentum') renderMomentum();
    if (v === 'macro') renderMacro();
}

const formatShortVal = (v) => {
    if (isNaN(v) || v === null) return "$0";
    const isNeg = v < 0;
    v = Math.abs(v); // Input is now ALWAYS in DOLLARS after normalization
    if (v >= 1e12) return (isNeg ? '-' : '') + `$${(v / 1e12).toFixed(2)}T`;
    if (v >= 1e9) return (isNeg ? '-' : '') + `$${(v / 1e9).toFixed(1)}B`;
    if (v >= 1e6) return (isNeg ? '-' : '') + `$${(v / 1e6).toFixed(1)}M`;
    return (isNeg ? '-' : '') + `$${v.toLocaleString()}`;
};

function initMarketOverview() {
    const agg = new Map(), funds = new Map(), sectors = {};
    dataStore.forEach(r => {
        const nm = (r.Issuer || 'Unknown').toUpperCase().trim().replace(/  +/g, ' ');
        const v = parseFloat(r['Value_USD']) || 0;
        agg.set(nm, (agg.get(nm) || 0) + v);
        if (!funds.has(nm)) funds.set(nm, new Set()); funds.get(nm).add(r.Fund);
        const s = getSector(nm); sectors[s] = (sectors[s] || 0) + v;
    });
    const ranked = Array.from(agg.entries()).map(([n, t]) => ({ n, t, f: funds.get(n).size })).sort((a, b) => b.t - a.t);
    document.getElementById('total-val').textContent = formatShortVal(ranked.reduce((a, c) => a + c.t, 0));
    document.getElementById('consensus-pick').textContent = ranked[0]?.n || 'N/A';
    document.getElementById('entities-count').textContent = new Set(dataStore.map(d => d.Fund)).size;

    const ctx = document.getElementById('global-sector-chart').getContext('2d');
    const sData = Object.entries(sectors).filter(([n]) => n !== "Others").sort((a, b) => b[1] - a[1]);
    if (globalSectorChart) globalSectorChart.destroy();
    globalSectorChart = new Chart(ctx, { type: 'bar', data: { labels: sData.map(d => d[0]), datasets: [{ data: sData.map(d => d[1]), backgroundColor: '#5c7cff', borderRadius: 4, barThickness: 10 }] }, options: { indexAxis: 'y', plugins: { legend: { display: false } }, scales: { x: { display: false }, y: { grid: { display: false }, ticks: { color: '#718096', font: { size: 9 } } } }, responsive: true, maintainAspectRatio: false } });

    const b = document.getElementById('overview-body'); b.innerHTML = '';
    ranked.slice(0, 100).forEach((it, i) => {
        const r = document.createElement('tr'); r.style.cursor = 'pointer'; r.onclick = () => showSecurityDetail(it.n);
        let sentiment = "";
        if (changeStore && changeStore.weekly) {
            const chg = changeStore.weekly.changes.find(c => c.Issuer.toUpperCase().trim() === it.n);
            if (chg) sentiment = chg.value_change > 0 ? "📈" : "📉";
        }
        r.innerHTML = `<td class="mono">#${(i + 1).toString().padStart(2, '0')}</td><td class="mono" style="font-size:11px">${it.n.substring(0, 12)}</td><td style="font-weight:600">${it.n} ${sentiment}</td><td style="color:#718096; font-size:12px">${getSector(it.n)}</td><td class="text-right mono">${formatShortVal(it.t)}</td><td class="text-right mono" style="color:var(--accent-blue); font-weight:600">${it.f}</td>`;
        b.appendChild(r);
    });
}

function showSecurityDetail(iss) {
    const p = document.getElementById('security-breakdown-panel'), b = document.getElementById('security-detail-body');
    document.getElementById('detail-security-title').textContent = `${iss} - Institutional Holders`;
    p.style.display = 'block'; b.innerHTML = '';
    const h = dataStore.filter(d => (d.Issuer || '').toUpperCase().trim() === iss).sort((a, b) => parseFloat(b['Value_USD']) - parseFloat(a['Value_USD']));
    h.forEach(x => {
        const r = document.createElement('tr');
        r.innerHTML = `<td><span class="btn" style="border:none; padding:0; text-decoration:underline" onclick="goToFund('${x.Fund}')">${x.Fund}</span></td><td class="text-right mono">${parseInt(x.Shares).toLocaleString()}</td><td class="text-right mono">${formatShortVal(parseFloat(x['Value_USD']))}</td><td class="text-right mono" style="color:#718096">${x.FilingDate}</td>`;
        b.appendChild(r);
    });
    window.scrollTo({ top: p.offsetTop - 20, behavior: 'smooth' });
}

function closeSecurityDetail() { document.getElementById('security-breakdown-panel').style.display = 'none'; }
function goToFund(f) { switchView('funds'); document.getElementById('fund-select').value = f; renderFundDetail(); }

function renderMomentum() {
    const p = document.getElementById('momentum-period').value;
    if (!changeStore || !changeStore[p]) return;
    const d = changeStore[p];
    document.getElementById('change-source-count').textContent = new Set(dataStore.map(d => d.Fund)).size;

    const rotData = Object.entries(d.sector_rotation || {}).sort((a, b) => b[1] - a[1]);
    const ctx = document.getElementById('rotation-chart').getContext('2d');
    if (rotationChart) rotationChart.destroy();
    rotationChart = new Chart(ctx, { type: 'bar', data: { labels: rotData.map(r => r[0]), datasets: [{ label: 'Flow', data: rotData.map(r => r[1]), backgroundColor: rotData.map(r => r[1] >= 0 ? '#48bb78' : '#f56565'), borderRadius: 4 }] }, options: { indexAxis: 'y', plugins: { legend: { display: false } }, scales: { x: { grid: { color: '#23232a' }, ticks: { color: '#4a5568', font: { size: 9 } } }, y: { grid: { display: false }, ticks: { color: '#718096', font: { size: 10 } } } }, responsive: true, maintainAspectRatio: false } });

    const cb = (id, list, lim = false) => {
        const b = document.getElementById(id); if (!b) return;
        b.innerHTML = '';
        (lim ? list.slice(0, 15) : list.slice(0, 50)).forEach(it => {
            const r = document.createElement('tr'), c = it.value_change >= 0 ? 'var(--accent-green)' : 'var(--accent-red)';
            if (id === 'momentum-body') r.innerHTML = `<td class="mono" style="color:#718096">${it.CUSIP || '-'}</td><td style="font-weight:600">${it.Issuer}</td><td style="font-size:12px; color:#4a5568">${it.Sector || getSector(it.Issuer)}</td><td class="text-right mono" style="color:${c}">${it.share_change >= 0 ? '+' : ''}${parseInt(it.share_change).toLocaleString()}</td><td class="text-right mono" style="color:${c}">${formatShortVal(it.value_change)}</td><td class="text-right mono">${it.fund_change >= 0 ? '+' : ''}${it.fund_change}</td>`;
            else r.innerHTML = `<td style="font-weight:600; font-size:12px">${it.Issuer}</td><td class="text-right mono" style="color:${c}; font-size:11px">${formatShortVal(it.value_change)}</td>`;
            b.appendChild(r);
        });
    };
    cb('momentum-new-body', d.new_positions || [], true); cb('momentum-closed-body', d.closed_positions || [], true); cb('momentum-body', d.changes || []);
}

function renderMacro() {
    if (!macroStore || !macroStore.categories) return;
    const s = macroStore.summary || {};
    const cats = macroStore.categories;
    const activeCat = document.getElementById('macro-cat-select').value || 'Liquidity';

    // 1. Regime Summary
    const gScore = s.global_score || 50;
    const rLabel = s.regime || 'NEUTRAL';
    const rSent = s.sentiment || 'neutral';

    document.getElementById('global-macro-score').textContent = gScore.toFixed(1);
    document.getElementById('regime-label').textContent = rLabel;
    document.getElementById('macro-regime-badge').textContent = `${rLabel} REGIME`;
    document.getElementById('regime-sentiment').textContent = rSent;

    const descriptions = {
        'EXPANSIONARY': 'High liquidity and positive macro activity suggest a supportive environment for risk assets.',
        'STABLE / POSITIVE': 'Balanced growth and stable policy rates. Favorable market conditions.',
        'NEUTRAL': 'Market conditions are balanced with no extreme stressors or expansionary signals.',
        'CONTRACTIONARY': 'Declining liquidity or rising rates indicate a cooling economic cycle.',
        'CRISIS / STRESS': 'Severe credit stress, spiking volatility, and shrinking liquidity detected.'
    };
    document.getElementById('regime-description').textContent = descriptions[rLabel] || 'Monitoring market signals...';

    // Theme applying
    const rc = document.querySelector('.regime-container');
    rc.classList.remove('regime-exp', 'regime-con', 'regime-str');
    if (gScore > 55) rc.classList.add('regime-exp');
    else if (gScore < 40) rc.classList.add('regime-str');
    else if (gScore < 50) rc.classList.add('regime-con');

    // 2. Category Grid
    const catGrid = document.getElementById('macro-category-grid');
    catGrid.innerHTML = '';

    const KEY_SERIES = {
        "Liquidity": { id: "WALCL", label: "Fed Bal. Sheet", isCurrency: true },
        "Rates": { id: "EFFR", label: "Fed Funds", isPercent: true },
        "YieldCurve": { id: "T10Y2Y", label: "10Y-2Y", isPercent: true },
        "Inflation": { id: "CPIAUCSL", label: "CPI Index", isIndex: true },
        "Credit": { id: "BAMLH0A0HYM2", label: "HY Spread", isPercent: true },
        "Volatility": { id: "VIXCLS", label: "VIX", isIndex: true },
        "Global": { id: "DTWEXBGS", label: "Dollar Index", isIndex: true },
        "Consumption": { id: "UMCSENT", label: "Sentiment", isIndex: true },
        "Housing": { id: "MORTGAGE30US", label: "30Y Mtg", isPercent: true },
        "Labor": { id: "UNRATE", label: "Unemployment", isPercent: true },
        "Industrial": { id: "INDPRO", label: "Ind. Prod.", isIndex: true }
    };

    // Helper: Sparkline Generator
    const getSparkline = (data, width = 120, height = 30) => {
        if (!data || data.length < 2) return '';
        const min = Math.min(...data);
        const max = Math.max(...data);
        const range = max - min || 1;
        const step = width / (data.length - 1);

        const points = data.map((d, i) => {
            const x = i * step;
            const y = height - ((d - min) / range * height);
            return `${x},${y}`;
        }).join(' ');

        return `
            <svg width="100%" height="${height}" viewBox="0 0 ${width} ${height}" preserveAspectRatio="none" style="opacity:0.5; overflow:visible">
                <polyline points="${points}" fill="none" stroke="currentColor" stroke-width="2" vector-effect="non-scaling-stroke"/>
            </svg>
        `;
    };

    Object.entries(cats).forEach(([name, c]) => {
        const d = document.createElement('div');
        const isActive = name === activeCat;
        d.className = `card cat-card ${isActive ? 'active-cat' : ''}`;
        d.onclick = () => selectMacroCategory(name);
        d.style.cursor = 'pointer';
        d.style.position = 'relative';
        d.style.overflow = 'hidden';

        // Find Key Data & Sparkline History
        let keyStatHtml = '';
        let sparklineHtml = '';

        const kMap = KEY_SERIES[name];
        if (kMap && c.series[kMap.id]) {
            // Stats
            if (c.series[kMap.id].analytics) {
                const val = c.series[kMap.id].analytics.current;
                let fmtVal = val.toFixed(2);
                if (kMap.isCurrency) fmtVal = formatShortVal(val);
                if (kMap.isPercent) fmtVal = val.toFixed(2) + '%';

                keyStatHtml = `
                    <div style="margin-top:8px; padding-top:8px; border-top:1px solid #2d3748; width:100%; display:flex; justify-content:space-between; align-items:center; position:relative; z-index:2">
                        <span style="font-size:10px; color:#718096; text-transform:uppercase">${kMap.label}</span>
                        <span style="font-size:12px; font-weight:600; color:#e2e8f0; font-family:var(--font-mono)">${fmtVal}</span>
                    </div>
                `;
            }

            // Sparkline
            // Use the last 30 points for the sparkline
            const histData = c.series[kMap.id].history.map(h => h.value).slice(-30);
            sparklineHtml = `
                <div style="position:absolute; bottom:20px; left:0; right:0; height:30px; z-index:1; color:${c.score > 60 ? 'var(--accent-green)' : c.score < 40 ? 'var(--accent-red)' : '#718096'}; opacity:0.3; pointer-events:none">
                    ${getSparkline(histData)}
                </div>
            `;
        }

        d.innerHTML = `
            <div class="cat-header" style="position:relative; z-index:2">${name}</div>
            <div class="cat-score" style="color:${c.score > 60 ? 'var(--accent-green)' : c.score < 40 ? 'var(--accent-red)' : 'var(--text-white)'}; position:relative; z-index:2">${c.score}</div>
            <div style="font-size:10px; color:var(--text-gray); position:relative; z-index:2">Group Intensity</div>
            ${sparklineHtml}
            ${keyStatHtml}
        `;
        catGrid.appendChild(d);
    });

    // 3. Main Chart
    const ctx = document.getElementById('chart-macro-main').getContext('2d');
    const catData = cats[activeCat];
    document.getElementById('macro-chart-title').textContent = `${activeCat} Multi-Series History`;

    if (chartMacro) chartMacro.destroy();

    const datasets = Object.entries(catData.series).map(([sid, d], i) => {
        const colors = ['#5c7cff', '#48bb78', '#f6e05e', '#ed64a1', '#38b2ac', '#9f7aea'];
        return {
            label: sid,
            data: d.history.map(o => o.value),
            borderColor: colors[i % colors.length],
            borderWidth: 2,
            pointRadius: 0,
            tension: 0.3,
            yAxisID: i === 1 ? 'y1' : 'y'
        };
    });

    const labels = catData.series[Object.keys(catData.series)[0]].history.map(o => {
        const p = o.date.split('-');
        return p[1] + '/' + p[0].substring(2);
    });

    chartMacro = new Chart(ctx, {
        type: 'line',
        data: { labels, datasets },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { position: 'bottom', labels: { boxWidth: 12, color: '#718096', font: { size: 10 } } } },
            scales: {
                x: { grid: { display: false }, ticks: { color: '#4a5568', font: { size: 9 }, maxRotation: 0 } },
                y: { grid: { color: '#23232a' }, ticks: { color: '#718096', font: { size: 9 } } },
                y1: { display: datasets.length > 1, position: 'right', grid: { display: false }, ticks: { color: '#718096', font: { size: 9 } } }
            }
        }
    });

    // 4. Analytics Table
    const tBody = document.getElementById('macro-analytics-body');
    tBody.innerHTML = '';
    Object.values(catData.series).forEach(s => {
        const a = s.analytics;
        if (!a) return;
        const r = document.createElement('tr');
        const c7 = a.chg_7d >= 0 ? 'var(--accent-green)' : 'var(--accent-red)';
        const c30 = a.chg_30d >= 0 ? 'var(--accent-green)' : 'var(--accent-red)';
        r.innerHTML = `
            <td><div style="font-weight:600">${s.name}</div><div style="font-size:9px; color:var(--text-gray)">${a.current.toLocaleString()}</div></td>
            <td class="text-right mono" style="color:${c7}">${(a.chg_7d * 100).toFixed(1)}%</td>
            <td class="text-right mono" style="color:${c30}">${(a.chg_30d * 100).toFixed(1)}%</td>
            <td class="text-right mono" style="font-weight:600; color:${Math.abs(a.z_score) > 1.5 ? 'var(--accent-red)' : 'var(--text-white)'}">${a.z_score}</td>
        `;
        tBody.appendChild(r);
    });
}

function selectMacroCategory(cat) {
    const s = document.getElementById('macro-cat-select');
    if (s) {
        s.value = cat;
        renderMacro();
    }
}

function initFundDropdown() {
    const s = document.getElementById('fund-select'); s.innerHTML = '<option value="" disabled selected>Select Entity</option>';
    [...new Set(dataStore.map(d => d.Fund))].sort().forEach(f => { const o = document.createElement('option'); o.value = f; o.textContent = f; s.appendChild(o); });
}

function renderFundDetail() {
    const f = document.getElementById('fund-select').value;
    const rawSub = dataStore.filter(d => d.Fund === f);
    if (!rawSub.length) return;

    // Aggregate by Issuer
    const agg = new Map();
    rawSub.forEach(it => {
        const key = (it.Issuer || 'Unknown').toUpperCase().trim().replace(/  +/g, ' ');
        if (!agg.has(key)) {
            agg.set(key, { ...it, Issuer: key, Value_USD: 0, Shares: 0 });
        }
        const entry = agg.get(key);
        entry.Value_USD += parseFloat(it.Value_USD) || 0;
        entry.Shares += parseFloat(it.Shares) || 0;
    });

    const sub = Array.from(agg.values()).sort((a, b) => b.Value_USD - a.Value_USD);
    const aum = sub.reduce((a, c) => a + c.Value_USD, 0);
    const t10 = sub.slice(0, 10).reduce((a, c) => a + c.Value_USD, 0);

    document.getElementById('fund-name-title').textContent = f;
    document.getElementById('fund-aum-val').textContent = formatShortVal(aum);
    document.getElementById('fund-pos-count').textContent = sub.length;
    document.getElementById('fund-top10-weight').textContent = `${((t10 / aum) * 100).toFixed(1)}%`;

    if (changeStore) {
        const p = document.getElementById('momentum-period').value;
        if (changeStore[p]) {
            const totalDelta = changeStore[p].changes.filter(c => sub.some(d => d.Issuer === c.Issuer.toUpperCase().trim())).reduce((a, c) => a + Math.abs(c.value_change), 0);
            document.getElementById('fund-turnover').textContent = `${(totalDelta / aum * 100).toFixed(1)}%`;
        }
    }

    const b = document.getElementById('fund-detail-body'); b.innerHTML = '';
    sub.forEach(it => {
        const v = it.Value_USD;
        b.innerHTML += `<tr><td class="mono" style="color:#718096">${it.CUSIP || '-'}</td><td style="font-weight:600">${it.Issuer}</td><td style="color:#4a5568; font-size:12px">${getSector(it.Issuer)}</td><td class="text-right mono">${formatShortVal(v)}</td><td class="text-right mono">${parseInt(it.Shares).toLocaleString()}</td><td class="text-right mono" style="color:var(--accent-blue); font-weight:600">${((v / aum) * 100).toFixed(2)}%</td></tr>`;
    });

    const t5 = sub.slice(0, 5), t5s = t5.reduce((a, c) => a + c.Value_USD, 0);
    if (portfolioSnapshotChart) portfolioSnapshotChart.destroy();
    portfolioSnapshotChart = new Chart(document.getElementById('fund-doughnut-chart').getContext('2d'), {
        type: 'doughnut',
        data: {
            labels: [...t5.map(t => t.Issuer), 'Others'],
            datasets: [{
                data: [...t5.map(t => t.Value_USD), Math.max(0, aum - t5s)],
                backgroundColor: ['#5c7cff', '#48bb78', '#f6e05e', '#f6ad55', '#ed64a1', '#2d3748'],
                borderWidth: 0
            }]
        },
        options: { plugins: { legend: { display: false } }, cutout: '70%', responsive: true, maintainAspectRatio: false }
    });

    const scts = {}; sub.forEach(it => { const s = getSector(it.Issuer); scts[s] = (scts[s] || 0) + it.Value_USD; });
    const sSorted = Object.entries(scts).filter(([n]) => n !== "Others").sort((a, b) => b[1] - a[1]);
    if (sectorSnapshotChart) sectorSnapshotChart.destroy();
    sectorSnapshotChart = new Chart(document.getElementById('fund-sector-chart').getContext('2d'), {
        type: 'doughnut',
        data: {
            labels: sSorted.map(s => s[0]),
            datasets: [{
                data: sSorted.map(s => s[1]),
                backgroundColor: ['#5c7cff', '#ed64a1', '#48bb78', '#f6e05e', '#f6ad55', '#38b2ac', '#9f7aea'],
                borderWidth: 0
            }]
        },
        options: { plugins: { legend: { display: false } }, cutout: '70%', responsive: true, maintainAspectRatio: false }
    });
}

function setupSearch() {
    const i = document.getElementById('search-input');
    i.addEventListener('input', (e) => {
        const q = e.target.value.toUpperCase();
        document.querySelectorAll('#overview-body tr').forEach(r => { r.style.display = r.innerText.toUpperCase().includes(q) ? '' : 'none'; });
    });
}
