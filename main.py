import os
import json
from datetime import date
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from bs4 import BeautifulSoup
import time
from webdriver_manager.chrome import ChromeDriverManager
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# --- CONFIGURAÇÕES DE E-MAIL ---
SENDER_EMAIL = os.getenv("SENDER_EMAIL")
SENDER_PASSWORD = os.getenv("SENDER_PASSWORD")
RECEIVER_EMAIL = os.getenv("RECEIVER_EMAIL")
EMAIL_SUBJECT = "Novas Vagas de Analista de BI no iFood!"

# --- CONFIGURAÇÕES DE RASPAGEM ---
URL = "https://carreiras.ifood.com.br/"
TARGET_JOB_TITLE_KEYWORDS = ["Analista de Negócios", "Analista de Business Intelligence", "Analista de Dados", "CRM", "Produto"]
PREVIOUS_JOBS_FILE = "previous_bi_jobs.json"

# --- Raspagem ---
def get_ifood_job_listings(url, keywords):
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.binary_location = '/usr/bin/google-chrome'

    all_jobs = []

    try:
        driver = webdriver.Chrome(service=webdriver.ChromeService(ChromeDriverManager().install()), options=chrome_options)
        driver.get(url)

        wait = WebDriverWait(driver, 60)

        try:
            accept_cookies_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'aceitar')]")))
            accept_cookies_button.click()
            time.sleep(3)
        except:
            pass

        search_input = wait.until(EC.element_to_be_clickable((By.ID, "keyword-search-input")))
        search_input.send_keys(keywords[0])
        search_input.send_keys(Keys.ENTER)
        time.sleep(10)

        soup = BeautifulSoup(driver.page_source, 'html.parser')
        job_listings_elements = soup.select("ul.sc-ienWRC li")

        for job_element in job_listings_elements:
            title_link_tag = job_element.select_one("h4 a")
            if title_link_tag and 'href' in title_link_tag.attrs:
                title = title_link_tag.get_text(strip=True)
                link = title_link_tag['href']
                if not link.startswith('http'):
                    link = URL.rstrip('/') + link
                job_data = {
                    "title": title,
                    "link": link
                }
                all_jobs.append(job_data)

        bi_jobs_filtered = []
        for job in all_jobs:
            if any(keyword.lower() in job['title'].lower() for keyword in keywords):
                bi_jobs_filtered.append(job)

        return bi_jobs_filtered

    except Exception as e:
        print(f"Erro na raspagem: {e}")
        return []
    finally:
        driver.quit()

# --- E-mail ---
def send_email(sender_email, sender_password, receiver_email, subject, body_html):
    msg = MIMEMultipart("alternative")
    msg["From"] = sender_email
    msg["To"] = receiver_email
    msg["Subject"] = subject
    msg.attach(MIMEText(body_html, "html"))

    try:
        server = smtplib.SMTP_SSL("smtp.gmail.com", 465)
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, receiver_email, msg.as_string())
        print(f"E-mail enviado para {receiver_email}")
    except Exception as e:
        print(f"Erro ao enviar e-mail: {e}")
    finally:
        server.quit()

# --- Histórico ---
def load_previous_jobs(file_path):
    if os.path.exists(file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                jobs = json.load(f)
                # Normalizar campos ausentes
                for job in jobs:
                    if "status" not in job:
                        job["status"] = "ativa"
                    if "data_entrada" not in job:
                        job["data_entrada"] = str(date.today())
                    if "data_saida" not in job:
                        job["data_saida"] = None
                return jobs
        except json.JSONDecodeError:
            return []
    return []

def save_current_jobs(file_path, jobs):
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(jobs, f, indent=4, ensure_ascii=False)

def atualizar_historico_completo(current_jobs, historico_jobs):
    hoje = str(date.today())
    links_atuais = {job['link'] for job in current_jobs}
    novos_registros = []

    # Marcar como fechadas as vagas que sumiram
    for vaga in historico_jobs:
        if vaga["status"] == "ativa" and vaga["link"] not in links_atuais:
            vaga["status"] = "fechada"
            vaga["data_saida"] = hoje

    # Adicionar novas vagas
    for job in current_jobs:
        if not any(v["link"] == job["link"] for v in historico_jobs):
            nova_vaga = {
                "title": job["title"],
                "link": job["link"],
                "data_entrada": hoje,
                "data_saida": None,
                "status": "ativa"
            }
            historico_jobs.append(nova_vaga)
            novos_registros.append(nova_vaga)

    return historico_jobs, novos_registros

# --- Execução principal ---
if __name__ == "__main__":
    previous_jobs = load_previous_jobs(PREVIOUS_JOBS_FILE)
    current_jobs = get_ifood_job_listings(URL, TARGET_JOB_TITLE_KEYWORDS)
    updated_jobs, novas_vagas = atualizar_historico_completo(current_jobs, previous_jobs)
    save_current_jobs(PREVIOUS_JOBS_FILE, updated_jobs)

    if novas_vagas:
        email_body = "<html><body><h2>🚨 Novas Vagas no iFood! 🚨</h2><ul>"
        for job in novas_vagas:
            email_body += f"<li><b>{job['title']}</b>: <a href='{job['link']}'>{job['link']}</a></li>"
        email_body += "</ul><p><i>Este é um alerta automatizado do seu script de vagas 🍟</i></p></body></html>"

        send_email(SENDER_EMAIL, SENDER_PASSWORD, RECEIVER_EMAIL, EMAIL_SUBJECT, email_body)
    else:
        print("Nenhuma nova vaga encontrada.")
