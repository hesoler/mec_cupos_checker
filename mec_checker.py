import logging
import os

from playwright.sync_api import sync_playwright

from notifier import enviar_telegram
from utils import cargar_estado, guardar_estado

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")


class MECChecker:
    def __init__(self, etapa_id: int, headless: bool = True):
        self.etapa_id = etapa_id
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

    def ensure_login(self):
        logging.info("🔎 Verificando sesión...")

        self.page.goto(
            "https://bpmgob.mec.gub.uy/",
            wait_until="networkidle"
        )

        if self.esta_logueado():
            logging.info("✅ Sesión válida")
            return

        logging.info("🔐 Sesión no válida, esperando login automático...")
        self.page.goto("https://bpmgob.mec.gub.uy/autenticacion/login")

        self.page.wait_for_function(
            "() => document.querySelector('#userMenu') && "
            "!document.querySelector('#userMenu').innerText.toLowerCase().includes('iniciar')",
            timeout=0
        )

        if self.esta_logueado():
            logging.info("✅ Sesión válida")
            return

        self.page.wait_for_url("**iduruguay.gub.uy/**", timeout=0)

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
        self.page.wait_for_url("**bpmgob.mec.gub.uy/**", timeout=0)

        logging.info("✅ Login completado")

    # -------------------------
    # Lógica principal
    # -------------------------
    def check_tramite(self):
        logging.info("📅 Comprobando disponibilidades del trámite...")

        self.page.goto(
            f"https://bpmgob.mec.gub.uy/etapas/ejecutar/{self.etapa_id}/0",
            wait_until="networkidle",
            timeout=0
        )

        self.page.wait_for_selector("div.controls > input[type='text']~label", timeout=2000)
        self.page.pause()
        # self.page.wait_for_selector("div.controls > input[name='pregunta']")

        self.page.goto(
            f"https://bpmgob.mec.gub.uy/etapas/ejecutar/{self.etapa_id}/1",
            wait_until="networkidle",
            timeout=0
        )

        # Esperar a que el JS haga sus llamadas
        self.page.wait_for_timeout(5000)

        return self.datos

    def process_results(self):
        if not self.datos["fechas"]:
            logging.info("❌ No hay cupos disponibles")
            return

        self.datos["fechas"].sort()
        fecha = self.datos["fechas"][0]
        fecha_fmt = f"{fecha[6:8]}/{fecha[4:6]}/{fecha[0:4]}"

        if fecha == self.estado.get("ultima_fecha_notificada"):
            logging.info("ℹ️ Cupos ya notificados anteriormente")
            return

        mensaje = (
            f"✅ *Cupos disponibles*\n\n"
            f"📄 Trámite: *{self.datos['nombre_tramite']}*\n"
            f"📅 Fecha más próxima: *{fecha_fmt}*\n\n"
            f"Ingresá al sistema para reservar."
        )

        enviar_telegram(
            os.getenv("TELEGRAM_BOT_TOKEN"),
            os.getenv("TELEGRAM_CHAT_ID"),
            mensaje
        )

        guardar_estado(fecha)
        logging.info("📣 Notificación enviada")
