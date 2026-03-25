from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import uvicorn
import webbrowser
import os

app = FastAPI(title="TuristaIA Backend")

# Configuração para servir arquivos estáticos (CSS, JS, Imagens)
# O diretório 'static' deve conter style.css e script.js
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/", response_class=HTMLResponse)
async def read_root():
    """
    Rota principal que retorna o arquivo index.html.
    """
    with open("index.html", "r", encoding="utf-8") as f:
        return f.read()

if __name__ == "__main__":
    # URL do servidor
    url = "http://127.0.0.1:8000"
    
    # Diferencial: Abrir o navegador automaticamente
    if os.environ.get("RUN_MAIN") != "true": # Evita abrir duas vezes no modo reload
        webbrowser.open(url)
    
    # Inicia o servidor Uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
