#!/bin/bash

echo """
===================================================== ATENÇÃO ===================================================

Certifique-se de ter carregado as variáveis de ambiente do projeto Railway no shell antes de executar este script.
Isso pode ser feito através dos comandos:

$ railway login -p
$ railway link <ID-PROJETO>
$ railway shell

Caso as variáveis de ambiente de desenvolvimento estiverem carregadas, o dump trará os dados do banco local.
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

# Diretório onde o dump será salvo
LOCAL_DUMP_DIR="../dumps"
DUMP_FILE_NAME="dump_railway_$(date +%Y%m%d%H%M%S).tar"

# Criar o diretório local se não existir
mkdir -p $LOCAL_DUMP_DIR

# Executa o pg_dump no servidor remoto e salva o dump localmente
PGPASSWORD=$DB_PASSWORD pg_dump -h $DB_HOST -d $DB_NAME -U $DB_USER -p $DB_PORT -F t -n public > $LOCAL_DUMP_DIR/$DUMP_FILE_NAME

# Verifica se o dump foi bem-sucedido
if [ $? -eq 0 ]; then
    echo """
Dump do banco de dados realizado com sucesso e salvo em $LOCAL_DUMP_DIR/$DUMP_FILE_NAME
"""
else
    echo """
Ocorreu um erro ao realizar o dump do banco de dados
"""
fi
