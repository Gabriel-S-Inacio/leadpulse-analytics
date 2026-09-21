#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Source: requires-python in pyproject.toml.
MINIMUM_PYTHON_MAJOR=3
MINIMUM_PYTHON_MINOR=12
ENTRYPOINT="app/app.py"
VENV_PYTHON=".venv/bin/python"

fail() {
    printf '%s\n' "$@"
    exit 1
}

show_analytics_instructions() {
    printf '%s\n' \
        "[LeadPulse] A camada analítica ainda não está disponível." \
        "" \
        "Este projeto utiliza datasets públicos da Olist que não são versionados no Git." \
        "" \
        "Para a primeira execução:" \
        "1. obtenha os datasets conforme docs/data/source-contracts.md;" \
        "2. coloque os arquivos na estrutura data/raw indicada no README;" \
        "3. execute as ingestões documentadas no README;" \
        "4. execute dbt run;" \
        "5. execute novamente ./start.sh."
}

printf '%s\n' "[LeadPulse] Verificando Python..."
PYTHON_COMMAND=""
FOUND_PYTHON=false
for candidate in python3 python; do
    if ! command -v "$candidate" >/dev/null 2>&1; then
        continue
    fi

    candidate_path="$(command -v "$candidate")"
    case "$candidate_path" in
        *WindowsApps*) continue ;;
    esac

    if ! version="$($candidate -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")' 2>/dev/null)"; then
        continue
    fi
    FOUND_PYTHON=true

    if "$candidate" -c "import sys; raise SystemExit(0 if sys.version_info >= ($MINIMUM_PYTHON_MAJOR, $MINIMUM_PYTHON_MINOR) else 1)"; then
        PYTHON_COMMAND="$candidate"
        break
    fi
done

if [[ -z "$PYTHON_COMMAND" ]]; then
    if [[ "$FOUND_PYTHON" == true ]]; then
        fail \
            "[LeadPulse] A versão instalada do Python não é compatível." \
            "Versão mínima necessária: $MINIMUM_PYTHON_MAJOR.$MINIMUM_PYTHON_MINOR"
    fi
    fail \
        "[LeadPulse] Python compatível não foi encontrado." \
        "Instale a versão mínima indicada no README e execute novamente."
fi

printf '%s\n' "[LeadPulse] Preparando ambiente virtual..."
if [[ ! -d .venv ]]; then
    "$PYTHON_COMMAND" -m venv .venv
fi

if [[ ! -x "$VENV_PYTHON" ]]; then
    fail \
        "[LeadPulse] A pasta .venv existe, mas o Python do ambiente virtual não foi encontrado." \
        "Remova ou corrija a .venv manualmente e execute novamente."
fi

if ! "$VENV_PYTHON" -c "import sys; raise SystemExit(0 if sys.version_info >= ($MINIMUM_PYTHON_MAJOR, $MINIMUM_PYTHON_MINOR) else 1)"; then
    fail \
        "[LeadPulse] O Python da .venv não é compatível." \
        "Versão mínima necessária: $MINIMUM_PYTHON_MAJOR.$MINIMUM_PYTHON_MINOR" \
        "Corrija a .venv manualmente e execute novamente."
fi

printf '%s\n' "[LeadPulse] Sincronizando dependências..."
if ! "$VENV_PYTHON" -m pip install -e ".[dev,data,dashboard]"; then
    fail "[LeadPulse] Não foi possível instalar as dependências do projeto."
fi

printf '%s\n' "[LeadPulse] Verificando configuração..."
if [[ ! -f .env ]]; then
    if [[ ! -f .env.example ]]; then
        fail \
            "[LeadPulse] Arquivo .env não encontrado." \
            "[LeadPulse] O arquivo .env.example também não existe. Restaure-o e execute novamente."
    fi
    printf '%s\n' \
        "[LeadPulse] Arquivo .env não encontrado." \
        "[LeadPulse] Criando .env a partir de .env.example..."
    cp .env.example .env
fi

printf '%s\n' "[LeadPulse] Verificando Docker..."
if ! command -v docker >/dev/null 2>&1 || ! docker --version >/dev/null 2>&1; then
    fail \
        "[LeadPulse] Docker não foi encontrado." \
        "Instale Docker Desktop ou Docker Engine com Compose e execute novamente."
fi

if ! docker info >/dev/null 2>&1; then
    fail \
        "[LeadPulse] Docker está instalado, mas o daemon não está disponível." \
        "Inicie o Docker e execute novamente."
fi

if ! docker compose version >/dev/null 2>&1; then
    fail \
        "[LeadPulse] Docker Compose não está disponível." \
        "Instale uma versão do Docker com Compose e execute novamente."
fi

printf '%s\n' "[LeadPulse] Iniciando PostgreSQL..."
if ! docker compose up -d; then
    fail "[LeadPulse] Não foi possível iniciar o PostgreSQL com Docker Compose."
fi

printf '%s\n' "[LeadPulse] Aguardando banco de dados..."
health_deadline=$((SECONDS + 60))
postgres_ready=false
while (( SECONDS < health_deadline )); do
    container_id="$(docker compose ps -q postgres 2>/dev/null || true)"
    if [[ -n "$container_id" ]]; then
        health_status="$(docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' "$container_id" 2>/dev/null || true)"
        if [[ "$health_status" == "healthy" ]]; then
            postgres_ready=true
            break
        fi
    fi
    sleep 2
done

if [[ "$postgres_ready" != true ]]; then
    fail \
        "[LeadPulse] PostgreSQL não ficou disponível dentro do tempo esperado." \
        "Verifique:" \
        "docker compose ps" \
        "docker compose logs postgres"
fi
printf '%s\n' "[LeadPulse] PostgreSQL disponível."

printf '%s\n' "[LeadPulse] Verificando camada analítica..."
if "$VENV_PYTHON" - <<'PYTHON'
import sys

import psycopg

from leadpulse.config import PostgresConfig

MARTS = (
    "analytics.mart_acquisition_performance",
    "analytics.mart_seller_activation",
    "analytics.mart_marketing_efficiency",
    "analytics.mart_downstream_performance",
)

try:
    config = PostgresConfig.from_env()
    with psycopg.connect(
        dbname=config.dbname,
        user=config.user,
        password=config.password,
        host=config.host,
        port=config.port,
        connect_timeout=5,
        options="-c default_transaction_read_only=on",
    ) as connection:
        with connection.cursor() as cursor:
            missing = []
            for mart in MARTS:
                cursor.execute("SELECT to_regclass(%s)", (mart,))
                if cursor.fetchone()[0] is None:
                    missing.append(mart)
except Exception:
    raise SystemExit(2)

raise SystemExit(3 if missing else 0)
PYTHON
then
    analytics_status=0
else
    analytics_status=$?
fi

if [[ $analytics_status -eq 3 ]]; then
    show_analytics_instructions
    exit 0
elif [[ $analytics_status -ne 0 ]]; then
    fail \
        "[LeadPulse] Não foi possível verificar a camada analítica." \
        "Confirme a configuração do banco em .env e tente novamente."
fi

printf '%s\n' "[LeadPulse] Validando Streamlit..."
if ! "$VENV_PYTHON" -m streamlit --version >/dev/null 2>&1; then
    fail \
        "[LeadPulse] Streamlit não está disponível no ambiente virtual." \
        "Tente reinstalar as dependências:" \
        'python -m pip install -e ".[dev,data,dashboard]"'
fi

if [[ ! -f "$ENTRYPOINT" ]]; then
    fail "[LeadPulse] O entrypoint do dashboard não foi encontrado."
fi

printf '%s\n' \
    "[LeadPulse] Iniciando dashboard..." \
    "[LeadPulse] URL: http://localhost:8501"
exec "$VENV_PYTHON" -m streamlit run "$ENTRYPOINT" --server.port 8501
