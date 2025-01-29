<div align="center">
  <img src="core\static\core\img\palpiteiros.png" width="100px">
  <h2>Palpiteiros</h2>
  <p>Seu app de palpites em partidas de futebol 🍀</p>

  [![Issues](https://img.shields.io/github/issues/eldersantoss/palpiteiros)](https://github.com/eldersantoss/palpiteiros/issues)
  [![Last commit](https://img.shields.io/github/last-commit/eldersantoss/palpiteiros)](https://github.com/eldersantoss/palpiteiros/commits/main)
</div>

- [**Configurando ambiente de desenvolvimento**](#configurando-ambiente-de-desenvolvimento)
- [**Comandos úteis**](#comandos-úteis)
  - [**Executando os testes**](#executando-os-testes)
  - [**Cadastrando ou atualizando competições**](#cadastrando-ou-atualizando-competições)
  - [**Cadastrando ou atualizando equipes de uma competição**](#cadastrando-ou-atualizando-equipes-de-uma-competição)
  - [**Cadastrando e atualizando partidas**](#cadastrando-e-atualizando-partidas)
  - [**Dump e restauração do banco de dados**](#dump-e-restauração-do-banco-de-dados)
    - [Dump](#dump)
    - [Restauração](#restauração)
- [**Contribuindo**](#contribuindo)
- [**Licença**](#licença)

## **Configurando ambiente de desenvolvimento**

Utilizando [Docker Compose](https://docs.docker.com/compose/):

**1.** Clone o repositório
```bash
git clone https://github.com/eldersantoss/palpiteiros.git
```

**2.** Acesse o diretório do projeto e crie o arquivo `.env`, com as variáveis de ambiente, a partir do arquivo de exemplo `.env.example`:
```bash
cd palpiteiros
cp .env.example .env
```

* Não esqueça de preencher os valores das configurações dentro do arquivo .env.

**3.** Dentro da raiz do projeto, onde está o arquivo `docker-compose.yml`, inicie os contêineres dos serviços:
```bash
docker compose up -d
```

**4.** Crie um ambiente virtual, instale as dependências do projeto e execute as migrações do banco de dados:
```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
```

**5.** Crie um superusuário para acessar a aplicação e a área de administração:
```bash
python manage.py createsuperuser
```

**6.** Inicie o servidor de desenvolvimento e acesse a aplicação em `localhost:8000` e a área de administração em `localhost:8000/admin`.
```bash
python manage.py runserver
```

## **Comandos úteis**

### **Executando os testes**
```bash
pytest
```
**Obs:** sempre que alguma alteração nos modelos for realizada, é necessário executar o comando `pytest --create-db` para recriar o banco de dados de testes.

### **Cadastrando ou atualizando competições**
```bash
python manage.py create_or_update_competitions <league_ids>
```

### **Cadastrando ou atualizando equipes de uma competição**
```bash
python manage.py create_or_update_teams_for_competitions <season> <league_ids>
```

### **Cadastrando e atualizando partidas**
```bash
python manage.py create_or_update_matches
```

### **Dump e restauração do banco de dados**
#### Dump
```bash
./scripts/db_dump.sh
```

#### Restauração
```bash
./scripts/db_restore.sh
```

**Obs:** para efetuar as operações no banco de dados de produção, basta definir/carregar no shell as váriaveis solicitadas pelo script (DB_HOST, DB_NAME, DB_USER, DB_PASSWORD e DB_PORT) com os valores de produção.

## **Contribuindo**

Contribuições são bem-vindas! Para contribuir, faça um fork deste repositório, crie uma nova branch para suas contribuições, faça as alterações que desejar e envie-as para a branch que você criou através de um pull request da sua branch para a branch main. Ah, não esqueça de implementar os testes para o seu código.

Qualquer dúvida ou sugestão, fique à vontade para abrir uma [issue](https://github.com/eldersantoss/palpiteiros/issues/new).

## **Licença**

Este projeto é licenciado sob os termos da [Licença CC BY-NC 4.0](https://creativecommons.org/licenses/by-nc/4.0/legalcode).
