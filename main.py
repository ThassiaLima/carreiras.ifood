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
URL = "https://carreiras.ifood.com.br/jobs" # Sua URL atualizada
SEARCH_KEYWORDS = ["Analista de Negócios", "Analista de Business Intelligence", "Data", "CRM", "Dados", "Product", "Manager"] # Sua lista de palavras-chave atualizada
PREVIOUS_JOBS_FILE = "previous_bi_jobs.json"


def scrape_jobs_for_term(search_term):
    """
    Apenas digita o termo e espera a página atualizar sozinha (live search).
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

        search_input = wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "input[name='JobSearch']")))
        
        search_input.clear()
        search_input.send_keys(search_term)
        print(f"Termo '{search_term}' digitado. Aguardando atualização da página...")

        time.sleep(6)

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
    """
    Envia um e-mail com conteúdo HTML e logs detalhados para depuração.
    """
    print("\n--- INICIANDO PROCESSO DE ENVIO DE E-MAIL ---")

    # 1. Verificação das credenciais
    if not all([sender_email, sender_password, receiver_email]):
        print(">>> AVISO: Uma ou mais credenciais de e-mail (SENDER_EMAIL, SENDER_PASSWORD, RECEIVER_EMAIL) não foram encontradas.")
        print(">>> Verifique se os 'GitHub Secrets' foram configurados corretamente no repositório.")
        print(">>> Pulando envio de e-mail.")
        print("--- PROCESSO DE ENVIO DE E-MAIL FINALIZADO (COM AVISO) ---")
        return

    print(">>> SUCESSO: Credenciais de e-mail encontradas. Prosseguindo com o envio.")

    # 2. Montagem da mensagem
    msg = MIMEMultipart("alternative")
    msg["From"] = f"Vagas carreira iFood <{sender_email}>"
    msg["To"] = receiver_email
    msg["Subject"] = subject
    msg.attach(MIMEText(body_html, "html"))
    print(">>> Mensagem de e-mail montada.")

    server = None
    try:
        # 3. Conexão com o servidor
        print(">>> Conectando ao servidor SMTP do Gmail (smtp.gmail.com:465)...")
        server = smtplib.SMTP_SSL("smtp.gmail.com", 465)
        print(">>> Conexão com o servidor SMTP estabelecida.")

        # 4. Login na conta
        print(f">>> Realizando login com o e-mail: {sender_email}...")
        server.login(sender_email, sender_password)
        print(">>> Login realizado com sucesso.")

        # 5. Envio do e-mail
        print(f">>> Enviando a mensagem para: {receiver_email}...")
        server.sendmail(sender_email, receiver_email, msg.as_string())
        print(f"✅ SUCESSO! E-mail enviado para {receiver_email}!")

    except Exception as e:
        # 6. Tratamento de erro detalhado
        print(f"❌ FALHA AO ENVIAR E-MAIL. Erro do tipo: {e.__class__.__name__}")
        print(f"   Detalhe do erro: {e}")
        print("   CAUSAS COMUNS: A 'Senha de App' está incorreta ou a Verificação em Duas Etapas não está ativa na conta Google.")
    
    finally:
        # 7. Finalização da conexão
        if server:
            server.quit()
            print(">>> Conexão com o servidor SMTP fechada.")
        print("--- PROCESSO DE ENVIO DE E-MAIL FINALIZADO ---")


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
        # A lógica do e-mail é chamada aqui
        email_body_html = "<html><body><h2>🍟 Novas vagas no portal de carreira iFood! 🍟</h2><ul>"
        for job in new_jobs_for_notification:
            location = job.get('location', 'N/A')
            email_body_html += f"<li><b>{job['title']}</b> ({location}): <a href='{job['link']}'>{job['link']}</a></li>"
        email_body_html += "</ul></body></html>"
        send_email(SENDER_EMAIL, SENDER_PASSWORD, RECEIVER_EMAIL, EMAIL_SUBJECT, email_body_html)
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
