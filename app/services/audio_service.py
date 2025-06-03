import ffmpeg
import os
import asyncio
from typing import Dict, Optional
import re

class AudioService:
    """Serviço para manipulação de arquivos de áudio usando ffmpeg."""
    
    def __init__(self):
        self.downloads_dir = os.getenv("DOWNLOADS_DIR", "./downloads")
    
    async def trim_audio(self, input_path: str, start_time: str, end_time: str) -> Optional[Dict]:
        """
        Corta um trecho de áudio especificando início e fim.
        
        Args:
            input_path: Caminho do arquivo de entrada
            start_time: Tempo de início (formato: "00:00:10" ou "10")
            end_time: Tempo de fim (formato: "00:01:00" ou "60")
            
        Returns:
            Informações do arquivo cortado ou None se falhou
        """
        try:
            # Validar arquivo de entrada
            if not os.path.exists(input_path):
                raise FileNotFoundError(f"Arquivo não encontrado: {input_path}")
            
            # Converter tempos para segundos
            start_seconds = self._time_to_seconds(start_time)
            end_seconds = self._time_to_seconds(end_time)
            
            # Validar tempos
            if start_seconds >= end_seconds:
                raise ValueError("Tempo de início deve ser menor que tempo de fim")
            
            # Gerar nome do arquivo de saída
            base_name = os.path.splitext(os.path.basename(input_path))[0]
            output_filename = f"{base_name}_trimmed_{start_seconds}_{end_seconds}.mp3"
            output_path = os.path.join(self.downloads_dir, output_filename)
            
            # Calcular duração do corte
            duration = end_seconds - start_seconds
            
            # Executar corte em thread separada
            loop = asyncio.get_event_loop()
            success = await loop.run_in_executor(
                None,
                self._trim_with_ffmpeg,
                input_path,
                output_path,
                start_seconds,
                duration
            )
            
            if success and os.path.exists(output_path):
                # Obter duração original
                original_duration = await self.get_audio_duration(input_path)
                trimmed_duration = await self.get_audio_duration(output_path)
                
                return {
                    "trimmed_file_path": output_path,
                    "original_duration": self._seconds_to_time(original_duration),
                    "trimmed_duration": self._seconds_to_time(trimmed_duration),
                    "start_time": start_time,
                    "end_time": end_time
                }
            
            return None
            
        except Exception as e:
            print(f"Erro ao cortar áudio: {str(e)}")
            return None
    
    def _trim_with_ffmpeg(self, input_path: str, output_path: str, start_seconds: float, duration: float) -> bool:
        """
        Executa o corte usando ffmpeg.
        
        Args:
            input_path: Arquivo de entrada
            output_path: Arquivo de saída
            start_seconds: Início em segundos
            duration: Duração em segundos
            
        Returns:
            True se sucesso, False caso contrário
        """
        try:
            # Usar ffmpeg-python para cortar o áudio
            (
                ffmpeg
                .input(input_path, ss=start_seconds, t=duration)
                .output(output_path, acodec='mp3', audio_bitrate='192k')
                .overwrite_output()
                .run(quiet=True)
            )
            return True
            
        except Exception as e:
            print(f"Erro no ffmpeg: {str(e)}")
            return False
    
    async def get_audio_duration(self, file_path: str) -> float:
        """
        Obtém a duração de um arquivo de áudio em segundos.
        
        Args:
            file_path: Caminho do arquivo
            
        Returns:
            Duração em segundos
        """
        try:
            loop = asyncio.get_event_loop()
            duration = await loop.run_in_executor(
                None,
                self._get_duration_with_ffmpeg,
                file_path
            )
            return duration
            
        except Exception as e:
            print(f"Erro ao obter duração: {str(e)}")
            return 0.0
    
    def _get_duration_with_ffmpeg(self, file_path: str) -> float:
        """
        Usa ffmpeg para obter duração do arquivo.
        
        Args:
            file_path: Caminho do arquivo
            
        Returns:
            Duração em segundos
        """
        try:
            probe = ffmpeg.probe(file_path)
            duration = float(probe['format']['duration'])
            return duration
            
        except Exception as e:
            print(f"Erro no probe ffmpeg: {str(e)}")
            return 0.0
    
    def _time_to_seconds(self, time_str: str) -> float:
        """
        Converte string de tempo para segundos.
        
        Args:
            time_str: Tempo em formato "HH:MM:SS", "MM:SS" ou segundos
            
        Returns:
            Tempo em segundos
        """
        try:
            # Se já é um número (segundos)
            if time_str.isdigit() or (time_str.count('.') == 1 and time_str.replace('.', '').isdigit()):
                return float(time_str)
            
            # Formato HH:MM:SS ou MM:SS
            parts = time_str.split(':')
            
            if len(parts) == 1:
                # Apenas segundos
                return float(parts[0])
            elif len(parts) == 2:
                # MM:SS
                minutes, seconds = parts
                return int(minutes) * 60 + float(seconds)
            elif len(parts) == 3:
                # HH:MM:SS
                hours, minutes, seconds = parts
                return int(hours) * 3600 + int(minutes) * 60 + float(seconds)
            else:
                raise ValueError(f"Formato de tempo inválido: {time_str}")
                
        except Exception as e:
            print(f"Erro ao converter tempo: {str(e)}")
            return 0.0
    
    def _seconds_to_time(self, seconds: float) -> str:
        """
        Converte segundos para formato HH:MM:SS.
        
        Args:
            seconds: Tempo em segundos
            
        Returns:
            Tempo formatado
        """
        try:
            if seconds <= 0:
                return "00:00:00"
            
            hours = int(seconds // 3600)
            minutes = int((seconds % 3600) // 60)
            secs = int(seconds % 60)
            
            if hours > 0:
                return f"{hours:02d}:{minutes:02d}:{secs:02d}"
            else:
                return f"{minutes:02d}:{secs:02d}"
                
        except Exception as e:
            print(f"Erro ao formatar tempo: {str(e)}")
            return "00:00"
    
    def get_audio_info(self, file_path: str) -> Dict:
        """
        Obtém informações completas de um arquivo de áudio.
        
        Args:
            file_path: Caminho do arquivo
            
        Returns:
            Dicionário com informações do áudio
        """
        try:
            probe = ffmpeg.probe(file_path)
            format_info = probe.get('format', {})
            
            return {
                "filename": os.path.basename(file_path),
                "format": format_info.get('format_name', ''),
                "duration": float(format_info.get('duration', 0)),
                "size": format_info.get('size', 0),
                "bitrate": format_info.get('bit_rate', 0)
            }
            
        except Exception as e:
            print(f"Erro ao obter informações do áudio: {str(e)}")
            return {}
