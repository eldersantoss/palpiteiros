<div align="center">
  <img src="core\static\core\img\palpiteiros.png" width="100px">
  <h2>Palpiteiros</h2>
  <p>Seu app de palpites em partidas de futebol 🍀</p>

  [![License](https://img.shields.io/github/license/eldersantoss/palpiteiros)](https://creativecommons.org/licenses/by-nc/4.0/legalcode)
  [![Issues](https://img.shields.io/github/issues/eldersantoss/palpiteiros)](https://github.com/eldersantoss/palpiteiros/issues)
  [![Last commit](https://img.shields.io/github/last-commit/eldersantoss/palpiteiros)](https://github.com/eldersantoss/palpiteiros/commits/main)
</div>

- [🚀 **Funcionalidades**](#-funcionalidades)
- [🛠 **Tecnologias utilizadas**](#-tecnologias-utilizadas)
- [🤗 **Contribuindo**](#-contribuindo)
- [🔥 **Configurando ambiente de desenvolvimento**](#-configurando-ambiente-de-desenvolvimento)
- [⚖ **Licença**](#-licença)

<!-- <div align="center"><img src="docs\animacao.gif" width="250"></div> -->

## 🚀 **Funcionalidades**

* `Autenticação`: o usuário pode se cadastrar, fazer login e recuperar sua senha através do email.

* `Edição de perfil`: o usuário poderá visualizar e editar suas informações pessoais e algumas preferências como, por exemplo, se deseja receber *notificações por email*.

* `Área de administração`: permite ao admin da aplicação gerenciar as ligas, competições, usuários, tarefas de execução periódicas, etc.

* `Criação de bolões públicos e privados`: o jogador pode criar seus próprios bolões públicos ou privados, sendo os **bolões públicos** acessíveis a todos os outros jogadores através da *página de busca de bolões* e os **bolões privados** acessíveis somente por meio do link de acesso exclusivo, disponibilizado ao dono do bolão na página de *Gerenciar bolão*. Além disso, durante a criação, o jogador poderá escolher quais partidas deseja que sejam incluídas no bolão: baseadas em competições, em equipes avulsas, ou um misto dos dois. Se escolher criar seu bolão **baseado em competições**, todas as partidas dos campeonatos escolhidos serão disponibilizadas para palpites. Caso opte por criar o bolão escolhendo **equipes avulsas**, somente as partidas das equipes escolhidas serão incluídas no bolão, independentemente das competições. Por último, se escolher vincular o bolão à **competições e equipes avulsas**, tanto as partidas das competições escolhidas quanto as partidas das equipes escolhidas serão disponibilizadas para palpites no bolão.

* `Gerenciamento de bolões`: o jogador dono de um bolão poderá editar informações como o nome do bolão, se ele é público ou privado, seus participantes e as competições e equipes avulsas cadastradas. Além disso, essa página também terá o link de acesso ao bolão para permitir que outros jogadores entrem no bolão quando ele for privado.

* `Busca de bolões públicos`: tela em que os jogadores podem procurar por bolões públicos criados por outros jogadores e entrar nos que se interessar.

* `Área de palpites`: o jogador terá acesso aos jogos disponíveis para palpites e poderá deixar suas previsões.

* `Tabela de classificação`: tabela com a classificação de todos os palpiteiros do bolão e um formulário que permite a filtragem do período no qual o jogador deseja visualizar a classificação, sendo possível escolher entre as opções **geral** (da data de criação do bolão até o dia atual), **anual**, **mensal** ou **semanal**.

* `Tabela de últimos palpites`: clicando na linha de qualquer jogador na *tabela de classificação*, será exibida uma outra tabela com os dados dos seus últimos palpites daquele jogador no período em que a classificação está filtrada.

* `Cadastro e atualização automático de partidas`: novas partidas serão buscadas e cadastradas no aplicativo semanalmente para todas as competições, de forma que todas as partidas sejam disponibilizadas com tempo suficiente para que os jogadores deem seus palpites. Além disso, de hora em hora serão buscadas atualizações para as partidas já cadastradas, todos os dias.

* `Notificações por email`: os jogadores serão notificados por email quando houverem novas partidas disponíveis para palpites ou quando as partidas dos bolões dos quais fazem parte forem atualizadas. Caso queira desativar as notificações, basta acessar o perfil e desmarcar a opção.

## 🛠 **Tecnologias utilizadas**

* [Django](https://www.djangoproject.com/): framework para desenvolvimento web em Python que facilita a criação de aplicativos web robustos e escaláveis.
* [PostgreSQL](https://www.postgresql.org/): banco de dados relacional de código aberto, robusto e altamente escalável, que suporta recursos avançados como consultas complexas, índices, transações ACID e replicação.
* [Docker](https://www.docker.com/): plataforma para criação e execução de aplicativos em contêineres, proporcionando isolamento, portabilidade e facilidade na implantação.
* [Celery](https://docs.celeryq.dev/en/stable/): biblioteca Python para execução de tarefas assíncronas e distribuídas. Permite que você agende e processe tarefas em segundo plano, gerenciando filas de trabalho e garantindo a escalabilidade e o desempenho em aplicativos web.

## 🤗 **Contribuindo**

Contribuições são bem-vindas! Para contribuir, faça um fork deste repositório e clone em sua máquina. Depois, crie uma nova branch, faça as alterações que desejar e envie-as para a branch que você criou. Por último, abra um pull request da sua branch para branch main. Ah, seria muito legal se você também implementasse os testes para o seu código. 😀

Qualquer `dúvida ou sugestão`, fique à vontade para abrir uma [nova issue](https://github.com/eldersantoss/palpiteiros/issues/new).

## 🔥 **Configurando ambiente de desenvolvimento**

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

Com isso, sua aplicação Django deve estar disponível em `localhost:8000`, seu banco de dados PostgreSQL em `localhost:5432` e o Flower (serviço de monitoramento das tarefas assíncronas) em `localhost:5555`.

```bash
docker compose up
```

## ⚖ **Licença**

Este projeto é licenciado sob os termos da [Licença CC BY-NC 4.0](https://creativecommons.org/licenses/by-nc/4.0/legalcode).
