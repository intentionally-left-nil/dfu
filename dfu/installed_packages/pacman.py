import subprocess


def get_installed_packages():
    result = subprocess.run(['pacman', '-Qqe'], capture_output=True, text=True, check=True)
    packages = result.stdout.split('\n')
    packages = [package.strip() for package in packages]
    packages = [package for package in packages if package]
    packages.sort()
    return packages
