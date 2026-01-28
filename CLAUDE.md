# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Backend de scraping web inteligente que combina Playwright en modo stealth con análisis de IA (OpenAI) para extraer información de sitios web y enviarla por email.

**Stack tecnológico:**
- Python 3.11+ con Flask
- Playwright (navegación web con anti-detección)
- OpenAI GPT (análisis de contenido)
- SMTP/Nodemailer (envío de emails)
- Docker para deployment

**Características clave:**
- Modo ULTRA-STEALTH: evita detección de bots mediante técnicas anti-fingerprinting
- Análisis inteligente de contenido usando LLM
- Soporte para múltiples navegadores (Chromium/Brave)
- Detección automática de CAPTCHA
- Envío automatizado de emails con resultados

## Development Commands

### Entorno virtual (RECOMENDADO)

**Configuración inicial:**
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/Mac
python3 -m venv venv
source venv/bin/activate
```

**Instalar dependencias:**
```bash
pip install -r requirements.txt
playwright install chromium          # Navegador para scraping
playwright install-deps chromium     # Dependencias del sistema (Linux)
```

**Configurar variables de entorno:**
```bash
cp .env.example .env
# Editar .env con tus credenciales (OPENAI_API_KEY, EMAIL_*, etc.)
```

### Ejecutar servidor

```bash
# Desarrollo (con auto-reload)
python main.py

# Servidor estará en http://localhost:3000
```

### Docker

```bash
docker build -t backend-python .
docker run -p 3000:3000 --env-file .env backend-python
```

### Desactivar entorno virtual

```bash
deactivate
```

## Architecture

### Estructura del proyecto

```
backend/
├── main.py                 # Flask app + endpoints API
├── scraper_stealth.py      # Lógica de scraping con Playwright
├── requirements.txt        # Dependencias Python
├── Dockerfile             # Imagen Docker
├── .env                   # Variables de entorno (no versionado)
└── .env.example          # Template de configuración
```

### Flujo de ejecución

1. **Request a /api/scrape**: Frontend envía URL y término de búsqueda
2. **scraper_stealth.py**:
   - Inicia Playwright con configuración anti-detección
   - Navega a la URL usando Chromium o Brave
   - Aplica scripts para ocultar webdriver y simular usuario real
   - Cierra popups automáticamente
   - Extrae contenido HTML
3. **Análisis con OpenAI**:
   - Envía HTML + prompt a GPT-4o-mini
   - LLM extrae información estructurada (títulos, precios, descripciones)
   - Genera resumen y tabla HTML
4. **Response**: Retorna JSON con contenido extraído
5. **Email opcional**: /api/email envía resultados por SMTP

### Componentes principales

**main.py:**
- `scrape_with_agent_OLD_DEPRECATED()`: Implementación original con browser-use (deprecada)
- `simulate_scrape()`: Mock cuando dependencias no están instaladas
- `send_email()`: Cliente SMTP para Gmail
- Endpoints: `/api/scrape`, `/api/email`, `/api/status`, `/health`

**scraper_stealth.py:**
- `scrape_with_stealth()`: Función principal de scraping
- `_search_fotocasa()`: Búsqueda específica para Fotocasa (inmobiliaria)
- `_close_fotocasa_popups()`: Cierre automático de modales
- `_build_html_table()`: Genera tabla HTML para emails
- Scripts anti-detección: oculta `navigator.webdriver`, simula plugins de Chrome, falsifica hardware fingerprint

### Técnicas anti-detección implementadas

**Configuración de Playwright:**
- `headless=False`: navegador visible (más difícil de detectar)
- `--disable-blink-features=AutomationControlled`: oculta señal de automatización
- User-agent real: simula Chrome/Windows auténtico
- Viewport 1920x1080 con device_scale_factor=1

**JavaScript injection:**
- `navigator.webdriver = false`
- `window.chrome.runtime` simulado
- Plugins fake (PDF viewer, Native Client)
- WebGL vendor spoofing (Intel UHD Graphics)
- Battery API con valores realistas
- Media devices enumerate simulado

**Comportamiento humano:**
- Delays aleatorios entre acciones (0.3-1.5s)
- Scroll progresivo con paradas
- Movimientos de mouse naturales
- Esperas antes de clicks

### Endpoints API

**POST /api/scrape**
```json
Request:
{
  "url": "https://www.fotocasa.es/",
  "searchTerm": "Madrid",
  "priceMax": 1500,
  "browser": "chromium" | "brave"
}

Response:
{
  "success": true,
  "content": "HTML table with results",
  "summary": "Brief description",
  "totalResults": 25,
  "items": [...]
}
```

**POST /api/email**
```json
Request:
{
  "to": "user@example.com",
  "subject": "Resultados búsqueda",
  "body": "Plain text",
  "html": "<html>..."
}

Response:
{
  "success": true
}
```

**GET /api/status**
Retorna estado de configuración (Playwright instalado, OpenAI configurado, SMTP configurado).

### Variables de entorno requeridas

**Essentials:**
- `PORT`: Puerto del servidor (default: 3000)
- `OPENAI_API_KEY`: API key de OpenAI (obtener en platform.openai.com)
- `LLM_MODEL`: Modelo a usar (default: gpt-4o-mini)

**Email (Gmail):**
- `EMAIL_HOST`: smtp.gmail.com
- `EMAIL_PORT`: 587
- `EMAIL_USER`: tu_email@gmail.com
- `EMAIL_PASS`: Contraseña de aplicación (NO contraseña normal)

**Opcionales:**
- `BRAVE_PATH`: Ruta al ejecutable de Brave (Windows: `C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe`)
- `HEADLESS`: true/false (para Docker, local siempre False)

### Configuración de Gmail

Para usar Gmail con SMTP:
1. Habilitar verificación en 2 pasos: https://myaccount.google.com/security
2. Generar contraseña de aplicación: https://myaccount.google.com/apppasswords
3. Usar esa contraseña de 16 caracteres en `EMAIL_PASS`

### Opciones de LLM

**Opción A: OpenAI (recomendado)**
- Más preciso y confiable
- Costo: ~$0.15 por 1M tokens
- Configurar `OPENAI_API_KEY` en `.env`

**Opción B: Ollama (local, gratuito)**
- 100% privado, corre en tu máquina
- Instalar Ollama: https://ollama.ai/
- Descargar modelo: `ollama run llama2`
- Modificar `main.py` para usar `langchain_community.llms.Ollama`
- Instalar: `pip install langchain-community`

## Important Notes

- **Entorno virtual obligatorio**: Siempre activar `venv` antes de ejecutar comandos pip o python
- **Playwright browsers**: Ejecutar `playwright install chromium` después de instalar requirements.txt
- **No versionar .env**: Contiene API keys sensibles
- **Modo stealth**: `headless=False` es intencional para evitar detección
- **CAPTCHA**: El scraper detecta pero NO resuelve CAPTCHAs automáticamente
- **Rate limiting**: Implementar delays entre requests para evitar bloqueos
- **Brave opcional**: Funciona sin Brave, usando Chromium de Playwright
- **Docker**: La imagen incluye todas las dependencias de Chromium/Playwright
- **Logs verbosos**: `main.py` imprime estado detallado al iniciar

## Troubleshooting

**"browser-use no instalado":**
```bash
pip install browser-use langchain-openai playwright
playwright install chromium
```

**"No module named 'browser_use'":**
Entorno virtual no activado. Ejecutar:
- Windows: `venv\Scripts\activate`
- Linux/Mac: `source venv/bin/activate`

**Error de Playwright en Linux:**
```bash
playwright install-deps chromium
```

**"Invalid login" en email:**
Estás usando tu contraseña normal. Debes generar una contraseña de aplicación en Google.

**CAPTCHA detected:**
Normal en sitios como Idealista/Fotocasa. Reducir frecuencia de requests o usar proxies rotantes.
