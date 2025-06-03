from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os

from app.api import search, download, trim, transcribe

# Criar diretório de downloads se não existir
downloads_dir = os.getenv("DOWNLOADS_DIR", "./downloads")
os.makedirs(downloads_dir, exist_ok=True)

app = FastAPI(
    title="TuneWhisperer API",
    description="API para processamento de músicas com YouTube Music, Whisper e tradução",
    version="1.0.0"
)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Incluir rotas
app.include_router(search.router, prefix="/api/v1")
app.include_router(download.router, prefix="/api/v1")
app.include_router(trim.router, prefix="/api/v1")
app.include_router(transcribe.router, prefix="/api/v1")

@app.get("/")
async def root():
    return {"message": "TuneWhisperer API - Processamento de Músicas"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}
