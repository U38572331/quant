const pnlCtx = document.getElementById('pnlChart').getContext('2d');
const distCtx = document.getElementById('distChart').getContext('2d');

let mainChart;
let distChart;

function initCharts() {
    mainChart = new Chart(pnlCtx, {
        type: 'line',
        data: { datasets: [] },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            elements: { point: { radius: 0 }, line: { borderWidth: 1 } },
            animation: false,
            scales: {
                x: { type: 'linear', position: 'bottom', grid: { color: 'rgba(255,255,255,0.05)' } },
                y: { grid: { color: 'rgba(255,255,255,0.05)' } }
            },
            plugins: {
                legend: { display: false },
                tooltip: { enabled: false }
            },
            // Performance optimization for 1000+ paths
            parsing: false,
            normalized: true
        }
    });

    distChart = new Chart(distCtx, {
        type: 'bar',
        data: { labels: [], datasets: [{ backgroundColor: '#00f2ff', data: [] }] },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: {
                x: { grid: { display: false } },
                y: { display: false }
            }
        }
    });
}

function simulate() {
    const nSteps = parseInt(document.getElementById('stepsInput').value);
    const nPaths = parseInt(document.getElementById('pathsInput').value);
    const pWin = parseInt(document.getElementById('probInput').value) / 100;

    const datasets = [];
    const finalPnLs = [];
    let totalDrawdown = 0;
    let winCount = 0;

    for (let i = 0; i < nPaths; i++) {
        let currentPnL = 0;
        const data = [{ x: 0, y: 0 }];
        let peak = 0;
        let pathMaxDD = 0;

        for (let j = 1; j <= nSteps; j++) {
            const won = Math.random() < pWin;
            currentPnL += won ? 1 : -1;
            data.push({ x: j, y: currentPnL });
            
            if (currentPnL > peak) peak = currentPnL;
            const dd = peak - currentPnL;
            if (dd > pathMaxDD) pathMaxDD = dd;
        }

        datasets.push({
            data: data,
            borderColor: i % 10 === 0 ? 'rgba(0, 242, 255, 0.4)' : 'rgba(112, 0, 255, 0.1)',
            showLine: true
        });

        finalPnLs.push(currentPnL);
        totalDrawdown += pathMaxDD;
        if (currentPnL > 0) winCount++;
    }

    // Update Main Chart
    mainChart.data.datasets = datasets;
    mainChart.update();

    // Update Stats
    const avgPnL = finalPnLs.reduce((a, b) => a + b, 0) / nPaths;
    document.getElementById('expectedValue').textContent = avgPnL.toFixed(2);
    document.getElementById('winRate').textContent = ((winCount / nPaths) * 100).toFixed(1) + '%';
    document.getElementById('maxDrawdown').textContent = (totalDrawdown / nPaths).toFixed(2);

    // Update Distribution
    updateDistribution(finalPnLs);
}

function updateDistribution(pnls) {
    const min = Math.min(...pnls);
    const max = Math.max(...pnls);
    const bins = {};
    
    pnls.forEach(v => {
        bins[v] = (bins[v] || 0) + 1;
    });

    const labels = Object.keys(bins).sort((a, b) => a - b);
    distChart.data.labels = labels;
    distChart.data.datasets[0].data = labels.map(l => bins[l]);
    distChart.update();
}

document.getElementById('runBtn').addEventListener('click', simulate);

// Auto-run on load
initCharts();
simulate();
