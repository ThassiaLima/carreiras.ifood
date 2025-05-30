1. Visão Geral do Projeto
Este projeto é um monitor automatizado de vagas de Analista de BI e áreas correlatas no portal de carreiras do iFood. Ele é projetado para raspar o site periodicamente, identificar novas vagas, monitorar o status das vagas existentes (ativas ou fechadas) e notificar o usuário por e-mail sobre as novas oportunidades encontradas. O histórico de todas as vagas monitoradas é mantido em um arquivo JSON local para análise de tendências futuras, que pode ser visualizado em ferramentas de BI como Power BI ou Google Looker Studio.
_____________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________

2. Estrutura do Repositório
O repositório principal contém os seguintes arquivos essenciais:
-main.py: O script Python principal que executa a raspagem, a lógica de atualização do histórico e o envio de e-mails.
-previous_bi_jobs.json: Um arquivo JSON que armazena o histórico de todas as vagas encontradas e monitoradas, incluindo suas datas de entrada e saída (se aplicável), e status.
-requirements.txt: Lista as dependências Python necessárias para o projeto.
-.github/workflows/scrape_and_email.yml: O arquivo de configuração do GitHub Actions que automatiza a execução do main.py em um cronograma regular.

_______________________________________________________________________________________________________________________________________________________________________________________________

3. Detalhamento do Arquivo: main.py
O arquivo main.py é o coração da automação. Ele orquestra todas as etapas do processo: desde a configuração do ambiente de raspagem até a gestão do histórico e a notificação.
Caminho do Arquivo: main.py

Propósito:
Este script Python é responsável por:
-Inicializar e configurar o navegador Chrome para raspagem web (web scraping).
-Navegar até o portal de carreiras do iFood.
-Interagir com a página (aceitar cookies, usar campo de busca).
-Raspar os detalhes das vagas (título e link).
-Filtrar as vagas raspadas com base em palavras-chave relevantes para Analista de BI e áreas afins.
-Gerenciar um histórico de vagas (previous_bi_jobs.json), marcando vagas como "fechadas" se não forem mais encontradas e adicionando novas vagas como "ativas".
-Enviar notificações por e-mail para o usuário sobre novas vagas detectadas.

Bibliotecas Utilizadas:
-os: Para interagir com o sistema operacional, especialmente para obter variáveis de ambiente (como credenciais de e-mail).
-json: Para ler e escrever dados no formato JSON (previous_bi_jobs.json).
-selenium: Uma ferramenta poderosa para automação de navegadores web, usada para interagir com o site do iFood de forma programática.
-webdriver.Chrome: O driver para controlar o navegador Chrome.
-Options: Para configurar opções do Chrome (ex: modo headless, tamanho da janela).
-By: Para localizar elementos na página por diferentes critérios (ID, XPATH, CSS_SELECTOR).
-WebDriverWait, expected_conditions as EC: Para esperar que elementos específicos apareçam ou se tornem clicáveis na página, garantindo a robustez da raspagem.
-Keys: Para simular o pressionamento de teclas (ex: ENTER no campo de busca).
-beautifulsoup4 (bs4): Uma biblioteca para parsing de HTML e XML, usada para extrair dados das páginas raspadas de forma eficiente.
-time: Para introduzir pausas no script, permitindo que a página carregue completamente ou que as ações do navegador sejam processadas.
-webdriver_manager.chrome: Facilita o gerenciamento do ChromeDriver, baixando e instalando a versão correta automaticamente.
-smtplib: Para enviar e-mails via protocolo SMTP.
-email.mime.text, email.mime.multipart: Para criar mensagens de e-mail com conteúdo HTML.
-datetime: Do módulo datetime, usada para obter a data e hora atual para registrar a date_entrada e date_saida das vagas.

Seções Principais e Funcionalidades:
Configurações de E-mail (SENDER_EMAIL, SENDER_PASSWORD, RECEIVER_EMAIL, EMAIL_SUBJECT):
  -Definem as credenciais e o destinatário para o envio de e-mails, obtidas via variáveis de ambiente para segurança.
  -SENDER_EMAIL: E-mail remetente.
  -SENDER_PASSWORD: Senha do e-mail remetente (preferencialmente uma senha de aplicativo para Gmail).
  -RECEIVER_EMAIL: E-mail destinatário.
  -EMAIL_SUBJECT: Assunto do e-mail de notificação.
  
Configurações de Raspagem (URL, TARGET_JOB_TITLE_KEYWORDS, PREVIOUS_JOBS_FILE):
  -URL: Endereço base do site de carreiras do iFood.
  -TARGET_JOB_TITLE_KEYWORDS: Uma lista de palavras-chave usadas para filtrar as vagas. O script buscará por vagas que contenham qualquer uma dessas palavras-chave no título (ignorando maiúsculas/minúsculas).
  -PREVIOUS_JOBS_FILE: O nome do arquivo JSON onde o histórico de vagas será armazenado.
get_ifood_job_listings(url, keywords) Função:
Propósito: Esta é a função central de web scraping. Ela configura o navegador, navega até a URL, interage com a página e extrai as informações das vagas.

Configuração do Chrome:
  -Instancia Options para configurar o Chrome em modo headless (sem interface gráfica), desabilitando a sandbox e o uso de /dev/shm (comuns em ambientes Linux como o GitHub Actions), definindo um tamanho de janela e desabilitando a GPU.
  -Define chrome_options.binary_location para /usr/bin/google-chrome, garantindo que o Selenium encontre o binário do Chrome em ambientes Linux.
  -Utiliza webdriver.ChromeService(ChromeDriverManager().install()) para gerenciar o ChromeDriver, assegurando que a versão compatível seja baixada automaticamente.

Navegação e Interação:
  -Abre a url fornecida.
  -Usa WebDriverWait e expected_conditions para esperar que o botão de aceitar cookies (se presente) ou o campo de busca se tornem clicáveis. Isso aumenta a robustez contra variações no carregamento da página.
  -Tenta aceitar o banner de cookies usando um XPath genérico que busca por botões com "concordar" ou "aceitar" no texto (case-insensitive).
  -Localiza o campo de busca (primeiro por ID, depois por um XPath mais genérico com placeholder) e digita a primeira palavra-chave definida em TARGET_JOB_TITLE_KEYWORDS, seguido por Keys.ENTER para iniciar a busca.
  -Aguarda a presença e visibilidade dos elementos que contêm as listagens de vagas (ul.sc-ienWRC e seus lis).

Extração de Dados:
  -Realiza rolagem da página (window.scrollTo) para garantir que todas as vagas dinamicamente carregadas sejam visíveis antes de parsear o HTML.
  -Usa BeautifulSoup para parsear o driver.page_source (o HTML da página).
  -Seleciona todos os elementos <li> dentro de ul.sc-ienWRC que representam as vagas.
  -Itera sobre cada elemento de vaga, extraindo o title (do texto de h4 a) e o link (do atributo href do a). Normaliza os links para serem absolutos, se necessário.

Filtragem:
  -Filtra as vagas extraídas com base nas keywords fornecidas, comparando-as com o título da vaga (case-insensitive).
  -Fechamento do Driver:
  -Garate que driver.quit() seja chamado no bloco finally para fechar o navegador Selenium, liberando recursos, mesmo que ocorram erros.
  -Retorno: Retorna uma lista de dicionários, onde cada dicionário representa uma vaga filtrada com title e link.

Fechamento do Driver:
  -Garate que driver.quit() seja chamado no bloco finally para fechar o navegador Selenium, liberando recursos, mesmo que ocorram erros.
  -Retorno: Retorna uma lista de dicionários, onde cada dicionário representa uma vaga filtrada com title e link.
send_email(sender_email, sender_password, receiver_email, subject, body_html) Função:

Propósito: Envia um e-mail com o corpo formatado em HTML.
  -Configuração: Cria uma mensagem multipart (MIMEMultipart) para suportar conteúdo HTML.
  -Servidor SMTP: Conecta-se ao servidor SMTP do Gmail (smtp.gmail.com, porta 465) usando SSL para segurança.
  -Autenticação e Envio: Realiza login com as credenciais fornecidas e envia o e-mail.
  -Tratamento de Erros: Inclui um bloco try-except para capturar e imprimir erros de envio de e-mail (ex: credenciais incorretas).
  -Fechamento da Conexão: Garante que a conexão SMTP seja fechada no bloco finally.

Funções para Gerenciar o Histórico de Vagas (load_all_jobs_history, save_all_jobs_history):
load_all_jobs_history(file_path):
  -Carrega o conteúdo do arquivo JSON especificado.
  -Se o arquivo não existir ou estiver corrompido, retorna uma lista vazia e imprime um aviso.
save_all_jobs_history(file_path, history):
  -Salva a lista history (que contém todas as vagas e seus status) no arquivo JSON especificado.
  -Usa indent=4 para formatar o JSON de forma legível e ensure_ascii=False para permitir caracteres especiais.

Execução Principal (if __name__ == "__main__":):
-today: Obtém a data atual no formato YYYY-MM-DD.
-Carregamento do Histórico: Chama load_all_jobs_history para carregar o estado atual do previous_bi_jobs.json.
-Raspagem de Vagas Atuais: Chama get_ifood_job_listings para obter as vagas atualmente listadas no site do iFood.

Gerenciamento de Status das Vagas:
  -Marcação de Vagas Fechadas: Itera sobre o all_jobs_history. Se uma vaga ativa no histórico não for encontrada na lista de current_scraped_jobs_links (extraídos da raspagem atual), seu status é alterado para 'fechada' e date_saida é preenchida com a data de hoje.
  -Adição de Novas Vagas: Itera sobre current_scraped_jobs_simple. Se uma vaga raspada não for encontrada no existing_job_links_in_history, ela é considerada nova. É adicionada ao all_jobs_history com status: 'ativa', date_entrada: today e date_saida: None. Ela também é adicionada à lista new_jobs_to_notify para envio de e-mail.
  -Reabertura de Vagas: Se uma vaga que estava no histórico como 'fechada' reaparecer na raspagem atual, seu status é atualizado para 'ativa' e date_saida é definida como None.

Salvamento do Histórico:
  -Após todas as atualizações de status, save_all_jobs_history é chamada para persistir o histórico completo no arquivo JSON.

Envio de E-mail:
  -Verifica se new_jobs_to_notify não está vazia.
  -Se houver novas vagas, constrói o corpo do e-mail em HTML, listando os títulos e links das novas vagas.
  -Chama send_email para enviar a notificação.
  -Se não houver novas vagas, imprime uma mensagem informativa.
  
_____________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________

4. Detalhamento do Arquivo: previous_bi_jobs.json
Caminho do Arquivo: previous_bi_jobs.json
Propósito:
Este arquivo atua como um banco de dados local para registrar e monitorar o ciclo de vida das vagas de Analista de BI e áreas correlatas no iFood. Ele é essencial para que o script possa diferenciar entre vagas já conhecidas, vagas novas e vagas que foram removidas do site.

Estrutura:
O arquivo é um array JSON de objetos, onde cada objeto representa uma vaga e contém os seguintes campos:
  -"title": String. O título completo da vaga, conforme raspado do site.
  -"link": String. O URL direto para a página da vaga no site de carreiras do iFood. Este campo serve como identificador único para cada vaga.
  -"date_entrada": String. A data em que a vaga foi detectada pela primeira vez e adicionada ao histórico, no formato YYYY-MM-DD.
  -"date_saida": String ou null. A data em que a vaga foi identificada como "fechada" (não mais presente na raspagem), no formato YYYY-MM-DD. Será null se a vaga estiver atualmente ativa.
  -"status": String. O status atual da vaga. Pode ser "ativa" (se a vaga foi encontrada na última raspagem) ou "fechada" (se não foi encontrada).

Exemplo de Conteúdo:

 {
    "title": "Analista de Business Intelligence Sênior",
    "link": "https://carreiras.ifood.com.br/vaga/analista-bi-senior-12345",
    "date_entrada": "2024-05-20",
    "date_saida": null,
    "status": "ativa"
  },

Gerenciamento pelo Script:
-O script main.py lê este arquivo no início de cada execução para carregar o histórico.
-Após a raspagem, ele compara as vagas recém-encontradas com as do histórico para:
  -Marcar vagas existentes como fechada se elas não aparecerem na raspagem atual.
  -Adicionar novas vagas ao arquivo com status ativa.
  -Atualizar o status para ativa e date_saida para null se uma vaga fechada reaparecer.
-O arquivo é sobrescrito com o histórico atualizado ao final de cada execução.
-No GitHub Actions, um passo específico (Check for previous_bi_jobs.json and create if not exists) garante que, se o arquivo não existir (na primeira execução ou após um reset), ele será criado como um array JSON vazio ([]) para evitar erros.

_____________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________

5. Detalhamento do Arquivo: requirements.txt
Caminho do Arquivo: requirements.txt

Propósito:
Este arquivo lista todas as bibliotecas Python de terceiros das quais o projeto depende. É uma prática padrão em projetos Python para garantir que o ambiente de execução (local ou em servidores de CI/CD como o GitHub Actions) tenha todas as dependências necessárias instaladas com as versões corretas.

Formato:
Cada linha do arquivo especifica o nome de uma biblioteca. Opcionalmente, você pode especificar uma versão exata ou um intervalo de versões.

Conteúdo:
  selenium
  webdriver-manager
  beautifulsoup4

Dependências Listadas:
  -selenium: A biblioteca principal para automação de navegadores, usada para interagir com o site do iFood. 
  -webdriver-manager: Uma ferramenta que simplifica o gerenciamento de drivers de navegador (como o ChromeDriver), baixando e configurando-os automaticamente. 
  -beautifulsoup4: Uma biblioteca para parsing (análise) de HTML e XML, utilizada para extrair dados dos elementos da página após a raspagem pelo Selenium. 
Uso no Projeto:
  -No ambiente de desenvolvimento local, você pode instalar todas as dependências listadas executando pip install -r requirements.txt.
  -No fluxo de trabalho do GitHub Actions (scrape_and_email.yml), o passo Install Python dependencies utiliza este arquivo para configurar o ambiente de execução antes de rodar o script main.py.

___________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________________

6. Detalhamento do Arquivo: scrape_and_email.yml
Caminho do Arquivo: .github/workflows/scrape_and_email.yml

Propósito:
Este arquivo de configuração YAML define um fluxo de trabalho (workflow) do GitHub Actions. Ele automatiza a execução do script main.py em um ambiente de nuvem, garantindo que o monitor de vagas seja executado periodicamente sem intervenção manual e que o histórico de vagas seja atualizado no repositório.

Gatilhos (on):
schedule:
  -cron: '0 */4 * * *': Este é um cron job que agenda a execução do workflow a cada 4 horas. O 0 significa minuto 0, */4 significa a cada 4 horas, e os asteriscos subsequentes significam qualquer dia do mês, qualquer mês, qualquer dia da semana.
workflow_dispatch:
  -Permite que o workflow seja acionado manualmente a partir da interface do usuário do GitHub (na aba "Actions" do seu repositório). Isso é útil para depuração ou para forçar uma execução fora do cronograma.

Jobs (jobs):
O workflow contém um único job chamado scrape_and_send.
  -runs-on: ubuntu-latest: Especifica que este job será executado em uma máquina virtual Linux (Ubuntu) hospedada pelo GitHub.
  -permissions: contents: write: CRUCIAL. Esta permissão é fundamental. Ela concede ao workflow a capacidade de escrever (modificar e commitar) no repositório. Isso é necessário para que o main.py possa atualizar o arquivo previous_bi_jobs.json e para que o GitHub Actions possa fazer o git commit e git push dessas alterações de volta para o repositório.

Passos (steps):
Cada passo é uma ação sequencial executada no ambiente do job.
1- name: Checkout repository:
  -uses: actions/checkout@v4: Utiliza uma action pré-definida do GitHub para clonar o repositório no ambiente de execução.
  -with: token: ${{ secrets.GITHUB_TOKEN }}: O GITHUB_TOKEN é um token de acesso temporário fornecido automaticamente pelo GitHub Actions. Ele é necessário para que a ação de checkout tenha permissão para interagir com o repositório, especialmente quando as permissões de escrita são necessárias.
2- name: Debug - List repository root after checkout:
  -run: |: Executa uma série de comandos de shell.
  -echo "Conteúdo da raiz do repositório APÓS checkout:": Imprime uma mensagem para o log do workflow.
  -pwd: Imprime o diretório de trabalho atual (deve ser a raiz do repositório clonado).
  -ls -la: Lista o conteúdo do diretório atual, incluindo arquivos ocultos, para fins de depuração. Isso ajuda a verificar se todos os arquivos do seu projeto estão presentes após o checkout.
3- name: Set up Python:
   -uses: actions/setup-python@v5: Utiliza uma action para configurar o ambiente Python.
   -with: python-version: '3.9': Especifica a versão do Python a ser usada (Python 3.9).
4 - name: Install Google Chrome stable:
  -run: |: Bloco de comandos para instalar o Google Chrome no ambiente Ubuntu.
  -Inclui comandos apt-get update, curl, gpg, echo, e tee para adicionar o repositório do Chrome e instalar a versão estável.
  -google-chrome-stable --version: Verifica se a instalação foi bem-sucedida imprimindo a versão do Chrome.
5- name: Install Python dependencies:
  -run: |: Instala as dependências Python.
  -python -m pip install --upgrade pip: Garante que o pip esteja atualizado.
  -pip install -r requirements.txt: Instala todas as bibliotecas listadas no arquivo requirements.txt do diretório raiz.
6- name: Check for previous_bi_jobs.json and create if not exists:
  -run: |: Um passo de preparação para o arquivo de histórico.
  -if [ ! -f previous_bi_jobs.json ]; then ... fi: Verifica se o arquivo previous_bi_jobs.json não existe.
  -Se não existir, ele cria o arquivo com um array JSON vazio ([]), garantindo que o main.py não falhe na primeira execução ao tentar carregar um arquivo inexistente ou corrompido.
  -ls -l previous_bi_jobs.json: Lista o arquivo para verificar sua presença e permissões.
7- name: Run scraper and send email:
  -env:: Define variáveis de ambiente que serão acessíveis ao script main.py durante esta execução.
    -SENDER_EMAIL, SENDER_PASSWORD, RECEIVER_EMAIL: Estas variáveis são preenchidas com os secrets configurados no repositório GitHub. É crucial que você configure esses segredos (Secrets) no seu repositório GitHub (Settings > Secrets and variables > Actions > New repository secret) para SENDER_EMAIL, SENDER_PASSWORD, e RECEIVER_EMAIL. Isso evita que credenciais sensíveis sejam expostas no código.
  -run: |: Executa o script Python principal.
  -echo "Caminho atual para python main.py:": Imprime o diretório atual.
  -pwd: Confirma o diretório de trabalho.
  -python main.py: Executa o script Python main.py, que fará a raspagem, atualização do histórico e envio de e-mails.
8- name: Commit updated previous_bi_jobs.json:
  -run: |: Este passo é responsável por salvar as alterações feitas no previous_bi_jobs.json de volta no repositório.
  -git config user.name "github-actions[bot]" e git config user.email "github-actions[bot]@users.noreply.github.com": Configura as informações do autor do commit para o bot do GitHub Actions.
  -git add previous_bi_jobs.json: Adiciona o arquivo previous_bi_jobs.json (que foi modificado pelo main.py) ao staging area do Git.
  -git commit -m "Atualiza histórico de vagas BI [skip ci]" || true: Cria um commit com uma mensagem descritiva. O [skip ci] na mensagem do commit é uma convenção para instruir o GitHub Actions a não disparar outro workflow de CI/CD (incluindo este mesmo workflow) para este commit específico, evitando um loop infinito. O || true garante que o passo não falhe se não houver nenhuma alteração no arquivo (ou seja, se git commit não tiver nada para commitar).
  -git push: Envia o commit (com as alterações no previous_bi_jobs.json) para o repositório remoto no GitHub.

