#!/bin/bash

# Verifica se um arquivo foi passado como parâmetro
if [ -z "$1" ]; then
    echo "Erro: Por favor, forneça o caminho do arquivo de dump (.tar) a ser restaurado."
    exit 1
fi

DUMP_FILE=$1

echo """
IMPORTANTE: Este script restaura o schema 'public' de um backup.
Ele irá APAGAR e RECRRIAR o schema 'public' no banco de dados de destino.
Certifique-se de:
1. Ter um container PostgreSQL padrão em execução.
2. Ter definido/carregado as variáveis de ambiente do banco de dados:
  - DB_HOST
  - DB_NAME
  - DB_USER
  - DB_PASSWORD
  - DB_PORT
"""

# Verifica se o arquivo de dump existe
if [ ! -f "$DUMP_FILE" ]; then
    echo "Erro: O arquivo de dump $DUMP_FILE não existe."
    exit 1
fi

# Se existir um arquivo .env, pergunta ao usuário se deseja carregá-lo
if [ -f .env ]; then
    read -p "Arquivo .env encontrado. Deseja carregar as variáveis de ambiente dele? (y/n): " resposta
    if [[ "$resposta" =~ ^[Yy]$ ]]; then
        export $(grep -v '^#' .env | xargs)
        echo "Variáveis de ambiente do .env carregadas."
    else
        echo "Carregamento do .env ignorado. Seguindo com variáveis previamente carregadas no shell."
    fi
fi

# Função para verificar se uma variável de ambiente está definida
check_env_var() {
    local var_name=$1
    local var_value="${!var_name}"

    if [ -z "$var_value" ]; then
        echo "Erro: A variável de ambiente $var_name não está definida."
        exit 1
    fi
}

# Verificar variáveis de ambiente
check_env_var "DB_HOST"
check_env_var "DB_NAME"
check_env_var "DB_USER"
check_env_var "DB_PASSWORD"
check_env_var "DB_PORT"

# --- Solicitar confirmação ---
echo ""
echo "------------------------------------------------------------------"
echo "ATENÇÃO: Esta ação é destrutiva e irreversível."
echo "Você está prestes a LIMPAR e RESTAURAR o schema 'public' no seguinte banco de dados:"
echo ""
echo "  Banco:    $DB_NAME"
echo "  Host:     $DB_HOST"
echo "  Usuário:  $DB_USER"
echo ""
read -p "Deseja continuar? (y/n): " confirm
if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
    echo "Restauração cancelada pelo usuário."
    exit 1
fi
echo "------------------------------------------------------------------"
echo ""

echo "Iniciando a restauração do schema 'public' a partir de $DUMP_FILE..."
PGPASSWORD=$DB_PASSWORD pg_restore -h $DB_HOST -d $DB_NAME -U $DB_USER -p $DB_PORT -F t --no-owner --clean --no-privileges "$DUMP_FILE"

# Verifica se o restore foi bem-sucedido
if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Restore do schema 'public' realizado com sucesso."
    echo ""
else
    echo ""
    echo "❌ Ocorreu um erro ao realizar o restore do banco de dados."
    echo ""
fi
