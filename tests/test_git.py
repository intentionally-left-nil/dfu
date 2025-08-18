import subprocess
from pathlib import Path
from shutil import rmtree
from unittest.mock import PropertyMock, patch

import pytest
from platformdirs import PlatformDirs

from dfu.revision.git import (
    DEFAULT_GITIGNORE,
    copy_template_gitignore,
    git_add,
    git_add_remote,
    git_apply,
    git_are_files_staged,
    git_bundle,
    git_check_ignore,
    git_commit,
    git_diff,
    git_fetch,
    git_init,
    git_ls_files,
    git_num_commits,
    git_stash,
    git_stash_pop,
)


@pytest.fixture(autouse=True)
def auto_init(tmp_path: Path, setup_git: None) -> None:
    pass


def test_git_init(tmp_path: Path) -> None:
    assert (tmp_path / '.git').exists()


def test_git_add(tmp_path: Path) -> None:
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


def test_git_commit(tmp_path: Path) -> None:
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


def test_git_num_commits_zero_commits(tmp_path: Path) -> None:
    assert git_num_commits(tmp_path) == 0


def test_git_num_commits_not_a_git_folder(tmp_path: Path) -> None:
    rmtree(tmp_path / '.git')
    with pytest.raises(subprocess.CalledProcessError):
        git_num_commits(tmp_path)


def test_git_num_commits_one_commit(tmp_path: Path) -> None:
    (tmp_path / 'file.txt').touch()
    git_add(tmp_path, ['file.txt'])
    git_commit(tmp_path, 'Initial commit')
    assert git_num_commits(tmp_path) == 1


def test_git_num_commits_two_commits(tmp_path: Path) -> None:
    (tmp_path / 'file.txt').touch()
    git_add(tmp_path, ['file.txt'])
    git_commit(tmp_path, 'Initial commit')
    (tmp_path / 'file.txt').write_text('hello')
    git_add(tmp_path, ['file.txt'])
    git_commit(tmp_path, 'Second commit')

    assert git_num_commits(tmp_path) == 2


def test_copy_template_gitignore(tmp_path: Path) -> None:
    template_dir = tmp_path / "template"
    template_dir.mkdir()
    (template_dir / ".gitignore").write_text("hello")
    with patch.object(PlatformDirs, "user_data_path", new_callable=PropertyMock) as mock_user_data_path:
        mock_user_data_path.return_value = template_dir
        copy_template_gitignore(tmp_path)
    assert (tmp_path / '.gitignore').read_text() == 'hello'


def test_copy_template_gitignore_generates_default_template(tmp_path: Path) -> None:
    template_dir = tmp_path / "template"
    template_dir.mkdir()
    with patch.object(PlatformDirs, "user_data_path", new_callable=PropertyMock) as mock_user_data_path:
        mock_user_data_path.return_value = template_dir
        copy_template_gitignore(tmp_path)
    assert (tmp_path / '.gitignore').read_text() == DEFAULT_GITIGNORE


def test_copy_template_gitignore_skips_if_gitignore_exists(tmp_path: Path) -> None:
    template_dir = tmp_path / "template"
    template_dir.mkdir()
    (template_dir / ".gitignore").write_text("template_copy")
    (tmp_path / '.gitignore').write_text("local_copy")
    with patch.object(PlatformDirs, "user_data_path", new_callable=PropertyMock) as mock_user_data_path:
        mock_user_data_path.return_value = template_dir
        copy_template_gitignore(tmp_path)
    assert (tmp_path / '.gitignore').read_text() == 'local_copy'


def test_git_ignore(tmp_path: Path) -> None:
    (tmp_path / '.gitignore').write_text(DEFAULT_GITIGNORE)
    ignored = git_check_ignore(
        tmp_path,
        [
            "files/allowed.txt",
            "files/also_allowed.txt",
            "files/usr/share/not_allowed.so",
            "files/usr/include/also_not_allowed",
        ],
    )
    assert ignored == [
        "files/usr/share/not_allowed.so",
        "files/usr/include/also_not_allowed",
    ]


def test_git_ignore_no_files_ignored(tmp_path: Path) -> None:
    (tmp_path / '.gitignore').write_text(DEFAULT_GITIGNORE)
    ignored = git_check_ignore(
        tmp_path,
        [
            "files/allowed.txt",
            "files/also_allowed.txt",
        ],
    )
    assert ignored == []


def test_git_ignore_handles_error(tmp_path: Path) -> None:
    (tmp_path / '.gitignore').write_text(DEFAULT_GITIGNORE)
    with pytest.raises(subprocess.CalledProcessError):
        git_check_ignore(
            tmp_path,
            ['\0'],
        )


def test_git_ls_files_when_no_changes(tmp_path: Path) -> None:
    assert git_ls_files(tmp_path) == []


def test_git_ls_files(tmp_path: Path) -> None:
    (tmp_path / '.gitignore').write_text("/ignore")
    git_add(tmp_path, ['.gitignore'])
    git_commit(tmp_path, 'Initial commit')

    (tmp_path / 'file.txt').touch()
    (tmp_path / 'staged.txt').touch()
    (tmp_path / 'ignore').mkdir()
    (tmp_path / 'ignore' / 'file.txt').touch()
    assert set(git_ls_files(tmp_path)) == set(['file.txt', 'staged.txt', '.gitignore'])


def test_git_diff(tmp_path: Path) -> None:
    (tmp_path / 'file.txt').touch()
    git_add(tmp_path, ['file.txt'])
    git_commit(tmp_path, 'Initial commit')
    (tmp_path / 'file.txt').write_text('hello')
    git_add(tmp_path, ['file.txt'])
    git_commit(tmp_path, 'hello')
    assert (
        git_diff(tmp_path, "HEAD~1", "HEAD")
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


def test_git_no_files_are_staged(tmp_path: Path) -> None:
    assert not git_are_files_staged(tmp_path)


def test_git_files_are_staged(tmp_path: Path) -> None:
    (tmp_path / 'file.txt').touch()
    git_add(tmp_path, ['file.txt'])
    assert git_are_files_staged(tmp_path)


def test_git_files_are_staged_error(tmp_path: Path) -> None:
    rmtree(tmp_path / ".git")
    with pytest.raises(subprocess.CalledProcessError):
        git_are_files_staged(tmp_path)


def test_git_stash(tmp_path: Path) -> None:
    (tmp_path / '.gitignore').touch()
    git_add(tmp_path, ['.gitignore'])
    git_commit(tmp_path, 'Initial commit')
    (tmp_path / 'file.txt').touch()
    git_add(tmp_path, [tmp_path])
    git_stash(tmp_path)
    assert (
        subprocess.run(
            ['git', 'status', '--porcelain'], cwd=tmp_path, check=True, text=True, capture_output=True
        ).stdout
        == ''
    )
    assert not (tmp_path / 'file.txt').exists()
    git_stash_pop(tmp_path)
    assert (tmp_path / 'file.txt').exists()


def test_git_apply(tmp_path: Path) -> None:
    (tmp_path / '.gitignore').touch()
    git_add(tmp_path, ['.gitignore'])
    git_commit(tmp_path, 'Initial commit')
    (tmp_path / 'file.txt').write_text('hello')
    git_add(tmp_path, ['file.txt'])
    git_commit(tmp_path, 'Created file.txt')
    diff = git_diff(tmp_path, "HEAD~1", "HEAD")
    subprocess.run(['git', 'reset', '--hard', 'HEAD~1'], cwd=tmp_path, check=True, capture_output=True)

    assert not (tmp_path / 'file.txt').exists()

    (tmp_path / 'changes.patch').write_text(diff)
    assert git_apply(tmp_path, (tmp_path / 'changes.patch'))
    assert (tmp_path / 'file.txt').read_text() == 'hello'


def test_git_apply_with_conflict(tmp_path: Path) -> None:
    (tmp_path / '.gitignore').touch()
    git_add(tmp_path, ['.gitignore'])
    git_commit(tmp_path, 'Initial commit')
    file = tmp_path / 'file.txt'
    file.write_text('hello')
    git_add(tmp_path, ['file.txt'])
    git_commit(tmp_path, 'Created file.txt')
    diff = git_diff(tmp_path, "HEAD~1", "HEAD")
    subprocess.run(['git', 'reset', '--hard', 'HEAD~1'], cwd=tmp_path, check=True, capture_output=True)

    file.write_text('goodbye')
    git_add(tmp_path, ['file.txt'])
    git_commit(tmp_path, 'Changed file.txt to goodbye')

    (tmp_path / 'changes.patch').write_text(diff)
    assert not git_apply(tmp_path, (tmp_path / 'changes.patch'))

    print(file.read_text())
    assert (
        file.read_text()
        == '''\
<<<<<<< ours
goodbye
EQUALS
hello
>>>>>>> theirs
'''.replace(
            "EQUALS",
            "=" * 7,  # Replaced to prevent text editors from thinking there's a merge conflict
        )
    )


def test_git_apply_with_unstaged_changes(tmp_path: Path) -> None:
    (tmp_path / '.gitignore').touch()
    git_add(tmp_path, ['.gitignore'])
    git_commit(tmp_path, 'Initial commit')
    file = tmp_path / 'file.txt'
    file.write_text('hello')
    git_add(tmp_path, ['file.txt'])
    git_commit(tmp_path, 'Created file.txt')
    diff = git_diff(tmp_path, "HEAD~1", "HEAD")
    subprocess.run(['git', 'reset', '--hard', 'HEAD~1'], cwd=tmp_path, check=True, capture_output=True)

    file.write_text('goodbye')

    (tmp_path / 'changes.patch').write_text(diff)
    assert not git_apply(tmp_path, (tmp_path / 'changes.patch'))


def test_git_apply_unknown_error(tmp_path: Path) -> None:
    patch = tmp_path / "changes.patch"
    patch.write_text("THIS IS NOT A PATCH FILE")
    with pytest.raises(subprocess.CalledProcessError):
        git_apply(tmp_path, patch)


def test_git_apply_reverse(tmp_path: Path) -> None:
    (tmp_path / '.gitignore').touch()
    git_add(tmp_path, ['.gitignore'])
    git_commit(tmp_path, 'Initial commit')
    (tmp_path / 'file.txt').write_text('hello')
    git_add(tmp_path, ['file.txt'])
    git_commit(tmp_path, 'Created file.txt')
    diff = git_diff(tmp_path, "HEAD~1", "HEAD")

    (tmp_path / 'changes.patch').write_text(diff)
    git_apply(tmp_path, (tmp_path / 'changes.patch'), reverse=True)
    assert not (tmp_path / 'file.txt').exists()


def test_git_bundle(tmp_path: Path) -> None:
    rmtree(tmp_path / '.git')
    src = tmp_path / 'src'
    src.mkdir()
    git_init(src)
    subprocess.run(['git', 'config', 'user.name', 'myself'], cwd=src, check=True)
    subprocess.run(['git', 'config', 'user.email', 'me@example.com'], cwd=src, check=True)
    (src / '.gitignore').touch()
    git_add(src, ['.gitignore'])
    git_commit(src, 'Initial commit')
    (src / '.gitignore').write_text('# hello')
    sha = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=src, check=True, capture_output=True).stdout.strip()

    dest = tmp_path / 'dest'
    dest.mkdir()
    git_init(dest)
    assert subprocess.run(['git', 'show', sha], cwd=dest, capture_output=True).returncode != 0
    bundle = src / 'bundle.pack'
    git_bundle(src, bundle)
    git_add_remote(dest, 'bundle', str(bundle.resolve()))
    git_fetch(dest, 'bundle')
    assert subprocess.run(['git', 'show', sha], cwd=dest, capture_output=True).returncode == 0
