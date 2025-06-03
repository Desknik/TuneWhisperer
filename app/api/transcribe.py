from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import os

from app.services.whisper_service import WhisperService

router = APIRouter()

class TranscribeRequest(BaseModel):
    file_path: str
    translate_to: Optional[str] = None  # Código do idioma para tradução (ex: "pt", "en", "es")
    model_size: Optional[str] = "base"  # Modelo do Whisper: tiny, base, small, medium, large
    force_language: Optional[str] = None  # Forçar idioma do áudio (ex: 'pt', 'en')

class TranscriptionSegment(BaseModel):
    start: float
    end: float
    text: str
    translated_text: Optional[str] = None

class TranscribeResponse(BaseModel):
    language: str
    translated_to: Optional[str] = None
    segments: List[TranscriptionSegment]
    file_duration: float

@router.post("/transcribe", response_model=TranscribeResponse)
async def transcribe_audio(request: TranscribeRequest):
    """
    Transcreve um arquivo de áudio com timestamps e opcionalmente traduz o resultado.
    - model_size: Modelo do Whisper a ser utilizado. Valores: 'tiny', 'base', 'small', 'medium', 'large'.
    """
    try:
        whisper_service = WhisperService(model_size=request.model_size or "base")
        
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
        
        # Transcrever áudio
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
            translated_to=transcription_result.get("translated_to"),
            segments=segments,
            file_duration=transcription_result.get("file_duration", 0.0)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro na transcrição: {str(e)}")
