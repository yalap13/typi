import os
import argparse
from typing import Optional
import platformdirs
import tomllib
import shutil
from pathlib import Path
import subprocess
import tempfile


def check_package(path: Path) -> tuple[Optional[str], Optional[str]]:
    if path.exists():
        subpath = path / "typst.toml"
        if not subpath.exists():
            return None, None
        else:
            with open(subpath, "rb") as f:
                config = tomllib.load(f)
                f.close()
            version = config["package"]["version"]
            name = config["package"]["name"]
            return version, name
    return None, None


def copy_package_files(source: Path, destination: Path) -> None:
    shutil.copytree(
        source,
        destination,
        ignore=shutil.ignore_patterns(".gitignore", ".git", "*.pdf"),
        dirs_exist_ok=True,
    )


def install_package(
    local_path: Path, path: Path, version: str, name: str, update: bool
) -> None:
    package_path = local_path / name
    if not package_path.exists():
        os.makedirs(package_path)
    version_path = package_path / version
    if version_path.exists():
        if not update:
            print(
                "Package '{}:{}' already installed, skipping.\nTo update use '-u' or '--update'.".format(
                    name, version
                )
            )
            return
        copy_package_files(path, version_path)
        print("Updated package '{}:{}'".format(name, version))
        return
    os.makedirs(version_path)
    copy_package_files(path, version_path)
    print("Installed package '{}:{}'".format(name, version))


def clone_repository(url: str, local_path: Path, update: bool) -> None:
    if shutil.which("git") is None:
        raise RuntimeError("Git is not installed, cannot proceed")
    with tempfile.TemporaryDirectory() as temp_dir:
        subprocess.run(
            ["git", "clone", "--depth", "1", url, str(temp_dir)],
            check=True,
        )
        # print(os.listdir(temp_dir))
        version, name = check_package(Path(temp_dir))
        if version is None or name is None:
            raise RuntimeError(
                "git repository is not a valid typst package, does not contain 'typst.toml' file"
            )
        install_package(local_path, Path(temp_dir), version, name, update)


def main() -> None:
    data_dir = platformdirs.user_data_dir()
    local_path = Path(data_dir) / "typst" / "packages" / "local"
    if not local_path.exists():
        os.makedirs(local_path)

    parser = argparse.ArgumentParser(
        prog="typi", description="Minimalistic Typst local package installer."
    )
    parser.add_argument("path", help="Path to the package source", type=str)
    parser.add_argument(
        "-u", "--update", help="Update the specified package", action="store_true"
    )
    args = parser.parse_args()

    if str(args.path).startswith("git+"):
        clone_repository(str(args.path).lstrip("git+"), local_path, args.update)
        return

    version, name = check_package(Path(args.path))
    if version is None or name is None:
        parser.error("provided path does not contain 'typst.toml' file")

    install_package(local_path, args.path, version, name, args.update)
