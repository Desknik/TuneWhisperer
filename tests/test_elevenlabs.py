import pytest
import os
from unittest.mock import Mock, patch, AsyncMock
from app.services.elevenlabs_service import ElevenLabsService

class TestElevenLabsService:
    
    def test_init_without_api_key(self):
        """Testa inicialização sem API key."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="ELEVENLABS_API_KEY não foi configurada"):
                ElevenLabsService()
    
    def test_init_with_api_key(self):
        """Testa inicialização com API key."""
        with patch.dict(os.environ, {"ELEVENLABS_API_KEY": "test_key"}):
            service = ElevenLabsService()
            assert service.api_key == "test_key"
            assert service.base_url == "https://api.elevenlabs.io/v1"
            assert service.headers["xi-api-key"] == "test_key"
    
    def test_is_api_key_valid(self):
        """Testa validação da API key."""
        with patch.dict(os.environ, {"ELEVENLABS_API_KEY": "test_key"}):
            service = ElevenLabsService()
            assert service.is_api_key_valid() is True
        
        with patch.dict(os.environ, {"ELEVENLABS_API_KEY": "your_elevenlabs_api_key_here"}):
            service = ElevenLabsService()
            assert service.is_api_key_valid() is False
    
    def test_normalize_language_code(self):
        """Testa normalização de códigos de idioma."""
        with patch.dict(os.environ, {"ELEVENLABS_API_KEY": "test_key"}):
            service = ElevenLabsService()
            
            # Teste com ISO 639-1 (2 caracteres)
            assert service._normalize_language_code("en") == "en"
            assert service._normalize_language_code("PT") == "pt"
            
            # Teste com ISO 639-3 (3 caracteres)
            assert service._normalize_language_code("eng") == "en"
            assert service._normalize_language_code("por") == "pt"
            assert service._normalize_language_code("spa") == "es"
            
            # Teste com código desconhecido
            assert service._normalize_language_code("xyz") == "xyz"
    
    def test_words_to_segments(self):
        """Testa conversão de palavras para segmentos."""
        with patch.dict(os.environ, {"ELEVENLABS_API_KEY": "test_key"}):
            service = ElevenLabsService()
            
            words = [
                {"type": "word", "text": "Hello", "start": 0.0, "end": 0.5},
                {"type": "spacing", "text": " ", "start": 0.5, "end": 0.5},
                {"type": "word", "text": "world", "start": 0.5, "end": 1.0},
                {"type": "word", "text": "this", "start": 12.0, "end": 12.5},
                {"type": "word", "text": "is", "start": 12.5, "end": 12.7},
                {"type": "word", "text": "test", "start": 12.7, "end": 13.0}
            ]
            
            segments = service._words_to_segments(words)
            
            # Deve criar 2 segmentos (devido ao gap de tempo)
            assert len(segments) == 2
            assert segments[0]["text"] == "Helloworld"
            assert segments[0]["start"] == 0.0
            assert segments[0]["end"] == 1.0
            assert segments[1]["text"] == "thisistest"
            assert segments[1]["start"] == 12.0
            assert segments[1]["end"] == 13.0
    
    def test_calculate_file_duration(self):
        """Testa cálculo da duração do arquivo."""
        with patch.dict(os.environ, {"ELEVENLABS_API_KEY": "test_key"}):
            service = ElevenLabsService()
            
            words = [
                {"end": 1.5},
                {"end": 2.3},
                {"end": 1.0}
            ]
            
            duration = service._calculate_file_duration(words)
            assert duration == 2.3
            
            # Teste com lista vazia
            assert service._calculate_file_duration([]) == 0.0
    
    @pytest.mark.asyncio
    async def test_transcribe_audio_file_not_found(self):
        """Testa transcrição com arquivo inexistente."""
        with patch.dict(os.environ, {"ELEVENLABS_API_KEY": "test_key"}):
            service = ElevenLabsService()
            
            with pytest.raises(Exception, match="Arquivo não encontrado"):
                await service.transcribe_audio("nonexistent.mp3")
    
    def test_convert_to_standard_format(self):
        """Testa conversão para formato padrão."""
        with patch.dict(os.environ, {"ELEVENLABS_API_KEY": "test_key"}):
            service = ElevenLabsService()
            
            elevenlabs_result = {
                "language_code": "eng",
                "language_probability": 0.95,
                "text": "Hello world",
                "words": [
                    {"type": "word", "text": "Hello", "start": 0.0, "end": 0.5},
                    {"type": "word", "text": "world", "start": 0.5, "end": 1.0}
                ]
            }
            
            result = service._convert_to_standard_format(elevenlabs_result, "test.mp3")
            
            assert result["language"] == "en"
            assert result["language_probability"] == 0.95
            assert result["text"] == "Hello world"
            assert result["provider"] == "elevenlabs"
            assert result["file_duration"] == 1.0
            assert len(result["segments"]) == 1
            assert result["segments"][0]["text"] == "Helloworld"
    
    def test_get_supported_models(self):
        """Testa lista de modelos suportados."""
        with patch.dict(os.environ, {"ELEVENLABS_API_KEY": "test_key"}):
            service = ElevenLabsService()
            models = service.get_supported_models()
            assert "scribe_v1" in models
            assert "scribe_v1_experimental" in models
