import yt_dlp
import os
import asyncio
from typing import Dict, Optional

class DownloadService:
    """Serviço para download de áudios do YouTube usando yt-dlp."""
    
    def __init__(self):
        self.downloads_dir = os.getenv("DOWNLOADS_DIR", "./downloads")
        os.makedirs(self.downloads_dir, exist_ok=True)
    
    async def download_audio(self, video_id: str) -> Optional[Dict]:
        """
        Baixa o áudio de um vídeo do YouTube.
        
        Args:
            video_id: ID do vídeo no YouTube
            
        Returns:
            Informações do arquivo baixado ou None se falhou
        """
        try:
            # URL completa do YouTube
            url = f"https://www.youtube.com/watch?v={video_id}"
            
            # Caminho final do arquivo
            final_path = os.path.join(self.downloads_dir, f"{video_id}.mp3")
            
            # Configurações do yt-dlp
            ydl_opts = {
                'format': 'bestaudio[ext=m4a]/bestaudio[ext=webm]/bestaudio',
                'outtmpl': os.path.join(self.downloads_dir, f"{video_id}.%(ext)s"),
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
                'postprocessor_args': [
                    '-ar', '44100'
                ],
                'prefer_ffmpeg': True,
                'keepvideo': False,
                'quiet': False,  # Mudado para False para debug
                'no_warnings': False,  # Mudado para False para debug
            }
            
            # Executar download em thread separada
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                self._download_with_ytdlp,
                url,
                ydl_opts,
                final_path
            )
            
            if result and os.path.exists(final_path):
                return {
                    "file_path": final_path,
                    "title": result.get("title", ""),
                    "duration": self._format_duration(result.get("duration", 0)),
                    "video_id": video_id
                }
            
            print(f"Download falhou. Arquivo esperado: {final_path}, existe: {os.path.exists(final_path)}")
            return None
        
        except Exception as e:
            print(f"Erro no download: {str(e)}")
            import traceback
            traceback.print_exc()
            return None
    
    def _download_with_ytdlp(self, url: str, ydl_opts: Dict, final_path: str) -> Optional[Dict]:
        """
        Executa o download usando yt-dlp.
        
        Args:
            url: URL do vídeo
            ydl_opts: Opções do yt-dlp
            final_path: Caminho final esperado do arquivo
            
        Returns:
            Informações do vídeo baixado
        """
        try:
            print(f"Iniciando download de: {url}")
            print(f"Diretório de downloads: {self.downloads_dir}")
            print(f"Arquivo final esperado: {final_path}")
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # Extrair informações do vídeo
                print("Extraindo informações do vídeo...")
                info = ydl.extract_info(url, download=False)
                
                print(f"Título: {info.get('title', 'N/A')}")
                print(f"Duração: {info.get('duration', 'N/A')} segundos")
                
                # Fazer o download
                print("Iniciando download...")
                ydl.download([url])
                
                # Verificar se o arquivo foi criado
                if os.path.exists(final_path):
                    print(f"Download concluído com sucesso: {final_path}")
                else:
                    print(f"Arquivo não encontrado após download: {final_path}")
                    # Listar arquivos no diretório para debug
                    files = os.listdir(self.downloads_dir)
                    print(f"Arquivos no diretório: {files}")
                
                return {
                    "title": info.get("title", ""),
                    "duration": info.get("duration", 0),
                    "uploader": info.get("uploader", "")
                }
                
        except Exception as e:
            print(f"Erro no yt-dlp: {str(e)}")
            import traceback
            traceback.print_exc()
            return None
    
    def _format_duration(self, duration_seconds: int) -> str:
        """
        Formata duração de segundos para MM:SS.
        
        Args:
            duration_seconds: Duração em segundos
            
        Returns:
            Duração formatada
        """
        if not duration_seconds:
            return "00:00"
        
        minutes = duration_seconds // 60
        seconds = duration_seconds % 60
        return f"{minutes:02d}:{seconds:02d}"
    
    def cleanup_old_files(self, max_age_hours: int = 24):
        """
        Remove arquivos antigos do diretório de downloads.
        
        Args:
            max_age_hours: Idade máxima dos arquivos em horas
        """
        try:
            import time
            current_time = time.time()
            max_age_seconds = max_age_hours * 3600
            
            for filename in os.listdir(self.downloads_dir):
                file_path = os.path.join(self.downloads_dir, filename)
                
                if os.path.isfile(file_path):
                    file_age = current_time - os.path.getmtime(file_path)
                    
                    if file_age > max_age_seconds:
                        os.remove(file_path)
                        print(f"Arquivo removido: {filename}")
                        
        except Exception as e:
            print(f"Erro na limpeza de arquivos: {str(e)}")
    
    def get_file_size(self, file_path: str) -> str:
        """
        Obtém o tamanho de um arquivo em formato legível.
        
        Args:
            file_path: Caminho do arquivo
            
        Returns:
            Tamanho formatado (ex: "5.2 MB")
        """
        try:
            if not os.path.exists(file_path):
                return "0 B"
            
            size_bytes = os.path.getsize(file_path)
            
            # Converter para unidades legíveis
            if size_bytes < 1024:
                return f"{size_bytes} B"
            elif size_bytes < 1024 ** 2:
                return f"{size_bytes / 1024:.1f} KB"
            elif size_bytes < 1024 ** 3:
                return f"{size_bytes / (1024 ** 2):.1f} MB"
            else:
                return f"{size_bytes / (1024 ** 3):.1f} GB"
                
        except Exception as e:
            print(f"Erro ao obter tamanho do arquivo: {str(e)}")
            return "N/A"
