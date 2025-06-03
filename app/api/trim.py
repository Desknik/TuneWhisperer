from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import os

from app.services.audio_service import AudioService

router = APIRouter()

class TrimRequest(BaseModel):
    file_path: str
    start_time: str  # Formato: "00:00:10" ou "10" (segundos)
    end_time: str    # Formato: "00:01:00" ou "60" (segundos)

class TrimResponse(BaseModel):
    trimmed_file_path: str
    original_duration: str
    trimmed_duration: str

@router.post("/trim", response_model=TrimResponse)
async def trim_audio(request: TrimRequest):
    """
    Corta um trecho específico de um arquivo de áudio.
    """
    try:
        audio_service = AudioService()
        
        # Validar arquivo de entrada
        if not os.path.exists(request.file_path):
            raise HTTPException(status_code=404, detail="Arquivo de áudio não encontrado")
        
        # Validar tempos
        if not request.start_time or not request.end_time:
            raise HTTPException(status_code=400, detail="start_time e end_time são obrigatórios")
        
        # Cortar áudio
        result = await audio_service.trim_audio(
            input_path=request.file_path,
            start_time=request.start_time,
            end_time=request.end_time
        )
        
        if not result:
            raise HTTPException(status_code=500, detail="Erro ao cortar o áudio")
        
        # Verificar se o arquivo foi criado
        if not os.path.exists(result["trimmed_file_path"]):
            raise HTTPException(status_code=500, detail="Erro: arquivo cortado não foi criado")
        
        return TrimResponse(
            trimmed_file_path=result["trimmed_file_path"],
            original_duration=result.get("original_duration", ""),
            trimmed_duration=result.get("trimmed_duration", "")
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao cortar áudio: {str(e)}")
