from ytmusicapi import YTMusic
import asyncio
from typing import List, Dict, Optional

class YouTubeMusicService:
    """Serviço para pesquisa no YouTube Music usando ytmusicapi."""
    
    def __init__(self):
        self.ytmusic = YTMusic()
    
    async def search(self, query: str, limit: int = 10) -> List[Dict]:
        """
        Pesquisa músicas no YouTube Music.
        
        Args:
            query: Termo de busca
            limit: Número máximo de resultados
            
        Returns:
            Lista de resultados com metadados das músicas
        """
        try:
            # Executar busca em thread separada para não bloquear
            loop = asyncio.get_event_loop()
            search_results = await loop.run_in_executor(
                None, 
                lambda: self.ytmusic.search(query, filter="songs", limit=limit)
            )
            
            # Processar resultados
            processed_results = []
            for result in search_results:
                processed_result = self._process_search_result(result)
                if processed_result:
                    processed_results.append(processed_result)
            
            return processed_results
            
        except Exception as e:
            print(f"Erro na busca do YouTube Music: {str(e)}")
            return []
    
    def _process_search_result(self, result: Dict) -> Optional[Dict]:
        """
        Processa um resultado individual da busca.
        
        Args:
            result: Resultado bruto da API do YouTube Music
            
        Returns:
            Resultado processado ou None se inválido
        """
        try:
            # Extrair informações básicas
            video_id = result.get("videoId")
            if not video_id:
                return None
            
            title = result.get("title", "")
            
            # Extrair artista(s)
            artists = result.get("artists", [])
            artist_names = []
            if artists:
                for artist in artists:
                    if isinstance(artist, dict) and "name" in artist:
                        artist_names.append(artist["name"])
                    elif isinstance(artist, str):
                        artist_names.append(artist)
            
            artist = ", ".join(artist_names) if artist_names else "Artista Desconhecido"
            
            # Extrair thumbnail
            thumbnails = result.get("thumbnails", [])
            thumbnail_url = ""
            if thumbnails:
                # Pegar a thumbnail de maior qualidade disponível
                thumbnail_url = thumbnails[-1].get("url", "") if thumbnails else ""
            
            # Extrair duração
            duration_text = ""
            if "duration" in result and result["duration"]:
                duration_text = result["duration"]
            elif "duration_seconds" in result:
                seconds = result["duration_seconds"]
                if seconds:
                    minutes = seconds // 60
                    remaining_seconds = seconds % 60
                    duration_text = f"{minutes}:{remaining_seconds:02d}"
            
            return {
                "title": title,
                "artist": artist,
                "videoId": video_id,
                "thumbnail": thumbnail_url,
                "duration": duration_text
            }
            
        except Exception as e:
            print(f"Erro ao processar resultado: {str(e)}")
            return None
    
    async def get_song_info(self, video_id: str) -> Optional[Dict]:
        """
        Obtém informações detalhadas de uma música específica.
        
        Args:
            video_id: ID do vídeo no YouTube
            
        Returns:
            Informações da música ou None se não encontrada
        """
        try:
            loop = asyncio.get_event_loop()
            song_info = await loop.run_in_executor(
                None,
                lambda: self.ytmusic.get_song(video_id)
            )
            
            if song_info:
                return {
                    "title": song_info.get("title", ""),
                    "artist": ", ".join([artist.get("name", "") for artist in song_info.get("artists", [])]),
                    "album": song_info.get("album", {}).get("name", ""),
                    "duration": song_info.get("duration", ""),
                    "videoId": video_id
                }
            
            return None
            
        except Exception as e:
            print(f"Erro ao obter informações da música: {str(e)}")
            return None
