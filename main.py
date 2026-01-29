"""
Backend Python con Playwright STEALTH + OpenAI

Backend unificado que maneja:
- Scraping web con Playwright en modo ULTRA-STEALTH
- Anti-detección avanzada (oculta webdriver, simula navegador real)
- Análisis de contenido con OpenAI
- Envío de emails
- API REST para frontend Angular

Todo corre 100% en tu servidor local, máxima privacidad.
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import asyncio
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from dotenv import load_dotenv
import pathlib

# Cargar variables de entorno
load_dotenv()

app = Flask(__name__)
CORS(app)

# Flag para verificar si browser-use está disponible
BROWSER_USE_AVAILABLE = False
LLM_CONFIGURED = False

try:
    from browser_use import Agent, Browser, BrowserConfig
    from langchain_openai import ChatOpenAI
    from scraper_stealth import scrape_with_stealth
    BROWSER_USE_AVAILABLE = True

    # Verificar si hay LLM configurado
    if os.getenv("OPENAI_API_KEY"):
        LLM_CONFIGURED = True
        print("✓ Playwright STEALTH + OpenAI configurado")
    else:
        print("✓ Playwright instalado (falta configurar LLM)")

except ImportError as e:
    print(f"⚠️  Playwright/OpenAI no instalado: {e}")
    print("   Instala: pip install browser-use langchain-openai playwright")


async def scrape_with_agent_OLD_DEPRECATED(url: str, search_term: str) -> dict:
    """
    Realiza scraping usando browser-use con IA (LOCAL) + modo STEALTH AVANZADO anti-detección
    """
    try:
        # Configurar LLM (OpenAI)
        llm = ChatOpenAI(
            model=os.getenv("LLM_MODEL", "gpt-4o-mini"),
            api_key=os.getenv("OPENAI_API_KEY"),
            temperature=0.1  # Más determinista para scraping
        )

        # Importar playwright para configuración avanzada
        from playwright.async_api import async_playwright

        # Iniciar playwright manualmente para control total
        playwright = await async_playwright().start()

        # Configuración STEALTH AVANZADA
        browser_instance = await playwright.chromium.launch(
            headless=False,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-web-security',
                '--disable-features=IsolateOrigins,site-per-process',
                '--window-size=1920,1080',
                '--start-maximized',
                '--disable-infobars',
                '--disable-notifications',
                '--disable-popup-blocking',
            ]
        )

        # Crear contexto con configuración de navegador real
        context = await browser_instance.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            locale='es-ES',
            timezone_id='Europe/Madrid',
            geolocation={'latitude': 40.4168, 'longitude': -3.7038},  # Madrid
            permissions=['geolocation'],
            color_scheme='light',
            device_scale_factor=1,
            is_mobile=False,
            has_touch=False,
        )

        # Scripts anti-detección AVANZADOS
        await context.add_init_script("""
            // Ocultar webdriver
            Object.defineProperty(navigator, 'webdriver', {
                get: () => false
            });

            // Chrome runtime
            window.chrome = {
                runtime: {},
                loadTimes: function() {},
                csi: function() {},
                app: {}
            };

            // Plugins reales
            Object.defineProperty(navigator, 'plugins', {
                get: () => [
                    {
                        0: {type: "application/x-google-chrome-pdf", suffixes: "pdf", description: "Portable Document Format"},
                        description: "Portable Document Format",
                        filename: "internal-pdf-viewer",
                        length: 1,
                        name: "Chrome PDF Plugin"
                    },
                    {
                        0: {type: "application/pdf", suffixes: "pdf", description: "Portable Document Format"},
                        description: "Portable Document Format",
                        filename: "mhjfbmdgcfjbbpaeojofohoefgiehjai",
                        length: 1,
                        name: "Chrome PDF Viewer"
                    },
                    {
                        0: {type: "application/x-nacl", suffixes: "", description: "Native Client Executable"},
                        description: "Native Client Executable",
                        filename: "internal-nacl-plugin",
                        length: 2,
                        name: "Native Client"
                    }
                ]
            });

            // Languages
            Object.defineProperty(navigator, 'languages', {
                get: () => ['es-ES', 'es', 'en-US', 'en']
            });

            // Platform
            Object.defineProperty(navigator, 'platform', {
                get: () => 'Win32'
            });

            // Hardware concurrency
            Object.defineProperty(navigator, 'hardwareConcurrency', {
                get: () => 8
            });

            // Device memory
            Object.defineProperty(navigator, 'deviceMemory', {
                get: () => 8
            });

            // Permissions
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                    Promise.resolve({ state: Notification.permission }) :
                    originalQuery(parameters)
            );

            // WebGL vendor
            const getParameter = WebGLRenderingContext.prototype.getParameter;
            WebGLRenderingContext.prototype.getParameter = function(parameter) {
                if (parameter === 37445) {
                    return 'Intel Inc.';
                }
                if (parameter === 37446) {
                    return 'Intel(R) UHD Graphics 620';
                }
                return getParameter.apply(this, [parameter]);
            };

            // Battery API (hacer que parezca que NO está conectado)
            Object.defineProperty(navigator, 'getBattery', {
                get: () => () => Promise.resolve({
                    charging: false,
                    chargingTime: Infinity,
                    dischargingTime: 5400,
                    level: 0.75
                })
            });

            // Connection
            Object.defineProperty(navigator, 'connection', {
                get: () => ({
                    effectiveType: '4g',
                    rtt: 50,
                    downlink: 10,
                    saveData: false
                })
            });

            // Media devices
            Object.defineProperty(navigator.mediaDevices, 'enumerateDevices', {
                value: () => Promise.resolve([
                    {deviceId: "default", kind: "audioinput", label: "", groupId: ""},
                    {deviceId: "default", kind: "audiooutput", label: "", groupId: ""},
                    {deviceId: "default", kind: "videoinput", label: "", groupId: ""}
                ])
            });
        """)

        # Agregar cookies y localStorage para simular sesión previa
        await context.add_cookies([
            {
                'name': 'userUUID',
                'value': 'simulated-user-' + str(os.urandom(8).hex()),
                'domain': '.idealista.com',
                'path': '/',
            }
        ])

        # Usar el contexto con browser-use
        # Nota: browser-use usa su propio Browser, así que vamos a pasar el context directamente
        browser_config = BrowserConfig(
            headless=False,
            disable_security=False,
            extra_chromium_args=['--disable-blink-features=AutomationControlled']
        )

        browser = Browser(config=browser_config)

        # Tarea con instrucciones para actuar como humano + manejo de CAPTCHA
        task = f"""
        🚨 IMPORTANT: Act like a REAL HUMAN USER. Move SLOWLY.

        Website: {url}
        Search for: "{search_term}"

        Instructions:
        1. Navigate to the URL
        2. WAIT 3-5 seconds after page loads (simulate reading)
        3. If you see property listings, extract:
           - Property titles
           - Prices
           - Locations
           - Number of bedrooms/bathrooms
           - Brief descriptions
        4. Scroll down if needed to see more results
        5. Summarize the findings clearly

        ⚠️ CAPTCHA HANDLING:
        - If you see a CAPTCHA, verification page, or "too many requests":
          * Report: "❌ CAPTCHA/VERIFICATION DETECTED"
          * Describe what you see on the page
          * Do NOT try to solve it
          * Return partial results if possible

        Focus on: {search_term}
        """

        agent = Agent(
            task=task,
            llm=llm,
            browser=browser,
        )

        print(f"🤖 Ejecutando agente LOCAL STEALTH")
        print(f"🔍 URL: {url}")
        print(f"🔍 Término: {search_term}")
        print("🥷 Anti-detección: headless=False, delays automáticos, user-agent real")

        # Ejecutar agente
        history = await agent.run()

        # Extraer contenido del historial
        content_parts = []
        for message in history:
            if hasattr(message, 'content') and message.content:
                content_parts.append(str(message.content))

        final_content = "\n".join(content_parts).strip()

        if not final_content:
            final_content = "El agente no pudo extraer contenido específico."

        print(f"✓ Scraping completado: {len(final_content)} caracteres")

        return {
            "success": True,
            "content": final_content,
            "description": f"Resultados de búsqueda para '{search_term}' en {url}"
        }

    except Exception as e:
        print(f"❌ Error en scraping: {e}")
        import traceback
        traceback.print_exc()
        return {
            "success": False,
            "content": "",
            "description": "",
            "error": str(e)
        }


def simulate_scrape(url: str, search_term: str) -> dict:
    """
    Simulación cuando browser-use no está disponible
    """
    if not BROWSER_USE_AVAILABLE:
        status_msg = """
Browser-use no está instalado.

Para instalar:
1. pip install browser-use langchain-openai playwright
2. playwright install chromium
3. Configura OPENAI_API_KEY en .env
4. Reinicia el servidor
        """
    elif not LLM_CONFIGURED:
        status_msg = """
Browser-use está instalado pero falta configurar el LLM.

Opciones:

A) OpenAI (recomendado):
   1. Obtén API key: https://platform.openai.com/api-keys
   2. Agrega en .env: OPENAI_API_KEY=sk-tu-key
   3. Reinicia el servidor

B) Ollama LOCAL (gratuito):
   1. Instala Ollama: https://ollama.ai/
   2. Descarga modelo: ollama run llama2
   3. Modifica main.py para usar Ollama
   4. Reinicia el servidor
        """
    else:
        status_msg = "Error de configuración desconocido."

    return {
        "success": True,
        "content": f"""
MODO SIMULACIÓN

Búsqueda de "{search_term}" en {url}

{status_msg}

Browser-use ejecuta IA localmente en tu servidor para:
- Navegar páginas web automáticamente
- Entender contenido usando visión + LLM
- Extraer información relevante
- Todo privado, en tu máquina
        """.strip(),
        "description": f"Simulación: '{search_term}' en {url}"
    }


def send_email(to: str, subject: str, body: str, html: str = None, attachments: list = None) -> bool:
    """
    Envía email usando SMTP con soporte para adjuntos
    attachments: lista de rutas a archivos para adjuntar
    """
    try:
        msg = MIMEMultipart('mixed')
        msg['From'] = os.getenv('EMAIL_USER')
        msg['To'] = to
        msg['Subject'] = subject

        # Crear parte de contenido (texto + html)
        msg_alternative = MIMEMultipart('alternative')
        msg.attach(msg_alternative)

        # Adjuntar texto plano
        msg_alternative.attach(MIMEText(body, 'plain'))

        # Adjuntar HTML si está disponible
        if html:
            msg_alternative.attach(MIMEText(html, 'html'))

        # Adjuntar archivos si existen
        if attachments:
            for file_path in attachments:
                try:
                    path = pathlib.Path(file_path)
                    if path.exists():
                        # Leer archivo
                        with open(path, 'rb') as attachment:
                            part = MIMEBase('application', 'octet-stream')
                            part.set_payload(attachment.read())
                            encoders.encode_base64(part)
                            part.add_header('Content-Disposition', f'attachment; filename= {path.name}')
                            msg.attach(part)
                        print(f"   ✓ Adjunto agregado: {path.name} ({path.stat().st_size} bytes)")
                    else:
                        print(f"   ⚠️  Archivo no encontrado: {file_path}")
                except Exception as e:
                    print(f"   ❌ Error adjuntando {file_path}: {e}")

        # Conectar y enviar
        with smtplib.SMTP(os.getenv('EMAIL_HOST'), int(os.getenv('EMAIL_PORT', 587))) as server:
            server.starttls()
            server.login(os.getenv('EMAIL_USER'), os.getenv('EMAIL_PASS'))
            server.send_message(msg)

        print(f"✓ Email enviado a {to}")
        return True

    except Exception as e:
        print(f"❌ Error enviando email: {e}")
        return False


# ============================================
# ENDPOINTS
# ============================================

@app.route('/', methods=['GET'])
def index():
    """Ruta raíz - información del backend"""
    return jsonify({
        "name": "Backend Web Scraper API (STEALTH MODE)",
        "version": "1.0.1",
        "status": "running",
        "features": {
            "stealth_mode": "Anti-detection enabled",
            "browser_visible": "headless=False",
            "human_simulation": "Random delays + natural behavior"
        },
        "endpoints": {
            "health": "/health",
            "status": "/api/status",
            "scrape": "/api/scrape (POST)",
            "email": "/api/email (POST)"
        },
        "message": "Backend funcionando con modo anti-detección. Ver /api/status para detalles."
    })


@app.route('/health', methods=['GET'])
def health():
    """Health check"""
    from datetime import datetime
    return jsonify({
        "status": "ok",
        "timestamp": datetime.now().isoformat()
    })


@app.route('/api/scrape', methods=['POST'])
def scrape():
    """
    Endpoint de scraping con modo STEALTH

    Body:
    {
        "url": "https://example.com",
        "searchTerm": "término a buscar"
    }
    """
    try:
        data = request.json
        url = data.get('url')
        search_term = data.get('searchTerm', '')
        price_max = data.get('priceMax')
        browser_choice = data.get('browser', 'chromium')

        if not url:
            return jsonify({
                "success": False,
                "error": "URL es requerida"
            }), 400

        print(f"\n📥 Nueva solicitud de scraping STEALTH")
        print(f"   URL: {url}")
        print(f"   Ciudad/localidad: {search_term or '(sin especificar)'}")
        print(f"   Precio máximo: {price_max or 'sin límite'}")
        print(f"   Navegador: {browser_choice}")

        # Verificar si está completamente configurado
        if not BROWSER_USE_AVAILABLE or not LLM_CONFIGURED:
            print("⚠️  Sistema no configurado, retornando simulación")
            result = simulate_scrape(url, search_term)
        else:
            # Ejecutar scraper STEALTH con Playwright puro + OpenAI
            print("🚀 Ejecutando scraping ULTRA-STEALTH con Playwright...")
            result = asyncio.run(scrape_with_stealth(
                url, search_term, os.getenv("OPENAI_API_KEY"), browser_choice,
                price_max=price_max
            ))

        # Enviar email automático con archivos de debug si existen
        try:
            debug_files = [
                '/tmp/fotocasa_search_failed.png',
                '/tmp/fotocasa_search_failed.html',
                '/tmp/fotocasa_low_content.html',
                '/tmp/fotocasa_results.png',
                '/tmp/fotocasa_content_debug.txt',
                '/tmp/captcha_detected.png',
            ]

            # Filtrar solo los archivos que existen
            existing_files = [f for f in debug_files if pathlib.Path(f).exists()]

            if existing_files and os.getenv('EMAIL_USER'):
                print(f"\n📎 Enviando {len(existing_files)} archivos de debug por email...")
                debug_subject = f"[DEBUG] Scraping de {search_term or 'Fotocasa'} - {len(existing_files)} archivos"
                debug_body = f"""Adjuntos de la ejecución de scraping:

URL: {url}
Búsqueda: {search_term or 'N/A'}
Resultado: {'Exitoso' if result.get('success') else 'Error/Bloqueado'}
Archivos: {len(existing_files)}

Archivos adjuntos:
{chr(10).join([f'- {pathlib.Path(f).name}' for f in existing_files])}
"""
                send_email(
                    os.getenv('EMAIL_USER'),
                    debug_subject,
                    debug_body,
                    attachments=existing_files
                )
                print("✓ Email de debug enviado")
        except Exception as e:
            print(f"⚠️  No se pudo enviar email de debug: {e}")

        return jsonify(result)

    except Exception as e:
        print(f"❌ Error en /api/scrape: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/api/email', methods=['POST'])
def email():
    """
    Endpoint de email

    Body:
    {
        "to": "destinatario@example.com",
        "subject": "Asunto",
        "body": "Texto plano",
        "html": "<html>...</html>"
    }
    """
    try:
        data = request.json
        to = data.get('to')
        subject = data.get('subject')
        body = data.get('body')
        html = data.get('html')

        if not to or not subject or not body:
            return jsonify({
                "success": False,
                "error": "to, subject y body son requeridos"
            }), 400

        print(f"📧 Enviando email a {to}")

        success = send_email(to, subject, body, html)

        return jsonify({"success": success})

    except Exception as e:
        print(f"❌ Error en /api/email: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/api/status', methods=['GET'])
def status():
    """Estado detallado del servicio"""
    email_configured = bool(
        os.getenv('EMAIL_HOST') and
        os.getenv('EMAIL_USER') and
        os.getenv('EMAIL_PASS')
    )

    return jsonify({
        "server": "ok",
        "stealth_mode": {
            "enabled": True,
            "features": [
                "headless=False (navegador visible)",
                "disable-blink-features=AutomationControlled",
                "Delays automáticos simulando humano",
                "User-agent real de Chrome",
                "Detección de CAPTCHA"
            ]
        },
        "browserUse": {
            "installed": BROWSER_USE_AVAILABLE,
            "llm_configured": LLM_CONFIGURED,
            "configured": BROWSER_USE_AVAILABLE and LLM_CONFIGURED,
            "mode": "local-ai-stealth" if (BROWSER_USE_AVAILABLE and LLM_CONFIGURED) else "simulation",
            "message": "Browser-use LOCAL STEALTH configurado" if (BROWSER_USE_AVAILABLE and LLM_CONFIGURED) else "Modo simulación"
        },
        "email": {
            "configured": email_configured,
            "host": os.getenv('EMAIL_HOST', 'not configured')
        },
        "llm": {
            "provider": "OpenAI" if os.getenv("OPENAI_API_KEY") else "None",
            "model": os.getenv("LLM_MODEL", "gpt-4o-mini"),
            "configured": LLM_CONFIGURED
        }
    })


if __name__ == '__main__':
    port = int(os.getenv('PORT', 3000))

    print("\n" + "="*60)
    print("🚀 BACKEND PYTHON - Playwright ULTRA-STEALTH + OpenAI")
    print("="*60)
    print(f"Puerto: {port}")
    print(f"Playwright: {'✓ Instalado' if BROWSER_USE_AVAILABLE else '✗ No instalado'}")
    print(f"OpenAI: {'✓ Configurado' if LLM_CONFIGURED else '✗ No configurado'}")
    print(f"Email: {'✓ Configurado' if os.getenv('EMAIL_USER') else '✗ No configurado'}")
    print(f"Modo: {'ULTRA-STEALTH' if (BROWSER_USE_AVAILABLE and LLM_CONFIGURED) else 'SIMULACIÓN'}")
    print("\n🥷 ULTRA-STEALTH MODE:")
    print("   • Navegador visible (headless=False)")
    print("   • navigator.webdriver = false")
    print("   • Chrome runtime simulado")
    print("   • Hardware fingerprint fake")
    print("   • Delays aleatorios + scroll humano")
    print("   • Detección automática de CAPTCHA")
    print("   • Análisis de contenido con OpenAI")
    print("="*60)

    if not BROWSER_USE_AVAILABLE:
        print("\n⚠️  Para instalar browser-use:")
        print("   pip install browser-use langchain-openai playwright")
        print("   playwright install chromium\n")

    if BROWSER_USE_AVAILABLE and not LLM_CONFIGURED:
        print("\n⚠️  Para configurar LLM:")
        print("   Opción A (OpenAI):")
        print("     1. Obtén key: https://platform.openai.com/api-keys")
        print("     2. Agrega en .env: OPENAI_API_KEY=sk-...")
        print("   Opción B (Ollama - gratis):")
        print("     1. Instala: https://ollama.ai/")
        print("     2. Descarga modelo: ollama run llama2")
        print("     3. Modifica main.py para usar Ollama\n")

    # Mostrar navegador configurado
    brave_path = os.getenv("BRAVE_PATH")

    if brave_path and os.path.exists(brave_path):
        print(f"\n🦁 BRAVE DISPONIBLE: {brave_path}")
        print("   El usuario puede seleccionar Brave o Chromium desde el frontend")
    else:
        print("\n⚠️  BRAVE no configurado (solo Chromium disponible)")
        print("   Para habilitar Brave, agrega en .env:")
        print("   BRAVE_PATH=C:\\Program Files\\BraveSoftware\\Brave-Browser\\Application\\brave.exe")

    print("\n🌐 Servidor iniciando...\n")
    app.run(host='0.0.0.0', port=port, debug=True)
