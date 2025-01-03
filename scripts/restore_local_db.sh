#!/bin/bash

# Verifica se um arquivo foi passado como parâmetro
if [ -z "$1" ]; then
    echo "Erro: Por favor, forneça o nome do arquivo de dump a ser restaurado."
    exit 1
fi

DUMP_FILE_PATH=$1

echo """
===================================================== ATENÇÃO =====================================================

Certifique-se de ter aplicado as migrações do Django e carregado as variáveis de ambiente do projeto local no shell
antes de executar este script. Isso pode ser feito através dos comandos:

$ python manage.py migrate
$ source .env
"""

# Verifica se o arquivo de dump existe
if [ ! -f "$DUMP_FILE_PATH" ]; then
    echo "Erro: O arquivo de dump $DUMP_FILE_PATH não existe."
    exit 1
fi

# Função para verificar se uma variável de ambiente está definida
check_env_var() {
    local var_name=$1
    local var_value=$(eval echo \$$var_name)

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
PGPASSWORD=$DB_PASSWORD pg_restore -h $DB_HOST -d $DB_NAME -U $DB_USER -p $DB_PORT -F t -c "$DUMP_FILE_PATH"

# Verifica se o restore foi bem-sucedido
if [ $? -eq 0 ]; then
    echo """
Restore do banco de dados realizado com sucesso utilizando o dump $DUMP_FILE_PATH
"""
else
    echo """
Ocorreu um erro ao realizar o restore do banco de dados
"""
fi
