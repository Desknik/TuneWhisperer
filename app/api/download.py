from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import os

from app.services.download_service import DownloadService

router = APIRouter()

class DownloadRequest(BaseModel):
    video_id: str
    use_cache: bool = True  # Novo parâmetro para controlar o uso do cache

class DownloadResponse(BaseModel):
    file_path: str
    title: str
    duration: str
    cached: bool = False  # Indica se o resultado veio do cache

@router.post("/download", response_model=DownloadResponse)
async def download_audio(request: DownloadRequest):
    """
    Baixa o áudio de uma música do YouTube Music.
    
    - use_cache: Se True (padrão), retorna o arquivo do cache se disponível
    """
    try:
        download_service = DownloadService()
        
        # Validar video_id
        if not request.video_id or len(request.video_id.strip()) == 0:
            raise HTTPException(status_code=400, detail="video_id é obrigatório")
        
        # Fazer download
        result = await download_service.download_audio(
            request.video_id,
            use_cache=request.use_cache
        )
        
        if not result:
            raise HTTPException(status_code=404, detail="Música não encontrada ou erro no download")
        
        # Verificar se o arquivo foi criado
        if not os.path.exists(result["file_path"]):
            raise HTTPException(status_code=500, detail="Erro: arquivo não foi criado")
        
        # Verificar se veio do cache
        is_cached = "cached_at" in result
        
        return DownloadResponse(
            file_path=result["file_path"],
            title=result.get("title", ""),
            duration=result.get("duration", ""),
            cached=is_cached
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro no download: {str(e)}")
