document.addEventListener('DOMContentLoaded', () => {
    // Set default dates (10 years ago to today)
    const endInput = document.getElementById('end-date');
    const startInput = document.getElementById('start-date');
    const today = new Date();
    const tenYearsAgo = new Date(today);
    tenYearsAgo.setFullYear(today.getFullYear() - 10);
    
    endInput.value = today.toISOString().split('T')[0];
    startInput.value = tenYearsAgo.toISOString().split('T')[0];

    const taxSlider = document.getElementById('tax-rate');
    const taxDisplay = document.getElementById('tax-rate-display');
    taxSlider.addEventListener('input', (e) => {
        taxDisplay.textContent = e.target.value + '%';
    });

    const form = document.getElementById('analyze-form');
    const statusEl = document.getElementById('status');
    const analyzeBtn = document.getElementById('analyze-btn');
    const tickerSelect = document.getElementById('chart-ticker-select');
    
    let currentData = null;
    let chartInstance = null;

    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const tickersRaw = document.getElementById('tickers').value;
        const tickers = tickersRaw.split(',').map(t => t.trim()).filter(t => t);
        const initialCapital = document.getElementById('initial-capital').value;
        const taxRate = document.getElementById('tax-rate').value;
        const startDate = startInput.value;
        const endDate = endInput.value;

        if (tickers.length === 0) return;

        setStatus('Loading data... This may take a moment.', 'loading');
        analyzeBtn.disabled = true;

        try {
            const res = await fetch('/api/analyze', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    tickers, initialCapital, taxRate, startDate, endDate
                })
            });

            const data = await res.json();
            
            if (data.success) {
                currentData = data.results;
                setStatus('Analysis Complete', 'success');
                updateDashboard(currentData);
            } else {
                setStatus('Error: ' + data.error, 'error');
            }
        } catch (err) {
            setStatus('Connection Error', 'error');
            console.error(err);
        } finally {
            analyzeBtn.disabled = false;
        }
    });

    tickerSelect.addEventListener('change', (e) => {
        if (!currentData) return;
        const ticker = e.target.value;
        const result = currentData.find(r => r.ticker === ticker);
        if (result) {
            renderChart(result);
        }
    });

    function setStatus(msg, type) {
        statusEl.textContent = msg;
        statusEl.className = 'status-indicator ' + type;
        if (type === 'success') {
            setTimeout(() => {
                statusEl.textContent = 'Ready';
                statusEl.className = 'status-indicator';
            }, 3000);
        }
    }

    function formatMoney(val) {
        return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(val);
    }
    
    function formatPct(val) {
        return (val * 100).toFixed(2) + '%';
    }

    function updateDashboard(results) {
        if (!results || results.length === 0) {
            setStatus('No data returned', 'error');
            return;
        }

        // Update top cards
        let bestCagr = { val: -Infinity, ticker: '' };
        let highestDiv = { val: -Infinity, ticker: '' };
        let topReturn = { val: -Infinity, ticker: '' };

        results.forEach(r => {
            const drip = r.metrics.drip;
            if (drip.cagr > bestCagr.val) {
                bestCagr = { val: drip.cagr, ticker: r.ticker };
            }
            if (drip.dividendsPaid > highestDiv.val) {
                highestDiv = { val: drip.dividendsPaid, ticker: r.ticker };
            }
            if (drip.totalReturn > topReturn.val) {
                topReturn = { val: drip.totalReturn, ticker: r.ticker };
            }
        });

        document.getElementById('best-cagr').innerHTML = `${formatPct(bestCagr.val)} <span style="font-size:1rem;color:var(--primary)">${bestCagr.ticker}</span>`;
        document.getElementById('highest-div').innerHTML = `${formatMoney(highestDiv.val)} <span style="font-size:1rem;color:var(--primary)">${highestDiv.ticker}</span>`;
        document.getElementById('top-return').innerHTML = `${formatPct(topReturn.val)} <span style="font-size:1rem;color:var(--primary)">${topReturn.ticker}</span>`;

        // Populate tables
        const dripTbody = document.querySelector('#drip-table tbody');
        const nodripTbody = document.querySelector('#nodrip-table tbody');
        dripTbody.innerHTML = '';
        nodripTbody.innerHTML = '';
        
        results.forEach(r => {
            // DRIP row
            let tr1 = document.createElement('tr');
            tr1.innerHTML = `
                <td><strong>${r.ticker}</strong></td>
                <td>${formatMoney(r.metrics.drip.finalValue)}</td>
                <td class="${r.metrics.drip.cagr >= 0 ? 'positive' : 'negative'}">${formatPct(r.metrics.drip.cagr)}</td>
                <td class="${r.metrics.drip.totalReturn >= 0 ? 'positive' : 'negative'}">${formatPct(r.metrics.drip.totalReturn)}</td>
                <td>${formatMoney(r.metrics.drip.dividendsPaid)}</td>
                <td>${formatPct(r.metrics.drip.avgYield)}</td>
                <td>${formatMoney(r.metrics.drip.taxPaid)}</td>
            `;
            dripTbody.appendChild(tr1);

            // NO DRIP row
            let tr2 = document.createElement('tr');
            tr2.innerHTML = `
                <td><strong>${r.ticker}</strong></td>
                <td>${formatMoney(r.metrics.nodrip.finalValue)}</td>
                <td class="${r.metrics.nodrip.cagr >= 0 ? 'positive' : 'negative'}">${formatPct(r.metrics.nodrip.cagr)}</td>
                <td class="${r.metrics.nodrip.totalReturn >= 0 ? 'positive' : 'negative'}">${formatPct(r.metrics.nodrip.totalReturn)}</td>
                <td>${formatMoney(r.metrics.nodrip.dividendsPaid)}</td>
                <td>${formatPct(r.metrics.nodrip.avgYield)}</td>
                <td>${formatMoney(r.metrics.nodrip.taxPaid)}</td>
            `;
            nodripTbody.appendChild(tr2);
        });

        // Update select options
        tickerSelect.innerHTML = '';
        results.forEach(r => {
            let opt = document.createElement('option');
            opt.value = r.ticker;
            opt.textContent = r.ticker;
            tickerSelect.appendChild(opt);
        });

        // Render chart for first ticker
        if (results.length > 0) {
            renderChart(results[0]);
        }
    }

    function renderChart(dataObj) {
        const ctx = document.getElementById('growthChart').getContext('2d');
        
        if (chartInstance) {
            chartInstance.destroy();
        }

        Chart.defaults.color = '#94a3b8';
        Chart.defaults.font.family = 'Inter';

        chartInstance = new Chart(ctx, {
            type: 'line',
            data: {
                labels: dataObj.dates,
                datasets: [
                    {
                        label: 'With DRIP',
                        data: dataObj.dripHistory,
                        borderColor: '#00f2fe',
                        backgroundColor: 'rgba(0, 242, 254, 0.1)',
                        borderWidth: 2,
                        fill: true,
                        pointRadius: 0,
                        pointHoverRadius: 4,
                        tension: 0.1
                    },
                    {
                        label: 'No DRIP (Cash Accumulation)',
                        data: dataObj.nodripHistory,
                        borderColor: '#ef4444',
                        backgroundColor: 'transparent',
                        borderWidth: 2,
                        borderDash: [5, 5],
                        fill: false,
                        pointRadius: 0,
                        pointHoverRadius: 4,
                        tension: 0.1
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: {
                    mode: 'index',
                    intersect: false,
                },
                plugins: {
                    tooltip: {
                        backgroundColor: 'rgba(11, 15, 25, 0.9)',
                        titleColor: '#fff',
                        bodyColor: '#e2e8f0',
                        borderColor: 'rgba(255,255,255,0.1)',
                        borderWidth: 1,
                        padding: 10,
                        callbacks: {
                            label: function(context) {
                                let label = context.dataset.label || '';
                                if (label) label += ': ';
                                if (context.parsed.y !== null) {
                                    label += new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(context.parsed.y);
                                }
                                return label;
                            }
                        }
                    },
                    legend: {
                        position: 'top',
                        labels: {
                            usePointStyle: true,
                            boxWidth: 8
                        }
                    }
                },
                scales: {
                    x: {
                        grid: {
                            color: 'rgba(255, 255, 255, 0.05)'
                        },
                        ticks: {
                            maxTicksLimit: 10
                        }
                    },
                    y: {
                        grid: {
                            color: 'rgba(255, 255, 255, 0.05)'
                        },
                        ticks: {
                            callback: function(value) {
                                return '$' + value;
                            }
                        }
                    }
                }
            }
        });
    }
});
