import subprocess
from pathlib import Path

from platformdirs import PlatformDirs


def git_init(package_dir: Path):
    subprocess.run(['git', 'init'], cwd=package_dir, check=True)


def git_add(package_dir: Path, paths: list[str | Path]):
    cmd = ['git', 'add'] + paths
    subprocess.run(cmd, cwd=package_dir, check=True)


def git_commit(package_dir: Path, message: str):
    subprocess.run(['git', 'commit', '-m', message], cwd=package_dir, check=True)


def git_checkout(package_dir: Path, branch: str, exist_ok: bool = False):
    try:
        subprocess.run(['git', 'checkout', '-b', branch], cwd=package_dir, check=True, capture_output=True)
    except subprocess.CalledProcessError as e:
        if exist_ok:
            subprocess.run(['git', 'checkout', branch], cwd=package_dir, check=True, capture_output=True)
        else:
            raise e


def git_reset_branch(package_dir: Path, target_branch: str):
    subprocess.run(['git', 'reset', '--hard', target_branch], cwd=package_dir, check=True)


def git_check_ignore(package_dir: Path, paths: list[str]) -> list[str]:
    stdin = '\n'.join(paths)
    cmd = ['git', 'check-ignore', '--stdin']
    result = subprocess.run(cmd, cwd=package_dir, input=stdin, text=True, capture_output=True)
    if result.returncode == 128:
        # Per the docs, only a status code of 128 indicates actual failure: https://git-scm.com/docs/git-check-ignore#_exit_status
        raise subprocess.CalledProcessError(result.returncode, cmd, output=result.stdout, stderr=result.stderr)
    return result.stdout.splitlines()


def git_ls_files(cwd: Path) -> list[str]:
    tracked_files = subprocess.run(
        ['git', 'ls-files', '--full-name'], cwd=cwd, text=True, capture_output=True, check=True
    )
    untracked_files = subprocess.run(
        ['git', 'ls-files', '--others', '--exclude-standard', '--full-name'],
        cwd=cwd,
        text=True,
        capture_output=True,
        check=True,
    )
    return tracked_files.stdout.splitlines() + untracked_files.stdout.splitlines()


def git_default_branch(package_dir: Path) -> str:
    default_branches = ['main', 'master']
    try:
        result = subprocess.run(
            ['git', 'config', '--get', 'init.defaultBranch'],
            cwd=package_dir,
            text=True,
            capture_output=True,
            check=True,
        )
        default_branches = [result.stdout.strip()]
    except subprocess.CalledProcessError:
        # No default branch config option is set, try main and master
        default_branches = ['main', 'master']

    local_branches = set(
        subprocess.run(
            ['git', 'for-each-ref', '--format=%(refname:short)', 'refs/heads/'],
            cwd=package_dir,
            text=True,
            capture_output=True,
            check=True,
        ).stdout.splitlines()
    )

    if len(local_branches) == 0:
        # This can happen if there isn't an initial commit yet (sigh)
        local_branches = set([git_current_branch(package_dir)])
    for branch in default_branches:
        if branch in local_branches:
            return branch
    raise ValueError("Could not find the default branch")


def git_current_branch(package_dir: Path) -> str:
    return subprocess.run(
        ['git', 'branch', '--show-current'], cwd=package_dir, text=True, capture_output=True, check=True
    ).stdout.strip()


def git_diff(package_dir: Path, base: str, target: str) -> str:
    return subprocess.run(
        ['git', 'diff', '--patch', f'{base}..{target}'],
        cwd=package_dir,
        text=True,
        capture_output=True,
        check=True,
    ).stdout


def git_stash(package_dir: Path):
    subprocess.run(['git', 'stash', 'save'], cwd=package_dir, check=True, capture_output=True)


def git_stash_pop(package_dir: Path):
    subprocess.run(['git', 'stash', 'pop'], cwd=package_dir, check=True, capture_output=True)


def git_delete_branch(package_dir: Path, branch: str):
    subprocess.run(['git', 'branch', '-D', branch], cwd=package_dir, check=True)


def ensure_template_gitignore() -> Path:
    template_gitignore = PlatformDirs("dfu").user_data_path / ".gitignore"
    if not template_gitignore.exists():
        template_gitignore.write_text(DEFAULT_GITIGNORE)
    return template_gitignore


def copy_template_gitignore(package_dir: Path):
    package_gitignore = package_dir / '.gitignore'
    template_gitignore = ensure_template_gitignore()
    if not package_gitignore.exists() and template_gitignore.is_file():
        package_gitignore.write_text(template_gitignore.read_text())


DEFAULT_GITIGNORE = """\
# Files created by dfu, which should not be committed
/.dfu-diff
# Paths where programs are installed into
/placeholders/usr/bin
/placeholders/usr/lib
/placeholders/usr/share
/placeholders/usr/include

# Paths where data changes, but is not user data
/placeholders/var
/placeholders/tmp

# File extensions we never care about
/placeholders/**/*.so
/placeholders/**/*.pyc
/placeholders/**/*.pyo
/placeholders/**/.bin

# Cache files and folders
/placeholders/**/.cache
"""
