import os
import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import time

# Configurações
URL = "https://carreiras.ifood.com.br/"
KEYWORDS = ["Analista de Dados", "Business Intelligence", "Produto", "BI"]
HISTORICO_JSON = "historico_ifood.json"
SENDER_EMAIL = os.getenv("SENDER_EMAIL")
SENDER_PASSWORD = os.getenv("SENDER_PASSWORD")
RECEIVER_EMAIL = os.getenv("RECEIVER_EMAIL")
EMAIL_SUBJECT = "📢 Novas vagas de dados no iFood"

# Função para carregar histórico
def carregar_historico():
    if os.path.exists(HISTORICO_JSON):
        with open(HISTORICO_JSON, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

# Função para salvar histórico
def salvar_historico(historico):
    with open(HISTORICO_JSON, "w", encoding="utf-8") as f:
        json.dump(historico, f, indent=2, ensure_ascii=False)

# Função para enviar e-mail
def enviar_email(vagas):
    corpo_html = "<h3>Novas vagas de dados no iFood:</h3><ul>"
    for v in vagas:
        corpo_html += f"<li><b>{v['titulo']}</b> - <a href='{v['link']}'>{v['link']}</a></li>"
    corpo_html += "</ul><p><i>Este é um e-mail automático do rastreador de carreiras iFood.</i></p>"

    msg = MIMEMultipart()
    msg["From"] = f"Carreiras iFood <{SENDER_EMAIL}>"
    msg["To"] = RECEIVER_EMAIL
    msg["Subject"] = EMAIL_SUBJECT
    msg.attach(MIMEText(corpo_html, "html"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.send_message(msg)
        print("✅ E-mail enviado com sucesso.")

# Função de raspagem
def buscar_vagas_ifood():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    driver = webdriver.Chrome(options=options)

    driver.get(URL)
    time.sleep(2)

    try:
        # Input de busca
        campo_busca = WebDriverWait(driver, 15).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "input[name='JobSearch']"))
        )       

        campo_busca.clear()
        campo_busca.send_keys("Dados")
        campo_busca.send_keys(Keys.ENTER)
        time.sleep(4)
    except:
        print("❌ Não foi possível realizar a busca.")
    
    # Scroll para garantir carregamento completo
    for _ in range(3):
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)

    soup = BeautifulSoup(driver.page_source, "html.parser")
    cards = soup.select("li.sc-byTJDB a")

    vagas = []
    for card in cards:
        titulo = card.find("h3").text.strip() if card.find("h3") else ""
        link = card.get("href", "")
        if not link.startswith("http"):
            link = URL.rstrip("/") + link
        if any(k.lower() in titulo.lower() for k in KEYWORDS):
            vagas.append({
                "titulo": titulo,
                "link": link
            })

    driver.quit()
    return vagas

# Execução principal
hoje = datetime.now().strftime("%Y-%m-%d")
historico = carregar_historico()
links_anteriores = {v["link"] for v in historico if v["status"] == "ativa"}
vagas_raspadas = buscar_vagas_ifood()

# Detectar novas vagas
novas_vagas = []
for vaga in vagas_raspadas:
    if vaga["link"] not in links_anteriores:
        nova = {
            "titulo": vaga["titulo"],
            "link": vaga["link"],
            "data_abertura": hoje,
            "data_fechamento": None,
            "status": "ativa"
        }
        historico.append(nova)
        novas_vagas.append(nova)

# Marcar vagas encerradas
links_atuais = {v["link"] for v in vagas_raspadas}
for v in historico:
    if v["status"] == "ativa" and v["link"] not in links_atuais:
        v["status"] = "fechada"
        v["data_fechamento"] = hoje

# Salvar histórico e enviar e-mail
salvar_historico(historico)
if novas_vagas:
    enviar_email(novas_vagas)
else:
    print("📭 Nenhuma nova vaga encontrada hoje.")
