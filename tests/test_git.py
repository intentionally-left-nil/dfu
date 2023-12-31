import subprocess
from pathlib import Path
from unittest.mock import PropertyMock, patch

import pytest
from platformdirs import PlatformDirs

from dfu.revision.git import (
    DEFAULT_GITIGNORE,
    copy_template_gitignore,
    git_add,
    git_check_ignore,
    git_checkout,
    git_commit,
    git_default_branch,
    git_delete_branch,
    git_diff,
    git_init,
    git_ls_files,
    git_reset_branch,
)


@pytest.fixture(autouse=True)
def setup_git(tmp_path: Path):
    git_init(tmp_path)
    subprocess.run(['git', 'config', 'user.name', 'myself'], cwd=tmp_path, check=True)
    subprocess.run(['git', 'config', 'user.email', 'me@example.com'], cwd=tmp_path, check=True)


def test_git_init(tmp_path: Path):
    assert (tmp_path / '.git').exists()


def test_git_add(tmp_path: Path):
    (tmp_path / 'file.txt').touch()
    git_add(tmp_path, ['file.txt'])
    result = subprocess.run(
        ['git', 'diff', '--cached', '--name-only'],
        cwd=tmp_path,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
    )
    assert result.stdout.splitlines() == ["file.txt"]


def test_git_commit(tmp_path: Path):
    (tmp_path / 'file.txt').touch()
    git_add(tmp_path, ['file.txt'])
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
    (tmp_path / '.gitignore').write_text(DEFAULT_GITIGNORE)
    with pytest.raises(subprocess.CalledProcessError):
        git_check_ignore(
            tmp_path,
            ['\0'],
        )


def test_git_ls_files_when_no_changes(tmp_path: Path):
    assert git_ls_files(tmp_path) == []


def test_git_ls_files(tmp_path: Path):
    (tmp_path / '.gitignore').write_text("/ignore")
    git_add(tmp_path, ['.gitignore'])
    git_commit(tmp_path, 'Initial commit')

    (tmp_path / 'file.txt').touch()
    (tmp_path / 'staged.txt').touch()
    (tmp_path / 'ignore').mkdir()
    (tmp_path / 'ignore' / 'file.txt').touch()
    assert set(git_ls_files(tmp_path)) == set(['file.txt', 'staged.txt', '.gitignore'])


def test_git_ls_files_in_subdirectory(tmp_path: Path):
    (tmp_path / 'file.txt').touch()
    placeholders = tmp_path / 'placeholders'
    placeholders.mkdir()
    (placeholders / 'test.txt').touch()
    assert git_ls_files(placeholders) == ['placeholders/test.txt']


def test_git_checkout_new_branch(tmp_path: Path):
    git_init(tmp_path)
    (tmp_path / 'file.txt').touch()
    git_add(tmp_path, ['file.txt'])
    git_commit(tmp_path, 'Initial commit')
    git_checkout(tmp_path, 'new_branch')
    assert (
        subprocess.run(
            ['git', 'rev-parse', '--abbrev-ref', 'HEAD'], cwd=tmp_path, check=True, text=True, capture_output=True
        ).stdout
        == "new_branch\n"
    )


def test_git_checkout_branch_already_exists(tmp_path: Path):
    git_init(tmp_path)
    (tmp_path / 'file.txt').touch()
    git_add(tmp_path, ['file.txt'])
    git_commit(tmp_path, 'Initial commit')
    git_checkout(tmp_path, 'new_branch')
    with pytest.raises(subprocess.CalledProcessError):
        git_checkout(tmp_path, 'new_branch', exist_ok=False)


def test_git_checkout_existing_branch(tmp_path: Path):
    git_init(tmp_path)
    (tmp_path / 'file.txt').touch()
    git_add(tmp_path, ['file.txt'])
    git_commit(tmp_path, 'Initial commit')
    git_checkout(tmp_path, 'new_branch')
    git_checkout(tmp_path, 'new_branch_2')
    assert (
        subprocess.run(
            ['git', 'rev-parse', '--abbrev-ref', 'HEAD'], cwd=tmp_path, check=True, text=True, capture_output=True
        ).stdout
        == "new_branch_2\n"
    )
    git_checkout(tmp_path, 'new_branch', exist_ok=True)
    assert (
        subprocess.run(
            ['git', 'rev-parse', '--abbrev-ref', 'HEAD'], cwd=tmp_path, check=True, text=True, capture_output=True
        ).stdout
        == "new_branch\n"
    )


def test_git_default_branch_no_commits(tmp_path: Path):
    current_branch = subprocess.run(
        ['git', 'branch', '--show-current'], cwd=tmp_path, check=True, text=True, capture_output=True
    ).stdout.strip()
    assert git_default_branch(tmp_path) == current_branch


def test_git_default_branch_with_one_commit(tmp_path: Path):
    current_branch = subprocess.run(
        ['git', 'branch', '--show-current'], cwd=tmp_path, check=True, text=True, capture_output=True
    ).stdout.strip()
    (tmp_path / 'file.txt').touch()
    git_add(tmp_path, ['file.txt'])
    git_commit(tmp_path, 'Initial commit')
    assert git_default_branch(tmp_path) == current_branch


def test_git_default_branch_missing(tmp_path: Path):
    (tmp_path / 'file.txt').touch()
    git_add(tmp_path, ['file.txt'])
    git_commit(tmp_path, 'Initial commit')
    current_branch = subprocess.run(
        ['git', 'branch', '--show-current'], cwd=tmp_path, check=True, text=True, capture_output=True
    ).stdout.strip()
    git_checkout(tmp_path, 'other_branch')
    git_delete_branch(tmp_path, current_branch)
    with pytest.raises(ValueError, match="Could not find the default branch"):
        git_default_branch(tmp_path)


def test_git_reset_branch(tmp_path: Path):
    (tmp_path / 'file.txt').touch()
    git_add(tmp_path, ['file.txt'])
    git_commit(tmp_path, 'Initial commit')
    current_branch = subprocess.run(
        ['git', 'branch', '--show-current'], cwd=tmp_path, check=True, text=True, capture_output=True
    ).stdout.strip()
    git_checkout(tmp_path, 'other_branch')
    (tmp_path / 'file2.txt').touch()
    git_add(tmp_path, ['file2.txt'])
    git_commit(tmp_path, 'other_branch')
    git_reset_branch(tmp_path, current_branch)
    assert (tmp_path / 'file.txt').exists() and not (tmp_path / 'file2.txt').exists()


def test_git_diff(tmp_path: Path):
    git_checkout(tmp_path, 'base')
    (tmp_path / 'file.txt').touch()
    git_add(tmp_path, ['file.txt'])
    git_commit(tmp_path, 'Initial commit')
    git_checkout(tmp_path, 'target')
    (tmp_path / 'file.txt').write_text('hello')
    git_add(tmp_path, ['file.txt'])
    git_commit(tmp_path, 'hello')
    assert (
        git_diff(tmp_path, 'base', 'target')
        == '''\
diff --git a/file.txt b/file.txt
index e69de29..b6fc4c6 100644
--- a/file.txt
+++ b/file.txt
@@ -0,0 +1 @@
+hello
\\ No newline at end of file
'''
    )


def test_delete_branch(tmp_path: Path):
    git_checkout(tmp_path, 'base')
    (tmp_path / 'file.txt').touch()
    git_add(tmp_path, ['file.txt'])
    git_commit(tmp_path, 'Initial commit')
    git_checkout(tmp_path, 'target')
    (tmp_path / 'file.txt').write_text('hello')
    git_add(tmp_path, ['file.txt'])
    git_commit(tmp_path, 'hello')
    git_delete_branch(tmp_path, 'base')
    assert (
        subprocess.run(
            ['git', 'branch', '--list', 'base'], cwd=tmp_path, check=True, text=True, capture_output=True
        ).stdout
        == ''
    )
