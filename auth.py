import json
from pathlib import Path

import requests
from playwright.sync_api import sync_playwright

LOGIN_URL = "https://bpmgob.mec.gub.uy/autenticacion/login"
COOKIES_FILE = "cookies.json"


def obtener_cookies(usuario: str, password: str):
    SUBMIT_BUTTON = "button[type='submit']"

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        page.goto(LOGIN_URL)
        page.wait_for_url("**iduruguay.gub.uy/**", timeout=10000)

        page.click("button[aria-label='Usuario Gub.uy']")
        page.wait_for_selector(
            "a[aria-label='No tengo documento uruguayo']", timeout=5000
        )
        page.click("a[aria-label='No tengo documento uruguayo']")
        page.wait_for_selector("select#pais_emisor", timeout=2000)
        page.select_option("select#pais_emisor", "Cuba")
        page.select_option("select#tipo_documento", "Pasaporte")

        page.fill("input#username", usuario)
        page.click(SUBMIT_BUTTON)

        page.wait_for_selector("input#password", timeout=2000)
        page.fill("input#password", password)
        page.click(SUBMIT_BUTTON)

        # Esperar retorno al MEC
        page.wait_for_url("**bpmgob.mec.gub.uy/**", timeout=10000)

        cookies = context.cookies()
        with open(COOKIES_FILE, "w") as f:
            json.dump(cookies, f, indent=2)

        print("✅ Cookies guardadas correctamente")
        browser.close()
        return cookies


def session_con_cookies(cookies):
    session = requests.Session()
    for c in cookies:
        session.cookies.set(c["name"], c["value"], domain=c["domain"], path=c["path"])
    return session


def cargar_cookies(user: str, password: str):
    if not Path(COOKIES_FILE).exists():
        return obtener_cookies(user, password)

    try:
        cookies = json.loads(Path(COOKIES_FILE).read_text())
        if not cookies or not isinstance(cookies, list):
            return obtener_cookies(user, password)

        return cookies
    except json.JSONDecodeError:
        return None
