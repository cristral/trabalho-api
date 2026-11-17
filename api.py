import json
import os
import tempfile
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit


ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
DATA_FILE = DATA_DIR / "personagens.json"
PORT = int(os.environ.get("PORT", "3000"))
FIELDS = (
    "nome",
    "classe",
    "nivel",
    "pontos_vida",
    "forca",
    "destreza",
    "constituicao",
    "inteligencia",
    "sabedoria",
    "carisma",
)
STAT_FIELDS = (
    "forca",
    "destreza",
    "constituicao",
    "inteligencia",
    "sabedoria",
    "carisma",
)
data_lock = threading.Lock()


def load_characters():
    if not DATA_FILE.exists():
        return []
    with DATA_FILE.open(encoding="utf-8") as file:
        characters = json.load(file)
    if not isinstance(characters, list):
        raise ValueError("O arquivo de personagens precisa conter uma lista.")
    return characters


def save_characters(characters):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    temporary_path = None
    try:
        with tempfile.NamedTemporaryFile(
            "w", encoding="utf-8", dir=DATA_DIR, delete=False
        ) as file:
            temporary_path = Path(file.name)
            json.dump(characters, file, ensure_ascii=False, indent=2)
            file.write("\n")
        os.replace(temporary_path, DATA_FILE)
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()


def validate_character(payload):
    if not isinstance(payload, dict):
        raise ValueError("Envie os dados do personagem em formato JSON.")

    character = {}
    for field in ("nome", "classe"):
        value = payload.get(field)
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"O campo '{field}' é obrigatório.")
        if len(value.strip()) > 60:
            raise ValueError(f"O campo '{field}' deve ter no máximo 60 caracteres.")
        character[field] = value.strip()

    for field in ("nivel", "pontos_vida", *STAT_FIELDS):
        value = payload.get(field)
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError(f"O campo '{field}' deve ser um número inteiro.")
        minimum, maximum = (1, 999) if field in ("nivel", "pontos_vida") else (0, 30)
        if not minimum <= value <= maximum:
            raise ValueError(
                f"O campo '{field}' deve estar entre {minimum} e {maximum}."
            )
        character[field] = value
    return character


class ApiHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def send_cors_headers(self):
        origin = self.headers.get("Origin")
        if origin:
            parsed_origin = urlsplit(origin)
            if (
                parsed_origin.scheme == "http"
                and parsed_origin.hostname in {"localhost", "127.0.0.1"}
                and parsed_origin.username is None
                and parsed_origin.password is None
            ):
                self.send_header("Access-Control-Allow-Origin", origin)
                self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
                self.send_header("Access-Control-Allow-Headers", "Content-Type")
                self.send_header("Vary", "Origin")

    def send_json(self, status, payload):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_cors_headers()
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        if self.route() is False:
            self.send_json(404, {"error": "Rota não encontrada."})
            return
        self.send_response(204)
        self.send_cors_headers()
        self.end_headers()

    def read_payload(self):
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError as error:
            raise ValueError("Cabeçalho Content-Length inválido.") from error
        if length <= 0 or length > 1_000_000:
            raise ValueError("O corpo da requisição está vazio ou é muito grande.")
        try:
            return json.loads(self.rfile.read(length))
        except (json.JSONDecodeError, UnicodeDecodeError) as error:
            raise ValueError("O corpo da requisição precisa ser um JSON válido.") from error

    def route(self):
        path = unquote(urlsplit(self.path).path)
        if path == "/personagens":
            return None
        if path.startswith("/personagens/"):
            character_id = path.removeprefix("/personagens/")
            if not character_id or "/" in character_id:
                return False
            return character_id
        return False

    def do_GET(self):
        route = self.route()
        if route is False:
            return super().do_GET()
        try:
            with data_lock:
                characters = load_characters()
            if route is None:
                self.send_json(200, {"data": characters})
                return
            character = next(
                (item for item in characters if str(item.get("id")) == route), None
            )
            if character is None:
                self.send_json(404, {"error": "Personagem não encontrado."})
                return
            self.send_json(200, {"data": character})
        except (OSError, ValueError, json.JSONDecodeError) as error:
            self.send_json(500, {"error": f"Não foi possível carregar personagens: {error}"})

    def do_POST(self):
        if self.route() is not None:
            self.send_json(404, {"error": "Rota não encontrada."})
            return
        try:
            character = validate_character(self.read_payload())
        except ValueError as error:
            self.send_json(400, {"error": str(error)})
            return
        try:
            with data_lock:
                characters = load_characters()
                next_id = max((item.get("id", 0) for item in characters), default=0) + 1
                character["id"] = next_id
                characters.append(character)
                save_characters(characters)
            self.send_json(201, {"data": character})
        except (OSError, ValueError, json.JSONDecodeError) as error:
            self.send_json(500, {"error": f"Não foi possível salvar personagem: {error}"})

    def do_PUT(self):
        route = self.route()
        if not isinstance(route, str):
            self.send_json(404, {"error": "Rota não encontrada."})
            return
        try:
            character = validate_character(self.read_payload())
        except ValueError as error:
            self.send_json(400, {"error": str(error)})
            return
        try:
            with data_lock:
                characters = load_characters()
                existing = next(
                    (item for item in characters if str(item.get("id")) == route), None
                )
                if existing is None:
                    self.send_json(404, {"error": "Personagem não encontrado."})
                    return
                character["id"] = existing["id"]
                characters[characters.index(existing)] = character
                save_characters(characters)
            self.send_json(200, {"data": character})
        except (OSError, ValueError, json.JSONDecodeError) as error:
            self.send_json(500, {"error": f"Não foi possível atualizar personagem: {error}"})

    def do_DELETE(self):
        route = self.route()
        if not isinstance(route, str):
            self.send_json(404, {"error": "Rota não encontrada."})
            return
        try:
            with data_lock:
                characters = load_characters()
                remaining = [
                    item for item in characters if str(item.get("id")) != route
                ]
                if len(remaining) == len(characters):
                    self.send_json(404, {"error": "Personagem não encontrado."})
                    return
                save_characters(remaining)
            self.send_json(200, {"message": "Personagem removido com sucesso."})
        except (OSError, ValueError, json.JSONDecodeError) as error:
            self.send_json(500, {"error": f"Não foi possível excluir personagem: {error}"})


if __name__ == "__main__":
    server = ThreadingHTTPServer(("127.0.0.1", PORT), ApiHandler)
    print(f"Grimório disponível em http://localhost:{PORT}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServidor encerrado.")
    finally:
        server.server_close()
