from fnmatch import fnmatch
from tabulate import tabulate
import os
import argparse
import platformdirs
import tomllib
import shutil
from pathlib import Path
import subprocess
import tempfile
import re


IMPORT_RE = re.compile(r'#import\s+"([^"]+)"')
ASSET_RE = re.compile(r'(image|read)\s*\(\s*"([^"]+)"\s*\)')


def collect_files(entrypoint: Path, package_root: Path) -> set[Path]:
    discovered = set()
    stack = [entrypoint.resolve()]

    while stack:
        current = stack.pop()
        if "@" in str(current):
            continue
        if current in discovered:
            continue
        if not current.exists():
            raise FileNotFoundError(
                f"Missing file: {current.relative_to(package_root)}"
            )
        discovered.add(current)
        if current.suffix != ".typ":
            continue
        text = current.read_text(encoding="utf-8")
        base = current.parent

        for rel in IMPORT_RE.findall(text):
            dep = (base / rel).resolve()
            stack.append(dep)

        for _, rel in ASSET_RE.findall(text):
            asset = (base / rel).resolve()
            if not asset.exists():
                continue
            stack.append(asset)
    return discovered


def apply_excludes(files: set[Path], root: Path, excludes: list[str]) -> set[Path]:
    if not excludes:
        return files
    kept = set()
    for path in files:
        rel = path.relative_to(root).as_posix()
        if any(fnmatch(rel, pat) for pat in excludes):
            continue
        kept.add(path)
    return kept


def check_package(path: Path) -> dict:
    if path.exists():
        subpath = path / "typst.toml"
        if not subpath.exists():
            raise FileNotFoundError("No typst.toml in this directory")
        else:
            with open(subpath, "rb") as f:
                config = tomllib.load(f)
                f.close()
            pkg_config = config.get("package", None)
            if pkg_config is None:
                raise RuntimeError("Not a valid typst.toml")
            return config
    raise FileNotFoundError("Directory does not exist")


def copy_package_files(files: set[Path], package_root: Path, target_root: Path) -> None:
    for src in files:
        rel = src.relative_to(package_root)
        dst = target_root / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)


def install_package(local_path: Path, package_path: Path, update: bool) -> None:
    config = check_package(package_path)
    pkg_config = config["package"]
    template_config = config.get("template", None)
    version_subpath = local_path / pkg_config["name"] / pkg_config["version"]
    if version_subpath.exists() and not update:
        print(
            "Package '{}:{}' already installed, skipping.\nTo update use '-u' or '--update'.".format(
                pkg_config["name"], pkg_config["version"]
            )
        )
        return
    entrypoint = package_path / pkg_config["entrypoint"]
    excludes = pkg_config.get("exclude", [])
    files = collect_files(entrypoint, package_path)
    files = apply_excludes(files, package_path, excludes)
    files.add((package_path / "typst.toml").resolve())
    readme = package_path / "README.md"
    license_ = package_path / "LICENSE"
    assets = package_path / "assets"
    if readme.exists():
        files.add(readme.resolve())
    if license_.exists():
        files.add(license_.resolve())
    if assets.exists():
        for file in assets.glob("*"):
            files.add(file.resolve())
    if template_config is not None:
        files.add(
            (
                package_path / template_config["path"] / template_config["entrypoint"]
            ).resolve()
        )
    copy_package_files(files, package_path, version_subpath)
    if version_subpath.exists() and update:
        print("Updated package {}:{}".format(pkg_config["name"], pkg_config["version"]))
    else:
        print(
            "Installed package {}:{}".format(pkg_config["name"], pkg_config["version"])
        )


def clone_repository_and_install(url: str, local_path: Path, update: bool) -> None:
    if shutil.which("git") is None:
        raise RuntimeError("Git is not installed, cannot proceed")
    with tempfile.TemporaryDirectory() as temp_dir:
        subprocess.run(
            ["git", "clone", "--depth", "1", url, str(temp_dir)],
            check=True,
        )
        install_package(local_path, Path(temp_dir), update)


def list_installed_packages(local_path: Path) -> None:
    packages = {}
    for pkg in local_path.iterdir():
        packages[pkg.name] = [ver.name for ver in (local_path / pkg).iterdir()]
    out = "-" * 38 + "\n"
    out += "Installed typst packages and versions\n"
    out += "-" * 38 + "\n"
    table_data = []
    for pkg, versions in packages.items():
        table_data.append([pkg, ", ".join(versions)])
    table = tabulate(table_data, tablefmt="plain")
    out += table
    print(out)


def main() -> None:
    data_dir = platformdirs.user_data_dir()
    local_path = Path(data_dir) / "typst" / "packages" / "local"
    if not local_path.exists():
        os.makedirs(local_path)

    parser = argparse.ArgumentParser(
        prog="typi", description="Minimalistic Typst local package installer."
    )
    parser.add_argument(
        "path", help="Path to the package source", type=str, nargs="?", default=""
    )
    parser.add_argument(
        "-u", "--update", help="Update the specified package", action="store_true"
    )
    parser.add_argument(
        "-l", "--list", help="Lists installed packages", action="store_true"
    )
    args = parser.parse_args()

    if args.path == "" and not args.list:
        parser.error("Argument 'path' must be specified")
    if args.path == "" and args.list:
        list_installed_packages(local_path)
        return

    if str(args.path).startswith("git+"):
        clone_repository_and_install(
            str(args.path).lstrip("git+"), local_path, args.update
        )
        return
    install_package(local_path, Path(args.path).resolve(), args.update)
