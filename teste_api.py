# teste_final.py
import os
from decouple import config

print("=== TESTE DO ARQUIVO .env ===")

# Verifica o conteúdo do arquivo .env
try:
    with open('.env', 'r', encoding='utf-8') as f:
        conteudo = f.read()
        print(f"✅ Arquivo .env encontrado!")
        print(f"Conteúdo: {conteudo}")
except Exception as e:
    print(f"❌ Erro ao ler arquivo: {e}")

# Tenta carregar a chave
try:
    api_key = config('OPENAI_API_KEY')
    print(f"✅ API Key carregada com sucesso!")
    print(f"Primeiros 25 caracteres: {api_key[:25]}...")
    print("🎉 Tudo configurado! Agora execute seu Streamlit.")
except Exception as e:
    print(f"❌ Erro ao carregar chave: {e}")
    print("💡 Dica: Verifique se a linha no .env está correta")