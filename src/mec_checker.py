import logging
import os
import socket
import time

from playwright.sync_api import sync_playwright, Error as PlaywrightError

from ai_agent import consultar_agente_ia_groq
from utils import cargar_estado, guardar_estado, get_mec_credentials, send_notification_message, get_agent_model
from notifier import send_telegram

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")

STORAGE_STATE_FILE = "data/storage_state.json"
# El handshake SAML (bpmgob -> IdUruguay) falla de forma intermitente a nivel TCP;
# este es el número máximo de veces que se reinicia el handshake completo.
LOGIN_MAX_HANDSHAKES = 3


class MECChecker:
    def __init__(self, headless: bool = True):
        self.headless = headless
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None

        self.datos = {
            "nombre_tramite": None,
            "fechas": [],
            "etapa_id": None
        }

        self.estado = cargar_estado()

    # -------------------------
    # Ciclo de vida
    # -------------------------
    def _ipv4_resolver_rules(self) -> str:
        """
        Forzar resolución IPv4 para los hosts clave.
        WSL2 no tiene ruta IPv6, pero el DNS devuelve registros AAAA; cuando
        Chromium intenta IPv6 en un POST SAML, la conexión se cuelga y termina
        en ERR_CONNECTION_RESET / ERR_TIMED_OUT. Mapear cada host a su IPv4
        evita el intento IPv6 por completo.
        """
        hosts = [
            "bpmgob.mec.gub.uy",
            "auth.iduruguay.gub.uy",
            "mi.iduruguay.gub.uy",
        ]
        rules = []
        for host in hosts:
            try:
                ip = socket.getaddrinfo(host, 443, socket.AF_INET)[0][4][0]
                rules.append(f"MAP {host} {ip}")
            except OSError as e:
                logging.warning(f"No se pudo resolver IPv4 de {host}: {e}")
        return ", ".join(rules)

    def start(self):
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(
            headless=self.headless,
            args=[f"--host-resolver-rules={self._ipv4_resolver_rules()}"]
        )

        self.context = self.browser.new_context(
            storage_state=STORAGE_STATE_FILE
            if os.path.exists(STORAGE_STATE_FILE)
            else None,
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
            locale="es-UY",
            timezone_id="America/Montevideo",
            ignore_https_errors=True
        )

        self.page = self.context.new_page()
        
        # Depuración: Log de errores de red
        self.page.on("requestfailed", self._on_request_failed)
        
        self._setup_interceptors()

    def _on_request_failed(self, request):
        # Ruido benigno: Google Analytics/GTM se abortan en cada navegación.
        # Filtrarlo deja ver los errores reales de la red (SAML, MEC).
        if "google-analytics.com" in request.url or "googletagmanager.com" in request.url:
            return
        logging.warning(f"❌ Error de red: {request.url} - {request.failure}")

    def close(self):
        self.context.storage_state(path=STORAGE_STATE_FILE)
        self.browser.close()
        self.playwright.stop()

    # -------------------------
    # Interceptores. Aquí se capturan las respuestas de las APIs
    # -------------------------
    def _setup_interceptors(self):
        def on_response(response):
            try:
                if "agenda_sae_api_disponibilidades" in response.url:
                    data = response.json()
                    for bloque in data.get("disponibilidades", []):
                        self.datos["fechas"].extend(bloque.keys())
            except Exception:
                pass

        self.page.on("response", on_response)

    # -------------------------
    # Login
    # -------------------------
    def esta_logueado(self) -> bool:
        try:
            menu = self.page.locator("#userMenu")
            if menu.count() == 0:
                return False

            texto = menu.inner_text().lower()
            if "iniciar" in texto:
                return False

            return True
        except Exception:
            return False

    def _safe_goto(self, url: str, wait_until: str = "domcontentloaded", timeout: int = 30000, retries: int = 3,
                   backoff: float = 1.5):
        """
        Ir a una URL con reintentos cuando Playwright lanza TimeoutError u otros errores transitorios.
        """
        last_exc = None
        for attempt in range(1, retries + 1):
            try:
                logging.info(f"Navegando a {url} (intento {attempt}/{retries}, timeout={timeout}ms)")
                self.page.goto(url, wait_until=wait_until, timeout=timeout)
                return
            except PlaywrightError as e:
                last_exc = e
                logging.warning(f"Navegación fallida en intento {attempt}: {e}")
                if attempt < retries:
                    sleep_time = backoff * attempt
                    logging.info(f"Esperando {sleep_time}s antes de reintentar...")
                    time.sleep(sleep_time)
        # si llegamos aquí, no hubo éxito
        logging.error(f"No se pudo navegar a {url} después de {retries} intentos")
        raise last_exc

    def ensure_login(self):
        logging.info("🔎 Verificando sesión...")

        # Intentar con un timeout mayor y reintentos
        try:
            self._safe_goto(
                "https://bpmgob.mec.gub.uy/",
                wait_until="domcontentloaded",
                timeout=15000,
                retries=3,
                backoff=2
            )
        except Exception as e:
            logging.error(f"Error al cargar la página principal: {e}")
            raise

        if self.esta_logueado():
            logging.info("✅ Sesión válida")
            return

        logging.info("🔐 Sesión no válida, iniciando login vía SAML...")

        # El handshake SAML (bpmgob -> IdUruguay) falla de forma intermitente a
        # nivel TCP (ERR_CONNECTION_RESET / ERR_TIMED_OUT), indistintamente de
        # IPv4/IPv6. Cada vuelta re-navega a login_saml para reiniciar el handshake
        # y espera la redirección a IdUruguay; es un reintento ACOTADO, no infinito.
        for attempt in range(1, LOGIN_MAX_HANDSHAKES + 1):
            logging.info(f"Handshake SAML intento {attempt}/{LOGIN_MAX_HANDSHAKES}")

            try:
                self._safe_goto(
                    "https://bpmgob.mec.gub.uy/autenticacion/login_saml",
                    wait_until="commit",
                    timeout=30000,
                    retries=1
                )
            except PlaywrightError as e:
                logging.warning(f"Navegación a login_saml falló (intento {attempt}): {e}")
                continue

            if self.esta_logueado():
                logging.info("✅ Sesión válida")
                return

            llegue_a_iduruguay = False
            try:
                self.page.wait_for_url("**iduruguay.gub.uy/**", timeout=25000)
                llegue_a_iduruguay = True
            except PlaywrightError:
                logging.warning(
                    f"Redirección a IdUruguay no completada (intento {attempt}); reintentando..."
                )

            if not llegue_a_iduruguay:
                continue

            try:
                self._login_formulario_iduruguay()
            except PlaywrightError as e:
                logging.warning(f"Flujo de login interactivo falló (intento {attempt}): {e}")
                continue

            if self.esta_logueado():
                logging.info("✅ Login completado con éxito")
                return

            logging.warning(
                f"No se verificó sesión tras el formulario (intento {attempt}); reintentando..."
            )

        raise RuntimeError("❌ Falló el inicio de sesión: no se pudo verificar la sesión activa tras el flujo de login")

    def _login_formulario_iduruguay(self):
        """Completa el formulario de login en mi.iduruguay.gub.uy y espera el retorno al MEC."""
        if self.page.locator("button[aria-label='Usuario Gub.uy']").count() > 0:
            self.page.click("button[aria-label='Usuario Gub.uy']")

        self.page.wait_for_selector(
            "a[aria-label='No tengo documento uruguayo']", timeout=20000
        )
        self.page.click("a[aria-label='No tengo documento uruguayo']")
        self.page.wait_for_selector("select#pais_emisor", timeout=10000)
        self.page.select_option("select#pais_emisor", "Cuba")
        self.page.select_option("select#tipo_documento", "Pasaporte")

        mec_credentials = get_mec_credentials()
        self.page.fill("input#username", mec_credentials["username"])
        self.page.click("button[type='submit']")

        self.page.wait_for_selector("input#password", timeout=10000)
        self.page.fill("input#password", mec_credentials["password"])
        self.page.click("button[type='submit']")

        # Esperar retorno al MEC
        try:
            self.page.wait_for_url("**bpmgob.mec.gub.uy/**", timeout=60000)
        except PlaywrightError:
            logging.warning("Timeout esperando retorno al MEC")

    # -------------------------
    # Lógica principal
    # -------------------------
    def check_tramite(self, etapa_id: int):
        logging.info("📅 Comprobando disponibilidades del trámite...")

        # Reset datos for each tramite
        self.datos = {
            "nombre_tramite": None,
            "fechas": [],
            "etapa_id": etapa_id
        }

        self._safe_goto(
            f"https://bpmgob.mec.gub.uy/etapas/ejecutar/{etapa_id}/0",
            wait_until="domcontentloaded",
            timeout=15000
        )

        # Si fuimos redirigidos fuera de la página de la etapa por sesión expirada
        if "autenticacion/login" in self.page.url or "iduruguay.gub.uy" in self.page.url or "tramites/participados" in self.page.url:
            logging.warning("Sesión expirada detectada al intentar acceder al trámite. Reintentando login...")
            if os.path.exists(STORAGE_STATE_FILE):
                os.remove(STORAGE_STATE_FILE)
            self.ensure_login()
            self._safe_goto(
                f"https://bpmgob.mec.gub.uy/etapas/ejecutar/{etapa_id}/0",
                wait_until="domcontentloaded",
                timeout=15000
            )

        # Extraer nombre del trámite desde el DOM con wait_for_selector adecuado
        self.page.wait_for_selector("#main > div > div > div.span9.contenido-publico > h1", timeout=10000)
        self.datos["nombre_tramite"] = self.page.locator(
            "#main > div > div > div.span9.contenido-publico > h1"
        ).inner_text().strip()

        # Obtener la pregunta de seguridad
        self.page.wait_for_selector("div.controls > input[type='text']~label", timeout=2000)
        pregunta = self.page.locator("div.controls > input[type='text']~label").inner_text()
        logging.info(f"❓ Pregunta de seguridad: {pregunta}")

        # Integrar agente IA para responder la pregunta de seguridad
        agent_model = get_agent_model()
        agent_response = consultar_agente_ia_groq(pregunta, agent_model)
        logging.info(f"🤖 Respuesta del agente: {agent_response}")

        self.page.fill("div.controls > input[name='pregunta']", agent_response)
        self.page.click("button#btn_siguiente_ciudadano[type='submit']", timeout=2000)

        self.page.click("div.radio input[type='radio']")
        # Esperar a que el JS haga sus llamadas para obtener las disponibilidades
        self.page.wait_for_timeout(2000)

        return self.datos

    def process_results(self):
        nombre_tramite = self.datos["nombre_tramite"] or "Trámite desconocido"

        if not self.datos["fechas"]:
            logging.info("❌ No hay cupos disponibles para trámite: " + nombre_tramite)
            return

        self.datos["fechas"].sort()
        fecha = self.datos["fechas"][0]
        fecha_fmt = f"{fecha[6:8]}/{fecha[4:6]}/{fecha[0:4]}"

        if fecha == self.estado.get("ultima_fecha_notificada"):
            logging.info("ℹ️ Cupos ya notificados anteriormente")
            return

        message = (
            f"✅ *Cupos disponibles*\n\n"
            f"📄 Trámite: *{nombre_tramite}*\n"
            f"📅 Fecha más próxima: *{fecha_fmt}*\n\n"
            f"Ingresá al sistema para reservar."
        )

        send_notification_message(message)
        data = {"nombre_tramite": nombre_tramite, "fecha": fecha_fmt}
        guardar_estado(data)
        logging.info("📣 Notificación enviada")
