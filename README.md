# 🛠️ VTEX Customer Promotion Updater

Exemplo open‑source de integração entre planilhas e APIs da VTEX, voltado para automação de cadastros de clientes com promoções de aniversário ou recompra.

---

## Funcionalidades

- Upload de planilhas `.xlsx` com dados de clientes;
- Processamento paralelizado para acelerar;
- Integração com VTEX Data Entities API;
- Atualização/criação de atributos personalizados;
- Monitoramento do progresso em tempo real;
- Relatório de execução em CSV com logs.

---

## Tecnologias

- Python 3.x
- Streamlit
- Pandas
- Requests
- concurrent.futures

---

## Execução local

```bash
git clone https://github.com/seuusuario/vtex-customer-updater.git
cd vtex-customer-updater
pip install streamlit pandas requests
streamlit run vtex_integration_app.py
