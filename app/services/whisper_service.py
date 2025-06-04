from faster_whisper import WhisperModel
from deep_translator import GoogleTranslator
import asyncio
import os
from typing import Dict, List, Optional

class WhisperService:
    """Serviço para transcrição de áudio usando Faster Whisper e tradução.
    
    Parâmetros:
        model_size (str): Tamanho do modelo Whisper a ser utilizado. Pode ser: 'tiny', 'base', 'small', 'medium', 'large'.
        Por padrão, utiliza 'base'.
    
    Exemplo de uso:
        ws = WhisperService(model_size="small")
    """
    
    def __init__(self, model_size: str = "base"):
        self.model = None
        self.model_size = model_size  # Pode ser: tiny, base, small, medium, large
        self._load_model()
    
    def _load_model(self):
        """Carrega o modelo Whisper."""
        try:
            # Usar CPU para compatibilidade máxima
            self.model = WhisperModel(self.model_size, device="cpu", compute_type="int8")
            print(f"Modelo Whisper '{self.model_size}' carregado com sucesso")
        except Exception as e:
            print(f"Erro ao carregar modelo Whisper: {str(e)}")
            self.model = None
    
    async def transcribe_audio(self, file_path: str, translate_to: Optional[str] = None, force_language: Optional[str] = None) -> Optional[Dict]:
        """
        Transcreve um arquivo de áudio com timestamps e opcionalmente traduz.
        
        Args:
            file_path: Caminho do arquivo de áudio
            translate_to: Código do idioma para tradução (ex: "pt", "en", "es")
            
        Returns:
            Resultado da transcrição com segmentos e traduções
        """
        try:
            if not self.model:
                raise Exception("Modelo Whisper não está carregado")
            
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"Arquivo não encontrado: {file_path}")
            
            # Executar transcrição em thread separada
            loop = asyncio.get_event_loop()
            transcription_result = await loop.run_in_executor(
                None,
                self._transcribe_with_whisper,
                file_path,
                force_language
            )
            
            if not transcription_result:
                return None
            
            # Aplicar tradução se solicitada
            if translate_to:
                transcription_result = await self._translate_segments(
                    transcription_result, 
                    translate_to
                )
            
            return transcription_result
            
        except Exception as e:
            print(f"Erro na transcrição: {str(e)}")
            return None
    
    def _transcribe_with_whisper(self, file_path: str, force_language: Optional[str] = None) -> Optional[Dict]:
        """
        Executa a transcrição usando Faster Whisper.
        
        Args:
            file_path: Caminho do arquivo de áudio
            force_language: Código do idioma forçado
            
        Returns:
            Resultado da transcrição no formato padronizado
        """
        try:
            # Transcrever com timestamps
            transcribe_kwargs = {
                'beam_size': 5,
                'word_timestamps': True,
                'vad_filter': True,  # Filtro de detecção de atividade de voz
                'vad_parameters': dict(min_silence_duration_ms=500)
            }
            if force_language:
                transcribe_kwargs['language'] = force_language
            segments, info = self.model.transcribe(
                file_path,
                **transcribe_kwargs
            )
            
            # Processar segmentos
            processed_segments = []
            for segment in segments:
                processed_segment = {
                    "start": round(segment.start, 2),
                    "end": round(segment.end, 2),
                    "text": segment.text.strip()
                }
                processed_segments.append(processed_segment)
            
            # Calcular duração total do arquivo
            file_duration = 0.0
            if processed_segments:
                file_duration = processed_segments[-1]["end"]
                
            # Criar texto completo
            full_text = " ".join([seg["text"] for seg in processed_segments])
            
            # Retornar no formato padronizado
            return {
                "language": info.language,
                "language_probability": info.language_probability,
                "segments": processed_segments,
                "file_duration": file_duration,
                "text": full_text,
                "provider": "whisper"
            }
            
        except Exception as e:
            print(f"Erro no Whisper: {str(e)}")
            return None
    
    async def _translate_segments(self, transcription_result: Dict, target_language: str) -> Dict:
        """
        Traduz os segmentos transcritos.
        
        Args:
            transcription_result: Resultado da transcrição
            target_language: Idioma de destino
            
        Returns:
            Resultado com traduções adicionadas
        """
        try:
            # Validar idioma de destino
            if not self._is_valid_language_code(target_language):
                print(f"Código de idioma inválido: {target_language}")
                return transcription_result
            
            source_language = transcription_result.get("language", "auto")
            
            # Se o idioma de origem é o mesmo que o de destino, não traduzir
            if source_language == target_language:
                print("Idioma de origem é o mesmo que o de destino")
                return transcription_result
            
            # Inicializar tradutor
            translator = GoogleTranslator(source=source_language, target=target_language)
            
            # Traduzir segmentos em lotes para eficiência
            segments = transcription_result.get("segments", [])
            translated_segments = await self._translate_segments_batch(translator, segments)
            
            # Atualizar resultado
            transcription_result["segments"] = translated_segments
            transcription_result["translated_to"] = target_language
            
            return transcription_result
            
        except Exception as e:
            print(f"Erro na tradução: {str(e)}")
            # Retornar resultado original sem tradução em caso de erro
            return transcription_result
    
    async def _translate_segments_batch(self, translator: GoogleTranslator, segments: List[Dict]) -> List[Dict]:
        """
        Traduz segmentos em lotes para melhor performance.
        
        Args:
            translator: Instância do tradutor
            segments: Lista de segmentos para traduzir
            
        Returns:
            Segmentos com traduções
        """
        try:
            # Processar em lotes de 10 segmentos
            batch_size = 10
            translated_segments = []
            
            for i in range(0, len(segments), batch_size):
                batch = segments[i:i + batch_size]
                
                # Traduzir lote atual
                loop = asyncio.get_event_loop()
                translated_batch = await loop.run_in_executor(
                    None,
                    self._translate_batch_sync,
                    translator,
                    batch
                )
                
                translated_segments.extend(translated_batch)
            
            return translated_segments
            
        except Exception as e:
            print(f"Erro na tradução em lote: {str(e)}")
            return segments
    
    def _translate_batch_sync(self, translator: GoogleTranslator, segments: List[Dict]) -> List[Dict]:
        """
        Traduz um lote de segmentos sincronamente.
        
        Args:
            translator: Instância do tradutor
            segments: Lote de segmentos
            
        Returns:
            Segmentos traduzidos
        """
        try:
            for segment in segments:
                text = segment.get("text", "").strip()
                
                if text:
                    try:
                        translated_text = translator.translate(text)
                        segment["translated_text"] = translated_text
                    except Exception as e:
                        print(f"Erro ao traduzir segmento '{text}': {str(e)}")
                        segment["translated_text"] = text  # Usar texto original em caso de erro
                else:
                    segment["translated_text"] = text
            
            return segments
            
        except Exception as e:
            print(f"Erro na tradução síncrona: {str(e)}")
            return segments
    
    def _is_valid_language_code(self, language_code: str) -> bool:
        """
        Valida se o código de idioma é suportado.
        
        Args:
            language_code: Código do idioma (ex: "pt", "en", "es")
            
        Returns:
            True se válido, False caso contrário
        """
        # Códigos de idioma mais comuns suportados pelo Google Translate
        supported_languages = {
            'pt', 'en', 'es', 'fr', 'de', 'it', 'ja', 'ko', 'zh', 'ru',
            'ar', 'hi', 'th', 'vi', 'tr', 'pl', 'nl', 'sv', 'no', 'da',
            'fi', 'cs', 'sk', 'hu', 'ro', 'bg', 'hr', 'sl', 'et', 'lv',
            'lt', 'mt', 'ga', 'cy', 'eu', 'ca', 'gl', 'is', 'mk', 'sq',
            'sr', 'bs', 'me', 'uz', 'kk', 'ky', 'tg', 'mn', 'my', 'km',
            'lo', 'ka', 'am', 'ne', 'si', 'bn', 'gu', 'ta', 'te', 'kn',
            'ml', 'ur', 'fa', 'ps', 'sw', 'zu', 'af', 'sq', 'be', 'bg'
        }
        
        return language_code.lower() in supported_languages
    
    def get_supported_languages(self) -> List[str]:
        """
        Retorna lista de códigos de idiomas suportados para tradução.
        
        Returns:
            Lista de códigos de idiomas
        """
        return [
            'pt', 'en', 'es', 'fr', 'de', 'it', 'ja', 'ko', 'zh', 'ru',
            'ar', 'hi', 'th', 'vi', 'tr', 'pl', 'nl', 'sv', 'no', 'da'
        ]
