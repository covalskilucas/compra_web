import streamlit as st
import json
import os
import re
from datetime import datetime
import cv2
import easyocr
import numpy as np
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
import io

# Configurações Iniciais da Página Web
st.set_page_config(page_title="Gerenciador de Compras", layout="wide")

ARQUIVO_DADOS = "historico_compras.json"
CATEGORIAS = [
    "Mercearia (Arroz, feijão, etc)", "Hortifrúti (Frutas e legumes)", 
    "Açougue / Peixaria", "Laticínios / Frios", "Limpeza", 
    "Higiene / Perfumaria", "Bebidas", "Padaria", "Outros"
]

# Inicializa o EasyOCR (armazenado em cache para não recarregar a cada clique)
@st.cache_resource
def carregar_leitor():
    return easyocr.Reader(['pt'])

leitor_ocr = carregar_leitor()

# --- FUNÇÕES DE MANIPULAÇÃO DE DADOS ---
def carregar_historico():
    if os.path.exists(ARQUIVO_DADOS):
        try:
            with open(ARQUIVO_DADOS, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {}
    return {}

def salvar_historico(dados):
    with open(ARQUIVO_DADOS, "w", encoding="utf-8") as f:
        json.dump(dados, f, indent=4, ensure_ascii=False)

# Inicializa o estado da sessão web do Streamlit
if "historico" not in st.session_state:
    st.session_state.historico = carregar_historico()

# --- INTERFACE WEB ---
st.title("🛒 Gerenciador de Compras com Scanner OCR")

# Seleção de Período
col1, col2 = st.columns(2)
with col1:
    mes = st.selectbox("Mês", ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"])
with col2:
    ano = st.selectbox("Ano", [str(a) for a in range(datetime.now().year - 1, datetime.now().year + 4)])

chave_periodo = f"{mes}-{ano}"
if chave_periodo not in st.session_state.historico:
    st.session_state.historico[chave_periodo] = {"orcamento": 0.0, "itens": []}

# Definição de Orçamento
dados_mes = st.session_state.historico[chave_periodo]
novo_orcamento = st.number_input("Definir Orçamento (R$)", min_value=0.0, value=float(dados_mes["orcamento"]), step=50.0)
if novo_orcamento != dados_mes["orcamento"]:
    dados_mes["orcamento"] = novo_orcamento
    salvar_historico(st.session_state.historico)

# --- SCANNER DE CÂMERA WEB ---
st.subheader("📸 Scanner de Preço por Imagem")
foto_camera = st.camera_input("Tire uma foto do preço do produto")

preco_sugerido = 0.0
if foto_camera is not None:
    # Converte a imagem da web para o formato do OpenCV
    bytes_data = foto_camera.getvalue()
    cv_img = cv2.imdecode(np.frombuffer(bytes_data, np.uint8), cv2.IMREAD_COLOR)
    cinza = cv2.cvtColor(cv_img, cv2.COLOR_BGR2GRAY)
    
    # Executa o OCR
    resultado = leitor_ocr.readtext(cinza)
    texto_detectado = " ".join([texto[1] for texto in resultado])
    
    valores_encontrados = re.findall(r'\d+[\.,]\d{2}', texto_detectado)
    if valores_encontrados:
        preco_sugerido = float(valores_encontrados[0].replace(",", "."))
        st.success(f"Preço detectado pelo Scanner: R$ {preco_sugerido:.2f}")
    else:
        st.warning("Não foi possível detectar o preço claramente. Digite manualmente abaixo.")

# --- FORMULÁRIO DE ENTRADA ---
st.subheader("✏️ Adicionar Novo Item")
with st.form("novo_item_form", clear_on_submit=True):
    nome_prod = st.text_input("Produto")
    qtd_prod = st.number_input("Quantidade", min_value=1, value=1)
    # Usa o preço sugerido pelo OCR se disponível
    preco_prod = st.number_input("Preço Unitário (R$)", min_value=0.0, value=preco_sugerido, step=0.5)
    categoria_prod = st.selectbox("Categoria", CATEGORIAS)
    
    bt_adicionar = st.form_submit_button("Inserir Produto")
    
    if bt_adicionar and nome_prod:
        novo_produto = {"nome": nome_prod, "quantidade": qtd_prod, "preco": preco_prod, "categoria": categoria_prod, "carrinho": False}
        dados_mes["itens"].append(novo_produto)
        salvar_historico(st.session_state.historico)
        st.rerun()

# --- EXIBIÇÃO DOS RESULTADOS ---
st.subheader("📋 Itens Cadastrados")
if dados_mes["itens"]:
    # Mostra os itens em uma tabela simples
    st.write(dados_mes["itens"])
    
    total_gasto = sum(i["quantidade"] * i["preco"] for i in dados_mes["itens"])
    saldo = dados_mes["orcamento"] - total_gasto
    
    st.metric("Orçamento", f"R$ {dados_mes['orcamento']:.2f}")
    st.metric("Total Gasto", f"R$ {total_gasto:.2f}")
    st.metric("Saldo Restante", f"R$ {saldo:.2f}", delta=saldo)
else:
    st.info("Nenhum item cadastrado para este período.")