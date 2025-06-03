import pytest
import os
import tempfile
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

class TestTranscribeAPI:
    """Testes para a rota de transcrição de áudio."""
    
    @pytest.fixture
    def temp_audio_file(self):
        """Cria um arquivo de áudio temporário para testes."""
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as temp_file:
            temp_file.write(b"fake audio data")
            yield temp_file.name
        
        try:
            os.unlink(temp_file.name)
        except:
            pass
    
    @pytest.fixture
    def temp_invalid_file(self):
        """Cria um arquivo inválido para testes."""
        with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as temp_file:
            temp_file.write(b"not audio data")
            yield temp_file.name
        
        try:
            os.unlink(temp_file.name)
        except:
            pass
    
    def test_transcribe_missing_file_path(self):
        """Testa transcrição sem file_path."""
        response = client.post("/api/v1/transcribe", json={})
        
        assert response.status_code == 422  # Validation error
    
    def test_transcribe_empty_file_path(self):
        """Testa transcrição com file_path vazio."""
        response = client.post("/api/v1/transcribe", json={"file_path": ""})
        
        assert response.status_code == 404
        data = response.json()
        assert "Arquivo de áudio não encontrado" in data["detail"]
    
    def test_transcribe_nonexistent_file(self):
        """Testa transcrição com arquivo inexistente."""
        response = client.post("/api/v1/transcribe", json={
            "file_path": "/nonexistent/file.mp3"
        })
        
        assert response.status_code == 404
        data = response.json()
        assert "Arquivo de áudio não encontrado" in data["detail"]
    
    def test_transcribe_invalid_file_format(self, temp_invalid_file):
        """Testa transcrição com formato de arquivo inválido."""
        response = client.post("/api/v1/transcribe", json={
            "file_path": temp_invalid_file
        })
        
        assert response.status_code == 400
        data = response.json()
        assert "Formato de arquivo não suportado" in data["detail"]
    
    def test_transcribe_valid_file_formats(self):
        """Testa formatos de arquivo válidos."""
        valid_formats = [".mp3", ".wav", ".m4a", ".flac", ".ogg"]
        
        for ext in valid_formats:
            response = client.post("/api/v1/transcribe", json={
                "file_path": f"/fake/file{ext}"
            })
            
            # Deve retornar 404 (arquivo não existe) não 400 (formato inválido)
            assert response.status_code == 404
    
    def test_transcribe_without_translation(self, temp_audio_file):
        """Testa transcrição sem tradução."""
        # Renomear arquivo temporário para ter extensão válida
        mp3_file = temp_audio_file.replace('.mp3', '') + '.mp3'
        os.rename(temp_audio_file, mp3_file)
        
        response = client.post("/api/v1/transcribe", json={
            "file_path": mp3_file
        })
        
        # Como é um arquivo fake, provavelmente retornará erro de processamento
        # Mas não deve ser erro de formato ou arquivo não encontrado
        assert response.status_code not in [400, 404]
        
        # Limpar arquivo
        try:
            os.unlink(mp3_file)
        except:
            pass
    
    def test_transcribe_with_translation(self):
        """Testa transcrição com tradução."""
        response = client.post("/api/v1/transcribe", json={
            "file_path": "/fake/file.mp3",
            "translate_to": "pt"
        })
        
        # Deve retornar 404 (arquivo não existe)
        assert response.status_code == 404
    
    def test_transcribe_valid_language_codes(self):
        """Testa códigos de idioma válidos para tradução."""
        valid_languages = ["pt", "en", "es", "fr", "de", "it", "ja", "ko"]
        
        for lang in valid_languages:
            response = client.post("/api/v1/transcribe", json={
                "file_path": "/fake/file.mp3",
                "translate_to": lang
            })
            
            # Deve retornar 404 (arquivo não existe) não erro de idioma
            assert response.status_code == 404
    
    def test_transcribe_invalid_language_code(self):
        """Testa código de idioma inválido."""
        response = client.post("/api/v1/transcribe", json={
            "file_path": "/fake/file.mp3",
            "translate_to": "invalid_lang"
        })
        
        # Pode retornar 404 (arquivo não existe) ou processar normalmente
        # Idiomas inválidos são tratados pelo serviço, não pela API
        assert response.status_code in [404, 500]
    
    def test_transcribe_response_structure_without_translation(self):
        """Testa estrutura da resposta sem tradução."""
        response = client.post("/api/v1/transcribe", json={
            "file_path": "/fake/file.mp3"
        })
        
        assert response.headers["content-type"] == "application/json"
        data = response.json()
        assert isinstance(data, dict)
        
        if response.status_code == 200:
            required_fields = ["language", "segments", "file_duration"]
            for field in required_fields:
                assert field in data
            
            assert data["translated_to"] is None
            assert isinstance(data["segments"], list)
            
            # Verificar estrutura dos segmentos
            if data["segments"]:
                segment = data["segments"][0]
                assert "start" in segment
                assert "end" in segment
                assert "text" in segment
                assert segment.get("translated_text") is None
        else:
            assert "detail" in data
    
    def test_transcribe_response_structure_with_translation(self):
        """Testa estrutura da resposta com tradução."""
        response = client.post("/api/v1/transcribe", json={
            "file_path": "/fake/file.mp3",
            "translate_to": "pt"
        })
        
        assert response.headers["content-type"] == "application/json"
        data = response.json()
        assert isinstance(data, dict)
        
        if response.status_code == 200:
            required_fields = ["language", "translated_to", "segments", "file_duration"]
            for field in required_fields:
                assert field in data
            
            assert data["translated_to"] == "pt"
            assert isinstance(data["segments"], list)
            
            # Verificar estrutura dos segmentos com tradução
            if data["segments"]:
                segment = data["segments"][0]
                assert "start" in segment
                assert "end" in segment
                assert "text" in segment
                assert "translated_text" in segment
        else:
            assert "detail" in data
    
    def test_transcribe_malformed_json(self):
        """Testa transcrição com JSON malformado."""
        response = client.post(
            "/api/v1/transcribe",
            data="{'file_path': '/fake/file.mp3'}",  # JSON inválido
            headers={"content-type": "application/json"}
        )
        
        assert response.status_code == 422
    
    def test_transcribe_extra_fields(self):
        """Testa transcrição com campos extras."""
        response = client.post("/api/v1/transcribe", json={
            "file_path": "/fake/file.mp3",
            "translate_to": "pt",
            "extra_field": "should_be_ignored",
            "model": "large"  # Campo não usado
        })
        
        # Campos extras devem ser ignorados
        assert response.status_code == 404  # Por causa do arquivo fake
    
    def test_transcribe_none_translation(self):
        """Testa transcrição com translate_to explicitamente None."""
        response = client.post("/api/v1/transcribe", json={
            "file_path": "/fake/file.mp3",
            "translate_to": None
        })
        
        assert response.status_code == 404
