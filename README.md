## Turista AI

Projeto simples com `FastAPI` no backend e interface web para responder perguntas turísticas.

## O que foi integrado

- API de chat da Hugging Face no backend.
- Base turística local em [data/tourism_knowledge.json](/c:/DEV/Atividade-IA/data/tourism_knowledge.json).
- Fallback local quando o token não estiver configurado ou a API falhar.
- Frontend conectado ao endpoint `/api/chat`.

## Como configurar

1. Instale as dependências:

```bash
pip install -r requirements.txt
```

2. Crie um arquivo `.env` na raiz a partir de `.env.example`.

3. Preencha o token da Hugging Face:

```env
HF_TOKEN=hf_seu_token_aqui
HF_MODEL=openai/gpt-oss-120b:fastest
HF_TIMEOUT_SECONDS=45
```

4. Rode o projeto:

```bash
python main.py
```

5. Abra `http://127.0.0.1:8000`.

## Onde editar a base turística

Os destinos, roteiros e dicas ficam em [data/tourism_knowledge.json](/c:/DEV/Atividade-IA/data/tourism_knowledge.json).

Cada destino pode receber campos como:

- `name`
- `aliases`
- `profile_tags`
- `summary`
- `highlights`
- `climate`
- `best_time`
- `transport`
- `foods`
- `neighborhoods`
- `tips`
- `itinerary_3_days`

## Fluxo atual

- O frontend envia a pergunta para `/api/chat`.
- O backend seleciona os destinos mais relevantes da base local.
- Se `HF_TOKEN` estiver configurado, a resposta é gerada pela Hugging Face com esse contexto.
- Se a API não responder, o sistema usa a base local para responder de forma determinística.
