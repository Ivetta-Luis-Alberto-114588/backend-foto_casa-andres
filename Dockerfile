FROM python:3.11-slim

WORKDIR /app

# Instalar dependencias del sistema necesarias para Chromium/Playwright
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates curl gnupg wget apt-transport-https \
    libnss3 libatk1.0-0 libatk-bridge2.0-0 libcups2 libxkbcommon0 libxcomposite1 libxdamage1 \
    libxrandr2 libgbm1 libasound2 libpangocairo-1.0-0 libpango-1.0-0 libxcb1 libx11-xcb1 \
    libx11-6 libxext6 libxss1 libxrender1 libstdc++6 fonts-liberation fonts-noto-color-emoji \
    fonts-dejavu-core libgtk-3-0 libgdk-pixbuf-xlib-2.0-0 libexpat1 libdbus-1-3 \
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements e instalar dependencias Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Instalar Chromium para Playwright
RUN python -m playwright install chromium
RUN python -m playwright install-deps chromium || true

# Copiar código de aplicación
COPY . .

# Variables de entorno por defecto (se sobreescriben en Coolify)
ENV PORT=3000 \
    FLASK_ENV=production \
    PYTHONUNBUFFERED=1

EXPOSE 3000

# Health check para Coolify
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD curl -f http://localhost:3000/api/status || exit 1

CMD ["python", "main.py"]
