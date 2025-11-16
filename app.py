from dotenv import load_dotenv
load_dotenv()
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import gspread
from google.oauth2 import service_account
from datetime import datetime
import os
import google.generativeai as genai

# Configuração da página (mantido igual)
st.set_page_config(
    page_title="Dashboard de Atendimentos - SAI",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

@st.cache_data(ttl=300)
def load_data(uploaded_file=None):
    """
    Carrega dados do Google Sheets - PLANILHA relatorio_set_out
    """
    try:
        # Opção 1: Arquivo enviado via upload (prioridade) - MANTIDO IGUAL
        if uploaded_file is not None:
            try:
                df = pd.read_excel(uploaded_file, sheet_name='dados', engine='openpyxl')
                st.sidebar.success("✅ Arquivo carregado via upload")
                return clean_data(df)
            except:
                try:
                    df = pd.read_excel(uploaded_file, sheet_name='dados', engine='xlrd')
                    st.sidebar.success("✅ Arquivo carregado via upload")
                    return clean_data(df)
                except Exception as e:
                    st.sidebar.warning("⚠️ Erro no upload, usando Google Sheets")
        
        # Opção 2: Google Sheets - CORREÇÃO APENAS NA CONEXÃO
        try:
            # Configuração do Google Sheets API - MANTIDO
            scope = [
                'https://spreadsheets.google.com/feeds',
                'https://www.googleapis.com/auth/drive',
                'https://www.googleapis.com/auth/spreadsheets'
            ]
            
            # CORREÇÃO: Nome correto do secret
            credentials = service_account.Credentials.from_service_account_info(
                st.secrets["relatorio_set_out_account"], scopes=scope  # Mudei apenas aqui
            )
            
            client = gspread.authorize(credentials)
            
            sheet_url = "https://docs.google.com/spreadsheets/d/152DHhNzoLlUs0Vq_uRuVkfoq3C2A_lcJfJjambA6EWA/edit?gid=804702972#gid=804702972"
            
            # Abre a planilha pela URL - MANTIDO
            spreadsheet = client.open_by_url(sheet_url)
            
            # Pega a primeira aba - MANTIDO
            worksheet = spreadsheet.sheet1
            
            # Obtém TODOS os valores - MANTIDO
            all_values = worksheet.get_all_values()
            
            if len(all_values) > 1:
                headers = all_values[0]
                data = all_values[1:]
                df = pd.DataFrame(data, columns=headers)
                
                st.sidebar.success("✅ Dados carregados do Google Sheets")
                return clean_data(df)  # Sua função clean_data mantida
            else:
                st.sidebar.warning("Planilha vazia")
                return pd.DataFrame()  # Retorna DataFrame vazio
            
        except Exception as e:
            st.sidebar.info("📊 Google Sheets indisponível")
            return pd.DataFrame()  # Retorna DataFrame vazio
            
    except Exception as e:
        st.sidebar.info("📋 Erro ao carregar dados")
        return pd.DataFrame()  # SEMPRE retorna um DataFrame, nunca None

def test_relatorio_connection():
    """Testa a conexão com a planilha relatorio_set_out - CORREÇÃO APENAS NO SECRET"""
    try:
        scope = ['https://spreadsheets.google.com/feeds']
        # CORREÇÃO: Nome correto do secret
        credentials = service_account.Credentials.from_service_account_info(
            st.secrets["relatorio_set_out_account"], scopes=scope  # Mudei apenas aqui
        )
        client = gspread.authorize(credentials)
        
        sheet_url = "https://docs.google.com/spreadsheets/d/152DHhNzoLlUs0Vq_uRuVkfoq3C2A_lcJfJjambA6EWA/edit?gid=804702972#gid=804702972"
        spreadsheet = client.open_by_url(sheet_url)
        
        st.success("✅ Conexão estabelecida com relatorio_set_out!")
        st.write(f"📊 Título: {spreadsheet.title}")
        st.write(f"🔗 ID: {spreadsheet.id}")
        
        worksheet = spreadsheet.sheet1
        all_values = worksheet.get_all_values()
        st.write(f"📈 Total de linhas: {len(all_values)}")
        st.write(f"📋 Registros (sem cabeçalho): {len(all_values) - 1}")
                
        
        return True
    except Exception as e:
        st.error(f"❌ Erro: {e}")
        return False
    
def corrigir_datas(df):
    """
    Corrige problemas de conversão de datas do Google Sheets
    """
    if 'Data' not in df.columns:
        return df
    
    # Tentar diferentes formatos de data
    date_formats = [
        '%d/%m/%Y', '%d-%m-%Y', '%Y-%m-%d', 
        '%d/%m/%y', '%d-%m-%y', '%m/%d/%Y',
        '%Y/%m/%d'
    ]
    
    for fmt in date_formats:
        try:
            df['Data'] = pd.to_datetime(df['Data'], format=fmt, errors='coerce')
            # Verificar se conseguiu converter alguma data
            if not df['Data'].isna().all():
                break
        except:
            continue
    
    # Se ainda não converteu, tentar método genérico
    if df['Data'].isna().all():
        df['Data'] = pd.to_datetime(df['Data'], errors='coerce')
    
    # Remover registros com datas inválidas
    datas_invalidas = df[df['Data'].isna()]
    if len(datas_invalidas) > 0:
        df = df.dropna(subset=['Data'])
    
    return df

def processar_multiplos_modulos(df):
    """
    Processa células com múltiplos módulos separados por VÍRGULA ou PONTO-E-VÍRGULA.
    Cria uma nova linha para cada módulo individual.
    """
    if 'Modulos' not in df.columns:
        return df
    
    # Lista para armazenar as novas linhas
    novas_linhas = []
    
    for idx, row in df.iterrows():
        modulo_valor = str(row['Modulos']).strip()
        
        # Pular valores vazios ou padrão
        if modulo_valor in ['', 'NÃO INFORMADO', 'nan', 'NaN']:
            novas_linhas.append(row)
            continue
        
        separadores = [',', ';']
        
        # Verificar se tem algum dos separadores
        tem_separador = any(sep in modulo_valor for sep in separadores)
        
        if tem_separador:
           
            if ';' in modulo_valor:
                # Dividir por ponto-e-vírgula
                modulos_divididos = [mod.strip() for mod in modulo_valor.split(';') if mod.strip()]
            else:
                # Dividir por vírgula
                modulos_divididos = [mod.strip() for mod in modulo_valor.split(',') if mod.strip()]
            
            # Criar uma linha para cada módulo individual
            for modulo_individual in modulos_divididos:
                if modulo_individual and modulo_individual not in ['', 'NÃO INFORMADO']:
                    nova_linha = row.copy()
                    nova_linha['Modulos'] = modulo_individual.strip()
                    novas_linhas.append(nova_linha)
        else:
            # Se não tem separadores, manter a linha original
            novas_linhas.append(row)
    
    # Criar novo DataFrame com as linhas processadas
    df_processado = pd.DataFrame(novas_linhas).reset_index(drop=True)
    
    return df_processado

def clean_data(df):
    """Função para limpeza e padronização dos dados"""
    
    # PRIMEIRO: Corrigir as datas
    df = corrigir_datas(df)
    
    # Converter data (fallback)
    date_columns = ['Data', 'DATA', 'data', 'Date', 'date']
    for col in date_columns:
        if col in df.columns and col != 'Data':
            df['Data'] = pd.to_datetime(df[col], errors='coerce')
            break
    
    # Se não encontrou coluna de data, criar uma dummy
    if 'Data' not in df.columns or df['Data'].isna().all():
        df['Data'] = pd.to_datetime('today')
    
    # 🆕 NOVO: PROCESSAR MÚLTIPLOS MÓDULOS
    if 'Modulos' in df.columns:
        df = processar_multiplos_modulos(df)
    
    # Preencher valores vazios, nulos e espaços em branco
    fill_columns = {
        'UF': 'NÃO INFORMADO',
        'Atendente': 'NÃO INFORMADO', 
        'Categorias': 'NÃO INFORMADA',
        'Tipos': 'NÃO INFORMADO',
        'Modulos': 'NÃO INFORMADO',  # Agora já processado acima
        'Canais': 'NÃO INFORMADO'
    }
    
    for col, default_value in fill_columns.items():
        if col in df.columns:
            # Converter para string e tratar vários casos
            df[col] = df[col].astype(str)
            
            # Substituir strings vazias, espaços e valores nulos
            df[col] = df[col].replace(['', ' ', 'nan', 'NaN', 'None', 'null'], default_value)
            
            # Também tratar valores nulos do pandas
            df[col] = df[col].fillna(default_value)
    
    return df

# Componente de upload na sidebar
def create_sidebar():
    st.sidebar.title("🎛️ Controle de Dados")
    
    # Botão para forçar atualização
    if st.sidebar.button("🔄 Atualizar Dados do Google Sheets"):
        st.cache_data.clear()
        st.rerun()
    
    # Upload de arquivo
    uploaded_file = st.sidebar.file_uploader(
        "📤 Upload da planilha atualizada",
        type=['xls', 'xlsx']
    )
    
    return uploaded_file

# FUNÇÃO PARA OBTER PERÍODO DOS DADOS
def get_data_period(df):
    """
    Retorna o período completo dos dados de forma formatada
    """
    if df.empty or 'Data' not in df.columns:
        return "Período não disponível"
    
    min_date = df['Data'].min()
    max_date = df['Data'].max()
    
    if min_date == max_date:
        return f"{min_date.strftime('%d/%m/%Y')} (apenas este dia)"
    else:
        return f"{min_date.strftime('%d/%m/%Y')} a {max_date.strftime('%d/%m/%Y')}"

# FUNÇÃO PARA FORMATAR PERÍODO FILTRADO
def format_periodo_filtrado(df):
    """
    Formata o período filtrado de forma mais legível
    """
    if df.empty or 'Data' not in df.columns:
        return "N/A"
    
    min_date = df['Data'].min()
    max_date = df['Data'].max()
    
    if min_date == max_date:
        return min_date.strftime('%d/%m/%Y')
    else:
        return f"{min_date.strftime('%d/%m/%Y')} a {max_date.strftime('%d/%m/%Y')}"

# FUNÇÃO MELHORADA PARA GRÁFICO DE EVOLUÇÃO DIÁRIA
def create_daily_evolution_chart(df):
    """
    Cria gráfico de evolução diária mais visual e informativo
    """
    if df.empty or 'Data' not in df.columns:
        return None
    
    # Agrupar por dia
    daily_counts = df.groupby(df['Data'].dt.date).size().reset_index()
    daily_counts.columns = ['Data', 'Quantidade']
    
    # Calcular estatísticas
    total_atendimentos = daily_counts['Quantidade'].sum()
    media_diaria = daily_counts['Quantidade'].mean()
    max_dia = daily_counts['Quantidade'].max()
    min_dia = daily_counts['Quantidade'].min()
    
    # Criar gráfico com Plotly Graph Objects para mais customização
    fig = go.Figure()
    
    # Linha principal azul com marcadores
    fig.add_trace(go.Scatter(
        x=daily_counts['Data'],
        y=daily_counts['Quantidade'],
        mode='lines+markers',
        name='Atendimentos por dia',
        line=dict(color='#1f77b4', width=4),
        marker=dict(
            size=8,
            color='#1f77b4',
            line=dict(width=2, color='white')
        ),
        hovertemplate='<b>%{x}</b><br>Atendimentos: %{y}<extra></extra>'
    ))
    
    # Linha de média
    fig.add_trace(go.Scatter(
        x=daily_counts['Data'],
        y=[media_diaria] * len(daily_counts),
        mode='lines',
        name=f'Média diária: {media_diaria:.1f}',
        line=dict(color='red', width=2, dash='dash'),
        hovertemplate=f'Média: {media_diaria:.1f} atendimentos/dia<extra></extra>'
    ))
    
    # Configurar layout
    fig.update_layout(
        title=dict(
            text="📈 Evolução Diária de Atendimentos",
            x=0.5,
            font=dict(size=20)
        ),
        xaxis=dict(
            title="Data",
            tickformat="%d/%m",
            gridcolor='lightgray'
        ),
        yaxis=dict(
            title="Quantidade de Atendimentos",
            gridcolor='lightgray'
        ),
        hovermode='x unified',
        plot_bgcolor='white',
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
        height=500
    )
    
    # Adicionar anotações com estatísticas
    fig.add_annotation(
        xref="paper", yref="paper",
        x=0.02, y=0.98,
        text=f"Total: {total_atendimentos} atendimentos<br>Máximo: {max_dia} atendimentos<br>Mínimo: {min_dia} atendimentos",
        showarrow=False,
        bgcolor="white",
        bordercolor="black",
        borderwidth=1
    )
    
    return fig

# FUNÇÃO PARA ANÁLISE POR MÓDULO
def show_analise_modulos(df):
    """
    Análise detalhada por módulo
    """
    if df.empty:
        st.info("Nenhum dado encontrado com os filtros aplicados.")
        return
        
    if 'Modulos' not in df.columns:
        st.info("Coluna 'Modulos' não encontrada nos dados")
        return
    
    st.subheader("🔍 Análise Detalhada por Módulo")
    
    # Seletor de módulo para análise detalhada
    modulos_disponiveis = sorted(df['Modulos'].unique())
    modulo_selecionado = st.selectbox("Selecione o módulo para análise detalhada:", modulos_disponiveis)
    
    if modulo_selecionado:
        # Dados do módulo selecionado
        dados_modulo = df[df['Modulos'] == modulo_selecionado]
        
        # Métricas do módulo
        col1, col2, col3, col4, col5 = st.columns(5)
        
        with col1:
            st.metric("Total de Atendimentos", len(dados_modulo))
        
        with col2:
            st.metric("Atendentes no Módulo", dados_modulo['Atendente'].nunique())
        
        with col3:
            st.metric("Dias com Atividade", dados_modulo['Data'].nunique())
        
        with col4:
            if 'Tipos' in dados_modulo.columns:
                st.metric("Tipos de Atendimento", dados_modulo['Tipos'].nunique())
            else:
                st.metric("Tipos de Atendimento", 0)
        
        with col5:
            if dados_modulo['Data'].nunique() > 0:
                media_dia = len(dados_modulo) / dados_modulo['Data'].nunique()
                st.metric("Média/dia", f"{media_dia:.1f}")
            else:
                st.metric("Média/dia", 0)
        
        st.markdown("---")
        
        # Análises específicas do módulo
        col1, col2 = st.columns(2)
        
        with col1:
            # Top atendentes no módulo
            st.subheader(f"👥 Top Atendentes - {modulo_selecionado}")
            top_atendentes_modulo = dados_modulo['Atendente'].value_counts().head(10)
            fig = px.bar(top_atendentes_modulo, orientation='v',
                        title=f"Top 10 Atendentes no {modulo_selecionado}",
                        labels={'value': 'Quantidade', 'index': 'Atendente'})
            st.plotly_chart(fig, use_container_width=True)
            
            # Tipos de atendimento mais comuns no módulo
            if 'Tipos' in dados_modulo.columns:
                st.subheader(f"📋 Tipos de Atendimento - {modulo_selecionado}")
                tipos_modulo = dados_modulo['Tipos'].value_counts().head(10)
                fig = px.pie(values=tipos_modulo.values, names=tipos_modulo.index,
                            title=f"Tipos de Atendimento no {modulo_selecionado}")
                st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            # Evolução temporal do módulo
            st.subheader(f"📈 Evolução - {modulo_selecionado}")
            if 'Data' in dados_modulo.columns:
                evolucao_modulo = dados_modulo.groupby(dados_modulo['Data'].dt.date).size().reset_index()
                evolucao_modulo.columns = ['Data', 'Quantidade']
                
                fig = px.line(evolucao_modulo, x='Data', y='Quantidade',
                             title=f"Atendimentos por Dia - {modulo_selecionado}",
                             markers=True)
                st.plotly_chart(fig, use_container_width=True)
            
            # Canais de atendimento no módulo
            if 'Canais' in dados_modulo.columns:
                st.subheader(f"📞 Canais - {modulo_selecionado}")
                canais_modulo = dados_modulo['Canais'].value_counts()
                fig = px.bar(canais_modulo, orientation='v',
                            title=f"Canais de Atendimento no {modulo_selecionado}",
                            labels={'value': 'Quantidade', 'index': 'Canal'})
                st.plotly_chart(fig, use_container_width=True)
    
    st.markdown("---")
    
    # Visão geral de todos os módulos
    st.subheader("📊 Visão Geral - Todos os Módulos")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Distribuição geral por módulo
        distribuicao_modulos = df['Modulos'].value_counts()
        fig = px.bar(distribuicao_modulos.head(15), orientation='v',
                    title="Top 15 Módulos por Volume de Atendimentos",
                    labels={'value': 'Quantidade de Atendimentos', 'index': 'Módulo'})
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        # Módulos por atendente (heatmap)
        st.subheader("🧩 Atendentes por Módulo")
        modulos_x_atendentes = df.groupby(['Modulos', 'Atendente']).size().unstack(fill_value=0)
        
        # Mostrar apenas os top módulos e atendentes para o heatmap
        top_modulos = df['Modulos'].value_counts().head(10).index
        top_atendentes = df['Atendente'].value_counts().head(15).index
        
        heatmap_data = modulos_x_atendentes.loc[top_modulos, top_atendentes]
        
        fig = px.imshow(heatmap_data,
                       title="Heatmap: Atendentes vs Módulos (Top 10 módulos e 15 atendentes)",
                       aspect="auto")
        st.plotly_chart(fig, use_container_width=True)
    
    # Tabela resumo dos módulos
    st.subheader("📋 Resumo Estatístico por Módulo")
    
    # Criar tabela resumo de forma mais robusta
    resumo_data = []
    
    for modulo in df['Modulos'].unique():
        dados_modulo = df[df['Modulos'] == modulo]
        
        resumo_modulo = {
            'Módulo': modulo,
            'Atendentes': dados_modulo['Atendente'].nunique(),
            'Dias Ativos': dados_modulo['Data'].nunique(),
            'Total Atendimentos': len(dados_modulo)
        }
        
        # Adicionar tipos de atendimento se a coluna existir
        if 'Tipos' in dados_modulo.columns:
            resumo_modulo['Tipos de Atendimento'] = dados_modulo['Tipos'].nunique()
        else:
            resumo_modulo['Tipos de Atendimento'] = 0
        
        # Calcular média por dia
        if resumo_modulo['Dias Ativos'] > 0:
            resumo_modulo['Média/Dia'] = round(resumo_modulo['Total Atendimentos'] / resumo_modulo['Dias Ativos'], 1)
        else:
            resumo_modulo['Média/Dia'] = 0
        
        resumo_data.append(resumo_modulo)
    
    # Criar DataFrame do resumo
    resumo_modulos = pd.DataFrame(resumo_data)
    
    # Ordenar por total de atendimentos
    resumo_modulos = resumo_modulos.sort_values('Total Atendimentos', ascending=False)
    
    st.dataframe(resumo_modulos, use_container_width=True)


# Função para Visão Geral
def show_overview(df):
    if df.empty:
        st.info("Nenhum dado encontrado com os filtros aplicados.")
        return
        
    col1, col2 = st.columns(2)
    
    with col1:
        if 'Atendente' in df.columns:
            top_atendentes = df['Atendente'].value_counts().head(10)
            fig = px.bar(top_atendentes, orientation='v',
                        title="Top 10 Atendentes",
                        labels={'value': 'Quantidade', 'index': 'Atendente'})
            st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        if 'Modulos' in df.columns:
            top_modulos = df['Modulos'].value_counts().head(10)
            fig = px.pie(values=top_modulos.values, names=top_modulos.index,
                        title="Distribuição por Módulo")
            st.plotly_chart(fig, use_container_width=True)
    
    # GRÁFICO DE EVOLUÇÃO DIÁRIA MELHORADO
    if 'Data' in df.columns and not df.empty:
        st.subheader("📈 Evolução Diária de Atendimentos")
        
        fig = create_daily_evolution_chart(df)
        if fig:
            st.plotly_chart(fig, use_container_width=True)
            
            # Estatísticas adicionais
            daily_counts = df.groupby(df['Data'].dt.date).size()
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Média diária", f"{daily_counts.mean():.1f}")
            with col2:
                st.metric("Dia com mais atendimentos", daily_counts.max())
            with col3:
                st.metric("Dia com menos atendimentos", daily_counts.min())
            with col4:
                st.metric("Total de dias analisados", len(daily_counts))

# Função para Análise por Colaborador
def show_colaboradores(df):
    if df.empty:
        st.info("Nenhum dado encontrado com os filtros aplicados.")
        return
        
    if 'Atendente' not in df.columns:
        st.info("Coluna 'Atendente' não encontrada nos dados")
        return
        
    colaboradores = sorted(df['Atendente'].unique())
    selected_colab = st.selectbox("Selecione o colaborador:", colaboradores)
    
    if selected_colab:
        colab_data = df[df['Atendente'] == selected_colab]
        
        # Métricas do colaborador
        col1, col2, col3, col4, col5 = st.columns(5)
        
        with col1:
            st.metric("Total", len(colab_data))
        
        with col2:
            st.metric("Módulos", colab_data['Modulos'].nunique())
        
        with col3:
            st.metric("Dias", colab_data['Data'].nunique())
        
        with col4:
            st.metric("Tipos", colab_data['Tipos'].nunique() if 'Tipos' in colab_data.columns else 0)
        
        with col5:
            if colab_data['Data'].nunique() > 0:
                media_dia = len(colab_data) / colab_data['Data'].nunique()
                st.metric("Média/dia", f"{media_dia:.1f}")
        
        # Gráficos do colaborador
        col1, col2 = st.columns(2)
        
        with col1:
            if 'Tipos' in colab_data.columns and not colab_data.empty:
                tipos = colab_data['Tipos'].value_counts().head(8)
                fig = px.bar(tipos, orientation='v',
                            title="Tipos de Atendimento",
                            labels={'value': 'Quantidade', 'index': 'Tipo'})
                st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            if 'Modulos' in colab_data.columns and not colab_data.empty:
                modulos = colab_data['Modulos'].value_counts()
                fig = px.pie(values=modulos.values, names=modulos.index,
                            title="Módulos Atendidos")
                st.plotly_chart(fig, use_container_width=True)

# Função para Tipos de Atendimento
def show_tipos_atendimento(df):
    if df.empty:
        st.info("Nenhum dado encontrado com os filtros aplicados.")
        return
        
    if 'Tipos' not in df.columns:
        st.info("Coluna 'Tipos' não encontrada nos dados")
        return
        
    col1, col2 = st.columns(2)
    
    with col1:
        tipos_count = df['Tipos'].value_counts().head(15)
        fig = px.bar(tipos_count, orientation='v',
                    title="Top 15 Tipos de Atendimento",
                    labels={'value': 'Quantidade', 'index': 'Tipo'})
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        if 'Canais' in df.columns:
            canais_count = df['Canais'].value_counts()
            fig = px.pie(values=canais_count.values, names=canais_count.index,
                        title="Canais de Atendimento")
            st.plotly_chart(fig, use_container_width=True)

# Função para mostrar dados completos
def show_dados_completos(df):
    if df.empty:
        st.info("Nenhum dado encontrado com os filtros aplicados.")
        return
        
    st.subheader("📊 Dados Completos")
    
    search_term = st.text_input("🔍 Buscar em todos os campos:")
    
    if search_term:
        mask = pd.Series(False, index=df.index)
        for col in df.columns:
            if df[col].dtype == 'object':
                mask = mask | df[col].astype(str).str.contains(search_term, case=False, na=False)
        filtered_df = df[mask]
    else:
        filtered_df = df
    
    st.dataframe(filtered_df, use_container_width=True)
    
    csv = filtered_df.to_csv(index=False)
    st.download_button(
        label="📥 Download dos dados filtrados (CSV)",
        data=csv,
        file_name=f"atendimentos_filtrados_{datetime.now().strftime('%Y%m%d')}.csv",
        mime="text/csv"
    )

def diagnostic_test():
    """Teste completo de diagnóstico"""
    try:
        st.header("🔍 Diagnóstico da Conexão")
        
        # 1. Teste se o secret existe
        st.subheader("1. Verificando Secrets...")
        if "relatorio_set_out_account" not in st.secrets:
            st.error("❌ Secret 'relatorio_set_out_account' não encontrado")
            return False
        else:
            st.success("✅ Secret encontrado")
            
        # 2. Teste se as credenciais são válidas
        st.subheader("2. Verificando Credenciais...")
        try:
            scope = ['https://spreadsheets.google.com/feeds']
            credentials = service_account.Credentials.from_service_account_info(
                st.secrets["relatorio_set_out_account"], scopes=scope
            )
            st.success("✅ Credenciais válidas")
        except Exception as e:
            st.error(f"❌ Erro nas credenciais: {e}")
            return False
        
        # 3. Teste de autorização
        st.subheader("3. Autorizando...")
        try:
            client = gspread.authorize(credentials)
            st.success("✅ Autorização concedida")
        except Exception as e:
            st.error(f"❌ Erro na autorização: {e}")
            return False
        
        # 4. Teste de abertura da planilha
        st.subheader("4. Acessando Planilha...")
        try:
            sheet_id = "152DHhNzoLlUs0Vq_uRuVkfoq3C2A_lcJfJjambA6EWA"
            spreadsheet = client.open_by_key(sheet_id)
            st.success(f"✅ Planilha aberta: {spreadsheet.title}")
        except Exception as e:
            st.error(f"❌ Erro ao abrir planilha: {e}")
            st.info("📝 Tentando por URL...")
            try:
                sheet_url = "https://docs.google.com/spreadsheets/d/152DHhNzoLlUs0Vq_uRuVkfoq3C2A_lcJfJjambA6EWA/edit"
                spreadsheet = client.open_by_url(sheet_url)
                st.success(f"✅ Planilha aberta por URL: {spreadsheet.title}")
            except Exception as e2:
                st.error(f"❌ Erro também por URL: {e2}")
                return False
        
        # 5. Teste de leitura de dados
        st.subheader("5. Lendo Dados...")
        try:
            worksheet = spreadsheet.sheet1
            all_values = worksheet.get_all_values()
            st.success(f"✅ Dados lidos: {len(all_values)} linhas totais")
            
            if len(all_values) > 0:
                st.write("📋 Cabeçalho:", all_values[0])
                st.write("📊 Linhas de dados:", len(all_values) - 1)
            else:
                st.warning("⚠️ Planilha vazia")
                
        except Exception as e:
            st.error(f"❌ Erro ao ler dados: {e}")
            return False
        
        st.success("🎉 TODOS OS TESTES PASSARAM!")
        return True
        
    except Exception as e:
        st.error(f"❌ Erro geral no diagnóstico: {e}")
        return False
    
# =============================================================================
# FUNÇÃO DO ASSISTENTE IA 
# =============================================================================

def show_assistente_ia(df_filtrado, gemini_key=None):
    """Exibe a interface do assistente de IA com dados filtrados - VERSÃO FINAL CORRIGIDA"""
    st.header("🤖 Assistente de IA - Análise de Atendimentos")
    st.write("Faça perguntas em português sobre os dados de atendimentos e receba insights automatizados.")
    
    # Inicializar estado da sessão PARA O ASSISTENTE ESPECIFICAMENTE
    if 'assistant_responses' not in st.session_state:
        st.session_state.assistant_responses = []
    if 'current_question' not in st.session_state:
        st.session_state.current_question = ""
    if 'last_response' not in st.session_state:
        st.session_state.last_response = ""
    if 'processing_question' not in st.session_state:
        st.session_state.processing_question = False
    if 'assistant_initialized' not in st.session_state:
        st.session_state.assistant_initialized = True      
   
    # Configuração do modelo
    model_options = [
        '🚀 Gemini Pro - Análise Avançada',
        '⚡ Gemini Flash - Resposta Rápida' 
    ]

    col1, col2 = st.columns([2, 1])

    with col1:
        selected_model = st.selectbox(
            label='**Nível de análise:**',
            options=model_options,
            index=0,
            key='assistant_model'
        )
    
        if selected_model == '🚀 Gemini Pro - Análise Avançada':
            st.caption("💡 Análises profundas e insights detalhados")
        elif selected_model == '⚡ Gemini Flash - Resposta Rápida':
            st.caption("💡 Respostas rápidas para perguntas simples")
    
    with col2:
        st.write("")
        st.write("")
        if st.button("🔄 Limpar Histórico", key='reset_assistant'):
            st.session_state.assistant_responses = []
            st.session_state.last_response = ""
            st.session_state.current_question = ""
            st.session_state.processing_question = False
            st.success("✅ Histórico limpo!")
            st.rerun()
    
    st.markdown("---")
    
    # Área de pergunta - SEMPRE mostrar o valor atual
    user_question = st.text_area(
        '**Digite sua pergunta:**',
        placeholder='Ex: Existe algum padrão sazonal nos atendimentos? Quais são os módulos com mais atendimentos? Quem são os top atendentes?',
        height=100,
        key='assistant_question',
        value=st.session_state.current_question
    )
    
    # Atualizar a pergunta atual no session_state
    st.session_state.current_question = user_question
    
    col1, col2 = st.columns([1, 4])
    
    with col1:
        consultar_button = st.button('🔍 Consultar Assistente', type='primary', key='assistant_btn', use_container_width=True)
    
    with col2:
        if st.session_state.last_response and not st.session_state.processing_question:
            if st.button('📋 Copiar Resposta', key='copy_response', use_container_width=True):
                st.code(st.session_state.last_response, language='markdown')
                st.success("✅ Resposta copiada para a área de transferência!")
    
    # VERIFICAR SE HÁ UMA CONSULTA PENDENTE PARA PROCESSAR
    if consultar_button and user_question and not st.session_state.processing_question:
        # Marcar que estamos processando
        st.session_state.processing_question = True
        st.session_state.current_question = user_question
        
        # Armazenar a pergunta para processamento
        st.session_state.pending_question = user_question
        st.session_state.pending_model = selected_model
        
        # Forçar rerun imediatamente para mostrar o spinner
        st.rerun()
    
    # PROCESSAR A CONSULTA APÓS O RERUN (quando processing_question = True)
    if st.session_state.get('processing_question', False) and st.session_state.get('pending_question'):
        # Container para o spinner
        processing_placeholder = st.empty()
        
        with processing_placeholder.container():
            with st.spinner('🤔 Analisando os dados filtrados... Isso pode levar alguns segundos'):
                try:
                    # Importar e criar assistente
                    from novo_assistente import consultar_assistente
                    
                    # Executar consulta com os dados pendentes
                    resposta = consultar_assistente(
                        pergunta=st.session_state.pending_question,
                        df_filtrado=df_filtrado,
                        tipo_modelo=st.session_state.pending_model,
                        gemini_key=gemini_key

                    )
                    
                    # Salvar no histórico
                    nova_resposta = {
                        'pergunta': st.session_state.pending_question,
                        'resposta': resposta,
                        'modelo': st.session_state.pending_model,
                        'timestamp': datetime.now().strftime('%d/%m/%Y %H:%M'),
                        'registros': len(df_filtrado)
                    }
                    
                    st.session_state.assistant_responses.append(nova_resposta)
                    st.session_state.last_response = resposta
                    
                except Exception as e:
                    error_msg = f"❌ Erro ao consultar assistente: {str(e)}"
                    st.error(error_msg)
                    st.session_state.last_response = error_msg
        
        # Limpar estados de processamento
        st.session_state.processing_question = False
        st.session_state.pending_question = None
        st.session_state.pending_model = None
        
        # Limpar o placeholder do spinner
        processing_placeholder.empty()
        
        # Rerun final para mostrar a resposta
        st.rerun()
    
    # MOSTRAR RESPOSTAS - APENAS quando não estiver processando
    if not st.session_state.processing_question:
        # Mostrar última resposta
        if st.session_state.last_response:
            st.markdown("---")
            st.subheader("📋 Resposta:")
            st.markdown(st.session_state.last_response)
            
            # Informações do contexto
            with st.expander("ℹ️ Informações do contexto"):
                st.write(f"**Modelo usado:** {selected_model}")
                st.write(f"**Registros analisados:** {len(df_filtrado)}")
                st.write(f"**Data/hora:** {datetime.now().strftime('%d/%m/%Y %H:%M')}")
        
        # Mostrar histórico de conversas
        if len(st.session_state.assistant_responses) > 1:
            st.markdown("---")
            st.subheader("📚 Histórico de Consultas")
            
            # Mostrar do mais recente para o mais antigo (exceto o último que já está mostrado)
            for i, resp in enumerate(reversed(st.session_state.assistant_responses[:-1])):
                with st.expander(f"🗨️ {resp['pergunta'][:50]}... - {resp['timestamp']}"):
                    st.write(f"**Pergunta:** {resp['pergunta']}")
                    st.markdown("**Resposta:**")
                    st.markdown(resp['resposta'])
                    st.caption(f"Modelo: {resp['modelo']} | Registros: {resp['registros']} | {resp['timestamp']}")


# INTERFACE PRINCIPAL
def main():
    st.title("📊 Dashboard de Atendimentos - SAI")
    st.markdown("---")
    
    # Sidebar com upload
    uploaded_file = create_sidebar()
    
    # Carregar dados
    df = load_data(uploaded_file)
    
    if df.empty:
        st.info("""
        ## 📁 Como usar o dashboard
        
        1. **Arquivo local**: Coloque `relatorio_set_out.xls` na mesma pasta deste app
        2. **Upload**: Ou use o upload na sidebar para um arquivo diferente
        """)
        return
    
    # =============================================================================
    # FILTRO DE DATA CORRIGIDO - NOVA VERSÃO SIMPLIFICADA
    # =============================================================================
    
    st.sidebar.markdown("---")
    st.sidebar.header("📅 Filtros por Período")
    
    if 'Data' in df.columns:
        # Garantir que as datas são válidas
        df['Data'] = pd.to_datetime(df['Data'], errors='coerce')
        df = df.dropna(subset=['Data'])
        
        # Obter min e max reais dos dados
        min_date = df['Data'].min().date()
        max_date = df['Data'].max().date()
        
        st.sidebar.write(f"📊 Período disponível: {min_date.strftime('%d/%m/%Y')} a {max_date.strftime('%d/%m/%Y')}")
        
        # Filtro simplificado - usar datas padrão que cobrem TODOS os dados
        col1, col2 = st.sidebar.columns(2)
        with col1:
            start_date = st.date_input(
                "Data inicial", 
                value=min_date,
                min_value=min_date,
                max_value=max_date
            )
        with col2:
            end_date = st.date_input(
                "Data final", 
                value=max_date,
                min_value=min_date,
                max_value=max_date
            )
        
        # Aplicar filtro diretamente
        mask = (df['Data'].dt.date >= start_date) & (df['Data'].dt.date <= end_date)
        df_filtered = df[mask]
        
        # Mostrar resultado do filtro
        st.sidebar.success(f"✅ Registros no período: {len(df_filtered)} de {len(df)}")
        
    else:
        df_filtered = df
        st.sidebar.warning("⚠️ Coluna 'Data' não encontrada nos dados")
    
    # =============================================================================
    # FILTROS ADICIONAIS
    # =============================================================================
    
    st.sidebar.header("🎯 Filtros Adicionais")
    
    # Filtro de atendentes
    if 'Atendente' in df_filtered.columns:
        atendentes = ['Todos'] + sorted(df_filtered['Atendente'].unique().tolist())
        selected_atendente = st.sidebar.selectbox("Atendente", atendentes)
        
        if selected_atendente != 'Todos':
            df_filtered = df_filtered[df_filtered['Atendente'] == selected_atendente]
    
    # Filtro de módulos
    if 'Modulos' in df_filtered.columns:
        modulos = ['Todos'] + sorted(df_filtered['Modulos'].unique().tolist())
        selected_modulo = st.sidebar.selectbox("Módulo", modulos)
        
        if selected_modulo != 'Todos':
            df_filtered = df_filtered[df_filtered['Modulos'] == selected_modulo]
    
    # Filtro de UF
    if 'UF' in df_filtered.columns:
        uf_options = ['TODOS'] + sorted(df_filtered['UF'].unique().tolist())
        selected_uf = st.sidebar.selectbox("📍 UF", uf_options)
        if selected_uf != 'TODOS':
            df_filtered = df_filtered[df_filtered['UF'] == selected_uf]
    
    # Filtro de Categorias
    if 'Categorias' in df_filtered.columns:
        categoria_options = ['TODAS'] + sorted(df_filtered['Categorias'].unique().tolist())
        selected_categoria = st.sidebar.selectbox("📂 Categoria", categoria_options)
        if selected_categoria != 'TODAS':
            df_filtered = df_filtered[df_filtered['Categorias'] == selected_categoria]

    # =============================================================================
    # BUSCA E VERIFICAÇÃO DA CHAVE GEMINI (NOVO BLOCO CRÍTICO)
    # =============================================================================
    gemini_key = None
    if "gemini" in st.secrets and "api_key" in st.secrets.gemini:
        # 1. Tenta buscar a chave na seção estruturada [gemini] do secrets.toml (Streamlit Cloud)
        gemini_key = st.secrets.gemini.api_key
        st.sidebar.success("🔑 Chave Gemini carregada via st.secrets!")
    elif os.getenv('GEMINI_API_KEY'):
        # 2. Tenta buscar como variável de ambiente (Local ou Secrets raiz)
        gemini_key = os.getenv('GEMINI_API_KEY')
        st.sidebar.info("🔑 Chave Gemini carregada via os.getenv (ambiente local)!")
    else:
        st.sidebar.error("❌ Chave Gemini NÃO encontrada. O Assistente IA estará desativado.")
    
    # =============================================================================
    # MÉTRICAS PRINCIPAIS
    # =============================================================================
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric("Registros filtrados", len(df_filtered))
    
    with col2:
        periodo_filtrado = format_periodo_filtrado(df_filtered)
        st.write("**Período filtrado:**")
        st.write(f"**{periodo_filtrado}**")
    
    with col3:
        dias_registro = df_filtered['Data'].nunique() if 'Data' in df_filtered.columns and not df_filtered.empty else 0
        st.metric("Dias com registro", dias_registro)
    
    with col4:
        st.metric("Atendentes", df_filtered['Atendente'].nunique() if 'Atendente' in df_filtered.columns else 0)
    
    with col5:
        st.metric("Módulos", df_filtered['Modulos'].nunique() if 'Modulos' in df_filtered.columns else 0)
    
    # Indicador de filtros ativos
    total_original = len(df)
    total_filtrado = len(df_filtered)
    
    if total_filtrado != total_original:
        st.sidebar.success(f"✅ Filtros ativos: {total_filtrado} de {total_original} registros")
    
    # =============================================================================
    # ABAS PARA ANÁLISES
    # =============================================================================
    
    st.markdown("---")
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "📈 Visão Geral", 
        "👥 Análise por Colaborador", 
        "📋 Tipos de Atendimento",
        "🔧 Análise por Módulo",
        "📊 Dados",
        "🤖 Assistente IA"
        
    ])
    
    with tab1:
        show_overview(df_filtered)
    
    with tab2:
        show_colaboradores(df_filtered)
    
    with tab3:
        show_tipos_atendimento(df_filtered)
    
    with tab4:
        show_analise_modulos(df_filtered)
    
    with tab5:
        show_dados_completos(df_filtered)

    with tab6:  
        show_assistente_ia(df_filtered, gemini_key=gemini_key)
  

if __name__ == "__main__":
    main()