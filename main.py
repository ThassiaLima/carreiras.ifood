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

def send_email(sender_email, sender_password, receiver_email, subject,
