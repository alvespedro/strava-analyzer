import os
import time
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs

import requests
from dotenv import load_dotenv

from infra.cache_repository import CacheRepository

load_dotenv()

AUTH_URL = "https://www.strava.com/oauth/authorize"
TOKEN_URL = "https://www.strava.com/oauth/token"
REDIRECT_PORT = 8080
REDIRECT_URI = f"http://localhost:{REDIRECT_PORT}/callback"
SCOPES = "activity:read_all"

_auth_code: str | None = None


class _CallbackHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        global _auth_code
        params = parse_qs(urlparse(self.path).query)
        if "code" in params:
            _auth_code = params["code"][0]
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"<h2>Autenticado com sucesso! Pode fechar esta aba.</h2>")
        else:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b"<h2>Erro: code nao encontrado na URL.</h2>")

    def log_message(self, *args):
        pass


def _run_callback_server() -> HTTPServer:
    server = HTTPServer(("localhost", REDIRECT_PORT), _CallbackHandler)
    thread = threading.Thread(target=server.handle_request)
    thread.daemon = True
    thread.start()
    return server


def _exchange_code(client_id: str, client_secret: str, code: str) -> dict:
    resp = requests.post(TOKEN_URL, data={
        "client_id": client_id,
        "client_secret": client_secret,
        "code": code,
        "grant_type": "authorization_code",
    })
    resp.raise_for_status()
    return resp.json()


def _refresh_token(client_id: str, client_secret: str, refresh_token: str) -> dict:
    resp = requests.post(TOKEN_URL, data={
        "client_id": client_id,
        "client_secret": client_secret,
        "refresh_token": refresh_token,
        "grant_type": "refresh_token",
    })
    resp.raise_for_status()
    return resp.json()


def get_valid_token(cache: CacheRepository) -> str:
    client_id = os.environ["STRAVA_CLIENT_ID"]
    client_secret = os.environ["STRAVA_CLIENT_SECRET"]

    token_data = cache.load_token()

    if token_data and token_data["expires_at"] > time.time() + 60:
        return token_data["access_token"]

    if token_data and token_data.get("refresh_token"):
        print("Token expirado — renovando automaticamente...")
        new_data = _refresh_token(client_id, client_secret, token_data["refresh_token"])
        cache.save_token(new_data)
        return new_data["access_token"]

    print("Primeira autenticação — abrindo navegador para autorizar o Strava...")
    _run_callback_server()

    auth_url = (
        f"{AUTH_URL}?client_id={client_id}"
        f"&redirect_uri={REDIRECT_URI}"
        f"&response_type=code"
        f"&scope={SCOPES}"
    )
    webbrowser.open(auth_url)

    print("Aguardando autorização no navegador...")
    timeout = 120
    elapsed = 0
    while _auth_code is None and elapsed < timeout:
        time.sleep(1)
        elapsed += 1

    if _auth_code is None:
        raise TimeoutError("Autenticação não completada em 2 minutos. Tente novamente.")

    token_data = _exchange_code(client_id, client_secret, _auth_code)
    cache.save_token(token_data)
    print("Autenticado com sucesso!")
    return token_data["access_token"]
