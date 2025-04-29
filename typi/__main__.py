import os
import argparse
import platformdirs
import tomllib
import shutil


def check_package(path: str) -> str | None:
    if os.path.exists(path):
        if not os.path.exists(os.path.join(path, "typst.toml")):
            return None
        else:
            with open(os.path.join(path, "typst.toml"), "rb") as f:
                config = tomllib.load(f)
                f.close()
            version = config["package"]["version"]
            return version
    return None


def install_package(local_path: str, path: str, version: str):
    name = os.path.split(path.strip(os.sep))[-1]
    if not os.path.exists(os.path.join(local_path, name, version)):
        os.makedirs(os.path.join(local_path, name, version))
    shutil.copytree(
        path,
        os.path.join(local_path, name, version),
        ignore=shutil.ignore_patterns(".gitignore", ".git", "*.pdf"),
        dirs_exist_ok=True,
    )
    print("Installed package '{}:{}'".format(name, version))


def main():
    data_dir = platformdirs.user_data_dir()
    local_path = os.path.join(data_dir, "typst", "packages", "local")
    if not os.path.exists(os.path.join(data_dir, "typst")):
        os.makedirs(local_path)

    parser = argparse.ArgumentParser(
        prog="typi", description="Minimalistic Typst local package installer."
    )
    parser.add_argument("path", help="Path to the package source")
    args = parser.parse_args()

    version = check_package(args.path)
    if version is None:
        parser.error("provided path does not contain 'typst.toml' file")

    install_package(local_path, args.path, version)
