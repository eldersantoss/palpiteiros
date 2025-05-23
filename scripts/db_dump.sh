#!/bin/bash

echo """
IMPORTANTE: certifique-se de ter o pg_dump disponível e ter definido/carregado no shell as seguintes variáveis:

- DB_HOST
- DB_NAME
- DB_USER
- DB_PASSWORD
- DB_PORT
"""

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

DUMP_FILE="db_dump_$(date +%Y%m%d%H%M%S).tar"

PGPASSWORD=$DB_PASSWORD pg_dump -h $DB_HOST -d $DB_NAME -U $DB_USER -p $DB_PORT -F t -n public > $DUMP_FILE

if [ $? -eq 0 ]; then
    echo """
Dump do banco de dados realizado com sucesso e salvo no arquivo $DUMP_FILE
"""
else
    echo """
Ocorreu um erro ao realizar o dump do banco de dados
"""
fi
