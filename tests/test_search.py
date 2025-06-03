import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

class TestSearchAPI:
    """Testes para a rota de busca de músicas."""
    
    def test_search_valid_query(self):
        """Testa busca com query válida."""
        response = client.get("/api/v1/search?query=imagine%20dragons&limit=5")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        
        if data:  # Se há resultados
            first_result = data[0]
            assert "title" in first_result
            assert "artist" in first_result
            assert "videoId" in first_result
            assert "thumbnail" in first_result
            assert "colors" in first_result
            assert isinstance(first_result["colors"], list)
    
    def test_search_empty_query(self):
        """Testa busca com query vazia."""
        response = client.get("/api/v1/search?query=")
        
        # Deve retornar erro 422 (validação)
        assert response.status_code == 422
    
    def test_search_no_query(self):
        """Testa busca sem parâmetro query."""
        response = client.get("/api/v1/search")
        
        # Deve retornar erro 422 (parâmetro obrigatório)
        assert response.status_code == 422
    
    def test_search_with_limit(self):
        """Testa busca com limite específico."""
        response = client.get("/api/v1/search?query=beatles&limit=3")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) <= 3
    
    def test_search_limit_boundaries(self):
        """Testa limites mínimos e máximos."""
        # Limite muito baixo
        response = client.get("/api/v1/search?query=test&limit=0")
        assert response.status_code == 422
        
        # Limite muito alto
        response = client.get("/api/v1/search?query=test&limit=100")
        assert response.status_code == 422
        
        # Limites válidos
        response = client.get("/api/v1/search?query=test&limit=1")
        assert response.status_code == 200
        
        response = client.get("/api/v1/search?query=test&limit=50")
        assert response.status_code == 200
    
    def test_search_special_characters(self):
        """Testa busca com caracteres especiais."""
        response = client.get("/api/v1/search?query=caf%C3%A9&limit=5")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    def test_search_very_long_query(self):
        """Testa busca com query muito longa."""
        long_query = "a" * 1000
        response = client.get(f"/api/v1/search?query={long_query}&limit=5")
        
        # Deve funcionar ou retornar erro graciosamente
        assert response.status_code in [200, 400, 500]
    
    def test_search_nonexistent_song(self):
        """Testa busca por música inexistente."""
        response = client.get("/api/v1/search?query=xyznonexistentsong123&limit=5")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        # Pode retornar lista vazia para buscas sem resultado
    
    def test_search_response_structure(self):
        """Testa estrutura da resposta de busca."""
        response = client.get("/api/v1/search?query=music&limit=1")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        
        if data:
            result = data[0]
            required_fields = ["title", "artist", "videoId", "thumbnail", "colors"]
            for field in required_fields:
                assert field in result
            
            # Verificar tipos
            assert isinstance(result["title"], str)
            assert isinstance(result["artist"], str)
            assert isinstance(result["videoId"], str)
            assert isinstance(result["thumbnail"], str)
            assert isinstance(result["colors"], list)
            
            # Verificar se cores são strings hexadecimais válidas
            for color in result["colors"]:
                assert isinstance(color, str)
                assert len(color) == 7  # #RRGGBB
                assert color.startswith("#")
