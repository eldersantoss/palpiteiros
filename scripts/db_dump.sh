echo """
IMPORTANTE: certifique-se de ter o pg_dump disponível e ter definido/carregado no shell as seguintes variáveis:

- DB_HOST
- DB_NAME
- DB_USER
- DB_PASSWORD
- DB_PORT
"""

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

DUMP_FILE="db_dump_public_schema_$(date +%Y%m%d%H%M%S).tar"

PGPASSWORD=$DB_PASSWORD pg_dump -h $DB_HOST -d $DB_NAME -U $DB_USER -p $DB_PORT -F t -n public --data-only > $DUMP_FILE

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Dump do schema 'public' realizado com sucesso e salvo no arquivo $DUMP_FILE"
    echo ""
else
    echo ""
    echo "❌ Ocorreu um erro ao realizar o dump do banco de dados."
    echo ""
fi
