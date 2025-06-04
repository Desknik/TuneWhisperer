from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import os

from app.services.whisper_service import WhisperService
from app.services.elevenlabs_service import ElevenLabsService

router = APIRouter()

class TranscribeRequest(BaseModel):
    file_path: str
    translate_to: Optional[str] = None  # Código do idioma para tradução (ex: "pt", "en", "es")
    model: Optional[str] = None  # Modelo a ser utilizado (depende do provedor)
    force_language: Optional[str] = None  # Forçar idioma do áudio (ex: 'pt', 'en')
    provider: Optional[str] = "whisper"  # Provedor: 'whisper' ou 'elevenlabs'

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
    """
    try:
        # Validar arquivo de entrada
        if not os.path.exists(request.file_path):
            raise HTTPException(status_code=404, detail="Arquivo de áudio não encontrado")
        
        # Validar formato do arquivo
        valid_extensions = ['.mp3', '.wav', '.m4a', '.flac', '.ogg']
        file_extension = os.path.splitext(request.file_path)[1].lower()
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
        
        # Escolher serviço baseado no provedor
        if provider == "elevenlabs":
            service = ElevenLabsService()
            if not service.is_api_key_valid():
                raise HTTPException(
                    status_code=400,
                    detail="API key da ElevenLabs não configurada. Configure ELEVENLABS_API_KEY no .env"
                )
            
            # ElevenLabs agora suporta tradução via deep_translator
            transcription_result = await service.transcribe_audio(
                file_path=request.file_path,
                language_code=request.force_language,
                model_id=model,
                translate_to=request.translate_to
            )
        else:
            # Usar Whisper
            whisper_service = WhisperService(model_size=model)
            transcription_result = await whisper_service.transcribe_audio(
                file_path=request.file_path,
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
        
        return TranscribeResponse(
            language=transcription_result["language"],
            language_probability=transcription_result.get("language_probability"),
            translated_to=transcription_result.get("translated_to"),
            segments=segments,
            file_duration=transcription_result.get("file_duration", 0.0),
            provider=transcription_result.get("provider", provider)
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
