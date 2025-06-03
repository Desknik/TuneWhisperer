import pytest
import os
import tempfile
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

class TestDownloadAPI:
    """Testes para a rota de download de áudio."""
    
    @pytest.fixture
    def cleanup_downloads(self):
        """Fixture para limpar arquivos de download após testes."""
        yield
        # Limpar arquivos de teste após execução
        downloads_dir = os.getenv("DOWNLOADS_DIR", "./downloads")
        if os.path.exists(downloads_dir):
            for file in os.listdir(downloads_dir):
                if file.startswith("test_") or file.endswith("_test.mp3"):
                    try:
                        os.remove(os.path.join(downloads_dir, file))
                    except:
                        pass
    
    def test_download_missing_video_id(self):
        """Testa download sem video_id."""
        response = client.post("/api/v1/download", json={})
        
        assert response.status_code == 422  # Validation error
    
    def test_download_empty_video_id(self):
        """Testa download com video_id vazio."""
        response = client.post("/api/v1/download", json={"video_id": ""})
        
        assert response.status_code == 400
        data = response.json()
        assert "video_id é obrigatório" in data["detail"]
    
    def test_download_whitespace_video_id(self):
        """Testa download com video_id apenas com espaços."""
        response = client.post("/api/v1/download", json={"video_id": "   "})
        
        assert response.status_code == 400
        data = response.json()
        assert "video_id é obrigatório" in data["detail"]
    
    def test_download_invalid_video_id(self):
        """Testa download com video_id inválido."""
        response = client.post("/api/v1/download", json={"video_id": "invalid_id_123"})
        
        # Pode retornar 404 (não encontrado) ou 500 (erro no download)
        assert response.status_code in [404, 500]
    
    def test_download_valid_video_id_format(self):
        """Testa formato de resposta com video_id válido (mock)."""
        # Este teste assumirá que temos um video_id válido conhecido
        # Em ambiente de teste real, você pode usar um video_id de teste
        test_video_id = "dQw4w9WgXcQ"  # Video famoso para teste
        
        response = client.post("/api/v1/download", json={"video_id": test_video_id})
        
        # Em ambiente de teste, pode falhar devido à rede ou restrições
        # Verificamos apenas que não é erro de validação
        assert response.status_code != 422
        
        if response.status_code == 200:
            data = response.json()
            assert "file_path" in data
            assert "title" in data
            assert "duration" in data
            assert isinstance(data["file_path"], str)
            assert isinstance(data["title"], str)
            assert isinstance(data["duration"], str)
    
    def test_download_response_structure(self):
        """Testa estrutura da resposta de download."""
        # Usar um video_id fictício para testar estrutura de erro
        response = client.post("/api/v1/download", json={"video_id": "test123"})
        
        # Independentemente do resultado, deve ter estrutura JSON válida
        assert response.headers["content-type"] == "application/json"
        data = response.json()
        assert isinstance(data, dict)
        
        if response.status_code == 200:
            # Estrutura de sucesso
            required_fields = ["file_path", "title", "duration"]
            for field in required_fields:
                assert field in data
        else:
            # Estrutura de erro
            assert "detail" in data
    
    def test_download_malformed_json(self):
        """Testa download com JSON malformado."""
        response = client.post(
            "/api/v1/download", 
            content=b"{'video_id': 'test'}",  # JSON inválido
            headers={"content-type": "application/json"}
        )
        
        assert response.status_code == 422
    
    def test_download_wrong_content_type(self):
        """Testa download com content-type incorreto."""
        response = client.post(
            "/api/v1/download",
            content=b"video_id=test",
            headers={"content-type": "application/x-www-form-urlencoded"}
        )
        
        assert response.status_code == 422
    
    def test_download_extra_fields(self):
        """Testa download com campos extras no JSON."""
        response = client.post("/api/v1/download", json={
            "video_id": "test123",
            "extra_field": "should_be_ignored",
            "another_field": 123
        })
        
        # Campos extras devem ser ignorados
        assert response.status_code != 422
    
    def test_download_very_long_video_id(self):
        """Testa download com video_id muito longo."""
        long_id = "a" * 1000
        response = client.post("/api/v1/download", json={"video_id": long_id})
        
        # Deve retornar erro (não encontrado ou erro de validação)
        assert response.status_code in [400, 404, 500]
    
    def test_download_special_characters_video_id(self):
        """Testa download com caracteres especiais no video_id."""
        special_id = "test@#$%^&*()"
        response = client.post("/api/v1/download", json={"video_id": special_id})
        
        # Deve retornar erro graciosamente
        assert response.status_code in [400, 404, 500]
        data = response.json()
        assert "detail" in data
