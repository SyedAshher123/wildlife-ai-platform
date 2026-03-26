"""Create a small sample folder for front-end batch upload testing."""
from pathlib import Path
import base64


def main() -> None:
    root = Path(__file__).resolve().parent.parent
    out_dir = root / "storage" / "sample_uploads"
    out_dir.mkdir(parents=True, exist_ok=True)

    sample_files = {
        "sample_1.png": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO7Zx7cAAAAASUVORK5CYII=",
        "sample_2.png": "iVBORw0KGgoAAAANSUhEUgAAAAIAAAACCAQAAABFaP0WAAAADElEQVR42mP8z8AARAAA//8D3v7oNwAAAABJRU5ErkJggg==",
    }

    for name, payload in sample_files.items():
        (out_dir / name).write_bytes(base64.b64decode(payload))

    print(f"Sample upload folder ready: {out_dir}")


if __name__ == "__main__":
    main()
