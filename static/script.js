const chatMessages = document.getElementById("chat-messages");
const chatForm = document.getElementById("chat-form");
const userInput = document.getElementById("user-input");
const suggestions = document.getElementById("suggestions");
const statusIndicator = document.getElementById("status-indicator");
const statusLabel = document.getElementById("status-label");
const welcomeMessage = document.getElementById("welcome-message");
const scrollBadge = document.getElementById("scroll-badge");

const state = {
    history: [],
    destinations: [],
};

// ── Scroll badge ──────────────────────────────────────────────
function isNearBottom() {
    return chatMessages.scrollHeight - chatMessages.scrollTop - chatMessages.clientHeight < 60;
}

function showScrollBadge() {
    scrollBadge.classList.remove("hidden");
}

function hideScrollBadge() {
    scrollBadge.classList.add("hidden");
}

function scrollToBottom() {
    chatMessages.scrollTo({ top: chatMessages.scrollHeight, behavior: "smooth" });
    hideScrollBadge();
}

scrollBadge.addEventListener("click", scrollToBottom);

chatMessages.addEventListener("scroll", () => {
    if (isNearBottom()) hideScrollBadge();
});

const defaultSuggestions = [
    "Monte um roteiro de 3 dias no Rio de Janeiro",
    "O que fazer em Salvador?",
    "Qual destino combina com gastronomia e cultura?"
];

function escapeHtml(text) {
    return text
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/\"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

function formatMessageText(text) {
    return escapeHtml(text)
        .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
        .replace(/\n/g, "<br>");
}

function setStatus(provider) {
    statusIndicator.classList.remove("local", "remote");

    if (provider === "huggingface") {
        statusIndicator.classList.add("remote");
        statusLabel.textContent = "Hugging Face";
        return;
    }

    if (provider === "local-fallback") {
        statusIndicator.classList.add("local");
        statusLabel.textContent = "Base local (fallback)";
        return;
    }

    statusIndicator.classList.add("local");
    statusLabel.textContent = "Base local";
}

function appendMessage(sender, text) {
    const time = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });

    if (sender === "ai") {
        const wrapper = document.createElement("div");
        wrapper.classList.add("message-wrapper", "ai-wrapper");

        const avatar = document.createElement("div");
        avatar.classList.add("ai-avatar");
        avatar.innerHTML = `<img src="/static/avatar-ai.svg" alt="Turista AI">`;

        const msgDiv = document.createElement("div");
        msgDiv.classList.add("message", "ai-message");
        msgDiv.innerHTML = `
            <div class="message-content">${formatMessageText(text)}</div>
            <div class="message-time">Turista AI - ${time}</div>
        `;

        wrapper.appendChild(avatar);
        wrapper.appendChild(msgDiv);
        chatMessages.appendChild(wrapper);

        if (isNearBottom()) {
            chatMessages.scrollTop = chatMessages.scrollHeight;
        } else {
            showScrollBadge();
        }
    } else {
        const msgDiv = document.createElement("div");
        msgDiv.classList.add("message", "user-message");
        msgDiv.innerHTML = `
            <div class="message-content">${formatMessageText(text)}</div>
            <div class="message-time">Você - ${time}</div>
        `;
        chatMessages.appendChild(msgDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }
}

function showTypingIndicator() {
    const wrapper = document.createElement("div");
    wrapper.classList.add("message-wrapper", "ai-wrapper");

    const avatar = document.createElement("div");
    avatar.classList.add("ai-avatar", "avatar-typing");
    avatar.innerHTML = `<img src="/static/avatar-ai.svg" alt="Turista AI">`;

    const typingDiv = document.createElement("div");
    typingDiv.classList.add("message", "ai-message", "typing-container");
    typingDiv.innerHTML = `
        <div class="message-content">
            <div class="typing">
                <span></span>
                <span></span>
                <span></span>
            </div>
        </div>
    `;

    wrapper.appendChild(avatar);
    wrapper.appendChild(typingDiv);
    chatMessages.appendChild(wrapper);
    chatMessages.scrollTop = chatMessages.scrollHeight;
    return wrapper;
}

function trimHistory() {
    if (state.history.length > 12) {
        state.history = state.history.slice(-12);
    }
}

function renderSuggestions(destinations = []) {
    const items = destinations.length
        ? [
            `O que fazer em ${destinations[0]}?`,
            `Qual a melhor época para visitar ${destinations[1] || destinations[0]}?`,
            `Monte um roteiro em ${destinations[2] || destinations[0]}`
        ]
        : defaultSuggestions;

    suggestions.innerHTML = "";

    items.forEach((text) => {
        const button = document.createElement("button");
        button.type = "button";
        button.className = "suggestion-btn";
        button.textContent = text;
        button.addEventListener("click", () => useSuggest(text));
        suggestions.appendChild(button);
    });
}

function buildWelcomeText(data) {
    const destinations = data.destinations?.join(", ");
    const intro = data.provider === "huggingface"
        ? "O projeto está usando a API da Hugging Face com base turística local."
        : "O projeto está em modo local usando a base turística cadastrada.";

    return `${intro}\n\nHoje eu consigo te orientar sobre: ${destinations}.\nPode pedir roteiro, pontos turísticos, clima ideal, comida típica ou comparação entre destinos.`;
}

async function loadStatus() {
    try {
        const response = await fetch("/api/status");
        if (!response.ok) {
            throw new Error("Não foi possível carregar o status.");
        }

        const data = await response.json();
        state.destinations = data.destinations || [];
        setStatus(data.provider);
        renderSuggestions(state.destinations);
        welcomeMessage.innerHTML = formatMessageText(buildWelcomeText(data));
    } catch (error) {
        setStatus("local");
        renderSuggestions();
        welcomeMessage.innerHTML = formatMessageText(
            "Não consegui confirmar o status da API agora, mas a base local continua pronta para responder."
        );
    }
}

async function handleSendMessage(event) {
    if (event) {
        event.preventDefault();
    }

    const message = userInput.value.trim();
    if (!message) {
        return;
    }

    const historyToSend = state.history.slice(-8);
    appendMessage("user", message);
    userInput.value = "";

    const typingIndicator = showTypingIndicator();

    try {
        const response = await fetch("/api/chat", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                message,
                history: historyToSend
            })
        });

        if (!response.ok) {
            throw new Error("Falha ao consultar o backend.");
        }

        const data = await response.json();
        typingIndicator.remove();

        appendMessage("ai", data.answer);
        state.history.push(
            { role: "user", content: message },
            { role: "assistant", content: data.answer }
        );
        trimHistory();

        if (data.provider) {
            setStatus(data.provider);
        }

        if (Array.isArray(data.destinations) && data.destinations.length) {
            renderSuggestions(data.destinations);
        }
    } catch (error) {
        typingIndicator.remove();
        appendMessage(
            "ai",
            "Tive um problema para responder agora. Verifique se o backend está rodando e se o token da Hugging Face foi configurado."
        );
        setStatus("local");
    }
}

function useSuggest(text) {
    userInput.value = text;
    userInput.focus();
}

chatForm.addEventListener("submit", handleSendMessage);
window.addEventListener("load", async () => {
    await loadStatus();
    userInput.focus();
});
