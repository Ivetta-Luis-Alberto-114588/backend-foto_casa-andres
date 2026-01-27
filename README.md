# Backend Python - Browser-use LOCAL

Backend con browser-use ejecutándose 100% localmente en tu servidor.

## Instalación

### 1. Crear entorno virtual (RECOMENDADO)

**Windows:**
```bash
cd backend
python -m venv venv
venv\Scripts\activate
```

**Linux/Mac:**
```bash
cd backend
python3 -m venv venv
source venv/bin/activate
```

Verás `(venv)` en tu terminal cuando esté activado.

### 2. Instalar dependencias

Con el entorno virtual activado:

```bash
pip install -r requirements.txt
```

### 3. Instalar navegadores

```bash
playwright install chromium
```

### 4. Configurar variables de entorno

```bash
cp .env.example .env
```

Edita `.env` con tus credenciales:

```env
PORT=3000

# LLM (elige una opción)
OPENAI_API_KEY=sk-tu-key-aqui
LLM_MODEL=gpt-4o-mini

# Email (Gmail)
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USER=tu_email@gmail.com
EMAIL_PASS=tu_contraseña_de_aplicacion
```

### 5. Ejecutar

Con el entorno virtual activado:

```bash
python main.py
```

El servidor estará en http://localhost:3000

## Opciones de LLM

### Opción A: OpenAI (Recomendado)

Más preciso y confiable.

1. Obtén API key: https://platform.openai.com/api-keys
2. Agrega en `.env`: `OPENAI_API_KEY=sk-tu-key`
3. Costo: ~$0.15 por 1 millón de tokens (muy barato)

### Opción B: Ollama (100% Gratis y Local)

Completamente gratuito, corre en tu máquina, 100% privado.

1. Descarga Ollama: https://ollama.ai/
2. Instala un modelo:
   ```bash
   ollama run llama2
   ```
3. Modifica `main.py` (líneas 53-58):
   ```python
   from langchain_community.llms import Ollama

   llm = Ollama(
       model="llama2",
       base_url="http://localhost:11434"
   )
   ```
4. Instala dependencia:
   ```bash
   pip install langchain-community
   ```

## Cómo funciona

Browser-use ejecuta IA **localmente** en tu servidor:

1. **Navegador local**: Playwright abre Chromium headless
2. **IA entiende la página**: Usa LLM para "ver" y entender el contenido
3. **Extrae información**: El agente navega inteligentemente y extrae datos
4. **Todo privado**: No envía datos a servicios externos (excepto LLM si usas OpenAI)

## API Endpoints

### POST /api/scrape

Realiza scraping con IA.

**Request:**
```json
{
  "url": "https://example.com",
  "searchTerm": "término a buscar"
}
```

**Response:**
```json
{
  "success": true,
  "content": "Contenido extraído...",
  "description": "Descripción"
}
```

### POST /api/email

Envía email.

**Request:**
```json
{
  "to": "destino@example.com",
  "subject": "Asunto",
  "body": "Texto",
  "html": "<html>...</html>"
}
```

**Response:**
```json
{
  "success": true
}
```

### GET /api/status

Estado del sistema.

```json
{
  "server": "ok",
  "browserUse": {
    "installed": true,
    "llm_configured": true,
    "mode": "local-ai"
  },
  "email": {
    "configured": true,
    "host": "smtp.gmail.com"
  }
}
```

## Configurar Gmail

Para enviar emails con Gmail necesitas una **contraseña de aplicación**:

1. Habilita verificación en 2 pasos: https://myaccount.google.com/security
2. Genera contraseña de aplicación: https://myaccount.google.com/apppasswords
3. Usa esa contraseña (16 caracteres) en `.env`, NO tu contraseña normal

## Docker

```bash
docker build -t backend-python .
docker run -p 3000:3000 --env-file .env backend-python
```

## Desactivar entorno virtual

Cuando termines de trabajar:

```bash
deactivate
```

## Troubleshooting

### "browser-use no instalado"

Activa el entorno virtual y ejecuta:
```bash
pip install browser-use langchain-openai playwright
playwright install chromium
```

### "No module named 'browser_use'"

El entorno virtual no está activado. Actívalo:
- Windows: `venv\Scripts\activate`
- Linux/Mac: `source venv/bin/activate`

### Error de Playwright

```bash
playwright install-deps chromium
```

### "Invalid login" en email

Estás usando tu contraseña normal. Debes usar una contraseña de aplicación de Gmail.

## Ventajas del entorno virtual

✅ Aisla dependencias del proyecto
✅ No contamina Python global del sistema
✅ Fácil de eliminar (solo borras carpeta `venv/`)
✅ Diferentes proyectos pueden tener diferentes versiones
✅ Replicable en otros servidores

## Recursos

- **Browser-use**: https://github.com/browser-use/browser-use
- **Playwright**: https://playwright.dev/python/
- **OpenAI API**: https://platform.openai.com/api-keys
- **Ollama**: https://ollama.ai/
- **Gmail App Passwords**: https://myaccount.google.com/apppasswords
