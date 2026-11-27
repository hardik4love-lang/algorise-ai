from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parent
SRC_DIR = ROOT / "guardian_angel_extension"
PKG_DIR = ROOT / "engine" / "packages"
PKG_DIR.mkdir(parents=True, exist_ok=True)
ZIP_PATH = PKG_DIR / "guardian_angel_extension_v3.2.0.zip"

with zipfile.ZipFile(ZIP_PATH, "w", zipfile.ZIP_DEFLATED) as zf:
    for p in sorted(SRC_DIR.rglob("*")):
        if p.is_file():
            zf.write(p, arcname=str(p.relative_to(SRC_DIR)))
            print(f"Added: {p.relative_to(SRC_DIR)}")

print(f"Created {ZIP_PATH} ({ZIP_PATH.stat().st_size} bytes)")
