import re
import subprocess
from pathlib import Path
from typing import Iterable

from platformdirs import PlatformDirs


def git_init(git_dir: Path):
    subprocess.run(['git', 'init'], cwd=git_dir, check=True, capture_output=True)


def git_add(git_dir: Path, paths: list[str | Path]):
    cmd = ['git', 'add'] + paths
    subprocess.run(cmd, cwd=git_dir, check=True, capture_output=True)


def git_commit(git_dir: Path, message: str):
    subprocess.run(['git', 'commit', '-m', message], cwd=git_dir, check=True, capture_output=True)


def git_num_commits(git_dir: Path) -> int:
    try:
        return int(
            subprocess.run(
                ['git', 'rev-list', '--count', 'HEAD'], cwd=git_dir, text=True, capture_output=True, check=True
            ).stdout.strip()
        )
    except subprocess.CalledProcessError as e:
        try:
            if (
                subprocess.run(
                    ['git', 'rev-list', '--all'], cwd=git_dir, text=True, capture_output=True, check=True
                ).stdout.strip()
                == ''
            ):
                return 0
        except Exception:
            pass  # Prefer the original exception
        raise e


def git_check_ignore(git_dir: Path, paths: Iterable[str]) -> list[str]:
    stdin = '\n'.join(paths)
    cmd = ['git', 'check-ignore', '--stdin']
    result = subprocess.run(cmd, cwd=git_dir, input=stdin, text=True, capture_output=True)
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


def git_diff(git_dir: Path, base: str, target: str, subdirectory: str | None = None) -> str:
    args = ['git', 'diff', '--patch', f'{base}..{target}']
    if subdirectory:
        args.extend(['--', subdirectory])
    return subprocess.run(
        args,
        cwd=git_dir,
        text=True,
        capture_output=True,
        check=True,
    ).stdout


def git_are_files_staged(git_dir: Path):
    return_code = subprocess.run(['git', 'diff', '--cached', '--quiet'], cwd=git_dir, capture_output=True).returncode
    match return_code:
        case 0:
            return False
        case 1:
            return True
        case _:
            raise subprocess.CalledProcessError(return_code, ['git', 'diff', '--cached', '--quiet'])


def git_apply(git_dir: Path, patch: Path, reverse: bool = False) -> bool:
    args: list[str] = ['git', 'apply', '--3way']
    if reverse:
        args.append('--reverse')
    args.append(str(patch.resolve()))
    try:
        # Since we're reading the output, set LC_ALL=C to ensure it's in English
        # TODO: If we ever end up displaying this to the user, then we should figure out another method
        # since this error won't be localized
        subprocess.run(args, cwd=git_dir, check=True, text=True, capture_output=True, env={'LC_ALL': 'C'})
        return True
    except subprocess.CalledProcessError as e:
        if e.returncode == 1:
            stderr: str = e.stderr
            if not re.match(r'^error:', stderr, flags=re.MULTILINE):
                # The failure was a merge conflict
                return False
        raise e


def git_stash(git_dir: Path):
    subprocess.run(['git', 'stash', 'save'], cwd=git_dir, check=True, capture_output=True)


def git_stash_pop(git_dir: Path):
    subprocess.run(['git', 'stash', 'pop'], cwd=git_dir, check=True, capture_output=True)


def git_bundle(git_dir: Path, dest: Path):
    return subprocess.run(
        ['git', 'bundle', 'create', dest.resolve(), "--all"], cwd=git_dir, text=True, check=True, capture_output=True
    )


def git_fetch(git_dir: Path, remote: str):
    return subprocess.run(['git', 'fetch', remote], cwd=git_dir, text=True, check=True, capture_output=True)


def git_add_remote(git_dir: Path, name: str, remote: str):
    return subprocess.run(
        ['git', 'remote', 'add', name, remote], cwd=git_dir, text=True, check=True, capture_output=True
    )


def ensure_template_gitignore() -> Path:
    template_gitignore = PlatformDirs("dfu").user_data_path / ".gitignore"
    if not template_gitignore.exists():
        template_gitignore.parent.mkdir(parents=True, exist_ok=True, mode=0o755)
        template_gitignore.write_text(DEFAULT_GITIGNORE)
    return template_gitignore


def copy_template_gitignore(git_dir: Path):
    package_gitignore = git_dir / '.gitignore'
    template_gitignore = ensure_template_gitignore()
    if not package_gitignore.exists() and template_gitignore.is_file():
        package_gitignore.write_text(template_gitignore.read_text())


DEFAULT_GITIGNORE = """\
# Files created by dfu, which should not be committed
/.dfu
# Paths where programs are installed into
/files/usr/bin
/files/usr/lib
/files/usr/share
/files/usr/include

# Paths where data changes, but is not user data
/files/var
/files/tmp
/files/**/baloo

# File extensions we never care about
/files/**/*.so
/files/**/*.pyc
/files/**/*.pyo
/files/**/.bin
/files/**/*.cache
/files/**/.viminfo

# Dfu files
/files/**/.dfu
/files/**/dfu_config.json
"""
