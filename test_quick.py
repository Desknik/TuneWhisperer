#!/usr/bin/env python3
"""
Script de teste rápido para verificar se a API está funcionando.
Execute com: python test_quick.py
"""

import requests
import json
import time

API_BASE = "http://localhost:8000"

def test_health():
    """Testa o endpoint de health check."""
    try:
        response = requests.get(f"{API_BASE}/health", timeout=5)
        if response.status_code == 200:
            print("✅ Health check: OK")
            return True
        else:
            print(f"❌ Health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Health check error: {e}")
        return False

def test_search():
    """Testa o endpoint de busca."""
    try:
        response = requests.get(
            f"{API_BASE}/api/v1/search",
            params={"query": "test music", "limit": 2},
            timeout=10
        )
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Search: OK - {len(data)} resultados")
            if data:
                print(f"   Primeiro resultado: {data[0].get('title', 'N/A')}")
            return True
        else:
            print(f"❌ Search failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Search error: {e}")
        return False

def test_docs():
    """Testa se a documentação está acessível."""
    try:
        response = requests.get(f"{API_BASE}/docs", timeout=5)
        if response.status_code == 200:
            print("✅ Docs: OK")
            return True
        else:
            print(f"❌ Docs failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Docs error: {e}")
        return False

def main():
    print("🧪 Testando TuneWhisperer API...")
    print(f"🔗 URL base: {API_BASE}")
    print()
    
    # Aguardar um pouco para a API inicializar
    print("⏳ Aguardando API inicializar...")
    time.sleep(2)
    
    tests = [
        ("Health Check", test_health),
        ("Documentação", test_docs),
        ("Busca de Músicas", test_search),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n🔍 Testando: {test_name}")
        if test_func():
            passed += 1
        time.sleep(1)
    
    print(f"\n📊 Resultado: {passed}/{total} testes passaram")
    
    if passed == total:
        print("🎉 Todos os testes passaram! API está funcionando.")
    else:
        print("⚠️  Alguns testes falharam. Verifique se a API está rodando:")
        print("   python -m uvicorn app.main:app --reload")
        print("   ou")
        print("   bash dev.sh")

if __name__ == "__main__":
    main()
