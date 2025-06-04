# TuneWhisperer API

API RESTful para processamento de músicas com YouTube Music, Whisper e tradução.

## 🎯 Funcionalidades

- **Busca de músicas** no YouTube Music com extração de cores da capa
- **Download de áudios** em formato MP3
- **Corte de trechos** específicos de áudios
- **Transcrição de áudios** com timestamps usando Whisper ou ElevenLabs
- **Tradução opcional** das transcrições com suporte a múltiplos idiomas

## 🚀 Início Rápido

### Pré-requisitos

- Python 3.11+
- FFmpeg instalado no sistema
- Docker e Docker Compose (opcional)

### Instalação Local

1. Clone o repositório:
```bash
git clone <repository-url>
cd TuneWhisperer
```

2. Crie um ambiente virtual:
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate     # Windows
```

3. Instale as dependências:
```bash
pip install -r requirements.txt
```

4. Execute a aplicação:
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Usando Docker

1. Execute com Docker Compose:
```bash
docker-compose up --build
```

A API estará disponível em: `http://localhost:8000`

## 📚 Documentação da API

### Endpoints

#### 🔍 GET /api/v1/search
Busca músicas no YouTube Music.

**Parâmetros:**
- `query` (string): Termo de busca
- `limit` (int): Número máximo de resultados (1-50)

**Exemplo:**
```bash
curl "http://localhost:8000/api/v1/search?query=imagine%20dragons&limit=5"
```

**Resposta:**
```json
[
  {
    "title": "Believer",
    "artist": "Imagine Dragons",
    "videoId": "7wtfhZwyrcc",
    "thumbnail": "https://...",
    "duration": "3:24",
    "colors": ["#3b5998", "#8b9dc3", "#dfe3ee"]
  }
]
```

#### ⬇️ POST /api/v1/download
Baixa o áudio de uma música.

**Body:**
```json
{
  "video_id": "7wtfhZwyrcc"
}
```

**Resposta:**
```json
{
  "file_path": "/app/downloads/7wtfhZwyrcc.mp3",
  "title": "Believer",
  "duration": "03:24"
}
```

#### ✂️ POST /api/v1/trim
Corta um trecho específico de áudio.

**Body:**
```json
{
  "file_path": "/app/downloads/7wtfhZwyrcc.mp3",
  "start_time": "00:00:10",
  "end_time": "00:01:00"
}
```

**Resposta:**
```json
{
  "trimmed_file_path": "/app/downloads/7wtfhZwyrcc_trimmed_10_60.mp3",
  "original_duration": "03:24",
  "trimmed_duration": "00:50"
}
```

#### 🧠 POST /api/v1/transcribe
Transcreve áudio com timestamps usando Whisper (local) ou ElevenLabs (API).

**Parâmetros principais:**
- `provider`: `"whisper"` (padrão) ou `"elevenlabs"`
- `model`: Modelo a ser utilizado (depende do provedor)
- `force_language`: Código do idioma do áudio (ex: "pt", "en")
- `translate_to`: Código do idioma para tradução (ex: "pt", "en")

**Modelos disponíveis:**
- **Whisper**: `"tiny"`, `"base"`, `"small"`, `"medium"`, `"large"` (padrão: `"base"`)
- **ElevenLabs**: `"scribe_v1"`, `"scribe_v1_experimental"` (padrão: `"scribe_v1"`)

**Body (Whisper - sem tradução):**
```json
{
  "file_path": "/app/downloads/7wtfhZwyrcc_trimmed_10_60.mp3",
  "provider": "whisper",
  "model": "base"
}
```

**Body (ElevenLabs - com tradução):**
```json
{
  "file_path": "/app/downloads/7wtfhZwyrcc_trimmed_10_60.mp3",
  "provider": "elevenlabs",
  "model": "scribe_v1",
  "force_language": "en",
  "translate_to": "pt"
}
```

**Resposta:**
```json
{
  "language": "en",
  "language_probability": 0.95,
  "translated_to": "pt",
  "file_duration": 50.0,
  "provider": "elevenlabs",
  "segments": [
    {
      "start": 0.0,
      "end": 5.2,
      "text": "Pain, you made me a believer",
      "translated_text": "Dor, você me fez um crente"
    }
  ]
}
```

#### 🔍 GET /api/v1/providers
Retorna informações sobre os provedores de transcrição disponíveis.

**Resposta:**
```json
{
  "whisper": {
    "name": "Faster Whisper",
    "description": "Transcrição local usando Faster Whisper",
    "available": true,
    "supports_translation": true,
    "supported_models": ["tiny", "base", "small", "medium", "large"],
    "default_model": "base"
  },
  "elevenlabs": {
    "name": "ElevenLabs Speech-to-Text",
    "description": "Transcrição via API da ElevenLabs",
    "available": false,
    "supports_translation": true,
    "supported_models": ["scribe_v1", "scribe_v1_experimental"],
    "default_model": "scribe_v1"
  }
}
```

## 🧪 Testes

Execute os testes automatizados:

```bash
# Testes locais
pytest tests/ -v

# Testes no Docker
docker-compose exec api pytest tests/ -v
```

## 🛠️ Configuração

### Variáveis de Ambiente

- `DOWNLOADS_DIR`: Diretório para arquivos baixados (padrão: `./downloads`)
- `ELEVENLABS_API_KEY`: Chave da API ElevenLabs (opcional, necessária apenas para usar o provedor ElevenLabs)
- `PYTHONUNBUFFERED`: Saída Python sem buffer (padrão: `1`)

### Configuração do ElevenLabs

Para usar o provedor ElevenLabs, você precisa:

1. Criar uma conta na [ElevenLabs](https://elevenlabs.io/)
2. Obter sua API key no painel de configurações
3. Criar um arquivo `.env` na raiz do projeto:

```bash
ELEVENLABS_API_KEY=your_api_key_here
```

**Vantagens do ElevenLabs:**
- Transcrição mais precisa para alguns idiomas
- Melhor detecção de eventos sonoros
- Identificação de falantes
- Processamento em nuvem (sem uso de recursos locais)

### Formatos de Tempo Suportados

Para as rotas de corte, você pode usar:
- Segundos: `"10"`, `"30.5"`
- MM:SS: `"01:30"`, `"02:45"`
- HH:MM:SS: `"00:01:30"`, `"01:02:45"`

### Idiomas Suportados para Tradução

- `pt` - Português
- `en` - Inglês
- `es` - Espanhol
- `fr` - Francês
- `de` - Alemão
- `it` - Italiano
- `ja` - Japonês
- `ko` - Coreano
- E muitos outros...

### Comparação entre Provedores

| Característica | Whisper (Local) | ElevenLabs (API) |
|---|---|---|
| **Processamento** | Local (CPU/GPU) | Nuvem |
| **Precisão** | Boa | Excelente |
| **Velocidade** | Média | Rápida |
| **Custo** | Gratuito | Pago (após limite) |
| **Privacidade** | Total | Dados enviados para API |
| **Modelos** | 5 opções | 2 opções |
| **Tradução** | ✅ | ✅ |
| **Eventos sonoros** | ❌ | ✅ |
| **Identificação de falantes** | ❌ | ✅ |

## 📁 Estrutura do Projeto

```
app/
├── main.py              # Aplicação principal FastAPI
├── api/                 # Endpoints da API
│   ├── search.py        # Busca de músicas
│   ├── download.py      # Download de áudios
│   ├── trim.py          # Corte de áudios
│   └── transcribe.py    # Transcrição e tradução
├── services/            # Lógica de negócio
│   ├── ytmusic_service.py    # Integração YouTube Music
│   ├── download_service.py   # Download de áudios
│   ├── audio_service.py      # Manipulação de áudio
│   ├── whisper_service.py    # Transcrição local com Whisper
│   └── elevenlabs_service.py # Transcrição via API ElevenLabs
└── utils/
    └── colors.py        # Extração de cores de imagens
tests/                   # Testes automatizados
downloads/              # Arquivos baixados (criado automaticamente)
```

## 🔧 Tecnologias Utilizadas

- **FastAPI** - Framework web moderno e rápido
- **faster-whisper** - Transcrição de áudio local otimizada
- **ElevenLabs API** - Transcrição de áudio em nuvem com alta precisão
- **deep-translator** - Tradução de textos
- **ytmusicapi** - API não oficial do YouTube Music
- **yt-dlp** - Download de vídeos/áudios do YouTube
- **ffmpeg-python** - Manipulação de áudios
- **colorthief** - Extração de cores de imagens
- **pytest** - Framework de testes

## 📄 Licença

Este projeto é licenciado sob a MIT License.

## 🤝 Contribuição

Contribuições são bem-vindas! Por favor:

1. Faça um fork do projeto
2. Crie uma branch para sua feature (`git checkout -b feature/AmazingFeature`)
3. Commit suas mudanças (`git commit -m 'Add some AmazingFeature'`)
4. Push para a branch (`git push origin feature/AmazingFeature`)
5. Abra um Pull Request

## ⚠️ Aviso Legal

Este projeto é para fins educacionais. Respeite os termos de serviço do YouTube e as leis de direitos autorais ao usar esta API.
