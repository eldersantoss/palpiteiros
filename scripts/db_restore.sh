#!/bin/bash

# Verifica se um arquivo foi passado como parâmetro
if [ -z "$1" ]; then
    echo "Erro: Por favor, forneça o caminho do arquivo de dump (.tar) a ser restaurado."
    exit 1
fi

DUMP_FILE=$1

echo """
IMPORTANTE: certifique-se de ter o pg_restore disponível, ter aplicado as migrações do Django e ter definido/carregado no shell as seguintes variáveis:

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
    if [ "$resposta" = "y" ]; then
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

# Executa o pg_restore no servidor remoto utilizando o dump fornecido
PGPASSWORD=$DB_PASSWORD pg_restore -h $DB_HOST -d $DB_NAME -U $DB_USER -p $DB_PORT -F t -c "$DUMP_FILE"

# Verifica se o restore foi bem-sucedido
if [ $? -eq 0 ]; then
    echo """
Restore do banco de dados realizado com sucesso utilizando o dump $DUMP_FILE
"""
else
    echo """
Ocorreu um erro ao realizar o restore do banco de dados
"""
fi
