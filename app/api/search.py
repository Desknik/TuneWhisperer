from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
import asyncio

from app.services.ytmusic_service import YouTubeMusicService
from app.utils.colors import ColorExtractor

router = APIRouter()

@router.get("/search")
async def search_music(
    query: str = Query(..., description="Termo de busca para músicas"),
    limit: int = Query(10, ge=1, le=50, description="Número máximo de resultados")
):
    """
    Pesquisa músicas no YouTube Music.
    """
    try:
        ytmusic_service = YouTubeMusicService()
        
        # Buscar músicas
        search_results = await ytmusic_service.search(query, limit)
        
        if not search_results:
            return []
            
        return search_results
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro na busca: {str(e)}")

@router.get("/song/{video_id}")
async def get_song_details(
    video_id: str,
):
    """
    Obtém detalhes de uma música específica incluindo as cores da thumbnail.
    """
    try:
        ytmusic_service = YouTubeMusicService()
        color_extractor = ColorExtractor()
        
        # Buscar informações da música
        song_info = await ytmusic_service.get_song_info(video_id)
        
        if not song_info:
            raise HTTPException(status_code=404, detail="Música não encontrada")
            
        # Extrair cores da thumbnail
        colors = []
        if song_info.get("thumbnail"):
            colors = await color_extractor.extract_colors_from_url(song_info["thumbnail"])
            
        # Adicionar cores ao resultado
        song_info["colors"] = colors
        
        return song_info
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao obter detalhes da música: {str(e)}")
