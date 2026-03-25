// Base de Conhecimento Simulada
const knowledgeBase = {
    "paris": {
        "descricao": "Paris, a 'Cidade Luz', é a capital da França e um centro mundial de arte, moda, gastronomia e cultura.",
        "pontos": ["Torre Eiffel", "Museu do Louvre", "Catedral de Notre-Dame", "Arco do Triunfo"],
        "clima": "O clima em Paris é temperado, com verões suaves e invernos frescos. A melhor época para visitar é na primavera (abril a junho).",
        "comida": "Experimente os famosos Croissants, Escargots, Macarons e vinhos franceses de alta qualidade.",
        "cultura": "Conhecida por seus cafés charmosos, livrarias ao longo do Sena e a vida artística em Montmartre."
    },
    "toquio": {
        "descricao": "Tóquio, a capital do Japão, mistura o ultramoderno com o tradicional, de arranha-céus iluminados a templos históricos.",
        "pontos": ["Cruzamento de Shibuya", "Templo Senso-ji", "Tokyo Skytree", "Palácio Imperial"],
        "clima": "Subtropical úmido. Verões quentes e úmidos, invernos secos e frios. A florada das cerejeiras (Sakura) ocorre em março/abril.",
        "comida": "Indispensável provar o Sushi autêntico, Ramen, Tempura e o delicioso Okonomiyaki.",
        "cultura": "Uma cultura fascinante que valoriza a disciplina, a tecnologia de ponta e tradições seculares como a cerimônia do chá."
    },
    "rio": {
        "descricao": "O Rio de Janeiro é uma grande cidade brasileira à beira-mar, famosa pelas praias de Copacabana e Ipanema e pelo morro do Corcovado.",
        "pontos": ["Cristo Redentor", "Pão de Açúcar", "Praia de Copacabana", "Escadaria Selarón"],
        "clima": "Clima tropical. Faz calor o ano todo, especialmente no verão (dezembro a março), quando ocorrem chuvas rápidas.",
        "comida": "Não deixe de comer uma Feijoada completa, um bom Churrasco e as famosas coxinhas de padaria.",
        "cultura": "O berço do Samba e do Carnaval. Uma cidade vibrante, alegre e com um povo extremamente acolhedor."
    }
};

// Elementos do DOM
const chatMessages = document.getElementById('chat-messages');
const chatForm = document.getElementById('chat-form');
const userInput = document.getElementById('user-input');

// Função para adicionar mensagem ao chat
function appendMessage(sender, text) {
    const msgDiv = document.createElement('div');
    msgDiv.classList.add('message', `${sender}-message`);
    
    const time = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    
    msgDiv.innerHTML = `
        <div class="message-content">${text}</div>
        <div class="message-time">${sender === 'ai' ? 'TuristaIA' : 'Você'} • ${time}</div>
    `;
    
    chatMessages.appendChild(msgDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

// Função para mostrar indicador de digitação
function showTypingIndicator() {
    const typingDiv = document.createElement('div');
    typingDiv.classList.add('message', 'ai-message', 'typing-container');
    typingDiv.innerHTML = `
        <div class="message-content">
            <div class="typing">
                <span></span>
                <span></span>
                <span></span>
            </div>
        </div>
    `;
    chatMessages.appendChild(typingDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
    return typingDiv;
}

// Lógica de resposta da IA
function getAIResponse(input) {
    const text = input.toLowerCase();
    let city = "";
    
    // Identificar a cidade
    if (text.includes("paris")) city = "paris";
    else if (text.includes("toquio") || text.includes("tóquio")) city = "toquio";
    else if (text.includes("rio") || text.includes("janeiro")) city = "rio";

    if (!city) {
        return "Desculpe, no momento só tenho informações detalhadas sobre **Paris**, **Tóquio** e **Rio de Janeiro**. Sobre qual dessas cidades você quer saber?";
    }

    const data = knowledgeBase[city];

    // Identificar intenção
    if (text.includes("fazer") || text.includes("ponto") || text.includes("visitar") || text.includes("lugar")) {
        return `Em **${city.charAt(0).toUpperCase() + city.slice(1)}**, você não pode deixar de visitar: ${data.pontos.join(", ")}.`;
    } 
    else if (text.includes("comer") || text.includes("comida") || text.includes("gastronomia") || text.includes("restaurante")) {
        return data.comida;
    }
    else if (text.includes("clima") || text.includes("tempo") || text.includes("época") || text.includes("quando ir")) {
        return data.clima;
    }
    else if (text.includes("cultura") || text.includes("curiosidade") || text.includes("história")) {
        return data.cultura;
    }
    else {
        return data.descricao + " Quer saber sobre pontos turísticos, comida ou clima de lá?";
    }
}

// Função para enviar mensagem
async function handleSendMessage(e) {
    if (e) e.preventDefault();
    
    const message = userInput.value.trim();
    if (!message) return;

    // Mensagem do usuário
    appendMessage('user', message);
    userInput.value = '';

    // Simulação de "Pensando"
    const typingIndicator = showTypingIndicator();
    
    // Delay aleatório para simular processamento (1s a 2s)
    await new Promise(resolve => setTimeout(resolve, 1000 + Math.random() * 1000));
    
    // Remover indicador de digitação
    typingIndicator.remove();

    // Gerar resposta
    const response = getAIResponse(message);
    
    // Simular digitação da resposta (opcionalmente mais lento para frases longas)
    appendMessage('ai', response);
}

// Função de sugestão
function useSuggest(text) {
    userInput.value = text;
    handleSendMessage();
}

// Event Listeners
chatForm.addEventListener('submit', handleSendMessage);

// Focar no input ao carregar
window.onload = () => userInput.focus();
