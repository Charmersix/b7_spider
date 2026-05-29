import argparse
import base64
import json
import mimetypes
import os
import subprocess
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse


ROOT_DIR = Path(__file__).resolve().parent
STATIC_DIR = ROOT_DIR / "jjt_gallery"
IMAGES_DIR = ROOT_DIR / "jjt_images"
SUPPORTED_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".gif",
    ".bmp",
    ".webp",
    ".heif",
    ".heic",
}
CONFIG = {
    "static_dir": STATIC_DIR,
    "images_dir": IMAGES_DIR,
    "auth": None,
}


def iter_image_files(folder: Path):
    for path in sorted(folder.rglob("*")):
        if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS:
            yield path


def folder_created_at(folder: Path):
    stat = folder.stat()
    birthtime = getattr(stat, "st_birthtime", None)
    if birthtime is not None:
        return birthtime

    if os.name != "nt":
        try:
            result = subprocess.run(
                ["stat", "--format=%W", str(folder)],
                capture_output=True,
                check=True,
                text=True,
            )
            unix_birthtime = int(result.stdout.strip())
            if unix_birthtime > 0:
                return float(unix_birthtime)
        except (OSError, ValueError, subprocess.CalledProcessError):
            pass

    return stat.st_ctime


def build_index():
    albums = []
    total_images = 0
    images_dir = CONFIG["images_dir"]

    if not images_dir.exists():
        return {
            "albums": [],
            "summary": {
                "albumCount": 0,
                "imageCount": 0,
            },
        }

    for album_dir in sorted((path for path in images_dir.iterdir() if path.is_dir()), key=lambda item: item.name.lower()):
        image_files = list(iter_image_files(album_dir))
        if not image_files:
            continue

        created_at = folder_created_at(album_dir)
        image_files.sort(key=lambda item: item.name, reverse=True)
        images = []
        for image_path in image_files:
            relative_path = image_path.relative_to(images_dir).as_posix()
            images.append(
                {
                    "name": image_path.name,
                    "path": relative_path,
                    "ext": image_path.suffix.lower().lstrip("."),
                    "size": image_path.stat().st_size,
                }
            )

        total_images += len(images)
        albums.append(
            {
                "name": album_dir.name,
                "path": album_dir.relative_to(images_dir).as_posix(),
                "count": len(images),
                "createdAt": created_at,
                "preview": images[0]["path"],
                "images": images,
            }
        )

    albums.sort(key=lambda item: (-item["count"], item["name"].lower()))
    return {
        "albums": albums,
        "summary": {
            "albumCount": len(albums),
            "imageCount": total_images,
        },
    }


def resolve_media_path(raw_path: str):
    images_dir = CONFIG["images_dir"].resolve()
    candidate = (images_dir / raw_path).resolve()
    try:
        candidate.relative_to(images_dir)
    except ValueError:
        return None
    return candidate if candidate.is_file() else None


class GalleryHandler(SimpleHTTPRequestHandler):
    def translate_path(self, path):
        parsed = urlparse(path)
        cleaned = parsed.path.lstrip("/") or "index.html"
        return str((CONFIG["static_dir"] / cleaned).resolve())

    def do_AUTHHEAD(self):
        self.send_response(HTTPStatus.UNAUTHORIZED)
        self.send_header("WWW-Authenticate", 'Basic realm="JJT Gallery"')
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write("Authentication required".encode("utf-8"))

    def check_auth(self):
        auth = CONFIG["auth"]
        if not auth:
            return True

        header = self.headers.get("Authorization", "")
        if not header.startswith("Basic "):
            return False

        try:
            decoded = base64.b64decode(header.split(" ", 1)[1]).decode("utf-8")
        except Exception:
            return False

        username, _, password = decoded.partition(":")
        return username == auth["username"] and password == auth["password"]

    def do_GET(self):
        if not self.check_auth():
            self.do_AUTHHEAD()
            return

        parsed = urlparse(self.path)
        if parsed.path == "/api/albums":
            self.serve_json(build_index())
            return

        if parsed.path == "/media":
            params = parse_qs(parsed.query)
            raw_path = params.get("path", [""])[0]
            media_path = resolve_media_path(raw_path)
            if not media_path:
                self.send_error(HTTPStatus.NOT_FOUND, "Image not found")
                return
            self.serve_file(media_path)
            return

        if parsed.path in {"/", "/index.html"}:
            self.path = "/index.html"
            return super().do_GET()

        static_dir = CONFIG["static_dir"].resolve()
        target = (static_dir / parsed.path.lstrip("/")).resolve()
        try:
            target.relative_to(static_dir)
        except ValueError:
            self.send_error(HTTPStatus.FORBIDDEN, "Forbidden")
            return

        if target.is_file():
            self.path = parsed.path
            return super().do_GET()

        self.send_error(HTTPStatus.NOT_FOUND, "Not found")

    def serve_json(self, payload):
        encoded = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def serve_file(self, file_path: Path):
        content_type, _ = mimetypes.guess_type(str(file_path))
        data = file_path.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type or "application/octet-stream")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(data)


def main():
    parser = argparse.ArgumentParser(description="Serve the local JJT gallery")
    parser.add_argument("--host", default=os.getenv("JJT_GALLERY_HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.getenv("JJT_GALLERY_PORT", "8000")))
    parser.add_argument(
        "--images-dir",
        default=os.getenv("JJT_GALLERY_IMAGES_DIR", str(IMAGES_DIR)),
        help="Directory containing album subfolders",
    )
    parser.add_argument(
        "--static-dir",
        default=os.getenv("JJT_GALLERY_STATIC_DIR", str(STATIC_DIR)),
        help="Directory containing the frontend files",
    )
    parser.add_argument("--username", default=os.getenv("JJT_GALLERY_USERNAME"))
    parser.add_argument("--password", default=os.getenv("JJT_GALLERY_PASSWORD"))
    args = parser.parse_args()

    CONFIG["images_dir"] = Path(args.images_dir).resolve()
    CONFIG["static_dir"] = Path(args.static_dir).resolve()
    if args.username and args.password:
        CONFIG["auth"] = {
            "username": args.username,
            "password": args.password,
        }
    else:
        CONFIG["auth"] = None

    if not CONFIG["static_dir"].exists():
        raise FileNotFoundError(f"Missing static directory: {CONFIG['static_dir']}")

    server = ThreadingHTTPServer((args.host, args.port), GalleryHandler)
    print(f"Serving JJT gallery at http://{args.host}:{args.port}")
    print(f"Images root: {CONFIG['images_dir']}")
    print(f"Static root: {CONFIG['static_dir']}")
    if CONFIG["auth"]:
        print(f"Basic auth enabled for user: {CONFIG['auth']['username']}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
