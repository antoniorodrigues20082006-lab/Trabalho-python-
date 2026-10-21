# Publicar a Cantina no Streamlit

Use o novo pacote **cantina-streamlit-deploy.zip**. Ele contém a interface
Streamlit, a camada MySQL e o certificado CA público do Aiven. Não contém senha.

## 1. Envie ao GitHub

Extraia o ZIP e envie o conteúdo extraído ao repositório. Não envie apenas o
arquivo ZIP. A estrutura deve ficar assim, na raiz:

```text
streamlit_app.py
streamlit_style.css
database.py
requirements.txt
.gitignore
.streamlit/
  config.toml
  secrets.example.toml
deploy/
  aiven-ca.pem
```

O pacote também inclui estas instruções e os testes. A pasta `.streamlit` deve
ser enviada, inclusive o arquivo `config.toml`. Não renomeie `streamlit_app.py`
para `app.py`: `app.py` no projeto original é a interface desktop.

Se enviar diretamente a pasta original do projeto, confirme que o
`requirements.txt` atualizado inclui `streamlit`. O pacote novo já tem um
`requirements.txt` mínimo adequado para o Community Cloud.

## 2. Crie o aplicativo

1. Entre em https://share.streamlit.io/ com sua conta GitHub.
2. Clique em **Create app** e escolha a opção para publicar do GitHub.
3. Selecione seu repositório e a branch onde enviou os arquivos.
4. Em **Main file path**, informe exatamente **`streamlit_app.py`**.
5. Abra **Advanced settings** e selecione **Python 3.12**.
6. No campo **Secrets**, cole o modelo abaixo e preencha o Host e a senha atual
   do painel do Aiven. Todos os campos ficam no nível raiz do TOML; não adicione
   uma seção `[mysql]`.

```toml
MYSQL_HOST = "seu-host-do-aiven.f.aivencloud.com"
MYSQL_PORT = "26176"
MYSQL_USER = "avnadmin"
MYSQL_PASSWORD = "sua-senha-atual-do-aiven"
MYSQL_DATABASE = "defaultdb"
MYSQL_CREATE_DATABASE = "false"
MYSQL_SSL_CA = "deploy/aiven-ca.pem"
```

7. Salve e clique em **Deploy**. Aguarde a instalação das dependências.
8. Quando o aplicativo abrir, entre com sua conta da cantina ou clique em **Criar registro**.

Depois da publicação, o endereço será `https://...streamlit.app`, acessível com
seu computador desligado. O banco permanece no Aiven. Contas, produtos e
movimentações existentes nesse mesmo banco são reaproveitados.

## Como usar

- **Início:** produtos em linhas horizontais, com itens em alerta primeiro.
- **Produtos:** busca, cadastro e edição; botões de entrada e saída em cada produto.
- **Vendas:** histórico de entradas e saídas em cards, com data, quantidade e valor.
- **Configurações:** conta, alteração de senha, alertas de estoque/validade e conexão.
  Ao trocar a senha, o aplicativo pede login novamente.
- **Sair da conta:** encerra a sessão atual. Uma atualização completa da página
  também pode encerrar a sessão, porque o login usa o estado da sessão Streamlit.

Uma nova conta usa senha com pelo menos 8 caracteres. Contas antigas do mesmo
banco continuam sendo aceitas. Cada conta tem acesso ao próprio estoque.
Não há cache compartilhado de dados de usuários: cada consulta usa a conta logada.

O visual retoma a paleta do aplicativo original: fundo azul-escuro, login central,
perfil e indicadores na barra lateral, botões azuis e alertas em verde, rosa e âmbar.
Envie também `streamlit_style.css`, responsável por esses estilos.

## Testar no computador

Na pasta original, mantenha o `.env` já configurado e execute:

```powershell
python -m pip install -r requirements-streamlit.txt
python -m streamlit run streamlit_app.py
```

No pacote extraído, instale `requirements.txt`. Para a conexão local, crie
`.streamlit/secrets.toml` com os mesmos campos do painel, ou use um `.env`.
O caminho do CA deve corresponder ao arquivo disponível: no pacote é
`deploy/aiven-ca.pem`; no `.env` original ele pode ser `certs/ca.pem`.

## Se houver erro

- **No module named streamlit/mysql/dotenv:** confira `requirements.txt` na raiz.
- **Tela sem o visual ou erro de arquivo de estilo:** confirme `streamlit_style.css` ao lado de `streamlit_app.py`.
- **Can't open file:** confira o Main file path e a localização de `streamlit_app.py`.
- **Não foi possível acessar o banco:** confira os Secrets, o status Running no Aiven
  e a presença de `deploy/aiven-ca.pem` no GitHub.
- **Tentando acessar um banco local:** os Secrets do Aiven não foram aplicados. No
  aplicativo publicado, abra **Settings → Secrets**, preencha os campos do modelo
  no nível raiz (sem `[mysql]`) e reinicie o aplicativo depois de salvar.
- **Código MySQL 1045:** confira o usuário e a senha atuais no Aiven.
- **Certificado CA não encontrado:** confirme a pasta `deploy` e o arquivo
  `aiven-ca.pem` no repositório; nomes e maiúsculas devem coincidir com os Secrets.
- **Alterou a senha do banco:** atualize `MYSQL_PASSWORD` nos Secrets e reinicie o app.
- **Certificado mudou:** substitua `deploy/aiven-ca.pem` pelo CA atual do serviço.

Não publique `.env` ou `.streamlit/secrets.toml` no GitHub. O arquivo de exemplo
tem apenas campos vazios/exemplos; a senha real deve ficar no painel Secrets.

Documentação oficial:
https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy
