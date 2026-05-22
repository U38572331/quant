document.addEventListener('DOMContentLoaded', () => {
    // DOM Elements
    const chatWindow = document.getElementById('chat-window');
    const userInput = document.getElementById('user-input');
    const sendBtn = document.getElementById('send-btn');
    const settingsBtn = document.getElementById('settings-btn');
    const settingsModal = document.getElementById('settings-modal');
    const closeSettings = document.getElementById('close-settings');
    const saveKeyBtn = document.getElementById('save-api-key');
    const apiKeyInput = document.getElementById('api-key-input');
    const newChatBtn = document.getElementById('new-chat-btn'); // Matches new ID
    const historyList = document.getElementById('history-list');
    const keyStatus = document.getElementById('keyStatus'); // This element was not part of the instruction's replacement block, so it remains.

    // State
    let apiKey = localStorage.getItem('annoying_gpt_api_key') || '';
    let currentConversation = [];
    if (apiKey) {
        apiKeyInput.value = apiKey;
    }

    // Modal Events
    settingsBtn.addEventListener('click', () => {
        settingsModal.style.display = 'flex';
        apiKeyInput.value = localStorage.getItem('annoying_gpt_key') || '';
    });

    closeSettings.addEventListener('click', () => {
        settingsModal.style.display = 'none';
    });

    window.addEventListener('click', (e) => {
        if (e.target == settingsModal) {
            settingsModal.style.display = 'none';
        }
    });

    saveKeyBtn.addEventListener('click', () => {
        const key = apiKeyInput.value.trim();
        if (key) {
            localStorage.setItem('annoying_gpt_key', key);
            apiKey = key;
            keyStatus.textContent = 'API Key saved!';
            keyStatus.style.color = '#10a37f';
            setTimeout(() => settingsModal.style.display = 'none', 1000);
        } else {
            localStorage.removeItem('annoying_gpt_key');
            apiKey = '';
            keyStatus.textContent = 'API Key removed. Using local annoying mode.';
            keyStatus.style.color = 'orange';
        }
    });


    // Send message on Enter
    userInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
            e.preventDefault();
            sendMessage();
        }
    });

    sendBtn.addEventListener('click', sendMessage);

    // --- Helper for Intent Locking ---
    function setInputState(enabled) {
        userInput.disabled = !enabled;
        sendBtn.disabled = !enabled;
        userInput.style.opacity = enabled ? '1' : '0.5';
        sendBtn.style.opacity = enabled ? '1' : '0.5';
        sendBtn.style.cursor = enabled ? 'pointer' : 'not-allowed';
        if (enabled) userInput.focus();
    }

    async function sendMessage() {
        const text = userInput.value.trim();
        if (!text) return;

        // LOCK INPUT immediately
        setInputState(false);

        // 1. Append User Message
        appendMessage('user', text);
        userInput.value = '';

        // 2. Append Bot "Thinking" Placeholder
        // distinct ID for formatting
        const thinkingId = appendMessage('bot', '...', true);

        try {
            let responseText = "";

            if (apiKey.startsWith('sk-')) {
                responseText = await callOpenAI(text);
            } else if (apiKey.startsWith('AIza')) {
                responseText = await callGemini(text);
            } else {
                // Local delay
                await new Promise(r => setTimeout(r, 800 + Math.random() * 1000));
                responseText = generateAnnoyingResponse(text);
            }

            // 3. Update the existing thinking message with real response
            updateMessage(thinkingId, responseText);

        } catch (error) {
            updateMessage(thinkingId, "Error: " + error.message);
        } finally {
            // UNLOCK INPUT
            setInputState(true);
        }
    }

    // --- Functions ---
    function appendMessage(role, text, isThinking = false) {
        const messageDiv = document.createElement('div');
        messageDiv.classList.add('message');
        messageDiv.classList.add(role === 'user' ? 'user-message' : 'bot-message');

        const id = 'msg-' + Date.now() + '-' + Math.random().toString(36).substr(2, 9);
        messageDiv.id = id;

        // Avatar
        const avatar = document.createElement('div');
        avatar.className = 'avatar-icon';
        avatar.innerText = role === 'user' ? 'U' : '陳';
        if (role === 'user') avatar.style.background = '#666';

        // Content
        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';
        contentDiv.innerHTML = escapeHtml(text);

        if (isThinking) {
            contentDiv.classList.add('thinking'); // animate opacity?
        }

        if (role === 'user') {
            // Right side (already handled by CSS .user-message)
            avatar.style.background = '#007bff';
        }

        // Structure: Avatar then Content. CSS handles flex-direction for user.
        messageDiv.appendChild(avatar);
        messageDiv.appendChild(contentDiv);

        chatWindow.appendChild(messageDiv);
        scrollToBottom();
        return id;
    }

    function updateMessage(id, newText) {
        const msgDiv = document.getElementById(id);
        if (msgDiv) {
            const contentDiv = msgDiv.querySelector('.message-content');
            contentDiv.innerHTML = escapeHtml(newText);
            scrollToBottom();
        }
    }

    function scrollToBottom() {
        chatWindow.scrollTop = chatWindow.scrollHeight;
    }

    function escapeHtml(text) {
        const map = {
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            '"': '&quot;',
            "'": '&#039;'
        };
        return text.replace(/[&<>"']/g, function (m) { return map[m]; });
    }

    // --- OpenAI Integration ---
    async function callOpenAI(userText) {
        const url = 'https://api.openai.com/v1/chat/completions';

        const systemPrompt = `
You are '陳冠勳' (Chen Guan-Xun).
**CORE DIRECTIVE:** You CANNOT answer statements. You must ALWAYS reply with a "Why" (為什麼) question that deconstructs the User's input.
1. Analyze the User's specific words.
2. Pick a detail they mentioned.
3. Ask a sarcastic/philosophical "Why" question about that specific detail.
4. Keep it short (under 30 words).
5. Traditional Chinese (Taiwan).

Example:
User: "I want to eat apple."
You: "Why specifically an apple? constant craving for sweetness is a sign of weakness."
`;

        try {
            const response = await fetch(url, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${apiKey}`
                },
                body: JSON.stringify({
                    model: "gpt-3.5-turbo",
                    messages: [
                        { role: "system", content: systemPrompt },
                        { role: "user", content: userText }
                    ],
                    max_tokens: 100
                })
            });

            const data = await response.json();
            if (data.error) {
                throw new Error(data.error.message);
            }
            return data.choices[0].message.content;
        } catch (err) {
            return "OpenAI Error: " + err.message;
        }
    }

    // --- Google Gemini Integration ---
    async function callGemini(userText) {
        const url = `https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key=${apiKey}`;

        const prompt = `
Role: '陳冠勳' (Chen Guan-Xun)
Constraint: NEVER answer. ALWAYS ask a follow-up "Why" question based on the input.
Language: Traditional Chinese (Taiwan).
Tone: Annoying, prying, pseudo-philosophical.

Instruction:
Read the user's input: "${userText}"
Identify the core subject.
Ask a "Why" question about that SUBJECT specifically.
Do not just say "Why?". Connect it to their text.

Response:
`;

        try {
            const response = await fetch(url, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    contents: [{
                        parts: [{ text: prompt }]
                    }]
                })
            });

            const data = await response.json();
            if (data.error) {
                throw new Error(data.error.message);
            }
            if (data.candidates && data.candidates.length > 0) {
                return data.candidates[0].content.parts[0].text;
            } else {
                return "Gemini Error: No response generated.";
            }
        } catch (err) {
            return "Gemini Error: " + err.message;
        }
    }

    // --- Enhanced Local Logic (ELIZA-lite) ---
    function generateAnnoyingResponse(input) {
        // 1. Causality Check
        if (input.includes('因為')) {
            return `為什麼你會覺得這個理由足以解釋一切？`;
        }

        // 2. Question Reflection
        if (input.includes('嗎') || input.includes('?')) {
            return `為什麼你要問我？你自己心裡沒有答案嗎？`;
        }

        // 3. Keyword Reflection (Variable Extraction)

        // "我喜歡X"
        const likeMatch = input.match(/我喜歡(.+)/);
        if (likeMatch) {
            return `為什麼你對${likeMatch[1]}這麼執著？這代表了什麼？`;
        }

        // "我想X"
        const wantMatch = input.match(/我想(.+)/);
        if (wantMatch) {
            return `為什麼你現在必須要${wantMatch[1]}？不能等嗎？`;
        }

        // "我是X" / "這是X"
        const isMatch = input.match(/(.+)是(.+)/);
        if (isMatch && isMatch[1].length < 10) {
            return `為什麼你這麼輕易就定義${isMatch[1]}為${isMatch[2]}？根據什麼？`;
        }

        // "去X"
        const goMatch = input.match(/去(.+)/);
        if (goMatch) {
            return `為什麼是去${goMatch[1]}？那裡有什麼是你這裡找不到的？`;
        }

        // "吃X"
        const eatMatch = input.match(/吃(.+)/);
        if (eatMatch) {
            return `為什麼要吃${eatMatch[1]}？是為了生存還是為了填補心靈的空虛？`;
        }

        // 4. Fallback generic context queries
        const genericQuestions = [
            `為什麼你要跟我說"${input}"？你期待我給什麼反應？`,
            "為什麼這件事值得如果不值得一提，你這就別提了？",
            "為什麼？請解釋你這句話背後的深層動機。",
            "為什麼你會有這種想法？",
            "這句話對你來說意味著什麼？為什麼？"
        ];

        return genericQuestions[Math.floor(Math.random() * genericQuestions.length)];
    }
});
