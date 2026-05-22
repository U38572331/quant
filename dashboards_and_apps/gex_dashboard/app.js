const outputEl = document.getElementById('ai-output');
const spxEls = {
    net: document.getElementById('spx-netgex'),
    zero: document.getElementById('spx-zero'),
    call: document.getElementById('spx-call'),
    put: document.getElementById('spx-put')
};
const qqqEls = {
    net: document.getElementById('qqq-netgex'),
    zero: document.getElementById('qqq-zero'),
    call: document.getElementById('qqq-call'),
    put: document.getElementById('qqq-put')
};

// System States
let isDemo = false;

// Mock Data for Demo
const DEMO_DATA = {
    spx: { net: "+$2.4B (Stable)", zero: "5240", call: "5300", put: "5150" },
    qqq: { net: "-$500M (Volatile)", zero: "445", call: "455", put: "430" }
};

// --- MANUAL INPUT HANDLING ---
// --- MANUAL INPUT HANDLING (MODAL) ---
const modal = document.getElementById('input-modal');
const inZero = document.getElementById('in-zero');
const inCall = document.getElementById('in-call');
const inPut = document.getElementById('in-put');

function openModal() {
    modal.classList.add('active');
    // Pre-fill if exists
    if (spxEls.zero.innerText !== "--" && spxEls.zero.innerText !== "OFFLINE") {
        inZero.value = spxEls.zero.innerText;
    }
}

function closeModal() {
    modal.classList.remove('active');
}

function submitManual() {
    const z = inZero.value;
    const c = inCall.value;
    const p = inPut.value;

    if (z && c && p) {
        // Update UI
        spxEls.zero.innerText = z;
        spxEls.call.innerText = c;
        spxEls.put.innerText = p;
        spxEls.net.innerText = "MANUAL OVERRIDE";
        spxEls.net.parentElement.className = "metric-card neutral";

        // Trigger Analysis
        generateAnalysis(z, c, p);
        closeModal();
    } else {
        alert("PLEASE ENTER ALL FIELDS");
    }
}

function generateAnalysis(zero, call, put) {
    const analysis = `AI MARKET ANALYSIS [MANUAL INJECTION]:

> SPX STRUCTURE:
  Zero Gamma Level: ${zero}
  Call Wall (Resistance): ${call}
  Put Wall (Support): ${put}

> SYSTEM INFERENCE:
  Market flow depends on the relation to ${zero}.
  - ABOVE ${zero}: Dealer hedging supports prices (Positive Gamma). Drift toward ${call}.
  - BELOW ${zero}: Volatility expands (Negative Gamma). Risk of acceleration to ${put}.
  
  CURRENT STATE: MONITOR PRICE ACTION RELATIVE TO ${zero}.`;

    typeText(analysis);
}

// AI Messages
const MSG_OFFLINE = `SYSTEM WARNING: LIVE FEED DISCONNECTED.
> Connection to GEXSTREAM API... FAILED.
> Unable to retrieve volumetric gamma data.
> Zero Gamma Levels: UNKNOWN.
> Wall structures: UNKNOWN.

RECOMMENDATION:
> Engage manual oversight.
> Monitor price action relative to VWAP.
> Await data restoration.`;

const MSG_DEMO = `AI MARKET ANALYSIS [DEMO SIMULATION]:

> SPX STRUCTURE: BULLISH STABILITY
  Net Positive Gamma suggests reduced volatility. Dealers are likely to supress muted moves. 5240 is the key pivot. As long as price holds above 5240, look for a drift towards the 5300 Call Wall.

> QQQ STRUCTURE: MIXED/BEARISH
  Negative Gamma indicates potential for expansion of range. 445 is the volatility trigger. Below 445, selling could accelerate towards the 430 Put Wall.

> SYNTHESIS:
  Market divergence detected. SPX providing ballast while Tech (QQQ) shows weakness. Prioritize relative strength strategies. 
  
  [ ACTION: LONG SPX / HEDGE QQQ ]`;

// Typewriter Effect
let typeInterval;
function typeText(text) {
    clearInterval(typeInterval);
    outputEl.innerText = "";
    let i = 0;

    // Fast typing
    typeInterval = setInterval(() => {
        outputEl.innerText += text.charAt(i);
        i++;
        // Auto scroll
        outputEl.scrollTop = outputEl.scrollHeight;

        if (i >= text.length) {
            clearInterval(typeInterval);
        }
    }, 15); // Speed ms
}

// Data Renderer
function render() {
    if (isDemo) {
        // SPX
        spxEls.net.innerText = DEMO_DATA.spx.net;
        spxEls.net.parentElement.className = "metric-card bullish"; // force styling for demo
        spxEls.zero.innerText = DEMO_DATA.spx.zero;
        spxEls.call.innerText = DEMO_DATA.spx.call;
        spxEls.put.innerText = DEMO_DATA.spx.put;

        // QQQ
        qqqEls.net.innerText = DEMO_DATA.qqq.net;
        qqqEls.net.parentElement.className = "metric-card bearish";
        qqqEls.zero.innerText = DEMO_DATA.qqq.zero;
        qqqEls.call.innerText = DEMO_DATA.qqq.call;
        qqqEls.put.innerText = DEMO_DATA.qqq.put;

        typeText(MSG_DEMO);
    } else {
        // Reset to Offline
        Object.values(spxEls).forEach(el => { el.innerText = "OFFLINE"; el.parentElement.className = "metric-card neutral"; });
        Object.values(qqqEls).forEach(el => { el.innerText = "OFFLINE"; el.parentElement.className = "metric-card neutral"; });

        typeText(MSG_OFFLINE);
    }
}

// Toggle
function toggleDemo() {
    isDemo = !isDemo;
    render();
}

// Initial Run
setTimeout(() => {
    render();
}, 1000);
