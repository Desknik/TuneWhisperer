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
    Pesquisa músicas no YouTube Music e retorna resultados com cores dominantes da capa.
    """
    try:
        ytmusic_service = YouTubeMusicService()
        color_extractor = ColorExtractor()
        
        # Buscar músicas
        search_results = await ytmusic_service.search(query, limit)
        
        if not search_results:
            return []
          # Extrair cores das thumbnails em paralelo
        tasks = []
        for result in search_results:
            if result.get("thumbnail"):
                task = color_extractor.extract_colors_from_url(result["thumbnail"])
                tasks.append(task)
            else:
                # Criar corrotina que retorna lista vazia
                async def empty_colors():
                    return []
                tasks.append(empty_colors())
        
        colors_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Combinar resultados com cores
        enhanced_results = []
        for i, result in enumerate(search_results):
            colors = colors_results[i] if i < len(colors_results) and not isinstance(colors_results[i], Exception) else []
            
            enhanced_result = {
                "title": result.get("title", ""),
                "artist": result.get("artist", ""),
                "videoId": result.get("videoId", ""),
                "thumbnail": result.get("thumbnail", ""),
                "duration": result.get("duration", ""),
                "colors": colors
            }
            enhanced_results.append(enhanced_result)
        
        return enhanced_results
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro na busca: {str(e)}")
