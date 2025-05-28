import os
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

# --- CONFIGURAÇÕES DE E-MAIL (AGORA LENDO DE VARIÁVEIS DE AMBIENTE) ---
# Em um ambiente de produção, essas variáveis devem ser carregadas de forma segura.
# No GitHub Actions, elas serão injetadas pelos GitHub Secrets.
SENDER_EMAIL = os.getenv("SENDER_EMAIL", "tha.muniz16@gmail.com") # Default para teste local se não houver env
SENDER_PASSWORD = os.getenv("SENDER_PASSWORD", "rpwr dtxn sicu khhr") # Sua senha de app do Gmail
RECEIVER_EMAIL = os.getenv("RECEIVER_EMAIL", "thassya.lima@hotmail.com") # Default para teste local
EMAIL_SUBJECT = "Novas Vagas de Analista de BI no iFood!"

# --- CONFIGURAÇÕES DE RASPAGEM ---
URL = "https://carreiras.ifood.com.br/"
TARGET_JOB_TITLE_KEYWORDS = ["Analista de Negócios", "Business Intelligence", "Analista de Dados", "CRM", "Produto"]

def get_ifood_job_listings(url, keywords):
    print(f"\nIniciando raspagem de vagas em: {url}")

    chrome_options = Options()
    chrome_options.add_argument("--headless")        # Roda o navegador em modo invisível
    chrome_options.add_argument("--no-sandbox")       # Necessário para ambientes Linux (GitHub Actions)
    chrome_options.add_argument("--disable-dev-shm-usage") # Necessário para ambientes Linux (GitHub Actions)
    chrome_options.add_argument("--window-size=1920,1080") # Garante uma boa resolução
    chrome_options.add_argument("--disable-gpu") # Pode ser útil

    # No GitHub Actions, o Chrome já estará instalado.
    # A linha abaixo pode ser removida se o Chrome estiver no PATH padrão
    # ou configurado de outra forma no ambiente do Action.
    # No entanto, em um ambiente Ubuntu padrão (como o GitHub Actions),
    # '/usr/bin/google-chrome' é o caminho comum.
    chrome_options.binary_location = '/usr/bin/google-chrome' 

    driver = None
    all_jobs = []

    try:
        # ChromeDriverManager.install() gerencia a instalação do ChromeDriver
        # compatível com a versão do Chrome que será usada no ambiente.
        driver = webdriver.Chrome(service=webdriver.ChromeService(ChromeDriverManager().install()), options=chrome_options)
        print("Driver do Chrome configurado e iniciado com sucesso.")

        driver.get(url)
        print("Página carregada. Tentando aceitar cookies e usar campo de busca...")

        wait = WebDriverWait(driver, 60) # Tempo de espera máximo

        # --- Tentar aceitar o banner de cookies se existir ---
        try:
            accept_cookies_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'concordar') or contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'aceitar')]")))
            print("Botão de aceitar cookies encontrado. Clicando...")
            accept_cookies_button.click()
            time.sleep(3) # Pequena pausa para o banner fechar e a página reagir
        except Exception:
            print("Nenhum botão de aceitar cookies detectado ou clicável (ou já aceito). Prosseguindo.")
            pass # Continua se o botão não for encontrado

        # --- Localizar o campo de busca e preencher ---
        try:
            search_input = wait.until(EC.element_to_be_clickable((By.ID, "keyword-search-input")))
            print(f"Campo de busca ('keyword-search-input') encontrado.")
            
            search_term = keywords[0] # Usaremos a primeira keyword da nossa lista para a busca inicial
            print(f"Digitando '{search_term}' no campo de busca e pressionando ENTER...")
            search_input.send_keys(search_term)
            search_input.send_keys(Keys.ENTER)
            
            time.sleep(5) # Pequena pausa para a busca ser processada e os resultados começarem a carregar
            print("Busca acionada. Aguardando resultados...")

            # --- Esperar pelos resultados da busca (vagas) ---
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "ul.sc-ienWRC")))
            print("Contêiner principal de vagas (ul.sc-ienWRC) detectado após a busca.")
            
            wait.until(EC.visibility_of_all_elements_located((By.CSS_SELECTOR, "ul.sc-ienWRC li")))
            print("Pelo menos uma vaga (<li>) detectada e visível dentro do contêiner após a busca.")
            
            print("Pausa estratégica de 10 segundos antes de parsear o HTML para garantir que o DOM esteja totalmente estável.")
            time.sleep(10) 

        except Exception as e:
            print(f"**Aviso:** Falha ao usar o campo de busca ou ao encontrar os elementos das vagas após a busca. Erro: {e}")
            print("Isso pode significar que o seletor do campo de busca mudou ou a página de resultados é diferente.")
        
        # --- SALVAR PAGE_SOURCE PARA DEPURAR (opcional, remova em produção para economizar espaço) ---
        # No GitHub Actions, isso aparecerá nos artefatos do workflow se você configurá-lo para isso.
        # Caso contrário, pode ser removido para um ambiente de produção limpo.
        try:
            with open("page_source_after_search_simplified.html", "w", encoding="utf-8") as f:
                f.write(driver.page_source)
            print("HTML da página (após busca) salvo em 'page_source_after_search_simplified.html' para depuração.")
        except Exception as e:
            print(f"Não foi possível salvar page_source para depuração: {e}")


        # Rolagem da página para garantir que todos os elementos dinâmicos sejam carregados (se houver lazy loading)
        last_height = driver.execute_script("return document.body.scrollHeight")
        scroll_attempts = 0
        while scroll_attempts < 5: # Tenta rolar 5 vezes para pegar mais vagas, se existirem
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2) # Pequena pausa para o conteúdo carregar após a rolagem
            new_height = driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                print("Altura da página não mudou, presumindo que todas as vagas foram carregadas.")
                break # Sai do loop se não houver mais rolagem
            last_height = new_height
            scroll_attempts += 1
        print("Rolagem da página concluída (se aplicável).")
        
        soup = BeautifulSoup(driver.page_source, 'html.parser')

        # --- EXTRAÇÃO DE VAGAS (APENAS TÍTULO E LINK) ---
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
                    link = URL.rstrip('/') + link # Garante que o link seja absoluto
                
                job_data = {
                    "title": title,
                    "link": link
                }
                all_jobs.append(job_data)
            else:
                # Este aviso é importante para depuração se as vagas não forem bem formadas.
                # Pode ser removido em produção se não houver interesse nessas "vagas parciais".
                print(f"  Aviso: Elemento de vaga (<li>) encontrado sem link ou título principal válido. Conteúdo parcial: {job_element.prettify()[:200]}...")

        # --- FILTRANDO POR VAGAS DE ANALISTA DE BI ---
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
        # Servidor SMTP do Gmail usando SSL na porta 465
        server = smtplib.SMTP_SSL("smtp.gmail.com", 465) 
        server.login(sender_email, sender_password)
        text = msg.as_string()
        server.sendmail(sender_email, receiver_email, text)
        print(f"\nE-mail enviado com sucesso para {receiver_email}!")
    except Exception as e:
        print(f"\nErro ao enviar e-mail: {e}")
        print(f"Detalhes do erro: {e.__class__.__name__}: {e}")
        print("Verifique suas credenciais de e-mail e configurações de segurança (ex: senha de app do Gmail).")
        print("Certifique-se de que SENDER_EMAIL, SENDER_PASSWORD e RECEIVER_EMAIL estão corretos.")
    finally:
        # Garante que a conexão com o servidor SMTP seja fechada
        if 'server' in locals() and server: # Verifica se server foi inicializado
            server.quit()
            print("Conexão SMTP fechada.")

# --- Execução principal ---
if __name__ == "__main__":
    current_bi_jobs = get_ifood_job_listings(URL, TARGET_JOB_TITLE_KEYWORDS)
    
    if current_bi_jobs:
        print(f"\n--- {len(current_bi_jobs)} Vagas de BI Encontradas no iFood! ---")
        email_body_html = "<html><body>"
        email_body_html += "<h2>Novas Vagas de Analista de BI no iFood:</h2>"
        email_body_html += "<p>Confira as vagas encontradas hoje:</p>"
        email_body_html += "<ul>"
        for job in current_bi_jobs:
            print(f"- Título: {job['title']}")
            print(f"  Link: {job['link']}\n")
            email_body_html += f"<li><b>{job['title']}</b>: <a href='{job['link']}'>{job['link']}</a></li>"
        email_body_html += "</ul>"
        email_body_html += "<p><i>Este é um e-mail automático.</i></p>"
        email_body_html += "</body></html>"
        
        send_email(SENDER_EMAIL, SENDER_PASSWORD, RECEIVER_EMAIL, EMAIL_SUBJECT, email_body_html)

    else:
        print("\n--- Nenhuma vaga de 'Analista de BI' (ou similar) foi encontrada no iFood. ---")
        email_body_html = "<html><body><h2>Nenhuma vaga de Analista de BI encontrada no iFood hoje.</h2><p>Verifique novamente mais tarde!</p></body></html>"
        send_email(SENDER_EMAIL, SENDER_PASSWORD, RECEIVER_EMAIL, EMAIL_SUBJECT, email_body_html)
