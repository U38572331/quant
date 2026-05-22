// Removed imports/exports
class UI {
    constructor() {
        // Common
        this.balanceEl = document.getElementById('balance');
        this.messageArea = document.getElementById('message-area');
        this.overlay = document.getElementById('lobby-overlay');

        // Blackjack Elements
        this.bjHud = document.getElementById('blackjack-hud');
        this.bjDealerHand = document.getElementById('dealer-hand');
        this.bjPlayerArea = document.getElementById('player-area-bj');
        this.bjControls = document.getElementById('game-actions');

        // Baccarat Elements
        this.baccStage = document.getElementById('baccarat-stage');
        this.baccHud = document.getElementById('baccarat-spots');
        this.baccPlayerHand = document.getElementById('player-hand-bacc');
        this.baccBankerHand = document.getElementById('banker-hand-bacc');
        this.baccPlayerScore = document.getElementById('stage-score-player');
        this.baccBankerScore = document.getElementById('stage-score-banker');

        // Controls
        this.btnDeal = document.getElementById('btn-deal');
        this.btnClear = document.getElementById('btn-clear');
        this.restartControls = document.getElementById('restart-controls');

        // Betting Zones Mapping
        this.baccZones = {
            player: { el: document.getElementById('bet-player'), val: document.getElementById('val-player') },
            banker: { el: document.getElementById('bet-banker'), val: document.getElementById('val-banker') },
            tie: { el: document.getElementById('bet-tie'), val: document.getElementById('val-tie') },
            ppair: { el: document.getElementById('bet-ppair'), val: document.getElementById('val-ppair') },
            bpair: { el: document.getElementById('bet-bpair'), val: document.getElementById('val-bpair') }
        };

        this.currentGameType = 'blackjack';
        this.isAnimating = false;
        this.animationQueue = [];
    }

    setGameMode(mode) {
        this.currentGameType = mode;
        this.resetBoard();

        // Theme Switching
        if (mode === 'baccarat') {
            document.body.classList.add('theme-bacc');
            document.body.classList.remove('theme-bj');

            this.baccStage.classList.remove('hidden');
            this.baccHud.classList.remove('hidden');

            this.bjHud.classList.add('hidden');
            this.bjPlayerArea.classList.add('hidden');
            if (document.getElementById('dealer-area-bj')) document.getElementById('dealer-area-bj').classList.add('hidden');
            this.bjControls.classList.add('hidden');
        } else {
            document.body.classList.add('theme-bj');
            document.body.classList.remove('theme-bacc');

            this.baccStage.classList.add('hidden');
            this.baccHud.classList.add('hidden');

            this.bjHud.classList.remove('hidden');
            this.bjPlayerArea.classList.remove('hidden');
            if (document.getElementById('dealer-area-bj')) document.getElementById('dealer-area-bj').classList.remove('hidden');
            this.bjControls.classList.remove('hidden');
        }
    }

    resetBoard() {
        this.baccPlayerHand.innerHTML = '';
        this.baccBankerHand.innerHTML = '';
        this.bjDealerHand.innerHTML = '';
        if (document.getElementById('player-hand')) document.getElementById('player-hand').innerHTML = ''; // BJ

        this.baccPlayerScore.classList.remove('visible');
        this.baccBankerScore.classList.remove('visible');
        this.baccPlayerScore.innerText = '0';
        this.baccBankerScore.innerText = '0';

        this.messageArea.innerText = '';
        this.restartControls.classList.add('hidden');

        this.animationQueue = [];
    }

    // ... createCardEl (Standard) ...
    createCardEl(card) {
        if (!card) return null;
        const cardEl = document.createElement('div');
        cardEl.className = `card ${card.suit === '♥' || card.suit === '♦' ? 'red' : 'black'}`;
        const inner = document.createElement('div');
        inner.className = 'card-inner';

        const back = document.createElement('div');
        back.className = 'card-face back';

        const front = document.createElement('div');
        front.className = 'card-face front';

        // Simple Content for Clean Look
        const top = document.createElement('div');
        top.className = 'card-corner top';
        top.innerHTML = `<div>${card.value}</div><div>${card.suit}</div>`;

        const center = document.createElement('div');
        center.className = 'card-center-suit';
        center.innerHTML = card.suit;

        const bot = document.createElement('div');
        bot.className = 'card-corner bottom';
        bot.innerHTML = `<div>${card.value}</div><div>${card.suit}</div>`;

        front.appendChild(top);
        front.appendChild(center);
        front.appendChild(bot);

        inner.appendChild(back);
        inner.appendChild(front);
        cardEl.appendChild(inner);
        return cardEl;
    }

    createBjHandWrapper(idx) {
        const div = document.createElement('div');
        div.id = `bj-hand-${idx}`;
        div.className = 'bj-hand-wrapper';

        const score = document.createElement('div');
        score.id = `bj-score-${idx}`;
        score.className = 'score-display hidden';
        div.appendChild(score);

        const container = document.createElement('div');
        container.className = 'hand-container';
        div.appendChild(container);

        return div;
    }

    update(state) {
        this.balanceEl.innerText = state.balance;

        // Bet Values
        if (state.gameType === 'baccarat') {
            for (const [key, zone] of Object.entries(this.baccZones)) {
                if (state.bets[key] > 0) {
                    zone.val.innerText = state.bets[key];
                    zone.el.classList.add('active-bet');
                } else {
                    zone.val.innerText = '';
                    zone.el.classList.remove('active-bet');
                }
            }
        }

        // Controls
        this.btnDeal.disabled = state.totalBet === 0 && state.currentBet === 0;

        // Blackjack Spot Visuals
        if (state.gameType === 'blackjack') {
            const spot = document.getElementById('betting-spot');
            if (spot) {
                if (state.currentBet > 0) {
                    spot.classList.add('active');
                    spot.innerHTML = `<div class="chip-marker">$${state.currentBet}</div>`;
                } else {
                    spot.classList.remove('active');
                    spot.innerHTML = ''; // Restores ::after content 'PLACE BET'
                }
            }
        }

        if (state.state === 'betting') {
            this.restartControls.classList.add('hidden');
            this.messageArea.innerText = '';
        }

        // Queue Logic
        if (state.gameType === 'baccarat') {
            this.diffAndQueue(this.baccPlayerHand, state.hands.player, 'bacc-p');
            this.diffAndQueue(this.baccBankerHand, state.hands.banker, 'bacc-b');
        } else {
            // BJ Logic
            this.diffAndQueue(this.bjDealerHand, state.dealerHand, 'bj-d');

            if (state.playerHands) {
                state.playerHands.forEach((hand, idx) => {
                    let wrapper = document.getElementById(`bj-hand-${idx}`);
                    if (!wrapper) {
                        wrapper = this.createBjHandWrapper(idx);
                        this.bjPlayerArea.appendChild(wrapper);
                    }

                    // Highlight active
                    if (idx === state.activeHandIndex && state.state === 'playerTurn') {
                        wrapper.classList.add('active-hand');
                    } else {
                        wrapper.classList.remove('active-hand');
                    }

                    // Score Live Update
                    const sc = calculateScore(hand.cards);
                    const sDisplay = document.getElementById(`bj-score-${idx}`);
                    if (sDisplay) {
                        sDisplay.innerText = sc;
                        if (sc > 0) sDisplay.classList.remove('hidden');
                    }

                    const container = wrapper.querySelector('.hand-container');
                    this.diffAndQueue(container, hand.cards, `bj-p-${idx}`);
                });
            }
        }

        this.processQueue(state);
    }

    renderedCounts = new Map();

    diffAndQueue(container, cards, id) {
        const count = this.renderedCounts.get(id) || 0;
        if (!cards) return;

        if (cards.length > count) {
            for (let i = count; i < cards.length; i++) {
                this.animationQueue.push({
                    type: 'deal',
                    card: cards[i],
                    container: container,
                    index: i
                });
            }
            this.renderedCounts.set(id, cards.length);
        } else if (cards.length < count) {
            container.innerHTML = '';
            this.renderedCounts.set(id, 0);
        }
    }

    async processQueue(state) {
        if (this.isAnimating) return;
        if (this.animationQueue.length === 0) {
            this.finalizeState(state);
            return;
        }

        this.isAnimating = true;

        while (this.animationQueue.length > 0) {
            const task = this.animationQueue.shift();
            const el = this.createCardEl(task.card);
            task.container.appendChild(el);

            // Fly In (CSS)
            // Start off screen
            el.style.transform = 'translateY(-500px) scale(0.5)';
            el.style.opacity = '0';

            // Force Reflow
            el.offsetHeight;

            // End State
            el.style.opacity = '1';
            el.style.transform = 'translateY(0) scale(1)';
            Sound.playCardSlide();

            await new Promise(r => setTimeout(r, 250)); // Faster deal

            if (!task.card.hidden) {
                el.classList.add('flipped');
            }
        }

        this.isAnimating = false;
        this.finalizeState(state);
    }

    finalizeState(state) {
        if (state.gameType === 'baccarat') {
            if (state.scores.player > 0) {
                this.baccPlayerScore.innerText = state.scores.player;
                this.baccPlayerScore.classList.add('visible');
            }
            if (state.scores.banker > 0) {
                this.baccBankerScore.innerText = state.scores.banker;
                this.baccBankerScore.classList.add('visible');
            }
        } else {
            // Blackjack Finalize Scores
            if (state.dealerScore > 0) {
                const ds = document.getElementById('dealer-score');
                if (ds) {
                    ds.innerText = state.dealerScore;
                    ds.classList.remove('hidden');
                }
            }
        }

        if (state.state === 'result' || state.state === 'gameOver') {
            this.messageArea.innerText = state.lastResult;
            if (state.lastResult.includes('WIN')) Sound.playWin();
        }
    }
}

// Score Helper
function calculateScore(cards) {
    if (!cards) return 0;
    let score = 0;
    let aces = 0;
    for (let card of cards) {
        if (['J', 'Q', 'K'].includes(card.value)) score += 10;
        else if (card.value === 'A') { aces++; score += 11; }
        else score += parseInt(card.value);
    }
    while (score > 21 && aces > 0) { score -= 10; aces--; }
    return score;
}
