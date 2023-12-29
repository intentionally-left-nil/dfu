import subprocess
from pathlib import Path
from unittest.mock import PropertyMock, patch

import pytest
from platformdirs import PlatformDirs

from dfu.revision.git import (
    DEFAULT_GITIGNORE,
    copy_template_gitignore,
    git_check_ignore,
    git_commit,
    git_init,
)


def test_git_init(tmp_path: Path):
    git_init(tmp_path)
    assert (tmp_path / '.git').exists()


def test_git_commit(tmp_path: Path):
    git_init(tmp_path)
    (tmp_path / 'file.txt').touch()
    subprocess.run(['git', 'config', 'user.name', 'myself'], cwd=tmp_path, check=True)
    subprocess.run(['git', 'config', 'user.email', 'me@example.com'], cwd=tmp_path, check=True)
    git_commit(tmp_path, 'Initial commit')
    result = subprocess.run(
        ['git', 'show', '--name-only', '--oneline', 'HEAD'],
        cwd=tmp_path,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
    )
    assert result.stdout.splitlines()[1:] == ["file.txt"]


def test_copy_template_gitignore(tmp_path: Path):
    template_dir = tmp_path / "template"
    template_dir.mkdir()
    (template_dir / ".gitignore").write_text("hello")
    with patch.object(PlatformDirs, "user_data_path", new_callable=PropertyMock) as mock_user_data_path:
        mock_user_data_path.return_value = template_dir
        copy_template_gitignore(tmp_path)
    assert (tmp_path / '.gitignore').read_text() == 'hello'


def test_copy_template_gitignore_generates_default_template(tmp_path: Path):
    template_dir = tmp_path / "template"
    template_dir.mkdir()
    with patch.object(PlatformDirs, "user_data_path", new_callable=PropertyMock) as mock_user_data_path:
        mock_user_data_path.return_value = template_dir
        copy_template_gitignore(tmp_path)
    assert (tmp_path / '.gitignore').read_text() == DEFAULT_GITIGNORE


def test_copy_template_gitignore_skips_if_gitignore_exists(tmp_path: Path):
    template_dir = tmp_path / "template"
    template_dir.mkdir()
    (template_dir / ".gitignore").write_text("template_copy")
    (tmp_path / '.gitignore').write_text("local_copy")
    with patch.object(PlatformDirs, "user_data_path", new_callable=PropertyMock) as mock_user_data_path:
        mock_user_data_path.return_value = template_dir
        copy_template_gitignore(tmp_path)
    assert (tmp_path / '.gitignore').read_text() == 'local_copy'


def test_git_ignore(tmp_path: Path):
    git_init(tmp_path)
    (tmp_path / '.gitignore').write_text(DEFAULT_GITIGNORE)
    ignored = git_check_ignore(
        tmp_path,
        [
            "placeholders/allowed.txt",
            "placeholders/also_allowed.txt",
            "placeholders/usr/share/not_allowed.so",
            "placeholders/usr/include/also_not_allowed",
        ],
    )
    assert ignored == [
        "placeholders/usr/share/not_allowed.so",
        "placeholders/usr/include/also_not_allowed",
    ]


def test_git_ignore_no_files_ignored(tmp_path: Path):
    git_init(tmp_path)
    (tmp_path / '.gitignore').write_text(DEFAULT_GITIGNORE)
    ignored = git_check_ignore(
        tmp_path,
        [
            "placeholders/allowed.txt",
            "placeholders/also_allowed.txt",
        ],
    )
    assert ignored == []


def test_git_ignore_handles_error(tmp_path: Path):
    git_init(tmp_path)
    (tmp_path / '.gitignore').write_text(DEFAULT_GITIGNORE)
    with pytest.raises(subprocess.CalledProcessError):
        git_check_ignore(
            tmp_path,
            ['\0'],
        )
