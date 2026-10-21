"""builds the zip file that aws lambda needs

the libraries are installed for linux, the lambda runtime runs on amazon
linux and the wheels in the venv here are for windows
"""

import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BUILD_DIR = ROOT / "build" / "lambda"
ZIP_PATH = ROOT / "build" / "lambda.zip"
REQUIREMENTS = ROOT / "infra" / "lambda" / "requirements.txt"

PLATFORM = "manylinux2014_x86_64"
PYTHON_VERSION = "3.13"
ABI = "cp313"


def install_libraries() -> None:
    subprocess.run(
        [
            sys.executable,
            "-m",
            "pip",
            "install",
            "--requirement",
            str(REQUIREMENTS),
            "--target",
            str(BUILD_DIR),
            "--platform",
            PLATFORM,
            "--python-version",
            PYTHON_VERSION,
            "--implementation",
            "cp",
            "--abi",
            ABI,
            "--only-binary=:all:",
            "--no-warn-script-location",
            "--quiet",
        ],
        check=True,
    )


def copy_app() -> None:
    shutil.copytree(
        ROOT / "app",
        BUILD_DIR / "app",
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
        dirs_exist_ok=True,
    )


def make_zip() -> None:
    with zipfile.ZipFile(ZIP_PATH, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(BUILD_DIR.rglob("*")):
            if path.is_file():
                archive.write(path, path.relative_to(BUILD_DIR))


def main() -> None:
    if BUILD_DIR.exists():
        shutil.rmtree(BUILD_DIR)
    BUILD_DIR.mkdir(parents=True)

    install_libraries()
    copy_app()
    make_zip()

    size = ZIP_PATH.stat().st_size / 1024 / 1024
    print(f"the zip is ready at {ZIP_PATH} ({size:.1f} mb)")


if __name__ == "__main__":
    main()
