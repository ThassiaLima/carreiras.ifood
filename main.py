import os
import json
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
from datetime import datetime # Importar datetime

# --- CONFIGURAÇÕES DE E-MAIL ---
SENDER_EMAIL = os.getenv("SENDER_EMAIL")
SENDER_PASSWORD = os.getenv("SENDER_PASSWORD")
RECEIVER_EMAIL = os.getenv("RECEIVER_EMAIL")
EMAIL_SUBJECT = "Novas Vagas no carreiras iFood!"

# --- CONFIGURAÇÕES DE RASPAGEM ---
URL = "https://carreiras.ifood.com.br/"
TARGET_JOB_TITLE_KEYWORDS = ["Analista de Negócios", "Analista de Business Intelligence", "Analista de Dados", "CRM", "Produto"]
PREVIOUS_JOBS_FILE = "previous_bi_jobs.json"

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
            # Tentar encontrar o campo de busca pelo ID primário
            search_input = wait.until(EC.element_to_be_clickable((By.ID, "keyword-search-input")))
            print(f"Campo de busca ('keyword-search-input') encontrado.")
        except:
            # Se não encontrar pelo ID, tentar por um XPath mais genérico que contenha um placeholder "Cargo, palavra-chave ou empresa"
            print("Campo de busca por ID não encontrado, tentando por placeholder de texto...")
            search_input = wait.until(EC.element_to_be_clickable((By.XPATH, "//input[@placeholder='Cargo, palavra-chave ou empresa']")))
            print(f"Campo de busca por placeholder encontrado.")

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

        # O bloco 'except' para falha na busca foi movido para fora do try/except interno
        # para pegar erros gerais na interação com o campo de busca e elementos subsequentes.
    except Exception as e:
        print(f"**Aviso Crítico:** Falha ao usar o campo de busca ou ao encontrar os elementos das vagas após a busca. Erro: {e}")
        print("Isso pode significar que o seletor do campo de busca mudou ou a página de resultados é diferente. Continuando para tentar parsear o HTML existente.")
    
    # Continuar processando o HTML, mesmo que a busca tenha falhado parcialmente,
    # para depurar ou tentar raspar o que está visível.
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
        # Considerar retornar aqui se nenhuma vaga for encontrada para evitar processamento inútil
        # ou se o erro de busca for muito grave
        # return [] 

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
                # Data e status serão adicionados na lógica principal
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
    
    # Certifica-se que o driver sempre fecha, mesmo que as etapas de raspagem falhem
    if driver:
        driver.quit()
        print("Navegador Selenium fechado.")
        
    return bi_jobs_filtered

# Esta função send_email não foi modificada
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
def load_all_jobs_history(file_path):
    """Carrega todo o histórico de vagas de um arquivo JSON."""
    if os.path.exists(file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                history = json.load(f)
                print(f"Carregado histórico com {len(history)} vagas de '{file_path}'.")
                return history
        except json.JSONDecodeError:
            print(f"Aviso: Arquivo '{file_path}' está corrompido ou vazio. Iniciando um histórico vazio.")
            return []
    print(f"Arquivo '{file_path}' não encontrado. Iniciando um histórico vazio.")
    return []

def save_all_jobs_history(file_path, history):
    """Salva todo o histórico de vagas em um arquivo JSON."""
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(history, f, indent=4, ensure_ascii=False)
    print(f"Salvo histórico com {len(history)} vagas em '{file_path}'.")

# --- Execução principal ---
if __name__ == "__main__":
    today = datetime.now().strftime('%Y-%m-%d')
    all_jobs_history = load_all_jobs_history(PREVIOUS_JOBS_FILE) # Carrega todo o histórico
    current_scraped_jobs_simple = get_ifood_job_listings(URL, TARGET_JOB_TITLE_KEYWORDS)

    # Convertendo as vagas raspadas para um formato fácil de comparar (apenas título e link)
    # É importante usar um identificador único, e o link é o mais confiável.
    current_scraped_jobs_links = {job['link'] for job in current_scraped_jobs_simple}
    
    new_jobs_to_notify = [] # Vagas que são novas NESTA execução e precisam ser notificadas

    # Passo 1: Marcar vagas que deixaram de aparecer como 'fechada'
    for job_in_history in all_jobs_history:
        # Se a vaga estava ativa e não foi encontrada na raspagem atual
        # Verifica pelo link, pois é o identificador único
        if job_in_history['status'] == 'ativa' and job_in_history['link'] not in current_scraped_jobs_links:
            
            job_in_history['status'] = 'fechada'
            job_in_history['date_saida'] = today
            print(f"Vaga marcada como FECHADA: {job_in_history['title']} - {job_in_history['link']}")
    
    # Passo 2: Adicionar novas vagas e identificar as que precisam ser notificadas
    # Usaremos os links para identificar as vagas já conhecidas no histórico
    existing_job_links_in_history = {job['link'] for job in all_jobs_history}

    for scraped_job in current_scraped_jobs_simple:
        if scraped_job['link'] not in existing_job_links_in_history:
            # É uma vaga nova!
            new_job_entry = {
                "title": scraped_job['title'],
                "link": scraped_job['link'],
                "date_entrada": today,
                "date_saida": None,
                "status": "ativa"
            }
            all_jobs_history.append(new_job_entry)
            new_jobs_to_notify.append(new_job_entry) # Adicionar para notificação
            print(f"Nova vaga adicionada ao histórico e para notificação: {new_job_entry['title']}")
        else:
            # Vaga já existe no histórico, garantir que está ativa e com date_saida nula
            # Isso é para o caso de uma vaga reabrir ou ter sido fechada erroneamente.
            # Também para atualizar data_saida para null se foi marcada como fechada e reapareceu
            for job_in_history in all_jobs_history:
                if job_in_history['link'] == scraped_job['link']:
                    if job_in_history['status'] == 'fechada':
                        print(f"Vaga reaberta ou reapareceu: {job_in_history['title']}. Atualizando status para 'ativa' e date_saida para null.")
                        job_in_history['status'] = 'ativa'
                        job_in_history['date_saida'] = None
                    # Não precisamos adicionar se já está ativa, apenas garantir que não foi marcada como fechada
                    break


    # Salvar o histórico COMPLETO e atualizado
    save_all_jobs_history(PREVIOUS_JOBS_FILE, all_jobs_history)

    # Enviar e-mail apenas com as vagas NOVAS
    if new_jobs_to_notify:
        print(f"\n--- {len(new_jobs_to_notify)} 🍟 Novas Vagas carreira iFood encontradas ---")
        email_body_html = "<html><body>"
        email_body_html += "<h2>🍟 Novas vagas no portal de carreira iFood! 🍟</h2>"
        email_body_html += "<p>Confira as vagas que foram publicadas desde a última busca:</p>"
        email_body_html += "<ul>"
        for job in new_jobs_to_notify:
            print(f"- Título: {job['title']}")
            print(f"  Link: {job['link']}\n")
            email_body_html += f"<li><b>{job['title']}</b>: <a href='{job['link']}'>{job['link']}</a> </li>"
        email_body_html += "</ul>"
        email_body_html += "<p><i>Este é um e-mail do seu monitor de vagas iFood.</i></p>"
        email_body_html += "</body></html>"
        
        send_email(SENDER_EMAIL, SENDER_PASSWORD, RECEIVER_EMAIL, EMAIL_SUBJECT, email_body_html)

    else:
        print("\n--- Nenhuma vaga nova de 'Analista de BI' (ou similar) foi encontrada no iFood. ---")
