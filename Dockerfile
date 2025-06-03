FROM python:3.11

WORKDIR /app

# Instalar dependências do sistema (incluindo ffmpeg)
RUN apt-get update && apt-get install -y \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Copiar arquivos de requisitos primeiro para melhor cache
COPY requirements.txt .

# Instalar dependências Python
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Copiar código da aplicação
COPY . .

# Criar diretório para downloads
RUN mkdir -p /app/downloads

# Expor porta
EXPOSE 8000

# Comando para executar a aplicação
# Para desenvolvimento, use --reload para hot reload
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
# Para produção, remova o --reload acima e use:
# CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
