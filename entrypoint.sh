#!/bin/bash
set -e

# entrypoint.sh - exporta variables de .env para cron y arranca cron
# Si CRON_DISABLED=true entonces ejecuta el comando una sola vez en foreground (útil para debug)

ENV_FILE="/app/.env"
ENV_CRON_FILE="/etc/envcron"
LOG_FILE="/var/log/mec_cupos_checker.log"
# Ejecutar cada 30 minutos
CRON_JOB="*/30 * * * * . ${ENV_CRON_FILE} && cd /app && python main.py >> ${LOG_FILE} 2>&1"

# Función para crear log file y directorios
create_log_file() {
  mkdir -p /var/log
  touch ${LOG_FILE}
}

# Función para exportar variables para cron
setup_env_for_cron() {
  echo "# Variables exportadas para cron (generadas por entrypoint.sh)" > ${ENV_CRON_FILE}

  if [ -f "${ENV_FILE}" ]; then
    # filtrar lineas válidas y no exportar comentarios
    grep -v '^#' ${ENV_FILE} | grep -E '=+' | sed "s/^[ \t]*//" | while IFS= read -r line; do
      key=$(printf "%s" "$line" | sed -E "s/=.*//")
      value=$(printf "%s" "$line" | sed -E "s/^[^=]*=//")
      # Escape backslashes and double quotes, luego escribir con double quotes
      value_escaped=$(printf "%s" "$value" | sed -e 's/\\/\\\\/g' -e 's/"/\\"/g')
      echo "export ${key}=\"${value_escaped}\"" >> ${ENV_CRON_FILE}
    done
  else
    # No hay .env copiado en la imagen; volcamos variables de entorno actuales
    # Excluir variables típicas del sistema para evitar ruido
    env | while IFS='=' read -r key value; do
      case "$key" in
        PWD|OLDPWD|HOME|SHLVL|PATH|TERM|HOSTNAME|LANG|LANGUAGE|LC_*)
          continue
          ;;
      esac
      # escape backslashes and double quotes
      value_escaped=$(printf "%s" "$value" | sed -e 's/\\/\\\\/g' -e 's/"/\\"/g')
      echo "export ${key}=\"${value_escaped}\"" >> ${ENV_CRON_FILE}
    done
  fi
  chmod 644 ${ENV_CRON_FILE}
}

# Función para ejecutar el proyecto una vez
run_once() {
  echo "Ejecutando el proyecto una vez: python main.py"
  . ${ENV_CRON_FILE} || true
  cd /app
  python main.py
}

# Función para configurar el cron job
setup_cron() {
  CRON_TMP_FILE="/tmp/mec_cron"
  echo "${CRON_JOB}" > ${CRON_TMP_FILE}
  crontab ${CRON_TMP_FILE}
  echo "Crontab installed at $(date)" >> /app/cron_setup.log
}

# Función para iniciar el daemon de cron
start_cron() {
  echo "Starting cron at $(date)" >> /app/cron_start.log
  if command -v cron >/dev/null 2>&1; then
    echo "Starting cron (cron)..."
    cron -f
  elif command -v crond >/dev/null 2>&1; then
    echo "Starting crond (foreground)..."
    crond -f
  else
    echo "No cron daemon found"
    exit 1
  fi
}

# Llamadas principales
create_log_file
setup_env_for_cron

# Ejecutar una vez el proyecto
run_once

# Si CRON_DISABLED=true ejecuta solo una vez y sale
if [ "${CRON_DISABLED}" = "true" ] || [ "${CRON_DISABLED}" = "1" ]; then
  exit $?
fi

# Configurar e iniciar cron
setup_cron
start_cron
