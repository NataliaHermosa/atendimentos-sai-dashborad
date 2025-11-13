import google.generativeai as genai
import pandas as pd
from datetime import datetime
import numpy as np
import os
import streamlit as st # Usado apenas para st.secrets em debug, mas mantido para robustez

# =============================================================================
# FUNÇÃO PRINCIPAL
# =============================================================================

def consultar_assistente(pergunta, df_filtrado, tipo_modelo="Gemini Pro", gemini_key=None):
    """
    Função principal do assistente. Recebe a chave diretamente do app.py e faz a chamada.
    
    :param gemini_key: Chave de API passada do st.secrets (app.py)
    """
    
    # 1. VERIFICAÇÃO CRÍTICA DA CHAVE: Se a chave não foi passada, retorne o fallback
    if not gemini_key:
        print("❌ Chave Gemini não fornecida. Retornando fallback com erro de configuração.")
        return analise_local_supercompleta(pergunta, df_filtrado, is_fallback_mode=True)
    
    # 2. CONFIGURAÇÃO E EXECUÇÃO DA IA
    try:
        # Tenta configurar o Gemini com a chave fornecida
        genai.configure(api_key=gemini_key)
        
        # 3. VERIFICAÇÃO DO DATAFRAME
        if not isinstance(df_filtrado, pd.DataFrame) or df_filtrado.empty:
            return "❌ Não há dados para análise com os filtros atuais."
        
        print(f"🔍 Consultando Gemini ({tipo_modelo}): {pergunta}")
        
        # 4. Escolher modelo
        # Note: Use gemini-2.5-pro/flash se estiver usando a biblioteca google-genai
        modelo_gemini = "gemini-2.5-pro" if "Pro" in tipo_modelo else "gemini-2.5-flash"

        # 5. Criar relatório COMPLETO
        relatorio_completo = criar_relatorio_supercompleto(df_filtrado, pergunta)

        # 6. Configurar e chamar o modelo
        model = genai.GenerativeModel(modelo_gemini)

        # 7. Prompt ESPECIALIZADO - (Mantenho o seu prompt detalhado)
        prompt = f"""
        VOCÊ: Especialista em análise completa de dados de atendimentos ao cliente

        DADOS COMPLETOS DISPONÍVEIS:
        {relatorio_completo}

        PERGUNTA DO USUÁRIO: {pergunta}

        CONTEXTO DAS COLUNAS:
        - Data: Data do atendimento
        - UF: Estado do cliente
        # ... (Resto do contexto das colunas) ...
        - Contato: Informações de contato do cliente

        NOVAS INSTRUÇÕES INTELIGENTES:
        - Analise padrões sazonais e tendências temporais
        - Identifique correlações entre módulos, atendentes e clientes
        - Detecte oportunidades de melhoria nos processos
        - Sugira ações baseadas nos dados (ex: treinamento, otimização)
        - Compare performance entre períodos diferentes
        - Identifique clientes que precisam de atenção especial
        - Analise eficiência por canal de atendimento
        - Detecte gargalos operacionais
        - Forneça insights preditivos quando possível
        - Relacione volume de atendimentos com complexidade
        - Use formatação markdown organizada com tópicos claros
        - Destaque os 3 principais insights em cada análise

        FORMATO DA RESPOSTA:
        ## 📊 Análise Principal
        [Resumo dos principais achados]

        ## 🎯 Insights Estratégicos
        [3-5 insights acionáveis]

        ## 📈 Recomendações
        [Ações específicas baseadas nos dados]

        ## 🔍 Detalhes Técnicos
        [Análises específicas por categoria]

        RESPOSTA:
        """

        # 6. Fazer consulta
        response = model.generate_content(prompt)
        print(f"✅ Resposta completa recebida!")
        return response.text

    except Exception as e:
        print(f"❌ Erro na API do Gemini durante a chamada: {e}")
        # Se houver um erro de conexão ou qualquer outro erro da API, usa o fallback local sem o flag de modo de erro
        return analise_local_supercompleta(pergunta, df_filtrado)

def criar_relatorio_supercompleto(df, pergunta):
    """Cria relatório MEGA COMPLETO com ANÁLISES TEMPORAIS AVANÇADAS"""
    
    # Verificação de segurança
    if not isinstance(df, pd.DataFrame) or df.empty:
        return "⚠️ Dados não disponíveis para análise"
    
    pergunta_lower = pergunta.lower()
    relatorio = "=== ANÁLISE COMPLETA DE TODOS OS DADOS ===\n\n"
    
    # CONTEXTO GERAL
    relatorio += "📊 CONTEXTO GERAL:\n"
    relatorio += f"• Total de registros: {len(df)} atendimentos\n"
    relatorio += f"• Colunas disponíveis: {', '.join(df.columns)}\n"
    
    # ✅ ANÁLISE TEMPORAL SUPER AVANÇADA
    if 'Data' in df.columns:
        try:
            df_temp = df.copy()
            df_temp['Data'] = pd.to_datetime(df_temp['Data'], errors='coerce')
            df_temp = df_temp.dropna(subset=['Data'])
            
            if not df_temp.empty:
                # Dados temporais básicos
                evolucao_diaria = df_temp.groupby(df_temp['Data'].dt.date).size()
                evolucao_mensal = df_temp.groupby(df_temp['Data'].dt.to_period('M')).size()
                
                relatorio += f"\n📅 ANÁLISE TEMPORAL DETALHADA:\n"
                relatorio += f"• Período: {df_temp['Data'].min().strftime('%d/%m/%Y')} a {df_temp['Data'].max().strftime('%d/%m/%Y')}\n"
                relatorio += f"• Dias com registro: {len(evolucao_diaria)}\n"
                relatorio += f"• Média diária: {evolucao_diaria.mean():.1f} atendimentos\n"
                
                if len(evolucao_diaria) > 0:
                    relatorio += f"• Dia de pico: {evolucao_diaria.idxmax().strftime('%d/%m/%Y')} ({evolucao_diaria.max()} atendimentos)\n"
                    relatorio += f"• Dia mais calmo: {evolucao_diaria.idxmin().strftime('%d/%m/%Y')} ({evolucao_diaria.min()} atendimentos)\n"
                
                # ✅ ANÁLISE DIÁRIA DETALHADA POR ATENDENTE (CRÍTICO!)
                if 'Atendente' in df_temp.columns:
                    relatorio += f"\n👥 ATENDIMENTOS DIÁRIOS POR ATENDENTE:\n"
                    
                    # Para cada dia, mostrar quantos atendimentos cada atendente fez
                    atendentes_diarios = df_temp.groupby([df_temp['Data'].dt.date, 'Atendente']).size().reset_index()
                    atendentes_diarios.columns = ['Data', 'Atendente', 'Atendimentos']
                    
                    # Ordenar por data mais recente primeiro
                    atendentes_diarios = atendentes_diarios.sort_values('Data', ascending=False)
                    
                    # Pegar os últimos 5 dias para análise
                    ultimos_dias = atendentes_diarios['Data'].unique()[:5]
                    
                    for dia in ultimos_dias:
                        dados_dia = atendentes_diarios[atendentes_diarios['Data'] == dia]
                        relatorio += f"• {dia.strftime('%d/%m/%Y')} - Total: {dados_dia['Atendimentos'].sum()} atendimentos:\n"
                        
                        # Ordenar por quantidade descendente
                        dados_dia = dados_dia.sort_values('Atendimentos', ascending=False)
                        
                        for _, row in dados_dia.head(5).iterrows():
                            relatorio += f"  - {row['Atendente']}: {row['Atendimentos']} atendimentos\n"
                        relatorio += "\n"
                
                # ✅ TOP ATENDENTES POR DIA ESPECÍFICO
                if 'Atendente' in df_temp.columns:
                    relatorio += f"\n🎯 TOP ATENDENTES POR DIA (ÚLTIMOS 5 DIAS):\n"
                    
                    # Encontrar o dia com mais atendimentos de cada top atendente
                    top_atendentes = df_temp['Atendente'].value_counts().head(5).index
                    
                    for atendente in top_atendentes:
                        dados_atendente = df_temp[df_temp['Atendente'] == atendente]
                        dia_top = dados_atendente.groupby(dados_atendente['Data'].dt.date).size()
                        
                        if len(dia_top) > 0:
                            melhor_dia = dia_top.idxmax()
                            melhor_quantidade = dia_top.max()
                            total_dias = len(dia_top)
                            relatorio += f"• {atendente}: Melhor dia {melhor_dia.strftime('%d/%m/%Y')} ({melhor_quantidade} atendimentos) - Atuou em {total_dias} dias\n"
                
                # ✅ ANÁLISE DO DIA ANTERIOR ESPECÍFICO
                if 'Atendente' in df_temp.columns:
                    # Encontrar a data mais recente nos dados
                    data_mais_recente = df_temp['Data'].max().date()
                    
                    # Calcular o "dia anterior" (último dia com dados)
                    dados_dia_anterior = df_temp[df_temp['Data'].dt.date == data_mais_recente]
                    
                    if not dados_dia_anterior.empty:
                        relatorio += f"\n📊 DETALHES DO DIA MAIS RECENTE ({data_mais_recente.strftime('%d/%m/%Y')}):\n"
                        relatorio += f"• Total de atendimentos: {len(dados_dia_anterior)}\n"
                        
                        # Atendentes que trabalharam nesse dia
                        atendentes_dia = dados_dia_anterior['Atendente'].value_counts()
                        relatorio += f"• Atendentes presentes: {len(atendentes_dia)}\n"
                        relatorio += f"• Distribuição:\n"
                        
                        for atendente, quantidade in atendentes_dia.head(5).items():
                            relatorio += f"  - {atendente}: {quantidade} atendimentos\n"
                
                # ✅ EVOLUÇÃO DOS TOP 3 ATENDENTES (ÚLTIMOS 7 DIAS)
                if 'Atendente' in df_temp.columns:
                    relatorio += f"\n📈 EVOLUÇÃO DOS TOP 3 ATENDENTES (ÚLTIMOS DIAS):\n"
                    
                    top_3_atendentes = df_temp['Atendente'].value_counts().head(3).index
                    datas_recentes = sorted(df_temp['Data'].dt.date.unique(), reverse=True)[:7]
                    
                    for atendente in top_3_atendentes:
                        relatorio += f"• {atendente}:\n"
                        dados_atendente = df_temp[df_temp['Atendente'] == atendente]
                        
                        for data in datas_recentes:
                            atendimentos_dia = len(dados_atendente[dados_atendente['Data'].dt.date == data])
                            if atendimentos_dia > 0:
                                relatorio += f"  - {data.strftime('%d/%m')}: {atendimentos_dia} atendimentos\n"
                
                # 🆕 ANÁLISE DE SAZONALIDADE SEMANAL
                if len(evolucao_diaria) > 7:
                    df_temp['Dia_Semana'] = df_temp['Data'].dt.day_name()
                    dias_semana = df_temp['Dia_Semana'].value_counts()
                    
                    relatorio += f"\n📆 PADRÃO SEMANAL DE ATENDIMENTOS:\n"
                    for dia, quantidade in dias_semana.items():
                        percentual = (quantidade / len(df_temp)) * 100
                        relatorio += f"• {dia}: {quantidade} atendimentos ({percentual:.1f}%)\n"
                
                # 🆕 TENDÊNCIA TEMPORAL (CRESCIMENTO/DECLÍNIO)
                if len(evolucao_mensal) > 1:
                    primeiro_mes = evolucao_mensal.iloc[0]
                    ultimo_mes = evolucao_mensal.iloc[-1]
                    variacao = ((ultimo_mes - primeiro_mes) / primeiro_mes) * 100
                    
                    relatorio += f"\n📈 TENDÊNCIA MENSAL:\n"
                    relatorio += f"• Primeiro mês: {primeiro_mes} atendimentos\n"
                    relatorio += f"• Último mês: {ultimo_mes} atendimentos\n"
                    relatorio += f"• Variação: {variacao:+.1f}%\n"
                
                # 🆕 ANÁLISE DE HORÁRIO DE PICO (se tiver hora)
                if 'Data' in df_temp.columns and any(':' in str(x) for x in df_temp['Data'].head()):
                    try:
                        df_temp['Hora'] = df_temp['Data'].dt.hour
                        pico_horario = df_temp['Hora'].value_counts().head(3)
                        relatorio += f"\n⏰ HORÁRIOS DE PICO:\n"
                        for hora, quantidade in pico_horario.items():
                            relatorio += f"• {hora:02d}:00 - {quantidade} atendimentos\n"
                    except:
                        pass
                        
        except Exception as e:
            relatorio += f"❌ Erro em análises temporais: {str(e)}\n\n"
    
    # ✅ ANÁLISE TEMPORAL POR MÓDULOS
    if 'Data' in df.columns and 'Modulos' in df.columns:
        try:
            df_temp = df.copy()
            df_temp['Data'] = pd.to_datetime(df_temp['Data'], errors='coerce')
            df_temp = df_temp.dropna(subset=['Data'])
            
            relatorio += f"\n🔧 EVOLUÇÃO DOS PRINCIPAIS MÓDULOS:\n"
            top_modulos = df_temp['Modulos'].value_counts().head(3).index
            
            for modulo in top_modulos:
                modulo_data = df_temp[df_temp['Modulos'] == modulo]
                evolucao_modulo = modulo_data.groupby(modulo_data['Data'].dt.date).size()
                if len(evolucao_modulo) > 0:
                    relatorio += f"• {modulo}: {len(modulo_data)} atendimentos em {len(evolucao_modulo)} dias\n"
                    
        except Exception as e:
            relatorio += f"❌ Erro em análise temporal por módulo: {str(e)}\n"
    
    # 🆕 ANÁLISE DE EFICIÊNCIA POR ATENDENTE
    if 'Atendente' in df.columns and 'Data' in df.columns:
        try:
            df_temp = df.copy()
            df_temp['Data'] = pd.to_datetime(df_temp['Data'], errors='coerce')
            df_temp = df_temp.dropna(subset=['Data'])
            
            relatorio += f"\n⚡ EFICIÊNCIA DOS ATENDENTES:\n"
            top_atendentes = df_temp['Atendente'].value_counts().head(5)
            
            for atendente, total_atendimentos in top_atendentes.items():
                dias_trabalhados = df_temp[df_temp['Atendente'] == atendente]['Data'].dt.date.nunique()
                if dias_trabalhados > 0:
                    media_diaria = total_atendimentos / dias_trabalhados
                    relatorio += f"• {atendente}: {total_atendimentos} atendimentos em {dias_trabalhados} dias ({media_diaria:.1f}/dia)\n"
                    
        except Exception as e:
            relatorio += f"❌ Erro em análise de eficiência: {str(e)}\n"
    
    # 🆕 CORRELAÇÃO ENTRE MÓDULOS E TIPOS DE ATENDIMENTO
    if 'Modulos' in df.columns and 'Tipos' in df.columns:
        try:
            relatorio += f"\n🔗 CORRELAÇÃO MÓDULOS x TIPOS:\n"
            modulo_tipo = df.groupby(['Modulos', 'Tipos']).size().reset_index()
            modulo_tipo.columns = ['Modulo', 'Tipo', 'Quantidade']
            
            # Encontrar combinações mais frequentes
            combinacoes_top = modulo_tipo.nlargest(5, 'Quantidade')
            
            for _, row in combinacoes_top.iterrows():
                relatorio += f"• {row['Modulo']} + {row['Tipo']}: {row['Quantidade']} atendimentos\n"
                
        except Exception as e:
            relatorio += f"❌ Erro em análise de correlação: {str(e)}\n"
    
    # 🆕 ANÁLISE DE CLIENTES RECORRENTES
    if 'Cliente' in df.columns:
        try:
            cliente_frequencia = df['Cliente'].value_counts()
            clientes_recorrentes = cliente_frequencia[cliente_frequencia > 1]
            
            relatorio += f"\n🔄 CLIENTES RECORRENTES:\n"
            relatorio += f"• Total de clientes únicos: {len(cliente_frequencia)}\n"
            relatorio += f"• Clientes com +1 atendimento: {len(clientes_recorrentes)}\n"
            
            if len(clientes_recorrentes) > 0:
                relatorio += "• Maior frequência:\n"
                for cliente, freq in clientes_recorrentes.head(3).items():
                    relatorio += f"  - {cliente}: {freq} atendimentos\n"
                    
        except Exception as e:
            relatorio += f"❌ Erro em análise de clientes recorrentes: {str(e)}\n"
    
    # 🆕 ANÁLISE DE DISTRIBUIÇÃO GEOGRÁFICA DETALHADA
    if 'UF' in df.columns and 'Cliente' in df.columns:
        try:
            uf_clientes = df.groupby('UF')['Cliente'].nunique()
            relatorio += f"\n🗺️ DISTRIBUIÇÃO GEOGRÁFICA AVANÇADA:\n"
            for uf, n_clientes in uf_clientes.nlargest(5).items():
                total_uf = len(df[df['UF'] == uf])
                relatorio += f"• {uf}: {n_clientes} clientes únicos, {total_uf} atendimentos\n"
                
        except Exception as e:
            relatorio += f"❌ Erro em análise geográfica avançada: {str(e)}\n"
    
    # 🆕 ANÁLISE DE COMPLEXIDADE POR MÓDULO
    if 'Modulos' in df.columns and 'Atendente' in df.columns:
        try:
            relatorio += f"\n🎯 COMPLEXIDADE DOS MÓDULOS:\n"
            modulo_stats = df.groupby('Modulos').agg({
                'Atendente': 'nunique',
                'Cliente': 'nunique'
            }).round(1)
            
            modulo_stats = modulo_stats.nlargest(5, 'Atendente')
            
            for modulo, row in modulo_stats.iterrows():
                relatorio += f"• {modulo}: {row['Atendente']} atendentes, {row['Cliente']} clientes\n"
                
        except Exception as e:
            relatorio += f"❌ Erro em análise de complexidade: {str(e)}\n"

    # ANÁLISE DE CLIENTES (mantido do original)
    if 'Cliente' in df.columns:
        cliente_stats = df['Cliente'].value_counts()
        relatorio += "\n🏢 ANÁLISE DE CLIENTES:\n"
        relatorio += f"• Total de clientes únicos: {len(cliente_stats)}\n"
        
        if len(cliente_stats) > 0:
            relatorio += "• Clientes com mais atendimentos:\n"
            for i, (cliente, quantidade) in enumerate(cliente_stats.head(10).items(), 1):
                percentual = (quantidade / len(df)) * 100
                relatorio += f"  {i}. {cliente}: {quantidade} atendimentos ({percentual:.1f}%)\n"
        relatorio += "\n"
    
    # ANÁLISE GEOGRÁFICA AVANÇADA (mantido do original)
    if 'UF' in df.columns:
        uf_stats = df['UF'].value_counts()
        relatorio += "📍 ANÁLISE GEOGRÁFICA (UF):\n"
        relatorio += f"• Estados atendidos: {len(uf_stats)}\n"
        relatorio += "• Distribuição por estado:\n"
        for uf, quantidade in uf_stats.head(8).items():
            percentual = (quantidade / len(df)) * 100
            relatorio += f"  - {uf}: {quantidade} ({percentual:.1f}%)\n"
        relatorio += "\n"
    
    # ANÁLISE DE NÚCLEOS (mantido do original)
    if 'Nucleos' in df.columns:
        nucleos_stats = df['Nucleos'].value_counts()
        relatorio += "🏛️ ANÁLISE DE NÚCLEOS:\n"
        relatorio += f"• Total de núcleos: {len(nucleos_stats)}\n"
        if len(nucleos_stats) > 0:
            relatorio += "• Núcleos mais atendidos:\n"
            for i, (nucleo, quantidade) in enumerate(nucleos_stats.head(6).items(), 1):
                relatorio += f"  {i}. {nucleo}: {quantidade} atendimentos\n"
        relatorio += "\n"
    
    # ANÁLISE DE PRODUTOS (mantido do original)
    if 'Produtos' in df.columns:
        produtos_stats = df['Produtos'].value_counts()
        relatorio += "📦 ANÁLISE DE PRODUTOS:\n"
        relatorio += f"• Total de produtos: {len(produtos_stats)}\n"
        if len(produtos_stats) > 0:
            relatorio += "• Produtos mais frequentes:\n"
            for i, (produto, quantidade) in enumerate(produtos_stats.head(6).items(), 1):
                relatorio += f"  {i}. {produto}: {quantidade} atendimentos\n"
        relatorio += "\n"
    
    # ANÁLISE DE CATEGORIAS (mantido do original)
    if 'Categorias' in df.columns:
        categorias_stats = df['Categorias'].value_counts()
        relatorio += "📂 ANÁLISE DE CATEGORIAS:\n"
        relatorio += f"• Total de categorias: {len(categorias_stats)}\n"
        if len(categorias_stats) > 0:
            relatorio += "• Categorias predominantes:\n"
            for i, (categoria, quantidade) in enumerate(categorias_stats.head(6).items(), 1):
                relatorio += f"  {i}. {categoria}: {quantidade} atendimentos\n"
        relatorio += "\n"
    
    # ANÁLISE DE TIPOS (mantido do original)
    if 'Tipos' in df.columns:
        tipos_stats = df['Tipos'].value_counts()
        relatorio += "🎯 ANÁLISE DE TIPOS DE ATENDIMENTO:\n"
        relatorio += f"• Total de tipos: {len(tipos_stats)}\n"
        if len(tipos_stats) > 0:
            relatorio += "• Tipos mais comuns:\n"
            for i, (tipo, quantidade) in enumerate(tipos_stats.head(6).items(), 1):
                relatorio += f"  {i}. {tipo}: {quantidade} atendimentos\n"
        relatorio += "\n"
    
    # ANÁLISE DE ATENDENTES DETALHADA (mantido do original)
    if 'Atendente' in df.columns:
        atendentes_stats = df['Atendente'].value_counts()
        relatorio += "👥 ANÁLISE DE ATENDENTES:\n"
        relatorio += f"• Total de atendentes: {len(atendentes_stats)}\n"
        if len(atendentes_stats) > 0:
            relatorio += "• Performance por atendente:\n"
            for i, (atendente, quantidade) in enumerate(atendentes_stats.head(8).items(), 1):
                relatorio += f"  {i}. {atendente}: {quantidade} atendimentos\n"
        relatorio += "\n"
    
    # ANÁLISE DE CANAIS (mantido do original)
    if 'Canais' in df.columns:
        canais_stats = df['Canais'].value_counts()
        relatorio += "📞 ANÁLISE DE CANAIS DE ATENDIMENTO:\n"
        relatorio += f"• Total de canais: {len(canais_stats)}\n"
        if len(canais_stats) > 0:
            relatorio += "• Distribuição por canal:\n"
            for canal, quantidade in canais_stats.items():
                relatorio += f"  - {canal}: {quantidade} atendimentos\n"
        relatorio += "\n"
    
    # ANÁLISE DE MÓDULOS (mantido do original)
    if 'Modulos' in df.columns:
        modulos_stats = df['Modulos'].value_counts()
        relatorio += "🔧 ANÁLISE DE MÓDULOS:\n"
        relatorio += f"• Total de módulos: {len(modulos_stats)}\n"
        if len(modulos_stats) > 0:
            relatorio += "• Módulos mais acessados:\n"
            for i, (modulo, quantidade) in enumerate(modulos_stats.head(6).items(), 1):
                relatorio += f"  {i}. {modulo}: {quantidade} atendimentos\n"
        relatorio += "\n"
    
    # ANÁLISE DE CONTATOS (mantido do original)
    if 'Contato' in df.columns:
        contato_stats = df['Contato'].value_counts()
        relatorio += "📱 ANÁLISE DE CONTATOS:\n"
        relatorio += f"• Total de contatos únicos: {len(contato_stats)}\n"
        relatorio += "\n"
    
    # 🆕 RESUMO EXECUTIVO PARA IA
    relatorio += "\n=== RESUMO EXECUTIVO PARA ANÁLISE IA ===\n"
    relatorio += f"• Volume total: {len(df)} atendimentos\n"
    if 'Data' in df.columns:
        try:
            df_temp = df.copy()
            df_temp['Data'] = pd.to_datetime(df_temp['Data'], errors='coerce')
            df_temp = df_temp.dropna(subset=['Data'])
            if not df_temp.empty:
                relatorio += f"• Período: {df_temp['Data'].min().strftime('%d/%m/%Y')} a {df_temp['Data'].max().strftime('%d/%m/%Y')}\n"
        except:
            pass
    
    if 'Atendente' in df.columns:
        relatorio += f"• Equipe: {df['Atendente'].nunique()} atendentes\n"
    
    if 'Cliente' in df.columns:
        relatorio += f"• Base: {df['Cliente'].nunique()} clientes\n"
    
    if 'Modulos' in df.columns:
        relatorio += f"• Cobertura: {df['Modulos'].nunique()} módulos\n"
    
    return relatorio

# 🆕 FUNÇÃO ADICIONAL PARA DETECÇÃO DE ANOMALIAS
def detectar_anomalias(df):
    """Detecta padrões incomuns nos dados"""
    insights = []
    
    try:
        if 'Data' in df.columns and 'Atendente' in df.columns:
            df_temp = df.copy()
            df_temp['Data'] = pd.to_datetime(df_temp['Data'], errors='coerce')
            df_temp = df_temp.dropna(subset=['Data'])
            
            # Detectar dias com volume anormal
            daily_volume = df_temp.groupby(df_temp['Data'].dt.date).size()
            volume_mean = daily_volume.mean()
            volume_std = daily_volume.std()
            
            anomalias = daily_volume[(daily_volume > volume_mean + 2*volume_std) | 
                                   (daily_volume < volume_mean - 2*volume_std)]
            
            if len(anomalias) > 0:
                insights.append(f"📊 Foram detectados {len(anomalias)} dias com volume anormal de atendimentos")
                
    except Exception as e:
        print(f"⚠️ Erro na detecção de anomalias: {e}")
    
    return insights

def analise_local_supercompleta(pergunta, df_filtrado, is_fallback_mode=False):
    """
    Fallback completo para análise local.
    A mensagem de erro da API só é incluída se is_fallback_mode for True.
    """
    try:
        print(f"🔧 Entrando no fallback local - Tipo: {type(df_filtrado)}")
        
        # ... (suas verificações robustas) ...
        if not isinstance(df_filtrado, pd.DataFrame) or df_filtrado.empty:
             return "📭 Não há dados disponíveis para análise com os filtros atuais."
        
        print(f"✅ Fallback local com {len(df_filtrado)} registros")
        
        pergunta_lower = pergunta.lower()
        # Alterei o título para indicar que é um fallback
        resposta = "📊 **Análise Local Detalhada (Modo Fallback):**\n\n"
        
        # 🆕 DETECÇÃO DE ANOMALIAS NO FALLBACK
        anomalias = detectar_anomalias(df_filtrado)
        if anomalias:
            resposta += "🚨 **ALERTAS DETECTADOS:**\n"
            for alerta in anomalias:
                resposta += f"• {alerta}\n"
            resposta += "\n"
        
        # PERGUNTA ESPECÍFICA SOBRE CLIENTES
        if any(palavra in pergunta_lower for palavra in ['cliente', 'clientes']):
            if 'Cliente' in df_filtrado.columns:
                cliente_stats = df_filtrado['Cliente'].value_counts()
                resposta += f"🏢 **ANÁLISE DE CLIENTES**\n"
                resposta += f"• Total de clientes únicos: {len(cliente_stats)}\n"
                resposta += f"• Total de atendimentos analisados: {len(df_filtrado)}\n\n"
                
                if len(cliente_stats) > 0:
                    resposta += "🎯 **TOP 10 CLIENTES COM MAIS ATENDIMENTOS:**\n"
                    for i, (cliente, quantidade) in enumerate(cliente_stats.head(10).items(), 1):
                        percentual = (quantidade / len(df_filtrado)) * 100
                        resposta += f"{i}. **{cliente}**: {quantidade} atendimentos ({percentual:.1f}%)\n"
                else:
                    resposta += "ℹ️ Não há dados de clientes para análise.\n"
                
                return resposta
        
        # RESPOSTAS PARA OUTRAS PERGUNTAS COMUNS
        resposta += f"**Contexto:** {len(df_filtrado)} registros filtrados\n\n"
        
        if any(palavra in pergunta_lower for palavra in ['total', 'quantos']):
            resposta += f"• **Total de atendimentos:** {len(df_filtrado)}\n"
        
        if any(palavra in pergunta_lower for palavra in ['uf', 'estado']):
            if 'UF' in df_filtrado.columns:
                resposta += f"• **Estados atendidos:** {df_filtrado['UF'].nunique()}\n"
        
        if any(palavra in pergunta_lower for palavra in ['atendente']):
            if 'Atendente' in df_filtrado.columns:
                resposta += f"• **Atendentes ativos:** {df_filtrado['Atendente'].nunique()}\n"
        
        if any(palavra in pergunta_lower for palavra in ['modulo', 'módulo']):
            if 'Modulos' in df_filtrado.columns:
                resposta += f"• **Módulos atendidos:** {df_filtrado['Modulos'].nunique()}\n"
        
        # 🆕 INSIGHTS ADICIONAIS NO FALLBACK
        resposta += "\n💡 **Insights Adicionais:**\n"
        
        if 'Data' in df_filtrado.columns:
            try:
                df_temp = df_filtrado.copy()
                df_temp['Data'] = pd.to_datetime(df_temp['Data'], errors='coerce')
                df_temp = df_temp.dropna(subset=['Data'])
                
                if not df_temp.empty:
                    dias_unicos = df_temp['Data'].dt.date.nunique()
                    resposta += f"• **Período analisado:** {dias_unicos} dias\n"
                    
                    if dias_unicos > 0:
                        media_diaria = len(df_filtrado) / dias_unicos
                        resposta += f"• **Média diária:** {media_diaria:.1f} atendimentos/dia\n"
            except:
                pass
        
        if 'Canais' in df_filtrado.columns:
            canal_principal = df_filtrado['Canais'].value_counts().head(1)
            if len(canal_principal) > 0:
                resposta += f"• **Canal principal:** {canal_principal.index[0]} ({canal_principal.iloc[0]} atendimentos)\n"
        
        if is_fallback_mode:
            resposta += "\n🔑 **ERRO DE CONFIGURAÇÃO:** A chave Gemini não foi encontrada, é inválida, ou o Streamlit falhou na comunicação. "
            resposta += "Por favor, configure a `GEMINI_API_KEY` no seu **secrets.toml** do Streamlit Cloud para análises completas com IA."
        
        return resposta
        
    except Exception as e:
        error_msg = f"❌ Erro na análise local: {str(e)}"
        print(error_msg)
        return error_msg
    
# Forcando o commit de sincronizacao