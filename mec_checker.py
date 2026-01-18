import logging
import os
import time

from playwright.sync_api import sync_playwright, Error as PlaywrightError

from ai_agent import consultar_agente_ia_groq
from notifier import send_telegram
from utils import cargar_estado, guardar_estado

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")


class MECChecker:
    def __init__(self, headless: bool = True):
        self.headless = headless
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None

        self.datos = {
            "nombre_tramite": None,
            "fechas": []
        }

        self.estado = cargar_estado()

    # -------------------------
    # Ciclo de vida
    # -------------------------
    def start(self):
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(headless=self.headless)

        self.context = self.browser.new_context(
            storage_state="storage_state.json"
            if os.path.exists("storage_state.json")
            else None
        )

        self.page = self.context.new_page()
        self._setup_interceptors()

    def close(self):
        self.context.storage_state(path="storage_state.json")
        self.browser.close()
        self.playwright.stop()

    # -------------------------
    # Interceptores. Aquí se capturan las respuestas de las APIs
    # -------------------------
    def _setup_interceptors(self):
        def on_response(response):
            try:
                if "agenda_sae_api_recursos" in response.url:
                    data = response.json()
                    recursos = data.get("recursos", [])
                    if recursos and not self.datos["nombre_tramite"]:
                        self.datos["nombre_tramite"] = recursos[0].get("nombre")

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

    def _safe_goto(self, url: str, wait_until: str = "networkidle", timeout: int = 30000, retries: int = 3,
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
                wait_until="networkidle",
                timeout=10000,
                retries=3,
                backoff=2
            )
        except Exception as e:
            logging.error(f"Error al cargar la página principal: {e}")
            raise

        if self.esta_logueado():
            logging.info("✅ Sesión válida")
            return

        logging.info("🔐 Sesión no válida, esperando login automático...")
        # Ir a la página de login con reintentos
        try:
            self._safe_goto(
                "https://bpmgob.mec.gub.uy/autenticacion/login",
                wait_until="networkidle",
                timeout=60000,
                retries=3,
                backoff=2
            )
        except Exception as e:
            logging.error(f"Error al cargar la página de login: {e}")
            raise

        if self.esta_logueado():
            logging.info("✅ Sesión válida")
            return

        logging.info("Esperando redirección al proveedor de identidad...")
        try:
            # Esperar redirección a iduruguay
            self.page.wait_for_url("**iduruguay.gub.uy/**", timeout=5000)
        except PlaywrightError:
            logging.warning("Timeout esperando redirección a iduruguay; continuando de todos modos")

        try:
            self.page.click("button[aria-label='Usuario Gub.uy']")
            self.page.wait_for_selector(
                "a[aria-label='No tengo documento uruguayo']", timeout=5000
            )
            self.page.click("a[aria-label='No tengo documento uruguayo']")
            self.page.wait_for_selector("select#pais_emisor", timeout=2000)
            self.page.select_option("select#pais_emisor", "Cuba")
            self.page.select_option("select#tipo_documento", "Pasaporte")

            self.page.fill("input#username", os.getenv("MEC_USER"))
            self.page.click("button[type='submit']")

            self.page.wait_for_selector("input#password", timeout=2000)
            self.page.fill("input#password", os.getenv("MEC_PASSWORD"))
            self.page.click("button[type='submit']")

            # Esperar retorno al MEC
            try:
                self.page.wait_for_url("**bpmgob.mec.gub.uy/**", timeout=120000)
            except PlaywrightError:
                logging.warning("Timeout esperando retorno al MEC; continuando de todos modos")

        except PlaywrightError as e:
            logging.error(f"Error durante el flujo de login interactivo: {e}")
            raise

        logging.info("✅ Login completado")

    # -------------------------
    # Lógica principal
    # -------------------------
    def check_tramite(self, etapa_id: int):
        logging.info("📅 Comprobando disponibilidades del trámite...")

        # Reset datos for each tramite
        self.datos = {
            "nombre_tramite": None,
            "fechas": []
        }

        self.page.goto(
            f"https://bpmgob.mec.gub.uy/etapas/ejecutar/{etapa_id}/0",
            wait_until="networkidle",
            timeout=8000
        )

        # Obtener la pregunta de seguridad
        self.page.wait_for_selector("div.controls > input[type='text']~label", timeout=2000)
        pregunta = self.page.locator("div.controls > input[type='text']~label").inner_text()
        logging.info(f"❓ Pregunta de seguridad: {pregunta}")

        # Integrar agente IA para responder la pregunta de seguridad
        agent_response = consultar_agente_ia_groq(pregunta)
        logging.info(f"🤖 Respuesta del agente: {agent_response}")

        self.page.fill("div.controls > input[name='pregunta']", agent_response)
        self.page.click("button#btn_siguiente_ciudadano[type='submit']", timeout=2000)

        self.page.click("div.radio input[type='radio']")
        # Esperar a que el JS haga sus llamadas para obtener las disponibilidades
        self.page.wait_for_timeout(2000)

        return self.datos

    def process_results(self):
        if not self.datos["fechas"]:
            logging.info("❌ No hay cupos disponibles")
            return

        print(self.datos)
        tramite = self.datos["nombre_tramite"][0] | self.datos["tramite"][0] | self.datos["tramite_id"][0]
        self.datos["fechas"].sort()
        fecha = self.datos["fechas"][0]
        fecha_fmt = f"{fecha[6:8]}/{fecha[4:6]}/{fecha[0:4]}"

        data = {"tramite": tramite, "fecha": fecha_fmt}

        if fecha == self.estado.get("ultima_fecha_notificada"):
            logging.info("ℹ️ Cupos ya notificados anteriormente")
            return

        mensaje = (
            f"✅ *Cupos disponibles*\n\n"
            f"📄 Trámite: *{tramite}*\n"
            f"📅 Fecha más próxima: *{fecha_fmt}*\n\n"
            f"Ingresá al sistema para reservar."
        )

        send_telegram(
            os.getenv("TELEGRAM_BOT_TOKEN"),
            os.getenv("TELEGRAM_CHAT_ID"),
            mensaje
        )

        guardar_estado(data)
        logging.info("📣 Notificación enviada")
