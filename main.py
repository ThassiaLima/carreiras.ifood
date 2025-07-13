import os
import json
import time
import smtplib
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from webdriver_manager.chrome import ChromeDriverManager

# --- CONFIGURAÇÕES ---
SENDER_EMAIL = os.getenv("SENDER_EMAIL")
SENDER_PASSWORD = os.getenv("SENDER_PASSWORD")
RECEIVER_EMAIL = os.getenv("RECEIVER_EMAIL")
EMAIL_SUBJECT = "Novas Vagas no carreiras iFood!"
URL = "https://carreiras.ifood.com.br/jobs" # URL direta da página de vagas
SEARCH_KEYWORDS = ["Analista de Negócios", "Analista de Business Intelligence", "Data", "CRM", "Dados", "Product", "Manager"]
PREVIOUS_JOBS_FILE = "previous_bi_jobs.json"


def scrape_jobs_for_term(search_term):
    """
    CORREÇÃO FINAL: Apenas digita o termo e espera a página atualizar sozinha (live search).
    """
    print(f"\n--- Buscando pelo termo: '{search_term}' ---")
    driver = None
    jobs_found = []
    
    try:
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--disable-gpu")
        
        service = webdriver.ChromeService(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        driver.get(URL)
        wait = WebDriverWait(driver, 20)

        # 1. Encontra o campo de busca
        search_input = wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "input[name='JobSearch']")))
        
        # 2. Digita o termo. A página atualizará sozinha.
        search_input.clear()
        search_input.send_keys(search_term)
        print(f"Termo '{search_term}' digitado. Aguardando atualização da página...")

        # 3. Pausa paciente para a mágica do 'live search' acontecer.
        time.sleep(6)

        # 4. Extrai os resultados
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        job_elements = soup.select('a[href^="/job/"]')
        print(f"Encontrados {len(job_elements)} resultados para '{search_term}'.")

        for job_element in job_elements:
            title_tag = job_element.select_one("h3")
            location_tag = job_element.select_one("h5")
            if title_tag:
                link = job_element.get('href', '')
                base_url = "https://carreiras.ifood.com.br"
                full_link = base_url + link if link.startswith('/') else link
                job_data = {
                    "title": title_tag.get_text(strip=True),
                    "link": full_link,
                    "location": location_tag.get_text(strip=True) if location_tag else "Não informado"
                }
                jobs_found.append(job_data)

    except Exception as e:
        print(f"ERRO inesperado ao buscar por '{search_term}': {e}")
    finally:
        if driver:
            driver.quit()
    
    return jobs_found


def send_email(sender_email, sender_password, receiver_email, subject, body_html):
    """Envia um e-mail com conteúdo HTML."""
    if not all([sender_email, sender_password, receiver_email]):
        print("\nAVISO: Credenciais de e-mail não configuradas. Pulando envio de e-mail.")
        return
    # (O resto da função de email permanece o mesmo)


def load_jobs_history(file_path):
    """Carrega o histórico de vagas de um arquivo JSON."""
    if os.path.exists(file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError:
            return []
    return []


def save_jobs_history(file_path, history):
    """Salva o histórico de vagas em um arquivo JSON."""
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(history, f, indent=4, ensure_ascii=False)


# --- Execução Principal ---
if __name__ == "__main__":
    today = datetime.now().strftime('%Y-%m-%d')
    jobs_history = load_jobs_history(PREVIOUS_JOBS_FILE)
    print(f"Carregado histórico com {len(jobs_history)} vagas de '{PREVIOUS_JOBS_FILE}'.")
    
    all_found_jobs = {}
    for keyword in SEARCH_KEYWORDS:
        jobs_from_term = scrape_jobs_for_term(keyword)
        for job in jobs_from_term:
            all_found_jobs[job['link']] = job

    # Filtra a lista total para manter apenas as vagas relevantes
    print("\n--- Filtrando resultados totais pelas palavras-chave ---")
    relevant_jobs = {}
    for link, job_data in all_found_jobs.items():
        title_lower = job_data['title'].lower()
        for keyword in SEARCH_KEYWORDS:
            if keyword.lower() in title_lower:
                relevant_jobs[link] = job_data
                break
    
    print(f"Total de vagas únicas e RELEVANTES encontradas: {len(relevant_jobs)}")

    open_relevant_job_links = set(relevant_jobs.keys())
    new_jobs_for_notification = []
    
    # Atualiza o status das vagas no histórico
    print("\nAnalisando mudanças no histórico de vagas...")
    for job_in_history in jobs_history:
        is_still_open = job_in_history['link'] in open_relevant_job_links
        if job_in_history.get('status') == 'ativa' and not is_still_open:
            job_in_history['status'] = 'fechada'
            job_in_history['date_saida'] = today
            print(f"- Vaga FECHADA: {job_in_history['title']}")
        if job_in_history.get('status') == 'fechada' and is_still_open:
            job_in_history['status'] = 'ativa'
            job_in_history['date_saida'] = None
            print(f"- Vaga REABERTA: {job_in_history['title']}")

    # Adiciona vagas que nunca foram vistas antes
    existing_links_in_history = {job['link'] for job in jobs_history}
    for link, job_data in relevant_jobs.items():
        if link not in existing_links_in_history:
            new_job_entry = {
                "title": job_data['title'],
                "link": job_data['link'],
                "location": job_data['location'],
                "status": "ativa",
                "date_entrada": today,
                "date_saida": None
            }
            jobs_history.append(new_job_entry)
            new_jobs_for_notification.append(new_job_entry)
            print(f"- Vaga NOVA: {new_job_entry['title']}")

    save_jobs_history(PREVIOUS_JOBS_FILE, jobs_history)

    if new_jobs_for_notification:
        # Lógica de e-mail (não mostrada para brevidade)
        print(f"\n--- {len(new_jobs_for_notification)} novas vagas para notificar. ---")
    else:
        print("\nNenhuma vaga nova para notificar.")

    # --- RELATÓRIO FINAL ---
    print("\n" + "="*40)
    print("      RESUMO DA EXECUÇÃO")
    print("="*40)
    print(f"- Total de vagas encontradas (relevantes e únicas): {len(relevant_jobs)}")
    print(f"- Total de vagas novas (para notificação): {len(new_jobs_for_notification)}")
    print(f"- Total de vagas salvas no histórico (JSON): {len(jobs_history)}")
    print("="*40)
