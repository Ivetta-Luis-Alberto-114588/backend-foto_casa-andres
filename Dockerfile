FROM mcr.microsoft.com/playwright/python:1.49.0

WORKDIR /app

# Copiar requirements y instalar dependencias Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código
COPY . .

# Variables de entorno por defecto (puedes sobreescribir en Coolify)
ENV PORT=3000 HEADLESS=true BROWSER=chromium

EXPOSE 3000

CMD ["python", "main.py"]
