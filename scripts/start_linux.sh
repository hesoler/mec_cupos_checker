#!/bin/bash
# MEC Cupos Checker - Script de arranque para Linux

# Navegar al directorio raíz del proyecto
PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_ROOT"

echo "=== MEC Cupos Checker ==="

# Verificar que Docker esté instalado
if ! command -v docker &> /dev/null; then
    echo "❌ Docker no está instalado. Instalalo desde https://docs.docker.com/get-docker/"
    exit 1
fi

# Iniciar el daemon de Docker si no está corriendo
if ! docker info &> /dev/null; then
    echo "🔄 Iniciando servicio Docker..."
    sudo service docker start > /dev/null 2>&1
    sleep 3

    if ! docker info &> /dev/null; then
        echo "❌ No se pudo iniciar Docker. Intentá manualmente: sudo service docker start"
        exit 1
    fi

    echo "✅ Docker iniciado correctamente."
fi

# Verificar que exista el .env
if [ ! -f ".env" ]; then
    echo "❌ No se encontró el archivo .env. Crealo con las variables requeridas."
    echo "   Consultá el README.md para ver qué variables son necesarias."
    exit 1
fi

# Crear archivos JSON si no existen o están vacíos
for file in data/available.json data/storage_state.json; do
    if [ ! -f "$file" ] || [ ! -s "$file" ]; then
        echo "📄 Creando $file..."
        echo '{}' > "$file"
    fi
done

# Corregir line endings del entrypoint.sh
if [ -f "scripts/entrypoint.sh" ]; then
    sed -i 's/\r//' scripts/entrypoint.sh
fi

# Detener contenedor previo si existe
CONTAINER_NAME="mec_checker"
if docker ps -a --format '{{.Names}}' | grep -q "^$CONTAINER_NAME$"; then
    echo "🛑 Deteniendo contenedor anterior..."
    IMAGE_ID=$(docker inspect $CONTAINER_NAME --format '{{.Image}}' 2>/dev/null)
    docker compose down -v
    # Eliminar la imagen exacta del contenedor
    if [ -n "$IMAGE_ID" ]; then
        echo "🗑️ Eliminando imagen específica: $IMAGE_ID"
        docker rmi "$IMAGE_ID"
    fi
fi

# Levantar el contenedor
echo "🚀 Levantando contenedor..."
docker compose up -d --build

if [ $? -eq 0 ]; then
    echo "✅ Contenedor iniciado correctamente."
    echo "📋 Para ver los logs: docker compose logs -f app"
else
    echo "❌ Error al levantar el contenedor. Revisá los logs con: docker compose logs app"
    exit 1
fi

timeout 60 docker container logs -f $CONTAINER_NAME
docker exec $CONTAINER_NAME tail -f /var/log/mec_cupos_checker.log
