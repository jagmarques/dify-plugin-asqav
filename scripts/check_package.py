"""Check the distributable against the source files it must carry."""
from pathlib import Path
import argparse
import zipfile


def check_package(package: Path, root: Path) -> None:
    required = ["LICENSE", "README.md", "PRIVACY.md", "manifest.yaml", "requirements.txt", "main.py"]
    required.extend(str(path.relative_to(root)) for folder in ("tools", "provider", "_assets")
                    for path in (root / folder).glob("*") if path.is_file())
    with zipfile.ZipFile(package) as archive:
        for name in required:
            if archive.read(name) != (root / name).read_bytes():
                raise ValueError(f"Packaged {name} differs from source")
    print(f"Package contains {len(required)} required source files, including LICENSE")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("package", type=Path)
    arguments = parser.parse_args()
    try:
        check_package(arguments.package, Path(__file__).resolve().parents[1])
    except (OSError, KeyError, ValueError, zipfile.BadZipFile) as error:
        parser.error(str(error))
