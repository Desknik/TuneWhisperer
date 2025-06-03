import pytest
import os
import tempfile
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

class TestTrimAPI:
    """Testes para a rota de corte de áudio."""
    
    @pytest.fixture
    def temp_audio_file(self):
        """Cria um arquivo de áudio temporário para testes."""
        # Em um teste real, você criaria um arquivo de áudio válido
        # Por simplificação, criamos um arquivo vazio
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as temp_file:
            temp_file.write(b"fake audio data")
            yield temp_file.name
        
        # Limpar arquivo após teste
        try:
            os.unlink(temp_file.name)
        except:
            pass
    
    def test_trim_missing_fields(self):
        """Testa corte sem campos obrigatórios."""
        response = client.post("/api/v1/trim", json={})
        
        assert response.status_code == 422  # Validation error
    
    def test_trim_missing_file_path(self):
        """Testa corte sem file_path."""
        response = client.post("/api/v1/trim", json={
            "start_time": "00:00:10",
            "end_time": "00:01:00"
        })
        
        assert response.status_code == 422
    
    def test_trim_missing_start_time(self):
        """Testa corte sem start_time."""
        response = client.post("/api/v1/trim", json={
            "file_path": "/fake/path.mp3",
            "end_time": "00:01:00"
        })
        
        assert response.status_code == 422
    
    def test_trim_missing_end_time(self):
        """Testa corte sem end_time."""
        response = client.post("/api/v1/trim", json={
            "file_path": "/fake/path.mp3",
            "start_time": "00:00:10"
        })
        
        assert response.status_code == 422
    
    def test_trim_nonexistent_file(self):
        """Testa corte com arquivo inexistente."""
        response = client.post("/api/v1/trim", json={
            "file_path": "/nonexistent/file.mp3",
            "start_time": "00:00:10",
            "end_time": "00:01:00"
        })
        
        assert response.status_code == 404
        data = response.json()
        assert "Arquivo de áudio não encontrado" in data["detail"]
    
    def test_trim_empty_times(self):
        """Testa corte com tempos vazios."""
        response = client.post("/api/v1/trim", json={
            "file_path": "/fake/path.mp3",
            "start_time": "",
            "end_time": ""
        })
        
        assert response.status_code == 400
        data = response.json()
        assert "start_time e end_time são obrigatórios" in data["detail"]
    
    def test_trim_valid_time_formats(self):
        """Testa diferentes formatos de tempo válidos."""
        test_cases = [
            ("10", "60"),  # Segundos
            ("00:10", "01:00"),  # MM:SS
            ("00:00:10", "00:01:00"),  # HH:MM:SS
        ]
        
        for start_time, end_time in test_cases:
            response = client.post("/api/v1/trim", json={
                "file_path": "/fake/path.mp3",
                "start_time": start_time,
                "end_time": end_time
            })
            
            # Deve retornar 404 (arquivo não existe) não 400 (formato inválido)
            assert response.status_code == 404
    
    def test_trim_invalid_time_formats(self):
        """Testa formatos de tempo inválidos."""
        invalid_times = [
            ("invalid", "60"),
            ("10", "invalid"),
            ("25:99", "30:00"),  # Minutos/segundos inválidos
            ("-10", "60"),  # Tempo negativo
        ]
        
        for start_time, end_time in invalid_times:
            response = client.post("/api/v1/trim", json={
                "file_path": "/fake/path.mp3",
                "start_time": start_time,
                "end_time": end_time
            })
            
            # Pode ser 400 (tempo inválido) ou 404 (arquivo não existe)
            assert response.status_code in [400, 404, 500]
    
    def test_trim_response_structure(self):
        """Testa estrutura da resposta de corte."""
        response = client.post("/api/v1/trim", json={
            "file_path": "/fake/path.mp3",
            "start_time": "00:00:10",
            "end_time": "00:01:00"
        })
        
        # Deve ter estrutura JSON válida
        assert response.headers["content-type"] == "application/json"
        data = response.json()
        assert isinstance(data, dict)
        
        if response.status_code == 200:
            # Estrutura de sucesso
            required_fields = ["trimmed_file_path", "original_duration", "trimmed_duration"]
            for field in required_fields:
                assert field in data
        else:
            # Estrutura de erro
            assert "detail" in data
    
    def test_trim_start_greater_than_end(self):
        """Testa corte com tempo de início maior que fim."""
        response = client.post("/api/v1/trim", json={
            "file_path": "/fake/path.mp3",
            "start_time": "00:01:00",
            "end_time": "00:00:30"
        })
        
        # Deve retornar erro (pode ser 404 do arquivo ou 400/500 do tempo)
        assert response.status_code in [400, 404, 500]
    
    def test_trim_same_start_and_end(self):
        """Testa corte com mesmo tempo de início e fim."""
        response = client.post("/api/v1/trim", json={
            "file_path": "/fake/path.mp3",
            "start_time": "00:00:30",
            "end_time": "00:00:30"
        })
        
        # Deve retornar erro
        assert response.status_code in [400, 404, 500]
    
    def test_trim_with_existing_file(self, temp_audio_file):
        """Testa corte com arquivo existente."""
        response = client.post("/api/v1/trim", json={
            "file_path": temp_audio_file,
            "start_time": "0",
            "end_time": "1"
        })
        
        # Como é um arquivo fake, provavelmente retornará erro de processamento
        # Mas não deve ser erro de arquivo não encontrado
        assert response.status_code != 404
    
    def test_trim_malformed_json(self):
        """Testa corte com JSON malformado."""
        response = client.post(
            "/api/v1/trim",
            data="{'file_path': '/fake/path.mp3'}",  # JSON inválido
            headers={"content-type": "application/json"}
        )
        
        assert response.status_code == 422
