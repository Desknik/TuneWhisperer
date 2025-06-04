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
        Agrupa palavras próximas em frases completas, priorizando pontuação final.
        """
        if not words:
            return []

        segments = []
        current_segment = {
            "start": None,
            "end": None,
            "text": "",
            "words": []
        }

        segment_max_duration = 8.0  # Permite frases maiores se necessário
        segment_max_words = 25      # Permite mais palavras por segmento
        segment_max_chars = 120     # Limite de caracteres por segmento

        def is_sentence_end(word_text):
            return word_text.strip().endswith(('.', '?', '!'))

        for word in words:
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

            # Adicionar palavra ao segmento atual
            current_segment["end"] = word_end
            current_segment["text"] += " " + word_text
            current_segment["words"].append(word)

            # Critérios para cortar segmento:
            # 1. Chegou ao fim de frase (pontuação final) E já tem pelo menos 4 palavras
            # 2. Excedeu o número máximo de palavras
            # 3. Excedeu o tamanho máximo de caracteres
            # 4. Excedeu a duração máxima

            segment_duration = current_segment["end"] - current_segment["start"]
            should_split = False

            if is_sentence_end(word_text) and len(current_segment["words"]) >= 4:
                should_split = True
            elif len(current_segment["words"]) >= segment_max_words:
                should_split = True
            elif len(current_segment["text"]) >= segment_max_chars:
                should_split = True
            elif segment_duration > segment_max_duration:
                should_split = True

            if should_split:
                segments.append({
                    "start": current_segment["start"],
                    "end": current_segment["end"],
                    "text": current_segment["text"].strip()
                })
                current_segment = {
                    "start": None,
                    "end": None,
                    "text": "",
                    "words": []
                }

        # Adicionar último segmento se houver
        if current_segment["words"]:
            segments.append({
                "start": current_segment["start"],
                "end": current_segment["end"],
                "text": current_segment["text"].strip()
            })

        # Não aplicar mais divisões por pontuação aqui, pois já priorizamos frases completas
        # Se algum segmento ainda for muito longo, dividir por pontuação secundária
        segments = self._split_very_long_segments(segments)

        return segments

    def _split_very_long_segments(self, segments: List[Dict]) -> List[Dict]:
        """
        Divide segmentos muito longos usando pontuação secundária ou tamanho de palavra.
        Só é chamado se o segmento ultrapassar um limite alto de caracteres.
        """
        refined_segments = []
        max_text_length = 160  # Só divide se for muito longo

        for segment in segments:
            text = segment["text"]
            if len(text) <= max_text_length:
                refined_segments.append(segment)
                continue

            # Tenta dividir por pontuação principal
            sentences = self._split_by_punctuation(text)
            if len(sentences) > 1:
                # Dividir tempo proporcionalmente
                segment_duration = segment["end"] - segment["start"]
                total_chars = len(text)
                current_time = segment["start"]
                for sentence in sentences:
                    sentence = sentence.strip()
                    if not sentence:
                        continue
                    sentence_duration = (len(sentence) / total_chars) * segment_duration
                    end_time = current_time + sentence_duration
                    refined_segments.append({
                        "start": round(current_time, 2),
                        "end": round(end_time, 2),
                        "text": sentence
                    })
                    current_time = end_time
                continue

            # Se não conseguiu dividir, tenta por vírgulas, ponto e vírgula, etc.
            sentences = self._split_by_secondary_punctuation(text)
            if len(sentences) > 1:
                segment_duration = segment["end"] - segment["start"]
                total_chars = len(text)
                current_time = segment["start"]
                for sentence in sentences:
                    sentence = sentence.strip()
                    if not sentence:
                        continue
                    sentence_duration = (len(sentence) / total_chars) * segment_duration
                    end_time = current_time + sentence_duration
                    refined_segments.append({
                        "start": round(current_time, 2),
                        "end": round(end_time, 2),
                        "text": sentence
                    })
                    current_time = end_time
                continue

            # Se ainda não conseguiu dividir, mantém como está
            refined_segments.append(segment)

        return refined_segments

    def _split_by_punctuation(self, text: str) -> List[str]:
        """
        Divide o texto por pontuação principal (ponto final, exclamação, interrogação).
        """
        import re
        # Dividir por pontos, exclamações, interrogações, mantendo a pontuação
        pattern = r'([.!?])'
        # Primeiro adiciona um espaço após a pontuação, se necessário
        text = re.sub(pattern + r'([^\s])', r'\1 \2', text)
        # Agora divide por pontuação
        segments = re.split(r'[.!?]\s+', text)
        
        # Remover segmentos vazios
        return [s.strip() for s in segments if s.strip()]
    
    def _split_by_secondary_punctuation(self, text: str) -> List[str]:
        """
        Divide o texto por pontuação secundária (vírgulas, ponto e vírgula, etc.)
        quando a pontuação principal não é suficiente.
        """
        import re
        # Dividir por vírgulas, ponto e vírgula, dois-pontos
        segments = re.split(r'[,;:]\s*', text)
        
        # Limitar tamanho dos segmentos
        max_segment_length = 60
        result = []
        
        for segment in segments:
            segment = segment.strip()
            if not segment:
                continue
                
            # Se o segmento ainda é muito longo, dividir por espaços
            if len(segment) > max_segment_length:
                words = segment.split()
                current_segment = []
                current_length = 0
                
                for word in words:
                    if current_length + len(word) + 1 > max_segment_length and current_segment:
                        result.append(" ".join(current_segment))
                        current_segment = [word]
                        current_length = len(word)
                    else:
                        current_segment.append(word)
                        current_length += len(word) + 1
                
                if current_segment:
                    result.append(" ".join(current_segment))
            else:
                result.append(segment)
        
        return result

    def _refine_segments_semantically(self, segments: List[Dict]) -> List[Dict]:
        """
        Refina os segmentos para garantir coerência semântica.
        Evita quebrar no meio de frases ou expressões comuns.
        """
        # Se houver poucos segmentos, não precisa refinar
        if len(segments) <= 1:
            return segments
            
        refined = []
        
        for segment in segments:
            text = segment["text"].strip()
            
            # Verificar se o segmento é muito longo (mais de 100 caracteres)
            if len(text) > 100:
                # Tentar dividir semanticamente
                parts = self._smart_text_split(text)
                if len(parts) > 1:
                    # Dividir o tempo proporcionalmente
                    segment_duration = segment["end"] - segment["start"]
                    total_chars = len(text)
                    current_time = segment["start"]
                    
                    for part in parts:
                        part = part.strip()
                        if not part:
                            continue
                        
                        part_duration = (len(part) / total_chars) * segment_duration
                        end_time = current_time + part_duration
                        
                        refined.append({
                            "start": round(current_time, 2),
                            "end": round(end_time, 2),
                            "text": part
                        })
                        
                        current_time = end_time
                    continue
            
            # Se não precisou dividir, manter como está
            refined.append(segment)
        
        return refined
    
    def _smart_text_split(self, text: str) -> List[str]:
        """
        Divide o texto de forma inteligente, considerando estruturas linguísticas.
        """
        # Primeiro tenta dividir por pontuação
        parts = self._split_by_punctuation(text)
        if len(parts) > 1:
            return parts
        
        # Depois tenta por vírgulas e ponto-e-vírgula
        parts = self._split_by_secondary_punctuation(text)
        if len(parts) > 1:
            return parts
        
        # Se ainda não conseguiu dividir e o texto é longo, força divisão
        if len(text) > 80:
            words = text.split()
            mid = len(words) // 2
            
            # Busca o melhor ponto de divisão próximo ao meio
            best_split = mid
            for i in range(max(0, mid - 3), min(len(words), mid + 3)):
                # Evita dividir entre palavras que normalmente vão juntas
                # como artigos e substantivos, preposições e seus objetos
                if i < len(words) - 1:
                    curr_word = words[i].lower()
                    next_word = words[i + 1].lower()
                    
                    # Evitar dividir após artigos, preposições, etc.
                    avoid_split_after = {'a', 'an', 'the', 'to', 'in', 'on', 'of', 'for', 'with',
                                         'um', 'uma', 'o', 'a', 'os', 'as', 'de', 'para', 'com', 'em'}
                    if curr_word in avoid_split_after:
                        continue
                    
                    best_split = i + 1
                    break
            
            return [" ".join(words[:best_split]), " ".join(words[best_split:])]
        
        return [text]

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
