import os
import httpx
import asyncio
import re
from typing import Dict, List, Optional
import json
from deep_translator import GoogleTranslator

class ElevenLabsService:
    """Serviço para transcrição de áudio usando ElevenLabs Speech-to-Text API.
    
    A API da ElevenLabs retorna um formato específico que precisamos adaptar
    para o formato padrão da nossa aplicação.
    """
    
    def __init__(self):
        self.api_key = os.getenv("ELEVENLABS_API_KEY")
        if not self.api_key:
            raise ValueError("ELEVENLABS_API_KEY não foi configurada nas variáveis de ambiente")
        
        self.base_url = "https://api.elevenlabs.io/v1"
        self.headers = {
            "xi-api-key": self.api_key
        }
    
    async def transcribe_audio(self, file_path: str, language_code: Optional[str] = None, model_id: Optional[str] = None, translate_to: Optional[str] = None) -> Optional[Dict]:
        """
        Transcreve um arquivo de áudio usando a API da ElevenLabs.
        
        Args:
            file_path: Caminho do arquivo de áudio
            language_code: Código do idioma (ISO-639-1 ou ISO-639-3)
            model_id: ID do modelo a ser utilizado (scribe_v1 ou scribe_v1_experimental)
            translate_to: Código do idioma para tradução (ex: "pt", "en", "es")
            
        Returns:
            Resultado da transcrição no formato padronizado
        """
        try:
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"Arquivo não encontrado: {file_path}")
            
            # Preparar dados para o request
            data = {
                "model_id": model_id or "scribe_v1",  # Usar modelo especificado ou padrão
                "timestamps_granularity": "word",
                "tag_audio_events": True,
                "diarize": False
            }
            
            if language_code:
                data["language_code"] = language_code
            
            # Fazer upload do arquivo
            async with httpx.AsyncClient(timeout=300.0) as client:
                with open(file_path, "rb") as audio_file:
                    files = {"file": audio_file}
                    
                    response = await client.post(
                        f"{self.base_url}/speech-to-text",
                        headers=self.headers,
                        data=data,
                        files=files
                    )
                    
                    response.raise_for_status()
                    result = response.json()
            
            # Converter para o formato padronizado
            result = self._convert_to_standard_format(result, file_path)
            
            # Aplicar tradução se solicitada
            if translate_to and self._is_valid_language_code(translate_to):
                result = await self._translate_segments(result, translate_to)
            
            return result
            
        except httpx.HTTPStatusError as e:
            error_detail = f"Erro na API ElevenLabs: {e.response.status_code}"
            if e.response.content:
                try:
                    error_data = json.loads(e.response.content)
                    error_detail += f" - {error_data.get('detail', 'Erro desconhecido')}"
                except:
                    pass
            raise Exception(error_detail)
        except Exception as e:
            raise Exception(f"Erro na transcrição ElevenLabs: {str(e)}")
    
    def _convert_to_standard_format(self, elevenlabs_result: Dict, file_path: str) -> Dict:
        """
        Converte o resultado da ElevenLabs para o formato padrão da aplicação.
        
        Args:
            elevenlabs_result: Resultado original da API ElevenLabs
            file_path: Caminho do arquivo de áudio (para calcular duração)
            
        Returns:
            Resultado no formato padronizado
        """
        try:
            # Processar palavras em segmentos
            segments = self._words_to_segments(elevenlabs_result.get("words", []))
            
            # Calcular duração do arquivo
            file_duration = self._calculate_file_duration(elevenlabs_result.get("words", []))
            
            return {
                "language": self._normalize_language_code(elevenlabs_result.get("language_code", "unknown")),
                "language_probability": elevenlabs_result.get("language_probability", 0.0),
                "segments": segments,
                "file_duration": file_duration,
                "text": elevenlabs_result.get("text", ""),
                "provider": "elevenlabs"
            }
            
        except Exception as e:
            raise Exception(f"Erro ao converter resultado ElevenLabs: {str(e)}")
    
    def _words_to_segments(self, words: List[Dict]) -> List[Dict]:
        """
        Converte a lista de palavras em segmentos de texto.
        Agrupa palavras próximas em segmentos menores e mais manejáveis.
        """
        if not words:
            return []
        
        segments = []
        current_segment = {
            "start": 0,
            "end": 0,
            "text": "",
            "words": []
        }
        
        segment_max_duration = 5.0  # Máximo de 5 segundos por segmento
        segment_max_words = 15      # Máximo de 15 palavras por segmento
        
        for word in words:
            # Filtrar apenas palavras (não espaços)
            if word.get("type") != "word":
                continue
            
            word_start = word.get("start", 0)
            word_end = word.get("end", 0)
            word_text = word.get("text", "")
            
            # Inicializar primeiro segmento
            if not current_segment["words"]:
                current_segment["start"] = word_start
                current_segment["end"] = word_end
                current_segment["text"] = word_text
                current_segment["words"].append(word)
                continue
            
            # Verificar se deve iniciar novo segmento (por duração OU número de palavras)
            segment_duration = word_end - current_segment["start"]
            should_split = (
                (segment_duration > segment_max_duration and current_segment["words"]) or
                (len(current_segment["words"]) >= segment_max_words)
            )
            
            if should_split:
                # Finalizar segmento atual
                segments.append({
                    "start": current_segment["start"],
                    "end": current_segment["end"],
                    "text": current_segment["text"].strip()
                })
                
                # Iniciar novo segmento
                current_segment = {
                    "start": word_start,
                    "end": word_end,
                    "text": word_text,
                    "words": [word]
                }
            else:
                # Adicionar palavra ao segmento atual (com espaço)
                current_segment["end"] = word_end
                current_segment["text"] += " " + word_text
                current_segment["words"].append(word)
        
        # Adicionar último segmento
        if current_segment["words"]:
            segments.append({
                "start": current_segment["start"],
                "end": current_segment["end"],
                "text": current_segment["text"].strip()
            })
        
        # Pós-processamento: dividir segmentos muito longos com base na pontuação
        segments = self._split_long_segments_by_punctuation(segments)
        
        return segments
    
    def _split_long_segments_by_punctuation(self, segments: List[Dict]) -> List[Dict]:
        """
        Divide segmentos muito longos usando pontuação como critério de quebra.
        """
        refined_segments = []
        max_text_length = 100  # Máximo de caracteres por segmento
        
        for segment in segments:
            text = segment["text"]
            
            # Se o segmento não é muito longo, manter como está
            if len(text) <= max_text_length:
                refined_segments.append(segment)
                continue
            
            # Tentar dividir por pontuação
            sentences = self._split_by_punctuation(text)
            if len(sentences) <= 1:
                # Não conseguiu dividir, manter como está
                refined_segments.append(segment)
                continue
            
            # Dividir proporcionalmente o tempo entre as sentenças
            segment_duration = segment["end"] - segment["start"]
            total_chars = len(text)
            current_time = segment["start"]
            
            for i, sentence in enumerate(sentences):
                sentence = sentence.strip()
                if not sentence:
                    continue
                
                # Calcular duração proporcional baseada no tamanho do texto
                sentence_duration = (len(sentence) / total_chars) * segment_duration
                end_time = current_time + sentence_duration
                
                refined_segments.append({
                    "start": round(current_time, 2),
                    "end": round(end_time, 2),
                    "text": sentence
                })
                
                current_time = end_time
        
        return refined_segments
    
    def _split_by_punctuation(self, text: str) -> List[str]:
        """
        Divide o texto por pontuação (ponto, vírgula, ponto e vírgula, etc).
        """
        import re
        # Dividir por pontos, exclamações, interrogações, vírgulas e ponto-e-vírgula
        sentences = re.split(r'[.!?;,]\s*', text)
        return [s.strip() for s in sentences if s.strip()]
    
    def _calculate_file_duration(self, words: List[Dict]) -> float:
        """Calcula a duração do arquivo baseada nas palavras."""
        if not words:
            return 0.0
        
        # Encontrar o tempo final máximo
        max_end = 0.0
        for word in words:
            word_end = word.get("end", 0)
            if word_end > max_end:
                max_end = word_end
        
        return max_end
    
    def _normalize_language_code(self, language_code: str) -> str:
        """
        Normaliza o código de idioma para o formato ISO 639-1.
        A ElevenLabs pode retornar códigos ISO 639-3, mas queremos padronizar para ISO 639-1.
        """
        # Mapeamento de códigos ISO 639-3 para ISO 639-1 mais comuns
        lang_mapping = {
            "eng": "en",
            "por": "pt", 
            "spa": "es",
            "fra": "fr",
            "deu": "de",
            "ita": "it",
            "jpn": "ja",
            "kor": "ko",
            "zho": "zh",
            "rus": "ru",
            "ara": "ar",
            "hin": "hi"
        }
        
        # Se já é ISO 639-1 (2 caracteres), retornar como está
        if len(language_code) == 2:
            return language_code.lower()
        
        # Se é ISO 639-3 (3 caracteres), tentar mapear
        if len(language_code) == 3:
            return lang_mapping.get(language_code.lower(), language_code.lower())
        
        return language_code.lower()
    
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
            if not self._is_valid_language_code(target_language):
                print(f"Código de idioma não suportado para tradução: {target_language}")
                return transcription_result
            
            # Criar instância do tradutor
            translator = GoogleTranslator(source='auto', target=target_language.lower())
            
            # Traduzir segmentos em lotes
            segments = transcription_result.get("segments", [])
            if segments:
                translated_segments = await self._translate_segments_batch(translator, segments)
                transcription_result["segments"] = translated_segments
                transcription_result["translated_to"] = target_language.lower()
            
            return transcription_result
            
        except Exception as e:
            print(f"Erro na tradução: {str(e)}")
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
            batch_size = 10  # Processar 10 segmentos por vez
            translated_segments = []
            
            for i in range(0, len(segments), batch_size):
                batch = segments[i:i + batch_size]
                
                # Executar tradução em thread separada para não bloquear
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
            translated_segments = []
            
            for segment in segments:
                try:
                    original_text = segment["text"].strip()
                    if original_text:
                        translated_text = translator.translate(original_text)
                        segment["translated_text"] = translated_text
                    else:
                        segment["translated_text"] = original_text
                except Exception as e:
                    print(f"Erro ao traduzir segmento '{segment['text']}': {str(e)}")
                    segment["translated_text"] = segment["text"]  # Manter texto original em caso de erro
                
                translated_segments.append(segment)
            
            return translated_segments
            
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
    
    def get_supported_models(self) -> List[str]:
        """Retorna lista de modelos suportados pela ElevenLabs."""
        return ["scribe_v1", "scribe_v1_experimental"]
    
    def is_api_key_valid(self) -> bool:
        """Verifica se a API key está configurada."""
        return bool(self.api_key and self.api_key != "your_elevenlabs_api_key_here")
