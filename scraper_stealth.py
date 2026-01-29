"""
Scraper STEALTH usando Playwright puro + OpenAI para análisis
Soporta selección de navegador (Chromium / Brave)
"""

import asyncio
import random
import json
import logging
import sys
from datetime import datetime
from playwright.async_api import async_playwright
from langchain_openai import ChatOpenAI
import os
from dotenv import load_dotenv

# CRÍTICO: Cargar variables de entorno del .env
load_dotenv()

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),  # Logs a stdout (visible en Docker)
        logging.FileHandler('/tmp/scraper.log')  # Logs a archivo en /tmp (accesible en Docker)
    ]
)
logger = logging.getLogger(__name__)


MAX_EMAIL_ITEMS = 15


def _build_html_table(items: list, summary: str, total_results: int, url: str) -> str:
    """Construye una tabla HTML con los primeros 15 resultados."""
    if not items:
        return f"<p>{summary}</p>"

    shown_items = items[:MAX_EMAIL_ITEMS]
    rows = ""
    for i, item in enumerate(shown_items, 1):
        title = item.get("title", "")
        link = item.get("link", "")
        desc = item.get("description", "")
        price = item.get("price", "N/A")

        title_cell = f'<a href="{link}" style="color:#007bff;text-decoration:none;">{title}</a>' if link else title

        rows += f"""
        <tr>
          <td style="padding:10px;border-bottom:1px solid #dee2e6;text-align:center;font-weight:bold;">{i}</td>
          <td style="padding:10px;border-bottom:1px solid #dee2e6;">{title_cell}</td>
          <td style="padding:10px;border-bottom:1px solid #dee2e6;">{desc}</td>
          <td style="padding:10px;border-bottom:1px solid #dee2e6;text-align:right;font-weight:bold;white-space:nowrap;">{price}</td>
        </tr>"""

    remaining = len(items) - MAX_EMAIL_ITEMS
    more_text = f'<p style="margin-top:10px;color:#6c757d;font-style:italic;">... y {remaining} resultados más. <a href="{url}">Ver todos en la web</a></p>' if remaining > 0 else ''

    return f"""
    <p style="margin-bottom:5px;"><strong>Resumen:</strong> {summary}</p>
    <p style="margin-bottom:15px;color:#6c757d;">Total de resultados en la página: {total_results} (mostrando los primeros {len(shown_items)})</p>
    <table style="width:100%;border-collapse:collapse;font-size:14px;">
      <thead>
        <tr style="background-color:#007bff;color:white;">
          <th style="padding:10px;text-align:center;width:50px;">#</th>
          <th style="padding:10px;text-align:left;">Anuncio</th>
          <th style="padding:10px;text-align:left;">Descripción</th>
          <th style="padding:10px;text-align:right;width:120px;">Precio</th>
        </tr>
      </thead>
      <tbody>{rows}
      </tbody>
    </table>
    {more_text}"""


async def _close_fotocasa_popups(page):
    """Cierra los popups molestos de Fotocasa (alertas, newsletters, etc.)"""
    popup_selectors = [
        'button:has-text("No, gracias")',
        'button:has-text("No gracias")',
        'button:has-text("Ahora no")',
        'button:has-text("Rechazar")',
        '[data-testid="reject-button"]',
        '[aria-label*="Cerrar"]',
        'button[aria-label*="Close"]',
        '.close-button',
        'button.close',
    ]

    for selector in popup_selectors:
        try:
            btn = page.locator(selector).first
            if await btn.is_visible(timeout=1000):
                await asyncio.sleep(random.uniform(0.3, 0.6))
                await btn.click()
                print(f"✅ Popup cerrado con: {selector}")
                await asyncio.sleep(random.uniform(0.5, 1))
        except:
            continue


async def _search_fotocasa(page, city: str, price_max: int = None) -> str:
    """
    Realiza búsqueda interactiva en fotocasa.es:
    1. Escribe la ciudad en el input de búsqueda
    2. Espera autocompletado
    3. Hace clic en la primera sugerencia (tiene el nombre correcto)
    4. Cierra popups
    5. Aplica filtro de precio máximo si se proporciona
    6. Retorna la URL final
    """
    logger.info(f"🔍 Buscando en Fotocasa: {city}")

    # Buscar input de búsqueda principal
    search_selectors = [
        'input[placeholder*="Buscar vivienda"]',
        'input[placeholder*="municipio"]',
        'input[placeholder*="barrio"]',
        'input[type="search"]',
        'input[placeholder*="Búsqueda"]',
        '#search-input',
        '[data-testid="search-input"]',
        'input[name*="search"]',
        'input[id*="search"]',
    ]

    search_done = False
    for selector in search_selectors:
        try:
            inp = page.locator(selector).first
            # En modo headless, usar is_enabled() en lugar de is_visible()
            try:
                is_visible = await inp.is_visible(timeout=1000)
            except:
                is_visible = False

            is_enabled = await inp.is_enabled(timeout=1000)

            if is_visible or is_enabled:
                logger.info(f"   ✓ Input encontrado con selector: {selector}")
                await asyncio.sleep(random.uniform(0.5, 1))

                # En modo headless, a veces es mejor usar focus() antes de click()
                try:
                    await inp.focus()
                    await asyncio.sleep(0.2)
                except:
                    pass

                await inp.click()
                await asyncio.sleep(random.uniform(0.3, 0.6))
                await inp.fill(city)
                logger.info(f"✅ Ciudad '{city}' introducida en: {selector}")

                # Esperar a que aparezca el dropdown de autocompletado
                print("⏳ Esperando autocompletado...")
                await asyncio.sleep(random.uniform(1.5, 2.5))

                # Intentar hacer clic en la primera sugerencia del dropdown
                suggestion_selectors = [
                    '[role="option"]',
                    '[class*="autocomplete"] li:first-child',
                    '[class*="suggestion"] li:first-child',
                    '[data-testid="suggestion-item"]',
                    'ul[role="listbox"] li:first-child',
                    '.re-Autocomplete-list li:first-child',
                ]

                suggestion_clicked = False
                for sug_selector in suggestion_selectors:
                    try:
                        suggestion = page.locator(sug_selector).first
                        if await suggestion.is_visible(timeout=1500):
                            await asyncio.sleep(random.uniform(0.3, 0.6))
                            await suggestion.click()
                            suggestion_clicked = True
                            print(f"✅ Sugerencia seleccionada con: {sug_selector}")
                            await asyncio.sleep(random.uniform(2, 3))
                            break
                    except:
                        continue

                if not suggestion_clicked:
                    # Fallback: presionar Enter si no se encuentra el dropdown
                    print("⚠️  No se encontró sugerencia, presionando Enter...")
                    await inp.press('Enter')
                    await asyncio.sleep(random.uniform(3, 5))

                search_done = True
                print("✅ Navegación a resultados completada")
                break
        except Exception as e:
            logger.debug(f"⚠️  Selector '{selector}' falló: {e}")
            continue

    if not search_done:
        logger.error("❌ No se pudo encontrar el input de búsqueda (búsqueda interactiva falló)")
        logger.error(f"   URL actual: {page.url}")

        # Guardar screenshot de debug
        try:
            screenshot_path = '/tmp/fotocasa_search_failed.png'
            await page.screenshot(path=screenshot_path)
            logger.info(f"   Screenshot guardado: {screenshot_path}")
        except Exception as e:
            logger.warning(f"   No se pudo guardar screenshot: {e}")

        # Guardar HTML de debug
        try:
            page_html = await page.content()
            html_path = '/tmp/fotocasa_search_failed.html'
            with open(html_path, 'w', encoding='utf-8') as f:
                f.write(page_html[:5000])
            logger.info(f"   HTML guardado: {html_path}")
        except Exception as e:
            logger.warning(f"   No se pudo guardar HTML: {e}")

        # Intentar búsqueda por URL como fallback
        logger.warning("🔄 Intentando búsqueda alternativa por URL directa...")
        try:
            from urllib.parse import urlencode

            # Construir URL de búsqueda directa para fotocasa con formato correcto
            # Formato: https://www.fotocasa.es/es/comprar/viviendas/{ciudad}/todas-las-zonas/l
            city_slug = city.lower().replace(' ', '-')
            base_url = f"https://www.fotocasa.es/es/comprar/viviendas/{city_slug}/todas-las-zonas/l"

            # Agregar parámetros de filtrado
            params = {
                'sortType': 'price',
                'sortOrderDesc': 'false'
            }

            if price_max is not None:
                params['maxPrice'] = str(price_max)

            search_url = f"{base_url}?{urlencode(params)}"
            logger.info(f"   Navegando a: {search_url}")
            await page.goto(search_url, wait_until='load', timeout=20000)

            # Esperar a que carguen los anuncios (articles)
            logger.info("   ⏳ Esperando carga de anuncios...")
            try:
                # Esperar a que aparezca al menos un artículo
                await page.wait_for_selector('article', timeout=10000)
                logger.info("   ✓ Anuncios detectados")
            except:
                logger.warning("   ⚠️  Timeout esperando anuncios, continuando...")

            await asyncio.sleep(random.uniform(2, 3))
            logger.info(f"✓ Búsqueda por URL completada exitosamente")
            return search_url
        except Exception as e:
            logger.error(f"⚠️  Búsqueda por URL también falló: {e}")
            return page.url

    # Cerrar popups ANTES de continuar
    logger.info("🚫 Cerrando popups...")
    await _close_fotocasa_popups(page)

    # Obtener URL actual (fotocasa ya nos llevó a la URL correcta)
    current_url = page.url
    logger.info(f"📍 URL actual después de búsqueda: {current_url}")

    # Aplicar filtros a la URL actual
    from urllib.parse import urlparse, urlencode, parse_qs, urlunparse

    parsed = urlparse(current_url)
    params = parse_qs(parsed.query)

    # Agregar/actualizar parámetros
    params['sortType'] = ['price']
    params['sortOrderDesc'] = ['false']

    if price_max is not None:
        params['maxPrice'] = [str(price_max)]
        print(f"💰 Aplicando filtro de precio: hasta {price_max}€")

    # Reconstruir query string
    flat_params = {k: v[0] if isinstance(v, list) and len(v) == 1 else v for k, v in params.items()}
    new_query = urlencode(flat_params, doseq=True)
    final_url = urlunparse((parsed.scheme, parsed.netloc, parsed.path, parsed.params, new_query, parsed.fragment))

    print(f"🔗 URL final con filtros: {final_url}")

    # Navegar a la URL correcta con filtros
    try:
        await page.goto(final_url, wait_until='load', timeout=30000)
        print("✅ Navegación exitosa")
        await asyncio.sleep(random.uniform(2, 3))

        # Cerrar popups de nuevo (pueden volver a salir después de navegar)
        await _close_fotocasa_popups(page)

        # Esperar a que se carguen los resultados
        await asyncio.sleep(random.uniform(1, 2))
    except Exception as e:
        print(f"⚠️  Error navegando a URL con filtros: {e}")
        print("   Intentando sin esperar networkidle...")
        try:
            await page.goto(final_url, timeout=30000)
            await asyncio.sleep(random.uniform(2, 3))
            await _close_fotocasa_popups(page)
        except Exception as e2:
            print(f"❌ Error definitivo: {e2}")

    return final_url


def _build_plain_text(items: list, summary: str, total_results: int) -> str:
    """Construye una versión texto plano con los primeros 15 resultados."""
    if not items:
        return summary

    shown_items = items[:MAX_EMAIL_ITEMS]
    lines = [f"Resumen: {summary}", f"Total resultados: {total_results} (mostrando primeros {len(shown_items)})", ""]
    for i, item in enumerate(shown_items, 1):
        title = item.get("title", "")
        link = item.get("link", "")
        desc = item.get("description", "")
        price = item.get("price", "N/A")
        lines.append(f"{i}. {title}")
        if link:
            lines.append(f"   Link: {link}")
        lines.append(f"   {desc}")
        lines.append(f"   Precio: {price}")
        lines.append("")

    remaining = len(items) - MAX_EMAIL_ITEMS
    if remaining > 0:
        lines.append(f"... y {remaining} resultados más.")

    return "\n".join(lines)


MAX_RETRIES = 2


async def scrape_with_stealth(url: str, search_term: str, openai_key: str, browser: str = "chromium",
                              price_max: int = None, retry_count: int = 0) -> dict:
    """
    Scraper STEALTH con selección explícita de navegador.
    browser: "chromium" o "brave"
    search_term: ciudad/localidad para fotocasa (ej: "Mataro", "Cabrils")
    price_max: precio máximo a filtrar (opcional)
    retry_count: contador interno de reintentos (máximo 2)
    """
    if retry_count > 0:
        print(f"🔄 Reintento {retry_count}/{MAX_RETRIES}")

    playwright = None
    browser_obj = None
    context = None
    page = None

    try:
        playwright = await async_playwright().start()

        # Control de headless vía env var.
        # Comportamiento seguro en contenedores: si no existe DISPLAY se fuerza headless=True
        headless_env = os.getenv("HEADLESS")
        if headless_env is not None:
            HEADLESS = headless_env.lower() in ("1", "true", "yes")
        else:
            # Si no hay DISPLAY (p.e. contenedor sin X), usar headless por defecto
            HEADLESS = not bool(os.getenv("DISPLAY"))

        print(f"[DEBUG] HEADLESS={HEADLESS} (HEADLESS env='{headless_env}', DISPLAY='{os.getenv('DISPLAY')}')")

        launch_args = [
            '--disable-blink-features=AutomationControlled',
            '--window-size=1920,1080',
            '--start-maximized',
            # Flags útiles en contenedores
            '--no-sandbox',
            '--disable-dev-shm-usage',
            '--disable-gpu',
        ]

        # Intentar usar Brave si fue solicitado y existe la ruta. Si no, caer a Chromium.
        browser_obj = None
        browser_name = 'Chromium'

        if browser == "brave":
            brave_path = os.getenv("BRAVE_PATH")
            if brave_path and os.path.exists(brave_path):
                print(f"🦁 Lanzando Brave desde: {brave_path}")
                browser_obj = await playwright.chromium.launch(
                    executable_path=brave_path,
                    headless=HEADLESS,
                    args=launch_args,
                    ignore_default_args=["--enable-automation"],
                )
                browser_name = "Brave"
            else:
                print(f"⚠️  BRAVE_PATH no configurado o no existe ({brave_path or 'None'}). Se usará Chromium en su lugar.")

        # Si no se creó browser_obj (either not brave or brave not available), lanzar Chromium
        if browser_obj is None:
            print("🌐 Lanzando Chromium...")
            browser_obj = await playwright.chromium.launch(
                headless=HEADLESS,
                args=launch_args,
                ignore_default_args=["--enable-automation"],
            )
            browser_name = "Chromium"

        # Crear context
        context = await browser_obj.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            locale='es-ES',
            timezone_id='Europe/Madrid',
            geolocation={'latitude': 40.4168, 'longitude': -3.7038},
            permissions=['geolocation'],
            color_scheme='light',
            device_scale_factor=1,
            is_mobile=False,
            has_touch=False,
            accept_downloads=False,
        )

        # Scripts ANTI-DETECCIÓN
        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => false });

            window.chrome = {
                runtime: {},
                loadTimes: function() {},
                csi: function() {},
                app: {}
            };

            Object.defineProperty(navigator, 'plugins', {
                get: () => [
                    {
                        0: {type: "application/x-google-chrome-pdf"},
                        description: "Portable Document Format",
                        filename: "internal-pdf-viewer",
                        length: 1,
                        name: "Chrome PDF Plugin"
                    }
                ]
            });

            Object.defineProperty(navigator, 'languages', {
                get: () => ['es-ES', 'es', 'en-US', 'en']
            });

            Object.defineProperty(navigator, 'platform', {
                get: () => 'Win32'
            });

            Object.defineProperty(navigator, 'hardwareConcurrency', {
                get: () => 8
            });

            Object.defineProperty(navigator, 'deviceMemory', {
                get: () => 8
            });

            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                    Promise.resolve({ state: Notification.permission }) :
                    originalQuery(parameters)
            );

            const getParameter = WebGLRenderingContext.prototype.getParameter;
            WebGLRenderingContext.prototype.getParameter = function(parameter) {
                if (parameter === 37445) return 'Intel Inc.';
                if (parameter === 37446) return 'Intel(R) UHD Graphics 620';
                return getParameter.apply(this, [parameter]);
            };
        """)

        # Crear página
        page = await context.new_page()

        print(f"🥷 Navegando a {url} con STEALTH MODE usando {browser_name}...")

        # Navegar con timeout generoso
        await page.goto(url, wait_until='networkidle', timeout=30000)

        # MANEJAR BANNER DE COOKIES / CONSENTIMIENTO GDPR
        print("🍪 Buscando banner de cookies...")
        await asyncio.sleep(random.uniform(1, 2))

        cookie_accepted = False
        # Selectores comunes para botones de aceptar cookies
        cookie_selectors = [
            # Texto exacto en botones
            'button:has-text("Aceptar y continuar")',
            'button:has-text("Aceptar todo")',
            'button:has-text("Aceptar todas")',
            'button:has-text("Aceptar cookies")',
            'button:has-text("Acepto")',
            'button:has-text("Accept all")',
            'button:has-text("Accept")',
            # IDs y clases comunes de CMPs (Consent Management Platforms)
            '#onetrust-accept-btn-handler',
            '#acceptAll',
            '.accept-cookies',
            '[data-testid="TcfAccept"]',
            '#didomi-notice-agree-button',
            '.css-1hy2vtq',  # fotocasa específico
        ]

        for selector in cookie_selectors:
            try:
                btn = page.locator(selector).first
                if await btn.is_visible(timeout=500):
                    await asyncio.sleep(random.uniform(0.3, 0.8))
                    await btn.click()
                    cookie_accepted = True
                    print(f"✅ Cookie banner aceptado con: {selector}")
                    await asyncio.sleep(random.uniform(1, 2))
                    break
            except:
                continue

        if not cookie_accepted:
            print("ℹ️  No se detectó banner de cookies (o ya fue aceptado)")

        # REALIZAR BÚSQUEDA INTERACTIVA en fotocasa.es
        nav_url = url
        if "fotocasa" in url and search_term and search_term.strip():
            nav_url = await _search_fotocasa(page, search_term, price_max)
        else:
            print("ℹ️  URL no es fotocasa o no se especificó ciudad, navegación directa")

        # SIMULAR COMPORTAMIENTO HUMANO
        logger.info("⏱️  Esperando 3-5 segundos (simular lectura)...")
        await asyncio.sleep(random.uniform(3, 5))

        # Inyectar script para forzar visibilidad de elementos
        logger.info("🔧 Inyectando scripts para mejorar visibilidad...")
        try:
            await page.evaluate("""
                // Forzar visibilidad de elementos ocultos
                document.querySelectorAll('[style*="display: none"]').forEach(el => {
                    el.style.display = 'block';
                });
                document.querySelectorAll('[style*="visibility: hidden"]').forEach(el => {
                    el.style.visibility = 'visible';
                });
                // Scroll al inicio para asegurar que se cargue el contenido
                window.scrollTo(0, 0);
            """)
            logger.info("   ✓ Scripts inyectados")
        except Exception as e:
            logger.warning(f"   ⚠️  No se pudo inyectar scripts: {e}")

        # Scroll progresivo para cargar los primeros 15+ resultados (lazy loading)
        logger.info("📜 Scroll progresivo para cargar resultados (hasta 15)...")
        for i in range(15):  # Aumentado de 10 a 15
            # Scrolls más grandes y más frecuentes para cargar lazy loading
            scroll_amount = random.randint(300, 600)
            await page.mouse.wheel(0, scroll_amount)
            logger.info(f"   Scroll {i+1}/15: {scroll_amount}px")
            # Esperar para que se cargue el contenido lazy
            await asyncio.sleep(random.uniform(1, 2))

        # Esperar un poco más al final para asegurar que todo cargó
        logger.info("⏱️  Esperando carga final de resultados...")
        await asyncio.sleep(random.uniform(3, 5))

        # Tomar screenshot para debug
        try:
            await page.screenshot(path='/tmp/fotocasa_results.png')
            logger.info("📸 Screenshot guardado en: /tmp/fotocasa_results.png")
        except Exception as e:
            logger.warning(f"   No se pudo guardar screenshot: {e}")

        # Verificar que hay anuncios cargados en la página
        try:
            # Selectores comunes de cards/artículos de viviendas en fotocasa
            article_selectors = [
                'article',
                '[data-testid*="property"]',
                '[class*="PropertyCard"]',
                '.re-CardPackMinimal',
                '.re-Card',
                '[class*="listing"]',
                '[class*="card"]',
            ]

            article_count = 0
            found_selector = None
            for sel in article_selectors:
                try:
                    count = await page.locator(sel).count()
                    if count > 0:
                        article_count = count
                        found_selector = sel
                        logger.info(f"✅ Encontrados {count} anuncios con selector: {sel}")
                        break
                except Exception as e:
                    logger.debug(f"   Selector '{sel}' no encontrado: {e}")
                    continue

            if article_count == 0:
                logger.error("❌ No se encontraron anuncios en la página")
                logger.error(f"   Selectores intentados: {', '.join(article_selectors)}")
            elif article_count < 15:
                logger.warning(f"⚠️  Solo se encontraron {article_count} anuncios (menos de 15)")

        except Exception as e:
            logger.error(f"❌ Error verificando anuncios: {e}")

        # Capturar contenido de la página (HTML completo para mejor análisis)
        page_html = await page.content()
        page_text = await page.inner_text('body')

        logger.info(f"📊 Contenido capturado:")
        logger.info(f"   - HTML: {len(page_html)} caracteres")
        logger.info(f"   - Texto visible: {len(page_text)} caracteres")

        # Verificar si la página tiene contenido de búsqueda o es la página principal
        is_search_results_page = (
            "fotocasa" in page_text.lower() and
            ("vivienda" in page_text.lower() or "anuncio" in page_text.lower())
        )
        logger.info(f"   - ¿Página de resultados?: {is_search_results_page}")
        logger.info(f"   - URL actual: {nav_url if 'nav_url' in locals() else url}")

        # Debug: guardar HTML capturado para análisis
        if len(page_text) < 500:
            logger.warning(f"   ⚠️  Contenido muy pequeño ({len(page_text)} chars), guardando HTML para debug")
            try:
                with open('/tmp/fotocasa_low_content.html', 'w', encoding='utf-8') as f:
                    f.write(page_html)
                logger.info("   HTML guardado en: /tmp/fotocasa_low_content.html")
                # Log primeras líneas del HTML
                logger.info(f"   HTML preview: {page_html[:300]}...")
            except Exception as e:
                logger.warning(f"   No se pudo guardar HTML: {e}")

        # Detectar CAPTCHA
        captcha_keywords = ['captcha', 'verification', 'verify you', 'too many requests',
                           'verificación', 'demasiadas peticiones', 'robot']

        has_captcha = any(keyword in page_text.lower() for keyword in captcha_keywords)

        if has_captcha:
            logger.error("❌ CAPTCHA/VERIFICACIÓN DETECTADA")
            try:
                await page.screenshot(path='/tmp/captcha_detected.png')
                logger.info("   Screenshot guardado: /tmp/captcha_detected.png")
            except:
                pass

            return {
                "success": False,
                "content": "❌ CAPTCHA/VERIFICACIÓN DETECTADA\n\nLa página muestra un sistema de verificación anti-bot.",
                "description": "CAPTCHA detectado",
                "error": "CAPTCHA_DETECTED"
            }

        # Usar OpenAI para extraer info relevante
        logger.info("🤖 Analizando contenido con OpenAI...")

        llm = ChatOpenAI(
            model=os.getenv("LLM_MODEL", "gpt-4o-mini"),
            api_key=openai_key,
            temperature=0
        )

        # Extraer enlaces de anuncios del HTML para pasarlos a OpenAI
        links_info = []
        try:
            articles = await page.locator('article').all()
            logger.info(f"   Artículos encontrados: {len(articles)}")
            for article in articles[:15]:  # Solo los primeros 15
                try:
                    # Buscar el link dentro del artículo
                    link_elem = article.locator('a[href*="/comprar/vivienda/"]').first
                    if link_elem:
                        href = await link_elem.get_attribute('href')
                        if href:
                            # Convertir href relativo a absoluto
                            if href.startswith('/'):
                                href = f"https://www.fotocasa.es{href}"
                            links_info.append(href)
                except:
                    continue
            logger.info(f"🔗 Enlaces extraídos: {len(links_info)}")
        except Exception as e:
            logger.warning(f"⚠️  Error extrayendo enlaces: {e}")

        # Truncar contenido para no exceder tokens (20k para capturar más anuncios)
        truncated_text = page_text[:20000] if len(page_text) > 20000 else page_text

        # Agregar los links extraídos al contexto
        if links_info:
            links_text = "\n\nENLACES DE ANUNCIOS ENCONTRADOS:\n" + "\n".join([f"- {link}" for link in links_info[:15]])
            truncated_text += links_text

        # Guardar contenido para debug
        try:
            debug_file = '/tmp/fotocasa_content_debug.txt'
            with open(debug_file, 'w', encoding='utf-8') as f:
                f.write(f"URL: {nav_url if 'nav_url' in locals() else url}\n")
                f.write(f"Longitud total texto: {len(page_text)}\n")
                f.write(f"Enlaces encontrados: {len(links_info)}\n")
                f.write(f"Longitud truncada: {len(truncated_text)}\n")
                f.write("="*80 + "\n")
                f.write(truncated_text)
            logger.info(f"📝 Contenido guardado en: {debug_file}")
        except Exception as e:
            logger.warning(f"   No se pudo guardar debug file: {e}")

        # Prompt que pide JSON estructurado
        search_context = f'Esta es una página de resultados de Fotocasa con viviendas en venta en: "{search_term}"\n' if search_term and search_term.strip() else ''
        description = f"Viviendas en {search_term}" if search_term and search_term.strip() else f"Contenido extraído de {url}"

        analysis_prompt = f"""
Analiza el siguiente contenido de una página de FOTOCASA (portal inmobiliario español): {url}
{search_context}

Contenido de la página:
{truncated_text}

CONTEXTO: Esto es una página de resultados de búsqueda de Fotocasa. Cada anuncio de vivienda contiene:
- Dirección o ubicación del inmueble
- Precio (ejemplo: "200.000 €")
- Características: número de habitaciones, baños, metros cuadrados (m²)
- Descripción breve

Tu tarea es extraer TODOS los anuncios de viviendas que encuentres en el texto.

IMPORTANTE: Responde EXCLUSIVAMENTE con un JSON válido, sin markdown, sin ```json, sin texto adicional.

El JSON debe tener esta estructura exacta:
{{
  "summary": "Resumen breve de lo encontrado (1-2 frases)",
  "total_results": 0,
  "items": [
    {{
      "title": "Título o dirección del anuncio/elemento",
      "link": "URL directa si está disponible, o vacío",
      "description": "Descripción breve: habitaciones, baños, superficie, planta, características principales",
      "price": "Precio tal como aparece (ej: 510.000 €)"
    }}
  ]
}}

Reglas:
- Extrae TODOS los anuncios/elementos/listados que encuentres en la página (máximo 15)
- Cada anuncio debe incluir:
  * title: La dirección o ubicación de la vivienda
  * link: La URL completa del anuncio (busca en la sección "ENLACES DE ANUNCIOS ENCONTRADOS" al final del texto y asigna el enlace correspondiente a cada anuncio EN EL MISMO ORDEN que aparecen)
  * description: Características (habitaciones, baños, m², planta, extras)
  * price: Precio exacto como aparece
- IMPORTANTE: Los enlaces están en la sección "ENLACES DE ANUNCIOS ENCONTRADOS" al final del texto
- Asigna los enlaces a los anuncios en el mismo orden (primer anuncio = primer enlace, segundo = segundo, etc.)
- Si hay más anuncios que enlaces, deja el "link" vacío para los restantes
- NO incluyas info de cookies, banners o elementos de navegación
"""

        response = llm.invoke(analysis_prompt)
        raw_response = response.content.strip()

        # Limpiar posibles wrappers de markdown
        if raw_response.startswith("```"):
            raw_response = raw_response.split("\n", 1)[1] if "\n" in raw_response else raw_response[3:]
            if raw_response.endswith("```"):
                raw_response = raw_response[:-3].strip()

        logger.info(f"✅ Análisis completado: {len(raw_response)} caracteres")

        # Intentar parsear JSON
        try:
            parsed = json.loads(raw_response)
            items = parsed.get("items", [])
            summary = parsed.get("summary", "")
            total_results = parsed.get("total_results", len(items))

            logger.info(f"📋 OpenAI extrajo: {len(items)} anuncios")
            logger.info(f"   Summary: {summary[:100]}..." if summary else "   Sin summary")

            # Verificar que haya al menos algún resultado válido
            if not items and not summary:
                logger.warning("⚠️  JSON válido pero sin resultados útiles")
                if retry_count < MAX_RETRIES:
                    logger.warning(f"⚠️  Reintentando análisis... (intento {retry_count + 1}/{MAX_RETRIES})")
                    # Cleanup y reintentar
                    await page.close()
                    await context.close()
                    await browser_obj.close()
                    await playwright.stop()
                    await asyncio.sleep(3)
                    return await scrape_with_stealth(
                        url, search_term, openai_key, browser, price_max, retry_count + 1
                    )

            # Construir tabla HTML (usar nav_url si está disponible, sino url original)
            final_link = nav_url if 'nav_url' in locals() else url
            content_html = _build_html_table(items, summary, total_results, final_link)
            # Construir texto plano
            content_plain = _build_plain_text(items, summary, total_results)

        except json.JSONDecodeError as json_err:
            logger.warning(f"⚠️  No se pudo parsear JSON: {json_err}")
            # Si es el primer o segundo intento, reintentar
            if retry_count < MAX_RETRIES:
                logger.warning(f"⚠️  Reintentando análisis... (intento {retry_count + 1}/{MAX_RETRIES})")
                # Cleanup y reintentar
                await page.close()
                await context.close()
                await browser_obj.close()
                await playwright.stop()
                await asyncio.sleep(3)
                return await scrape_with_stealth(
                    url, search_term, openai_key, browser, price_max, retry_count + 1
                )
            else:
                logger.error(f"❌ JSON inválido después de {MAX_RETRIES} reintentos, usando texto plano")
                content_plain = raw_response
                content_html = f"<p>{raw_response}</p>"

        return {
            "success": True,
            "content": content_plain,
            "contentHtml": content_html,
            "description": description,
            "finalUrl": nav_url
        }

    except Exception as e:
        logger.error(f"❌ Error: {e}")

        # Cleanup antes de reintentar
        if page:
            try:
                await page.close()
            except:
                pass
        if context:
            try:
                await context.close()
            except:
                pass
        if browser_obj:
            try:
                await browser_obj.close()
            except:
                pass
        if playwright:
            try:
                await playwright.stop()
            except:
                pass

        # Reintentar si no se ha alcanzado el límite
        if retry_count < MAX_RETRIES:
            logger.warning(f"⚠️  Reintentando en 3 segundos... (intento {retry_count + 1}/{MAX_RETRIES})")
            await asyncio.sleep(3)
            return await scrape_with_stealth(
                url, search_term, openai_key, browser, price_max, retry_count + 1
            )
        else:
            logger.error(f"❌ Error definitivo después de {MAX_RETRIES} reintentos")
            return {
                "success": False,
                "content": "",
                "description": "",
                "error": f"Error después de {MAX_RETRIES} reintentos: {str(e)}"
            }

    finally:
        # Cleanup final (solo si no se va a reintentar)
        if page:
            try:
                await page.close()
            except:
                pass
        if context:
            try:
                await context.close()
            except:
                pass
        if browser_obj:
            try:
                await browser_obj.close()
            except:
                pass
        if playwright:
            try:
                await playwright.stop()
            except:
                pass
