#!/bin/sh

# Habilitar modo estricto para errores
set -e

# Variables de entorno
# ENV=${ENV:-local}
echo "Ambiente: $ENV"
echo "Postgres Host: $POSTGRES_HOST"
echo "Postgres Port: $POSTGRES_PORT"
echo "Postgres User: $POSTGRES_USER"

# Función para esperar a que PostgreSQL esté disponible
wait_for_postgres() {
    echo "Esperando a que PostgreSQL esté disponible..."
    until pg_isready -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER"; do
        echo "PostgreSQL no está listo. Esperando..."
        sleep 1
    done
    echo "PostgreSQL está listo."
}

# Aplicar migraciones a la base de datos
run_migrations() {
    echo "Inicializando migracions en ambiente: $ENV"
    if [ "$ENV" != "local" ]; then
        echo "Ejecutando migraciones de base de datos..."
        alembic upgrade head
        echo "Migraciones completadas."
    else
        echo "Entorno local detectado. Omitiendo migraciones."
    fi
}

# Iniciar el servidor FastAPI con Uvicorn
start_server() {
    echo "Iniciando FastAPI..."
    exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
}

# Ejecutar los pasos en orden
wait_for_postgres
run_migrations
start_server

