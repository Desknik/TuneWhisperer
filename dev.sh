#!/bin/bash

# Script para executar a API em modo de desenvolvimento
# Para Windows, use: bash dev.sh

echo "🚀 Iniciando TuneWhisperer API em modo desenvolvimento..."

# Verificar se o Python está instalado
if ! command -v python &> /dev/null; then
    echo "❌ Python não encontrado. Instale Python 3.11+ primeiro."
    exit 1
fi

# Verificar se o ffmpeg está instalado
if ! command -v ffmpeg &> /dev/null; then
    echo "⚠️  FFmpeg não encontrado. Algumas funcionalidades podem não funcionar."
    echo "   Instale FFmpeg: https://ffmpeg.org/download.html"
fi

# Criar ambiente virtual se não existir
if [ ! -d "venv" ]; then
    echo "📦 Criando ambiente virtual..."
    python -m venv venv
fi

# Ativar ambiente virtual
echo "🔄 Ativando ambiente virtual..."
source venv/bin/activate 2>/dev/null || source venv/Scripts/activate

# Instalar dependências
echo "📚 Instalando dependências..."
pip install --upgrade pip
pip install -r requirements.txt

# Criar diretório de downloads
mkdir -p downloads

# Executar API
echo "🎵 Iniciando API na porta 8000..."
echo "📖 Documentação disponível em: http://localhost:8000/docs"
echo "🔍 Health check: http://localhost:8000/health"
echo ""
echo "Para parar: Ctrl+C"
echo ""

uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
