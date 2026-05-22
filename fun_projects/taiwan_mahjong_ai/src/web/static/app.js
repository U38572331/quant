
const STATE_URL = '/api/state';
const ACTION_URL = '/api/action';

// --- Unicode & Color Logic ---
function getTileChar(idx) {
    if (idx >= 0 && idx <= 8) return String.fromCodePoint(0x1F007 + idx);
    if (idx >= 9 && idx <= 17) return String.fromCodePoint(0x1F019 + (idx - 9));
    if (idx >= 18 && idx <= 26) return String.fromCodePoint(0x1F010 + (idx - 18));
    if (idx >= 27 && idx <= 30) return String.fromCodePoint(0x1F000 + (idx - 27));
    if (idx === 31) return String.fromCodePoint(0x1F006);
    if (idx === 32) return String.fromCodePoint(0x1F005);
    if (idx === 33) return String.fromCodePoint(0x1F004);
    if (idx >= 34) return String.fromCodePoint(0x1F022 + (idx - 34));
    return "?";
}

function getColor(idx) {
    if (idx === 33) return "#D00"; // Red
    if (idx === 32) return "#080"; // Green
    if (idx >= 0 && idx <= 8) return "#B00"; // Man
    if (idx >= 18 && idx <= 26) return "#070"; // Sou
    return "#000";
}

// --- 3D Tile Factory ---
function create3DTile(idx, type = 'standing', isClickable = false) {
    // Type: 'standing' (Hand), 'laying' (Discard), 'hidden' (Opponent Hand)
    const wrapper = document.createElement('div');

    if (type === 'hidden') {
        wrapper.className = 'tile-back-stand';
        // Needs faces to look 3D 
        // We reuse the structure but style changes via CSS
    } else if (type === 'laying') {
        wrapper.className = 'tile-3d tile-laying';
    } else {
        wrapper.className = 'tile-3d tile-standing';
    }

    // Create 6 faces
    const faces = ['front', 'back', 'left', 'right', 'top', 'bottom'];
    faces.forEach(f => {
        const div = document.createElement('div');
        div.className = `face t-${f}`;
        if (f === 'front' && type !== 'hidden') {
            div.innerText = getTileChar(idx);
            div.style.color = getColor(idx);
        }
        wrapper.appendChild(div);
    });

    if (isClickable) {
        wrapper.onclick = () => sendDiscard(idx);
    }

    return wrapper;
}

// --- Main Loop ---

async function updateState() {
    try {
        const res = await fetch(STATE_URL);
        const data = await res.json();

        document.getElementById('msg-box').innerText = data.last_action || data.message;

        // My Hand
        const myHandDiv = document.getElementById('my-hand');
        myHandDiv.innerHTML = '';
        data.me.hand.forEach(t => {
            myHandDiv.appendChild(create3DTile(t, 'standing', true));
        });

        // My Pool
        const myPool = document.getElementById('pool-me');
        myPool.innerHTML = '';
        data.me.discards.forEach(t => {
            myPool.appendChild(create3DTile(t, 'laying'));
        });

        // Opponents
        // Note: My code sorted opponents by Position order (Right, Top, Left)
        data.opponents.forEach(opp => {
            const pos = opp.position.toLowerCase();

            // Hand (Hidden)
            const handDiv = document.getElementById(`hand-${pos}`);
            if (handDiv) {
                handDiv.innerHTML = '';
                // Simple Flex row
                handDiv.style.display = 'flex';
                // Limit
                const count = Math.min(opp.hand_count, 17);
                for (let i = 0; i < count; i++) {
                    handDiv.appendChild(create3DTile(-1, 'hidden'));
                }
            }

            // Pool (Discards)
            const poolDiv = document.getElementById(`pool-${pos}`);
            if (poolDiv) {
                poolDiv.innerHTML = '';
                opp.discards.forEach(t => {
                    poolDiv.appendChild(create3DTile(t, 'laying'));
                });
            }
        });

    } catch (e) {
        console.error(e);
    }
}

async function sendDiscard(tileIdx) {
    await fetch(ACTION_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ discard: tileIdx })
    });
    updateState();
}

async function resetGame() {
    await fetch('/api/reset', { method: 'POST' });
}

setInterval(updateState, 500);
updateState();
