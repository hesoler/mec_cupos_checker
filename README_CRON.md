# Cron dentro del contenedor

Este proyecto ahora incluye un `entrypoint.sh` que configura un cron job que ejecuta `python main.py` cada 30 minutos
(expresión `*/30 * * * *`).

Cómo funciona:

- `Dockerfile` instala `cron` y copia `entrypoint.sh`.
- `entrypoint.sh` genera `/etc/envcron` con las variables de entorno (leídas desde `/app/.env` si existe, o desde el
  entorno del contenedor) y registra un `crontab` que ejecuta `python main.py` cada 30 minutos, redirigiendo logs a
  `/var/log/mec_cupos_checker.log`.
- El contenedor arranca `cron` en primer plano para que Docker lo mantenga vivo.

Instrucciones rápidas:

1) Construir la imagen:

```bash
docker compose build
```

2) Levantar el servicio (usando el `.env` definido en la raíz):

```bash
docker compose up -d
```

3) Ver logs:

```bash
# Logs del contenedor
docker compose logs -f app
# O ver el fichero montado en el host
tail -f mec_cupos_checker.log
```

Debugging / ejecutar manualmente:

- Para ejecutar una sola vez sin cron, definir en el `.env`:

```
CRON_DISABLED=true
```

y luego `docker compose up --build` para que el entrypoint ejecute `python main.py` una vez y salga.

Notas:

- Asegúrate de que el archivo `.env` contiene las variables necesarias (MEC_USER, MEC_PASSWORD, ID_RECURSOS o ID_ETAPA,
  TELEGRAM_*).
- Si necesitas cambiar la frecuencia, modifica la variable `CRON_JOB` dentro de `entrypoint.sh`.
- En entornos de producción también puedes programar el host cron/systemd timer en lugar de usar cron dentro del
  contenedor.
