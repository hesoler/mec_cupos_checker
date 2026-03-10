FROM python:3.12-slim

RUN apt-get update && apt-get install -y \
    ca-certificates \
    wget \
    fonts-liberation \
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libcups2 \
    libdbus-1-3 \
    libdrm2 \
    libgbm1 \
    libgtk-3-0 \
    libnspr4 \
    libnss3 \
    libx11-xcb1 \
    libxcomposite1 \
    libxdamage1 \
    libxrandr2 \
    xdg-utils \
    libu2f-udev \
    libvulkan1 \
    cron \
    && update-ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY config/mec_chain.pem /app/mec_chain.pem
COPY src/*.py /app/
COPY requirements.txt .
RUN sed -i 's/\r//' requirements.txt

RUN pip install --no-cache-dir -r requirements.txt \
    && playwright install chromium

COPY scripts /app

# Copiar entrypoint para manejar export de env y cron
COPY scripts/entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

RUN sed -i 's/\r//' /usr/local/bin/entrypoint.sh
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
CMD ["/bin/bash"]
EXPOSE 8000
