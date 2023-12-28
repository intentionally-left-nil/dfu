import subprocess
from pathlib import Path

from platformdirs import PlatformDirs


def git_init(package_dir: Path):
    subprocess.run(['git', 'init'], cwd=package_dir, check=True)


def git_commit(package_dir: Path, message: str):
    subprocess.run(['git', 'add', '.'], cwd=package_dir, check=True)
    subprocess.run(['git', 'commit', '-m', message], cwd=package_dir, check=True)


def copy_template_gitignore(package_dir: Path):
    package_gitignore = package_dir / '.gitignore'
    template_gitignore = PlatformDirs("dfu").user_data_path / ".gitignore"
    if not package_gitignore.exists() and template_gitignore.exists() and template_gitignore.is_file():
        package_gitignore.write_text(template_gitignore.read_text())
