import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import gspread
from google.oauth2 import service_account
from datetime import datetime
import os

# Configuração da página
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
        # Opção 1: Arquivo enviado via upload (prioridade)
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
        
        # Opção 2: Google Sheets - NOVA PLANILHA relatorio_set_out
        try:
            # Configuração do Google Sheets API
            scope = [
                'https://spreadsheets.google.com/feeds',
                'https://www.googleapis.com/auth/drive',
                'https://www.googleapis.com/auth/spreadsheets'
            ]
            
            # NOVAS CREDENCIAIS - nome diferente
            credentials = service_account.Credentials.from_service_account_info(
                st.secrets["relatorio_set_out_account"], scopes=scope
            )
            
            client = gspread.authorize(credentials)
            
            sheet_url = "https://docs.google.com/spreadsheets/d/152DHhNzoLlUs0Vq_uRuVkfoq3C2A_lcJfJjambA6EWA/edit?gid=804702972#gid=804702972"
            
            # Abre a planilha pela URL
            spreadsheet = client.open_by_url(sheet_url)
            
            # Pega a primeira aba (ajuste se necessário)
            worksheet = spreadsheet.sheet1
            
            # Obtém TODOS os valores
            all_values = worksheet.get_all_values()
            
            st.sidebar.write(f"📊 Planilha: {spreadsheet.title}")
            st.sidebar.write(f"📏 Dimensões: {worksheet.row_count} linhas × {worksheet.col_count} colunas")
            st.sidebar.write(f"🔍 Linhas encontradas: {len(all_values)}")
            
            if len(all_values) > 1:
                headers = all_values[0]
                data = all_values[1:]
                df = pd.DataFrame(data, columns=headers)
                
                # DEBUG: Mostrar dados brutos
                st.sidebar.write("📋 DEBUG - Dados brutos (primeiras 2 linhas):")
                st.sidebar.write(df.head(2))
                if 'Data' in df.columns:
                    st.sidebar.write(f"📅 Amostra de datas brutas: {df['Data'].head(3).tolist()}")
                
                st.sidebar.success(f"✅ Dados carregados: {len(df)} registros")
                
                # Verificação de quantidade
                if len(df) >= 1300:
                    st.sidebar.success("🎉 Todos os registros foram carregados!")
                elif len(df) > 586:
                    st.sidebar.success(f"📈 Melhoria: {len(df)} registros (antes: 586)")
                else:
                    st.sidebar.info(f"📊 Carregados {len(df)} registros")
                
                return clean_data(df)
            else:
                st.sidebar.warning("Planilha vazia ou apenas cabeçalho")
                return create_sample_data()
            
        except Exception as e:
            st.sidebar.error(f"❌ Erro Google Sheets: {str(e)}")
            st.sidebar.info("📋 Usando dados de exemplo")
            return create_sample_data()
            
    except Exception as e:
        st.sidebar.error(f"❌ Erro geral: {str(e)}")
        return create_sample_data()
    
def test_relatorio_connection():
    """Testa a conexão com a planilha relatorio_set_out"""
    try:
        scope = ['https://spreadsheets.google.com/feeds']
        credentials = service_account.Credentials.from_service_account_info(
            st.secrets["relatorio_set_out_account"], scopes=scope
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
        
        # Mostra as primeiras linhas para confirmar
        if len(all_values) > 0:
            st.write("👀 Primeiras linhas:")
            for i, row in enumerate(all_values[:3]):
                st.write(f"Linha {i}: {row}")
        
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
    
    # DEBUG: Mostrar amostra das datas antes da correção
    st.sidebar.write("🔍 DEBUG - Datas antes da correção:")
    st.sidebar.write(df['Data'].head(3))
    
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
                st.sidebar.success(f"✅ Formato detectado: {fmt}")
                break
        except:
            continue
    
    # Se ainda não converteu, tentar método genérico
    if df['Data'].isna().all():
        df['Data'] = pd.to_datetime(df['Data'], errors='coerce')
    
    # Remover registros com datas inválidas
    datas_invalidas = df[df['Data'].isna()]
    if len(datas_invalidas) > 0:
        st.sidebar.warning(f"⚠️ {len(datas_invalidas)} registros com data inválida removidos")
        df = df.dropna(subset=['Data'])
    
    # DEBUG: Mostrar amostra das datas depois da correção
    st.sidebar.write("📅 DEBUG - Datas depois da correção:")
    st.sidebar.write(df['Data'].head(3))
    
    return df


def clean_data(df):
    """Função para limpeza e padronização dos dados"""
    
    # PRIMEIRO: Corrigir as datas
    df = corrigir_datas(df)
    
    # Converter data (fallback)
    date_columns = ['Data', 'DATA', 'data', 'Date', 'date']
    for col in date_columns:
        if col in df.columns and col != 'Data':  # Já corrigimos a coluna 'Data'
            df['Data'] = pd.to_datetime(df[col], errors='coerce')
            break
    
    # Se não encontrou coluna de data, criar uma dummy
    if 'Data' not in df.columns or df['Data'].isna().all():
        df['Data'] = pd.to_datetime('today')
        st.sidebar.warning("⚠️ Nenhuma data válida encontrada, usando data atual")
    
    # DEBUG: Mostrar período real após limpeza
    if 'Data' in df.columns and not df.empty:
        min_date = df['Data'].min().date()
        max_date = df['Data'].max().date()
        st.sidebar.success(f"📅 Período real: {min_date} a {max_date}")
    
    # Preencher valores vazios
    fill_columns = {
        'UF': 'NÃO INFORMADO',
        'Atendente': 'NÃO INFORMADO', 
        'Categorias': 'NÃO INFORMADA',
        'Tipos': 'NÃO INFORMADO',
        'Modulos': 'NÃO INFORMADO',
        'Canais': 'NÃO INFORMADO'
    }
    
    for col, default_value in fill_columns.items():
        if col in df.columns:
            df[col] = df[col].fillna(default_value)
    
    return df

def create_sample_data():
    """Cria dados de exemplo"""
    import datetime
    sample_data = {
        'Data': [datetime.datetime.now() - datetime.timedelta(days=x) for x in range(10)],
        'UF': ['SP', 'RJ', 'MG', 'RS', 'PR'] * 2,
        'Atendente': ['Ana', 'João', 'Maria', 'Pedro', 'Carla'] * 2,
        'Categorias': ['Suporte', 'Vendas', 'Financeiro', 'Técnico', 'Outros'] * 2,
        'Tipos': ['Consulta', 'Problema', 'Sugestão', 'Elogio', 'Reclamação'] * 2,
        'Modulos': ['Módulo A', 'Módulo B', 'Módulo C'] * 3 + ['Módulo D'],
        'Canais': ['Chat', 'Email', 'Telefone', 'WhatsApp'] * 2 + ['Chat', 'Email']
    }
    return pd.DataFrame(sample_data)

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

# INTERFACE PRINCIPAL
def main():
    st.title("📊 Dashboard de Atendimentos - IMAP")
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
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📈 Visão Geral", 
        "👥 Análise por Colaborador", 
        "📋 Tipos de Atendimento",
        "🔧 Análise por Módulo",
        "📊 Dados"
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
    
    # Informações do dataset
    st.sidebar.header("ℹ️ Informações do Dataset")
    st.sidebar.write(f"Registros totais: {len(df)}")
    st.sidebar.write(f"Registros filtrados: {len(df_filtered)}")
    st.sidebar.write(f"Colunas: {len(df.columns)}")
    
    # Botão de teste de conexão
    if st.sidebar.button("🧪 Testar Conexão relatorio_set_out"):
        test_relatorio_connection()

if __name__ == "__main__":
    main()