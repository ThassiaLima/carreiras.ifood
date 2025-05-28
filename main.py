import os
import json # Importar a biblioteca json
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
TARGET_JOB_TITLE_KEYWORDS = ["Analista de BI", "Business Intelligence", "BI Analyst", "Inteligência de Negócios", "Data Analyst"]
PREVIOUS_JOBS_FILE = "previous_bi_jobs.json" # Nome do arquivo para armazenar vagas anteriores

def get_ifood_job_listings(url, keywords):
    print(f"\nIniciando raspagem de vagas em: {url}")

    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.binary_location = '/usr/bin/google-chrome' 

    driver = None
    all_jobs = []

    try:
        driver = webdriver.Chrome(service=webdriver.ChromeService(ChromeDriverManager().install()), options=chrome_options)
        print("Driver do Chrome configurado e iniciado com sucesso.")

        driver.get(url)
        print("Página carregada. Tentando aceitar cookies e usar campo de busca...")

        wait = WebDriverWait(driver, 60)

        try:
            accept_cookies_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'concordar') or contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'aceitar')]")))
            print("Botão de aceitar cookies encontrado. Clicando...")
            accept_cookies_button.click()
            time.sleep(3)
        except Exception:
            print("Nenhum botão de aceitar cookies detectado ou clicável (ou já aceito). Prosseguindo.")
            pass

        try:
            search_input = wait.until(EC.element_to_be_clickable((By.ID, "keyword-search-input")))
            print(f"Campo de busca ('keyword-search-input') encontrado.")
            
            search_term = keywords[0]
            print(f"Digitando '{search_term}' no campo de busca e pressionando ENTER...")
            search_input.send_keys(search_term)
            search_input.send_keys(Keys.ENTER)
            
            time.sleep(5)
            print("Busca acionada. Aguardando resultados...")

            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "ul.sc-ienWRC")))
            print("Contêiner principal de vagas (ul.sc-ienWRC) detectado após a busca.")
            
            wait.until(EC.visibility_of_all_elements_located((By.CSS_SELECTOR, "ul.sc-ienWRC li")))
            print("Pelo menos uma vaga (<li>) detectada e visível dentro do contêiner após a busca.")
            
            print("Pausa estratégica de 10 segundos antes de parsear o HTML para garantir que o DOM esteja totalmente estável.")
            time.sleep(10) 

        except Exception as e:
            print(f"**Aviso:** Falha ao usar o campo de busca ou ao encontrar os elementos das vagas após a busca. Erro: {e}")
            print("Isso pode significar que o seletor do campo de busca mudou ou a página de resultados é diferente.")
        
        try:
            with open("page_source_after_search_simplified.html", "w", encoding="utf-8") as f:
                f.write(driver.page_source)
            print("HTML da página (após busca) salvo em 'page_source_after_search_simplified.html' para depuração.")
        except Exception as e:
            print(f"Não foi possível salvar page_source para depuração: {e}")

        last_height = driver.execute_script("return document.body.scrollHeight")
        scroll_attempts = 0
        while scroll_attempts < 5: 
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2) 
            new_height = driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                print("Altura da página não mudou, presumindo que todas as vagas foram carregadas.")
                break 
            last_height = new_height
            scroll_attempts += 1
        print("Rolagem da página concluída (se aplicável).")
        
        soup = BeautifulSoup(driver.page_source, 'html.parser')

        job_listings_elements = soup.select("ul.sc-ienWRC li") 

        print(f"Total de elementos de vaga (<li>) encontrados via BeautifulSoup: {len(job_listings_elements)}")

        if not job_listings_elements:
            print("Aviso: Nenhum elemento <li> de vaga encontrado no HTML raspado. Isso é crítico.")
            return []

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
            else:
                print(f"  Aviso: Elemento de vaga (<li>) encontrado sem link ou título principal válido. Conteúdo parcial: {job_element.prettify()[:200]}...")

        bi_jobs_filtered = []
        print("\n--- FILTRANDO POR VAGAS DE ANALISTA DE BI ---")
        for job in all_jobs:
            found_keyword = False
            for keyword in keywords:
                if keyword.lower() in job['title'].lower():
                    found_keyword = True
                    break
            if found_keyword:
                bi_jobs_filtered.append(job)
        
        return bi_jobs_filtered

    except Exception as e:
        print(f"Ocorreu um erro geral durante a execução do Selenium: {e}")
        return []
    finally:
        if driver:
            driver.quit()
            print("Navegador Selenium fechado.")

def send_email(sender_email, sender_password, receiver_email, subject, body_html):
    """
    Envia um e-mail com conteúdo HTML.
    """
    msg = MIMEMultipart("alternative")
    msg["From"] = sender_email
    msg["To"] = receiver_email
    msg["Subject"] = subject

    msg.attach(MIMEText(body_html, "html"))

    try:
        server = smtplib.SMTP_SSL("smtp.gmail.com", 465) 
        server.login(sender_email, sender_password)
        text = msg.as_string()
        server.sendmail(sender_email, receiver_email, text)
        print(f"\nE-mail enviado com sucesso para {receiver_email}!")
    except Exception as e:
        print(f"\nErro ao enviar e-mail: {e}")
        print(f"Detalhes do erro: {e.__class__.__name__}: {e}")
        print("Verifique suas credenciais de e-mail e configurações de segurança (ex: senha de app do Gmail).")
    finally:
        if 'server' in locals() and server: 
            server.quit()
            print("Conexão SMTP fechada.")

# --- Funções para gerenciar o histórico de vagas ---
def load_previous_jobs(file_path):
    """Carrega vagas de um arquivo JSON."""
    if os.path.exists(file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                jobs = json.load(f)
                print(f"Carregadas {len(jobs)} vagas de '{file_path}'.")
                return jobs
        except json.JSONDecodeError:
            print(f"Aviso: Arquivo '{file_path}' está corrompido ou vazio. Iniciando do zero.")
            return []
    print(f"Arquivo '{file_path}' não encontrado. Iniciando a busca do zero.")
    return []

def save_current_jobs(file_path, jobs):
    """Salva vagas em um arquivo JSON."""
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(jobs, f, indent=4, ensure_ascii=False)
    print(f"Salvas {len(jobs)} vagas em '{file_path}'.")

def find_new_jobs(current_jobs, previous_jobs):
    """Compara as vagas atuais com as anteriores e retorna apenas as novas."""
    previous_jobs_set = {frozenset(job.items()) for job in previous_jobs} # Converte para set de frozensets para comparação
    new_jobs = []
    for job in current_jobs:
        if frozenset(job.items()) not in previous_jobs_set:
            new_jobs.append(job)
    return new_jobs

# --- Execução principal ---
if __name__ == "__main__":
    previous_bi_jobs = load_previous_jobs(PREVIOUS_JOBS_FILE)
    current_bi_jobs = get_ifood_job_listings(URL, TARGET_JOB_TITLE_KEYWORDS)
    
    # Salvar as vagas atuais para a próxima execução (mesmo que não haja novas para enviar e-mail)
    save_current_jobs(PREVIOUS_JOBS_FILE, current_bi_jobs)

    if not current_bi_jobs:
        print("Nenhuma vaga de BI encontrada na raspagem atual.")
        # Podemos optar por não enviar e-mail se não houver vagas ativas, ou enviar um e-mail de "nada encontrado"
        # Se você quiser um email de "nada encontrado", descomente a linha abaixo:
        # send_email(SENDER_EMAIL, SENDER_PASSWORD, RECEIVER_EMAIL, EMAIL_SUBJECT, "<html><body>Nenhuma vaga de Analista de BI encontrada no iFood hoje.</body></html>")
    else:
        new_bi_jobs = find_new_jobs(current_bi_jobs, previous_bi_jobs)
        
        if new_bi_jobs:
            print(f"\n--- {len(new_bi_jobs)} NOVAS Vagas de BI Encontradas no iFood! ---")
            email_body_html = "<html><body>"
            email_body_html += "<h2>🚨 Novas Vagas de Analista de BI no iFood! 🚨</h2>"
            email_body_html += "<p>Confira as vagas que foram publicadas desde a última busca:</p>"
            email_body_html += "<ul>"
            for job in new_bi_jobs:
                print(f"- Título: {job['title']}")
                print(f"  Link: {job['link']}\n")
                email_body_html += f"<li><b>{job['title']}</b>: <a href='{job['link']}'>{job['link']}</a></li>"
            email_body_html += "</ul>"
            email_body_html += "<p><i>Este é um e-mail automático.</i></p>"
            email_body_html += "</body></html>"
            
            send_email(SENDER_EMAIL, SENDER_PASSWORD, RECEIVER_EMAIL, EMAIL_SUBJECT, email_body_html)

        else:
            print("\n--- Nenhuma vaga nova de 'Analista de BI' (ou similar) foi encontrada no iFood. ---")
            # Nenhuma nova vaga, então não enviamos e-mail para evitar spam desnecessário.
            # Se você quiser receber um e-mail informando que não há novas vagas, descomente a linha abaixo:
            # send_email(SENDER_EMAIL, SENDER_PASSWORD, RECEIVER_EMAIL, EMAIL_SUBJECT, "<html><body>Nenhuma nova vaga de Analista de BI foi encontrada no iFood desde a última busca.</body></html>")
