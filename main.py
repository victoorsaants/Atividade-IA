from __future__ import annotations

import json
import os
import re
import unicodedata
import webbrowser
from pathlib import Path

import httpx
import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
INDEX_FILE = BASE_DIR / "index.html"
KNOWLEDGE_BASE_FILE = BASE_DIR / "data" / "tourism_knowledge.json"

load_dotenv(dotenv_path=BASE_DIR / ".env")

HF_API_URL = "https://router.huggingface.co/v1/chat/completions"
HF_MODEL = os.getenv("HF_MODEL", "openai/gpt-oss-120b:fastest").strip()
HF_TOKEN = os.getenv("HF_TOKEN", "").strip()
HF_TIMEOUT_SECONDS = float(os.getenv("HF_TIMEOUT_SECONDS", "45"))

with KNOWLEDGE_BASE_FILE.open("r", encoding="utf-8") as file:
    KNOWLEDGE_BASE = json.load(file)

DESTINATIONS = KNOWLEDGE_BASE["destinations"]
GENERAL_TIPS = KNOWLEDGE_BASE["general_tips"]
DESTINATION_NAMES = [destination["name"] for destination in DESTINATIONS]

STOPWORDS = {
    "como",
    "para",
    "sobre",
    "quero",
    "gostaria",
    "dicas",
    "viagem",
    "viajar",
    "destino",
    "cidade",
    "quais",
    "onde",
    "qual",
    "mais",
    "menos",
    "muito",
    "pouco",
    "uma",
    "umas",
    "esse",
    "essa",
    "isso",
    "com",
    "sem",
    "dos",
    "das",
    "que",
    "pra",
}

TOPIC_KEYWORDS = {
    "highlights": {"fazer", "visitar", "lugares", "pontos", "atrações", "turístico", "turística"},
    "food": {"comida", "comer", "gastronomia", "restaurante", "prato"},
    "climate": {"clima", "tempo", "época", "quando", "estação"},
    "transport": {"transporte", "locomoção", "metrô", "ônibus", "andar"},
    "itinerary": {"roteiro", "itinerário", "3 dias", "fim de semana"},
    "tips": {"dica", "dicas", "segurança", "cuidados"},
    "compare": {"comparar", "comparação", "versus", "vs", "melhor", "diferença", "escolher"},
}

SYSTEM_PROMPT = """
Você é o TuristaIA, um assistente de viagens em português do Brasil.
Regras:
- Responda sempre em pt-BR.
- Use apenas a base de conhecimento fornecida no sistema como fonte principal.
- Não invente preço, agenda, clima em tempo real, disponibilidade ou eventos atuais.
- Se a pergunta sair da base cadastrada, diga com clareza que a base atual não cobre esse destino ou detalhe.
- Seja objetivo, acolhedor e prático.
- Prefira respostas com no máximo 2 parágrafos curtos ou uma lista simples.
""".strip()

app = FastAPI(title="TuristaIA Backend")
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


class ChatTurn(BaseModel):
    role: str
    content: str = Field(min_length=1, max_length=2000)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    history: list[ChatTurn] = Field(default_factory=list)


class ChatResponse(BaseModel):
    answer: str
    provider: str
    destinations: list[str]


def normalize_text(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text)
    without_accents = "".join(character for character in normalized if not unicodedata.combining(character))
    return without_accents.lower()


def tokenize(text: str) -> set[str]:
    tokens = re.findall(r"[a-z0-9]+", normalize_text(text))
    return {token for token in tokens if len(token) > 2 and token not in STOPWORDS}


def contains_any(query: str, keywords: set[str]) -> bool:
    normalized_query = normalize_text(query)
    return any(normalize_text(keyword) in normalized_query for keyword in keywords)


def destination_document(destination: dict) -> str:
    parts = [
        destination["name"],
        destination.get("country", ""),
        destination.get("summary", ""),
        destination.get("climate", ""),
        destination.get("best_time", ""),
        destination.get("transport", ""),
        " ".join(destination.get("aliases", [])),
        " ".join(destination.get("profile_tags", [])),
        " ".join(destination.get("highlights", [])),
        " ".join(destination.get("foods", [])),
        " ".join(destination.get("neighborhoods", [])),
        " ".join(destination.get("tips", [])),
        " ".join(destination.get("itinerary_3_days", [])),
    ]
    return normalize_text(" ".join(parts))


def score_destination(destination: dict, query: str) -> int:
    normalized_query = normalize_text(query)
    tokens = tokenize(query)
    score = 0

    for alias in [destination["name"], *destination.get("aliases", [])]:
        normalized_alias = normalize_text(alias)
        if normalized_alias and normalized_alias in normalized_query:
            score += 10

    for tag in destination.get("profile_tags", []):
        if normalize_text(tag) in normalized_query:
            score += 5

    document = destination_document(destination)
    for token in tokens:
        if token in document:
            score += 1

    return score


def retrieve_destinations(query: str, limit: int = 3) -> list[dict]:
    scored_destinations = []
    for destination in DESTINATIONS:
        score = score_destination(destination, query)
        if score > 0:
            scored_destinations.append((score, destination))

    scored_destinations.sort(key=lambda item: item[0], reverse=True)
    return [destination for _, destination in scored_destinations[:limit]]


def format_destination_context(destination: dict) -> str:
    highlights = ", ".join(destination.get("highlights", []))
    foods = ", ".join(destination.get("foods", []))
    neighborhoods = ", ".join(destination.get("neighborhoods", []))
    tips = "; ".join(destination.get("tips", []))
    itinerary = " | ".join(destination.get("itinerary_3_days", []))
    tags = ", ".join(destination.get("profile_tags", []))

    return (
        f"Destino: {destination['name']} ({destination['country']})\n"
        f"Resumo: {destination['summary']}\n"
        f"Perfil: {tags}\n"
        f"Destaques: {highlights}\n"
        f"Clima: {destination['climate']}\n"
        f"Melhor época: {destination['best_time']}\n"
        f"Transporte: {destination['transport']}\n"
        f"Bairros ou regiões: {neighborhoods}\n"
        f"Gastronomia: {foods}\n"
        f"Dicas: {tips}\n"
        f"Roteiro 3 dias: {itinerary}"
    )


def build_prompt_context(query: str) -> tuple[str, list[dict]]:
    relevant_destinations = retrieve_destinations(query)
    destinations_list = ", ".join(DESTINATION_NAMES)
    general_tips = "\n".join(f"- {tip}" for tip in GENERAL_TIPS)

    if relevant_destinations:
        relevant_block = "\n\n".join(format_destination_context(destination) for destination in relevant_destinations)
    else:
        relevant_block = (
            "Nenhum destino da pergunta apareceu claramente na base.\n"
            "Se o usuário perguntar sobre um local não cadastrado, informe isso e ofereça os destinos disponíveis."
        )

    context = (
        "Base turística do projeto.\n"
        f"Destinos cadastrados: {destinations_list}\n\n"
        f"Dicas gerais:\n{general_tips}\n\n"
        f"Contexto relevante para a pergunta:\n{relevant_block}"
    )
    return context, relevant_destinations


def build_hf_messages(request: ChatRequest) -> tuple[list[dict[str, str]], list[dict]]:
    prompt_context, relevant_destinations = build_prompt_context(request.message)
    messages = [{"role": "system", "content": f"{SYSTEM_PROMPT}\n\n{prompt_context}"}]

    for turn in request.history[-8:]:
        role = "assistant" if turn.role == "assistant" else "user"
        messages.append({"role": role, "content": turn.content.strip()})

    messages.append({"role": "user", "content": request.message.strip()})
    return messages, relevant_destinations


def build_generic_response() -> str:
    destinations = ", ".join(DESTINATION_NAMES)
    return (
        f"A base turística atual cobre: {destinations}. "
        "Posso montar roteiro, destacar pontos turísticos, sugerir comidas típicas e explicar qual destino combina melhor com praia, cultura, natureza ou viagem romântica."
    )


def build_comparison_response(destinations: list[dict]) -> str:
    lines = ["Aqui vai um comparativo rápido com base no cadastro atual:"]
    for destination in destinations[:3]:
        highlights = ", ".join(destination.get("highlights", [])[:3])
        tags = ", ".join(destination.get("profile_tags", [])[:3])
        lines.append(
            f"- {destination['name']}: {destination['summary']} Destaques: {highlights}. Perfil: {tags}."
        )
    return "\n".join(lines)


def build_destination_response(destination: dict, message: str) -> str:
    query = normalize_text(message)

    if contains_any(query, TOPIC_KEYWORDS["itinerary"]):
        itinerary = "\n".join(f"- {item}" for item in destination.get("itinerary_3_days", []))
        return f"Roteiro sugerido para {destination['name']}:\n{itinerary}"

    if contains_any(query, TOPIC_KEYWORDS["food"]):
        foods = ", ".join(destination.get("foods", []))
        return f"Em {destination['name']}, vale provar: {foods}."

    if contains_any(query, TOPIC_KEYWORDS["climate"]):
        return f"{destination['climate']} Melhor época: {destination['best_time']}"

    if contains_any(query, TOPIC_KEYWORDS["transport"]):
        return f"Para circular em {destination['name']}, a base sugere: {destination['transport']}"

    if contains_any(query, TOPIC_KEYWORDS["tips"]):
        tips = "\n".join(f"- {tip}" for tip in destination.get("tips", []))
        return f"Dicas práticas para {destination['name']}:\n{tips}"

    if contains_any(query, TOPIC_KEYWORDS["highlights"]):
        highlights = ", ".join(destination.get("highlights", []))
        neighborhoods = ", ".join(destination.get("neighborhoods", []))
        return (
            f"Em {destination['name']}, os destaques são {highlights}. "
            f"Regiões que costumam concentrar a experiência turística: {neighborhoods}."
        )

    return (
        f"{destination['summary']} Destaques: {', '.join(destination.get('highlights', [])[:4])}. "
        f"Melhor época: {destination['best_time']} "
        f"Se quiser, eu também posso falar de comida, roteiro, transporte ou dicas práticas."
    )


def generate_local_response(message: str) -> tuple[str, list[dict]]:
    relevant_destinations = retrieve_destinations(message)
    if not relevant_destinations:
        return build_generic_response(), []

    if contains_any(message, TOPIC_KEYWORDS["compare"]) and len(relevant_destinations) > 1:
        return build_comparison_response(relevant_destinations), relevant_destinations

    return build_destination_response(relevant_destinations[0], message), relevant_destinations


async def query_hugging_face(request: ChatRequest) -> tuple[str, list[dict]]:
    messages, relevant_destinations = build_hf_messages(request)
    headers = {
        "Authorization": f"Bearer {HF_TOKEN}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": HF_MODEL,
        "messages": messages,
        "max_tokens": 650,
        "temperature": 0.3,
        "stream": False,
    }

    async with httpx.AsyncClient(timeout=HF_TIMEOUT_SECONDS) as client:
        response = await client.post(HF_API_URL, headers=headers, json=payload)
        response.raise_for_status()

    data = response.json()
    answer = data["choices"][0]["message"]["content"].strip()
    if not answer:
        raise ValueError("A resposta da Hugging Face veio vazia.")

    return answer, relevant_destinations


@app.get("/", response_class=HTMLResponse)
async def read_root() -> str:
    with INDEX_FILE.open("r", encoding="utf-8") as file:
        return file.read()


@app.get("/api/status")
async def get_status() -> dict:
    return {
        "provider": "huggingface" if HF_TOKEN else "local",
        "model": HF_MODEL if HF_TOKEN else None,
        "destinations": DESTINATION_NAMES,
        "destination_count": len(DESTINATION_NAMES),
    }


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    if HF_TOKEN:
        try:
            answer, relevant_destinations = await query_hugging_face(request)
            return ChatResponse(
                answer=answer,
                provider="huggingface",
                destinations=[destination["name"] for destination in relevant_destinations],
            )
        except (httpx.HTTPError, KeyError, IndexError, ValueError):
            answer, relevant_destinations = generate_local_response(request.message)
            return ChatResponse(
                answer=answer,
                provider="local-fallback",
                destinations=[destination["name"] for destination in relevant_destinations],
            )

    answer, relevant_destinations = generate_local_response(request.message)
    return ChatResponse(
        answer=answer,
        provider="local",
        destinations=[destination["name"] for destination in relevant_destinations],
    )


if __name__ == "__main__":
    url = "http://127.0.0.1:8000"
    webbrowser.open(url)

    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        reload_excludes=["__pycache__", "*.pyc", ".git"],
    )
