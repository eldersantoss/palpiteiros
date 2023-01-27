<div align="center">
<img src="core\static\core\img\palpiteiros.png" width="100px">
<h2>Palpiteiros</h2>
<p>Palpites em jogos de futebol</p>

[![License](https://img.shields.io/github/license/eldersantoss/palpiteiros)](https://github.com/eldersantoss/palpiteiros/blob/main/LICENSE)
[![Issues](https://img.shields.io/github/issues/eldersantoss/palpiteiros)](https://github.com/eldersantoss/palpiteiros/issues)
[![Last commit](https://img.shields.io/github/last-commit/eldersantoss/palpiteiros)](https://github.com/eldersantoss/palpiteiros/commits/main)

<img src="docs\animacao.gif" width="250">
</div>

## **Conteúdo**

* [Aplicação](#aplicação)
  * [Principais funcionalidades](#principais-funcionalidades)
  * [Teste a aplicação](#teste-a-aplicação)
* [Tecnologias utilizadas](#tecnologias-utilizadas)
* [Contribuindo](#contribuindo)
* [Configurando ambiente](#configurando-ambiente)
* [Licença](#licença)

## **Aplicação**

Resumidamente, o aplicativo consiste num jogo no qual os jogadores
(palpiteiros) podem palpitar no resultado de partidas de futebol
(inseridas no sistema por um membro da equipe de administração)
e acompanhar os resultados dos seus palpites rodada a rodada, mês a mês
e ano a ano, competindo pelo título de melhor Palpiteiro com os demais
participantes. As partidas são cadastradas e divididas em rodadas,
geralmente semanais, e os palpiteiros devem tentar adivinhar qual serão
os resultados. Cada acerto, seja ele total ou parcial, rende uma
determinada pontuação que será computada pelo aplicativo e poderá ser
consultada na tabela de classificação e detalhes da rodada.

### **Teste a aplicação**

A ideia por trás da aplicação já existe há mais de 3 anos e é praticada
por um grupo que gira em torno de 20 pessoas, incluindo a mim. Até
então, tudo era feito de forma manual, através de grupos de WhatsApp e
planilhas de Excel. Foi então que decidimos construir esse aplicativo
que, atualmente, está hospedado nos servidores gratuitos da
[Railway](https://railway.app/) e em fase de teste com alguns dos
palpiteiros do grupo. Então, caso deseje conhecer o funcionamento do
aplicação e todo o regulamento do jogo, envie um email para
elder_rn@hotmail.com e ficaremos felizes em disponibilizar uma conta de
teste para que você.

### **Principais funcionalidades**

* `Sistema de autenticação` completo com cadastro de novos usuários,
login e recuperação de senha;

  * **OBS:** o cadastro de novos usuários está temporariamente
  desativado.

* `Área de administração` devidamente configurada para conceder as
permissões necessárias para o cadastro de novas rodadas e partidas,
bem como a atualização dos resultados das partidas após seu término
aos membros da equipe;

* `Palpites:` o usuário tem acesso ao formulário para palpitar nas
partidas;

* `Classificação:` os usuários encontrarão uma tabela com a pontuação
acumulada de todos os palpiteiros em três períodos de tempo distintos
(mensal, anual e geral, computado desde a data da primeira partida
cadastrada no app), permitindo-os acompanhar seu desempenho e o dos
demais palpiteiros, bem como os vencedores nos períodos citados.

* `Rodadas:` listagem com links referentes a cada uma das rodadas já
disputadas cadatradas no sistema.

* `Detalhes da Rodada:` conjunto de tabelas aninhadas a classificação
e pontuação de todos os jogadores naquela rodada específica, além dos
palpites para cada uma das partidas e a respectiva pontuação recebida
por cada palpite. Além disso, também é possível visualizar os palpites
dos demais palpiteiros de forma discriminada clicando sobre a sua linha
na tabela.

**OBS:** Todas as telas citadas são `responsivas`.

## **Tecnologias utilizadas**

<div style="display:flex">
<a href="https://www.djangoproject.com/"><img src="https://www.opengis.ch/wp-content/uploads/2020/04/django-python-logo.png" alt="Python e Django" width=100px>
</a>
<a href="https://www.postgresql.org/"><img src="https://www.postgresql.org/media/img/about/press/elephant.png" alt="PostgreSQL" width=100px>
</a>
</div>

## **Contribuindo**

Pull Requests são bem-vindas! Para maiores mudanças, por favor abrir uma Issue para discutirmos sua proposta. Ah, seria muito bom se o código que deseja adicionar possuísse testes.

## **Configurando ambiente**

* Utilizando Docker + Docker Compose:

```bash
# clone o repositório
git clone https://github.com/eldersantoss/palpiteiros.git

# acesse a pasta do projeto, crie o arquivo .env a partir do arquivo
# .env.example e preencha o valor das várias para o seu ambiente. em
# especial, não esqueça de preencher o valor para a SECRET_KEY
cd palpiteiros
cp .env.example .env

# inicie os containers
docker compose up

# sua aplicação estará disponível para acessar através do navegador em
#  localhost:8000. alem disso, um usuário já foi sido criado com as
# credenciais ADMIN_USERNAME e ADMIN_PASSWORD que você definiu no
# arquivo .env
```

## **Licença**

Este projeto é licenciado sobre os termos da [Licença MIT](https://github.com/eldersantoss/palpiteiros/blob/main/LICENSE).
