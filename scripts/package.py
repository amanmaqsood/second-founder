"""Build the public skill ZIP for Claude uploads and manual installation."""
import hashlib
from pathlib import Path
import zipfile

from validate import ROOT, SKILL_DIRECTORY, validate_repository


def main():
    errors = validate_repository(ROOT)
    if errors:
        raise SystemExit("Package validation failed:\n" + "\n".join(errors))
    source = ROOT / SKILL_DIRECTORY
    destination = ROOT / "dist" / "second-founder.zip"
    destination.parent.mkdir(exist_ok=True)
    files = sorted(p for p in source.rglob("*") if p.is_file()
                   and "__pycache__" not in p.parts and p.suffix != ".pyc")
    with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in files:
            archive.write(path, "second-founder/" + path.relative_to(source).as_posix())
    digest = hashlib.sha256(destination.read_bytes()).hexdigest()
    checksum = destination.with_suffix(".zip.sha256")
    checksum.write_text(f"{digest}  {destination.name}\n", encoding="utf-8")
    print(f"Built {destination.name}: {len(files)} files; SHA-256 {digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
