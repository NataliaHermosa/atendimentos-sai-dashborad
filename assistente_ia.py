# assistente_ia.py
from openai import OpenAI
from decouple import config

def criar_assistente():
    try:
        api_key = config('OPENAI_API_KEY')
        if not api_key:
            print("❌ API Key não encontrada")
            return None
            
        client = OpenAI(api_key=api_key)
        print("✅ Cliente OpenAI configurado")
        
        assistentes = client.beta.assistants.list(limit=10)
        print(f"✅ {len(assistentes.data)} assistentes encontrados")
        
        for assistente in assistentes.data:
            if "Assistente de Atendimentos" in assistente.name:
                print(f"✅ Assistente existente encontrado: {assistente.id}")
                return assistente.id
        
        print("📝 Criando novo assistente...")
        assistente = client.beta.assistants.create(
            name="Assistente de Atendimentos",
            instructions="Você é um assistente especializado em análise de dados de atendimento ao cliente.",
            model="gpt-3.5-turbo",
            tools=[{"type": "code_interpreter"}]
        )
        print(f"✅ Novo assistente criado: {assistente.id}")
        return assistente.id
        
    except Exception as e:
        print(f"❌ Erro em criar_assistente: {e}")
        return None

def consultar_assistente(pergunta):
    try:
        print(f"📝 Consulta recebida: {pergunta}")
        
        if "total" in pergunta.lower() and "atendimento" in pergunta.lower():
            return "📊 Total de atendimentos: 42 (dados de exemplo)"
        
        return f"🤖 Resposta para: '{pergunta}'"
        
    except Exception as e:
        return f"❌ Erro na consulta: {e}"

if __name__ == "__main__":
    print("=== TESTE DO ASSISTENTE IA ===")
    
    try:
        api_key = config('OPENAI_API_KEY')
        if api_key:
            print(f"✅ API Key: {api_key[:15]}...")
        else:
            print("❌ API Key não configurada")
    except Exception as e:
        print(f"❌ Erro na API Key: {e}")
    
    print("\n🔧 Testando criar_assistente...")
    assistente_id = criar_assistente()
    print(f"Resultado: {assistente_id}")
    
    print("\n🔧 Testando consultar_assistente...")
    resposta = consultar_assistente("qual o total de atendimentos?")
    print(f"Resposta: {resposta}")
    
    print("\n=== FIM DO TESTE ===")
