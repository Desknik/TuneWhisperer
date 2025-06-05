from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import os
import json

from app.services.whisper_service import WhisperService
from app.services.elevenlabs_service import ElevenLabsService

router = APIRouter()

class TranscribeRequest(BaseModel):
    file_path: str
    translate_to: Optional[str] = None  # Código do idioma para tradução (ex: "pt", "en", "es")
    model: Optional[str] = None  # Modelo a ser utilizado (depende do provedor)
    force_language: Optional[str] = None  # Forçar idioma do áudio (ex: 'pt', 'en')
    provider: Optional[str] = "whisper"  # Provedor: 'whisper' ou 'elevenlabs'
    use_cache: bool = True  # Novo parâmetro para controlar o uso do cache

class TranscriptionSegment(BaseModel):
    start: float
    end: float
    text: str
    translated_text: Optional[str] = None

class TranscribeResponse(BaseModel):
    language: str
    language_probability: Optional[float] = None
    translated_to: Optional[str] = None
    segments: List[TranscriptionSegment]
    file_duration: float
    provider: str  # Indica qual provedor foi usado
    cached: bool = False  # Indica se o resultado veio do cache

def _get_absolute_path(relative_path: str) -> str:
    """Converte um caminho relativo para absoluto."""
    return os.path.abspath(relative_path)

def _get_transcription_cache_path(file_path: str, provider: str, model: str, translate_to: Optional[str] = None) -> str:
    """Retorna o caminho do arquivo de cache para a transcrição."""
    # Extrair o diretório base do arquivo de áudio
    base_dir = os.path.dirname(file_path)
    
    # Criar nome do arquivo de cache baseado nos parâmetros
    cache_name = f"transcription_{provider}_{model}"
    if translate_to:
        cache_name += f"_{translate_to}"
    cache_name += ".json"
    
    return os.path.join(base_dir, cache_name)

def _load_transcription_cache(cache_path: str) -> Optional[dict]:
    """Carrega a transcrição do cache."""
    if os.path.exists(cache_path):
        with open(cache_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None

def _save_transcription_cache(cache_path: str, transcription: dict):
    """Salva a transcrição no cache."""
    with open(cache_path, 'w', encoding='utf-8') as f:
        json.dump(transcription, f, ensure_ascii=False, indent=2)

@router.post("/transcribe", response_model=TranscribeResponse)
async def transcribe_audio(request: TranscribeRequest):
    """
    Transcreve um arquivo de áudio com timestamps e opcionalmente traduz o resultado.
    
    - provider: Escolha entre 'whisper' (padrão) ou 'elevenlabs'
    - model: Modelo a ser utilizado:
        - Para Whisper: 'tiny', 'base', 'small', 'medium', 'large' (padrão: 'base')
        - Para ElevenLabs: 'scribe_v1', 'scribe_v1_experimental' (padrão: 'scribe_v1')
    - force_language: Código do idioma do áudio (ex: 'pt', 'en') - funciona para ambos os provedores
    - translate_to: Código do idioma para tradução (ex: 'pt', 'en') - funciona para ambos os provedores
    - use_cache: Se True (padrão), retorna a transcrição do cache se disponível
    """
    try:
        # Converter caminho relativo para absoluto
        absolute_file_path = _get_absolute_path(request.file_path)
        
        # Validar arquivo de entrada
        if not os.path.exists(absolute_file_path):
            raise HTTPException(
                status_code=404,
                detail=f"Arquivo de áudio não encontrado: {request.file_path}"
            )
        
        # Validar formato do arquivo
        valid_extensions = ['.mp3', '.wav', '.m4a', '.flac', '.ogg']
        file_extension = os.path.splitext(absolute_file_path)[1].lower()
        if file_extension not in valid_extensions:
            raise HTTPException(
                status_code=400, 
                detail=f"Formato de arquivo não suportado. Use: {', '.join(valid_extensions)}"
            )
        
        # Validar provedor
        provider = request.provider or "whisper"
        if provider not in ["whisper", "elevenlabs"]:
            raise HTTPException(
                status_code=400,
                detail="Provedor deve ser 'whisper' ou 'elevenlabs'"
            )
        
        # Validar e definir modelo baseado no provedor
        if provider == "whisper":
            valid_whisper_models = ["tiny", "base", "small", "medium", "large"]
            model = request.model or "base"
            if model not in valid_whisper_models:
                raise HTTPException(
                    status_code=400,
                    detail=f"Modelo inválido para Whisper. Use: {', '.join(valid_whisper_models)}"
                )
        else:  # elevenlabs
            valid_elevenlabs_models = ["scribe_v1", "scribe_v1_experimental"]
            model = request.model or "scribe_v1"
            if model not in valid_elevenlabs_models:
                raise HTTPException(
                    status_code=400,
                    detail=f"Modelo inválido para ElevenLabs. Use: {', '.join(valid_elevenlabs_models)}"
                )
        
        # Verificar cache
        if request.use_cache:
            cache_path = _get_transcription_cache_path(
                absolute_file_path,
                provider,
                model,
                request.translate_to
            )
            cached_result = _load_transcription_cache(cache_path)
            if cached_result:
                # Preparar segmentos do cache
                segments = []
                for segment in cached_result.get("segments", []):
                    segment_data = TranscriptionSegment(
                        start=segment["start"],
                        end=segment["end"],
                        text=segment["text"],
                        translated_text=segment.get("translated_text")
                    )
                    segments.append(segment_data)
                
                return TranscribeResponse(
                    language=cached_result["language"],
                    language_probability=cached_result.get("language_probability"),
                    translated_to=cached_result.get("translated_to"),
                    segments=segments,
                    file_duration=cached_result.get("file_duration", 0.0),
                    provider=cached_result.get("provider", provider),
                    cached=True
                )
        
        # Escolher serviço baseado no provedor
        if provider == "elevenlabs":
            service = ElevenLabsService()
            if not service.is_api_key_valid():
                raise HTTPException(
                    status_code=400,
                    detail="API key da ElevenLabs não configurada. Configure ELEVENLABS_API_KEY no .env"
                )
            
            transcription_result = await service.transcribe_audio(
                file_path=absolute_file_path,
                language_code=request.force_language,
                model_id=model,
                translate_to=request.translate_to
            )
        else:
            # Usar Whisper
            whisper_service = WhisperService(model_size=model)
            transcription_result = await whisper_service.transcribe_audio(
                file_path=absolute_file_path,
                translate_to=request.translate_to,
                force_language=request.force_language
            )
        
        if not transcription_result:
            raise HTTPException(status_code=500, detail="Erro na transcrição do áudio")
        
        # Preparar segmentos
        segments = []
        for segment in transcription_result.get("segments", []):
            segment_data = TranscriptionSegment(
                start=segment["start"],
                end=segment["end"],
                text=segment["text"],
                translated_text=segment.get("translated_text")
            )
            segments.append(segment_data)
        
        # Salvar no cache
        cache_path = _get_transcription_cache_path(
            absolute_file_path,
            provider,
            model,
            request.translate_to
        )
        _save_transcription_cache(cache_path, transcription_result)
        
        return TranscribeResponse(
            language=transcription_result["language"],
            language_probability=transcription_result.get("language_probability"),
            translated_to=transcription_result.get("translated_to"),
            segments=segments,
            file_duration=transcription_result.get("file_duration", 0.0),
            provider=transcription_result.get("provider", provider),
            cached=False
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro na transcrição: {str(e)}")

@router.get("/providers")
async def get_transcription_providers():
    """
    Retorna informações sobre os provedores de transcrição disponíveis.
    """
    providers = {
        "whisper": {
            "name": "Faster Whisper",
            "description": "Transcrição local usando Faster Whisper",
            "available": True,
            "supports_translation": True,
            "supported_models": ["tiny", "base", "small", "medium", "large"],
            "default_model": "base"
        },        "elevenlabs": {
            "name": "ElevenLabs Speech-to-Text",
            "description": "Transcrição via API da ElevenLabs",
            "available": False,
            "supports_translation": True,
            "supported_models": ["scribe_v1", "scribe_v1_experimental"],
            "default_model": "scribe_v1"
        }
    }
    
    # Verificar se ElevenLabs está disponível
    try:
        elevenlabs_service = ElevenLabsService()
        if elevenlabs_service.is_api_key_valid():
            providers["elevenlabs"]["available"] = True
    except:
        pass
    
    return providers
