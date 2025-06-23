import streamlit as st
import pandas as pd
from PIL import Image
import time
import requests
from datetime import datetime
import concurrent.futures
import threading
import os
import dotenv

# Carrega variáveis de ambiente
dotenv.load_dotenv()

# ========== CONFIGURAÇÕES ========== 
USUARIOS_VALIDOS = {
    "admin": os.getenv("ADMIN_PASSWORD", "admin123"),
    "operator": os.getenv("OPERATOR_PASSWORD", "operator123")
}

# ========== ESTILO PREMIUM ATUALIZADO ==========
st.set_page_config(
    page_title="VTEX Master Data Integration",
    page_icon="🤖",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# ... (o mesmo CSS fornecido anteriormente, com cores neutras) ...

# ========== FUNÇÕES ==========
def carregar_logo():
    try:
        logo = Image.open("src/assets/generic_logo.png")
        st.markdown('<div class="logo-container">', unsafe_allow_html=True)
        st.image(logo, width=200)
        st.markdown('</div>', unsafe_allow_html=True)
    except:
        st.markdown('<div class="logo-container">', unsafe_allow_html=True)
        st.image("https://via.placeholder.com/200x60?text=BRAND+LOGO", width=200)
        st.markdown('</div>', unsafe_allow_html=True)

def processar_cliente(row, headers, usuario_exec, lock, stats, req_count, logs):
    email = row.email
    promo_aniv = bool(row.isPromoAniversario)
    promo_recompra = bool(row.isPromoRecompra)
    datahora = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    
    try:
        # Configuração dinâmica da URL VTEX
        vtex_account = os.getenv("VTEX_ACCOUNT_NAME", "youraccountname")
        base_url = f"https://{vtex_account}.vtexcommercestable.com.br"
        
        # Requisição SEARCH
        with lock:
            req_count['search'] += 1
            req_count['total'] += 1
            
        url_get = f"{base_url}/api/dataentities/CL/search"
        params = {"email": email, "_fields": "id,isPromoAniversario,isPromoRecompra"}
        r = requests.get(url_get, headers=headers, params=params)

        if r.status_code == 200:
            data = r.json()
            if data:
                cliente = data[0]
                id_cliente = cliente.get("id", "")
                promo_aniv_atual = cliente.get("isPromoAniversario", False)
                promo_recompra_atual = cliente.get("isPromoRecompra", False)

                if promo_aniv != promo_aniv_atual or promo_recompra != promo_recompra_atual:
                    # Requisição UPDATE
                    with lock:
                        req_count['update'] += 1
                        req_count['total'] += 1
                        
                    url_update = f"{base_url}/api/dataentities/CL/documents/{id_cliente}"
                    payload = {
                        "email": email,
                        "isPromoAniversario": promo_aniv,
                        "isPromoRecompra": promo_recompra
                    }
                    requests.put(url_update, headers=headers, json=payload)
                    acao = "Atualizado"
                    with lock:
                        stats['atualizados'] += 1
                else:
                    acao = "Sem mudanças"
                    with lock:
                        stats['sem_mudancas'] += 1

                with lock:
                    logs.append({
                        "Actions": acao,
                        "Email do Cliente": email,
                        "Data/Hora": datahora,
                        "Benefício Alterado": "isPromoAniversario",
                        "Valor Novo": promo_aniv,
                        "Valor Anterior": promo_aniv_atual,
                        "Usuário": usuario_exec
                    })
                    logs.append({
                        "Actions": acao,
                        "Email do Cliente": email,
                        "Data/Hora": datahora,
                        "Benefício Alterado": "isPromoRecompra",
                        "Valor Novo": promo_recompra,
                        "Valor Anterior": promo_recompra_atual,
                        "Usuário": usuario_exec
                    })
            else:
                # Requisição CREATE
                with lock:
                    req_count['create'] += 1
                    req_count['total'] += 1
                    
                url_create = f"{base_url}/api/dataentities/CL/documents"
                payload = {
                    "email": email,
                    "isPromoAniversario": promo_aniv,
                    "isPromoRecompra": promo_recompra
                }
                requests.post(url_create, headers=headers, json=payload)
                acao = "Criado"
                with lock:
                    stats['criados'] += 1
                    
                with lock:
                    logs.append({
                        "Actions": acao,
                        "Email do Cliente": email,
                        "Data/Hora": datahora,
                        "Benefício Alterado": "isPromoAniversario",
                        "Valor Novo": promo_aniv,
                        "Valor Anterior": "null",
                        "Usuário": usuario_exec
                    })
                    logs.append({
                        "Actions": acao,
                        "Email do Cliente": email,
                        "Data/Hora": datahora,
                        "Benefício Alterado": "isPromoRecompra",
                        "Valor Novo": promo_recompra,
                        "Valor Anterior": "null",
                        "Usuário": usuario_exec
                    })
        else:
            with lock:
                logs.append({
                    "Actions": "Erro",
                    "Email do Cliente": email,
                    "Data/Hora": datahora,
                    "Benefício Alterado": "N/A",
                    "Valor Novo": "N/A",
                    "Valor Anterior": "N/A",
                    "Usuário": usuario_exec,
                    "Erro": f"Status code: {r.status_code}"
                })
    except Exception as e:
        with lock:
            logs.append({
                "Actions": "Erro",
                "Email do Cliente": email,
                "Data/Hora": datahora,
                "Benefício Alterado": "N/A",
                "Valor Novo": "N/A",
                "Valor Anterior": "N/A",
                "Usuário": usuario_exec,
                "Erro": str(e)
            })
    finally:
        with lock:
            stats['processados'] += 1

def tela_login():
    carregar_logo()
    
    with st.container():
        st.markdown('<h1>🔐 VTEX Master Data Integration</h1>', unsafe_allow_html=True)
        st.markdown('<p style="text-align:center;">Acesso restrito à equipe autorizada</p>', unsafe_allow_html=True)
        
        with st.form("login_form"):
            usuario = st.text_input("**USUÁRIO**", placeholder="Digite seu ID de acesso")
            senha = st.text_input("**SENHA**", type="password", placeholder="••••••••")
            submit = st.form_submit_button("🔐 ACESSAR SISTEMA", type="primary")
            
            if submit:
                if usuario in USUARIOS_VALIDOS and senha == USUARIOS_VALIDOS[usuario]:
                    st.session_state["logado"] = True
                    st.session_state["usuario"] = usuario
                    st.rerun()
                else:
                    st.warning("Credenciais inválidas. Tente novamente.")
                    
        st.markdown('</div>', unsafe_allow_html=True)
        
    st.markdown("""
        <div style="text-align:center; margin-top:2rem; color:#6b7280;">
            <p>v1.2.0 | Sistema de integração VTEX | © 2025</p>
        </div>
    """, unsafe_allow_html=True)
    st.markdown('<p style="text-align:center;">Generic Integration System</p>', unsafe_allow_html=True)

def tela_principal():
    carregar_logo()
    
    st.markdown(f'<div class="user-badge">👤 Usuário: {st.session_state["usuario"].upper()}</div>', unsafe_allow_html=True)
    
    with st.container():
        st.markdown('<h1>🚀 Master Data Operations</h1>', unsafe_allow_html=True)
        st.markdown('<p style="font-size:1.1rem;">Bulk update operations for VTEX master data</p>', unsafe_allow_html=True)
        
        st.markdown('<div class="section-title"><h2>📤 Upload spreadsheet</h2></div>', unsafe_allow_html=True)
        arquivo = st.file_uploader("", type=["xlsx"], key="uploader", 
                                  help="Select customer data spreadsheet",
                                  label_visibility="collapsed")
        st.markdown('</div>', unsafe_allow_html=True)

        if arquivo:
            try:
                df = pd.read_excel(arquivo)
                if 'email' not in df.columns:
                    st.warning("Spreadsheet must contain 'email' column")
                    st.stop()

                # Processamento dos dados
                df['email'] = df['email'].astype(str).str.strip().str.lower()
                df["isPromoAniversario"] = df.get("isPromoAniversario", False).fillna(False).astype(bool)
                df["isPromoRecompra"] = df.get("isPromoRecompra", False).fillna(False).astype(bool)

                with st.expander("🔍 Preview Data", expanded=True):
                    st.dataframe(df.head(10), use_container_width=True)
                    st.caption(f"Total records: {len(df)}")

                # Estatísticas
                st.markdown('<div class="section-title"><h2>📊 Data Overview</h2></div>', unsafe_allow_html=True)
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.markdown(f"""
                        <div class="stat-card">
                            <div class="icon-box">👥</div>
                            <div class="stat-value">{len(df)}</div>
                            <div class="stat-label">CUSTOMERS</div>
                        </div>
                    """, unsafe_allow_html=True)
                with col2:
                    st.markdown(f"""
                        <div class="stat-card">
                            <div class="icon-box">🎂</div>
                            <div class="stat-value">{df['isPromoAniversario'].sum()}</div>
                            <div class="stat-label">PROMO 1</div>
                        </div>
                    """, unsafe_allow_html=True)
                with col3:
                    st.markdown(f"""
                        <div class="stat-card">
                            <div class="icon-box">🔄</div>
                            <div class="stat-value">{df['isPromoRecompra'].sum()}</div>
                            <div class="stat-label">PROMO 2</div>
                        </div>
                    """, unsafe_allow_html=True)

                st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)

                if st.button("⚡ Execute VTEX Integration (Multi-Thread)", use_container_width=True, key="run_integration"):
                    if len(df) > 1000000:
                        st.warning("Limit exceeded: Max 10,000 records per operation")
                        st.stop()

                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    
                    # Configuração VTEX via variáveis de ambiente
                    headers = {
                        "Accept": "application/json",
                        "Content-Type": "application/json",
                        "X-VTEX-API-AppKey": os.getenv("VTEX_APP_KEY"),
                        "X-VTEX-API-AppToken": os.getenv("VTEX_APP_TOKEN")
                    }
                    
                    num_threads = int(os.getenv("THREAD_COUNT", 4))
                    st.info(f"🚀 Using {num_threads} threads for parallel processing")
                    
                    # Estruturas para monitoramento
                    lock = threading.Lock()
                    stats = {'atualizados': 0, 'criados': 0, 'sem_mudancas': 0, 'processados': 0}
                    req_count = {'total': 0, 'search': 0, 'update': 0, 'create': 0}
                    logs = []
                    
                    usuario_exec = st.session_state["usuario"]
                    total_registros = len(df)
                    
                    placeholder = st.empty()
                    start_time = time.time()
                    
                    # Processamento paralelo
                    with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
                        futures = [executor.submit(
                            processar_cliente, 
                            row, 
                            headers, 
                            usuario_exec, 
                            lock, 
                            stats, 
                            req_count, 
                            logs
                        ) for row in df.itertuples()]
                        
                        # Monitoramento em tempo real
                        while stats['processados'] < total_registros:
                            progresso = stats['processados'] / total_registros
                            progress_bar.progress(progresso)
                            
                            elapsed_time = time.time() - start_time
                            req_per_min = (req_count['total'] / elapsed_time) * 60 if elapsed_time > 0 else 0
                            
                            status_text.text(
                                f"⏳ Processing: {stats['processados']}/{total_registros} | "
                                f"{int(progresso*100)}% | "
                                f"{req_per_min:.1f} req/min"
                            )
                            
                            # Atualização da UI
                            with placeholder.container():
                                st.markdown('<div class="section-title"><h2>⚙️ Operation Status</h2></div>', unsafe_allow_html=True)
                                
                                # Colunas de estatísticas
                                cols = st.columns(4)
                                metrics = [
                                    ("UPDATED", stats['atualizados']),
                                    ("CREATED", stats['criados']),
                                    ("NO CHANGES", stats['sem_mudancas']),
                                    ("PROCESSED", stats['processados'])
                                ]
                                
                                for col, (label, value) in zip(cols, metrics):
                                    with col:
                                        st.markdown(f"""
                                            <div class="stat-card">
                                                <div class="stat-value">{value}</div>
                                                <div class="stat-label">{label}</div>
                                            </div>
                                        """, unsafe_allow_html=True)
                                
                                # Requisições
                                st.markdown('<div class="section-title"><h3>📡 Requests</h3></div>', unsafe_allow_html=True)
                                req_cols = st.columns(4)
                                req_metrics = [
                                    ("TOTAL", req_count['total']),
                                    ("SEARCH", req_count['search']),
                                    ("UPDATE", req_count['update']),
                                    ("CREATE", req_count['create'])
                                ]
                                
                                for col, (label, value) in zip(req_cols, req_metrics):
                                    with col:
                                        st.markdown(f"""
                                            <div class="stat-card">
                                                <div class="stat-value">{value}</div>
                                                <div class="stat-label">{label}</div>
                                            </div>
                                        """, unsafe_allow_html=True)
                                
                                st.markdown(f"<div class='stat-label'>Speed: <strong>{req_per_min:.1f} req/min</strong></div>", unsafe_allow_html=True)
                            
                            time.sleep(0.5)

                    progress_bar.progress(1.0)
                    status_text.success(f"✅ Operation completed! Processed {total_registros} records in {elapsed_time:.1f} seconds")
                    
                    # Geração de relatório
                    df_logs = pd.DataFrame(logs)
                    
                    st.balloons()
                    st.markdown('<div class="section-title"><h2>📊 Final Report</h2></div>', unsafe_allow_html=True)
                    
                    # Resumo
                    report_cols = st.columns(3)
                    with report_cols[0]:
                        st.markdown(f"""
                            <div class="report-card">
                                <div class="icon-box">🔄</div>
                                <h3>Updated</h3>
                                <div class="stat-value">{stats['atualizados']}</div>
                                <p>Modified records</p>
                            </div>
                        """, unsafe_allow_html=True)
                    with report_cols[1]:
                        st.markdown(f"""
                            <div class="report-card">
                                <div class="icon-box">✨</div>
                                <h3>Created</h3>
                                <div class="stat-value">{stats['criados']}</div>
                                <p>New records</p>
                            </div>
                        """, unsafe_allow_html=True)
                    with report_cols[2]:
                        st.markdown(f"""
                            <div class="report-card">
                                <div class="icon-box">⏭️</div>
                                <h3>No Changes</h3>
                                <div class="stat-value">{stats['sem_mudancas']}</div>
                                <p>Unchanged records</p>
                            </div>
                        """, unsafe_allow_html=True)
                    
                    # Botão de download
                    csv = df_logs.to_csv(index=False, sep=';', encoding='utf-8-sig')
                    st.download_button(
                        "💾 Download Full Report", 
                        data=csv, 
                        file_name=f"vtex_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv", 
                        mime="text/csv",
                        use_container_width=True
                    )

            except Exception as e:
                st.error(f"Critical error: {str(e)}")

# ========== CONTROLE ==========
if "logado" not in st.session_state:
    tela_login()
else:
    tela_principal()
