import subprocess
from pathlib import Path
from shutil import copy, rmtree
from typing import Any, Generator
from unittest.mock import MagicMock, Mock, patch

import pytest

from dfu.api.playground import Playground
from dfu.revision.git import git_add, git_bundle, git_commit, git_diff, git_init


@pytest.fixture
def playground() -> Generator[Playground, None, None]:
    playground = Playground(prefix="unit_test")
    git_init(playground.location)
    subprocess.run(['git', 'config', 'user.name', 'myself'], cwd=playground.location, check=True)
    subprocess.run(['git', 'config', 'user.email', 'me@example.com'], cwd=playground.location, check=True)
    yield playground
    playground.cleanup()


@pytest.fixture
def mock_install() -> Generator[Mock, None, None]:
    original_subprocess_run = subprocess.run

    def side_effect(args: list[str], **kwargs: Any) -> subprocess.CompletedProcess[bytes]:
        assert args[0] == "sudo"
        return original_subprocess_run(args[1:], **kwargs)

    with patch('subprocess.run') as mock_run:
        mock_run.side_effect = side_effect
        yield mock_run


def test_temporary() -> None:
    location: Path
    with Playground.temporary(prefix="unit_test") as playground:
        location = playground.location
        assert playground.location.exists()
        assert playground.location.is_dir()
    assert not location.exists()


def test_list_files_in_patch_missing_file(playground: Playground) -> None:
    with pytest.raises(FileNotFoundError):
        playground.list_files_in_patch(playground.location / "missing.patch")


def test_list_files_empty_patch(playground: Playground) -> None:
    patch = playground.location / "empty.patch"
    patch.write_text("")
    assert playground.list_files_in_patch(patch) == set()


def test_list_files_new_file(tmp_path: Path, playground: Playground, setup_git: None) -> None:
    (tmp_path / '.gitignore').touch()
    git_add(tmp_path, ['.gitignore'])
    git_commit(tmp_path, 'Initial commit')
    (tmp_path / 'files' / 'nested').mkdir(parents=True, exist_ok=True)
    (tmp_path / 'files' / 'nested' / 'nested.txt').write_text('hello\nnested')
    (tmp_path / 'files' / 'file.txt').write_text('hello\nworld')
    git_add(tmp_path, ['.'])
    git_commit(tmp_path, 'Created files')
    diff = git_diff(tmp_path, "HEAD~1", "HEAD")

    patch = tmp_path / "changes.patch"
    patch.write_text(diff)

    assert playground.list_files_in_patch(patch) == {Path('/nested/nested.txt'), Path('/file.txt')}


def test_list_files_modified_file(tmp_path: Path, playground: Playground, setup_git: None) -> None:
    test_file = tmp_path / 'files' / 'file.txt'
    test_file.parent.mkdir(parents=True, exist_ok=True)
    test_file.write_text('hello\nworld')
    git_add(tmp_path, ['.'])
    git_commit(tmp_path, 'Initial commit')
    test_file.write_text('hello\nworld\nnew line')
    git_add(tmp_path, ['.'])
    git_commit(tmp_path, 'Modified file')
    diff = git_diff(tmp_path, "HEAD~1", "HEAD")

    patch = tmp_path / "changes.patch"
    patch.write_text(diff)

    assert playground.list_files_in_patch(patch) == {Path('/file.txt')}


def test_list_files_delete_file(tmp_path: Path, playground: Playground, setup_git: None) -> None:
    test_file = tmp_path / 'files' / 'file.txt'
    test_file.parent.mkdir(parents=True, exist_ok=True)
    test_file.write_text('hello\nworld')
    git_add(tmp_path, ['.'])
    git_commit(tmp_path, 'Initial commit')
    test_file.unlink()
    git_add(tmp_path, ['.'])
    git_commit(tmp_path, 'Deleted file')
    diff = git_diff(tmp_path, "HEAD~1", "HEAD")

    patch = tmp_path / "changes.patch"
    patch.write_text(diff)

    assert playground.list_files_in_patch(patch) == {Path('/file.txt')}


def test_list_files_unknown_file(tmp_path: Path, playground: Playground, setup_git: None) -> None:
    (tmp_path / '.gitignore').touch()
    git_add(tmp_path, ['.gitignore'])
    git_commit(tmp_path, 'Initial commit')
    (tmp_path / 'not_files' / 'nested').mkdir(parents=True, exist_ok=True)
    (tmp_path / 'not_files' / 'nested' / 'nested.txt').write_text('hello\nnested')
    (tmp_path / 'not_files' / 'file.txt').write_text('hello\nworld')
    git_add(tmp_path, ['.'])
    git_commit(tmp_path, 'Created files')
    diff = git_diff(tmp_path, "HEAD~1", "HEAD")

    patch = tmp_path / "changes.patch"
    patch.write_text(diff)

    with pytest.raises(ValueError):
        playground.list_files_in_patch(patch)


def test_list_files_create_symlink(tmp_path: Path, playground: Playground, setup_git: None) -> None:
    (tmp_path / '.gitignore').touch()
    git_add(tmp_path, ['.gitignore'])
    git_commit(tmp_path, 'Initial commit')
    (tmp_path / 'files' / 'nested').mkdir(parents=True, exist_ok=True)
    (tmp_path / 'files' / 'nested' / 'file.txt').write_text('hello\nworld')
    (tmp_path / 'files' / 'link.txt').symlink_to('./nested/file.txt')
    (tmp_path / 'files' / 'link_directory').symlink_to('./nested')
    git_add(tmp_path, ['.'])
    git_commit(tmp_path, 'Created files')
    diff = git_diff(tmp_path, "HEAD~1", "HEAD")

    patch = tmp_path / "changes.patch"
    patch.write_text(diff)

    assert playground.list_files_in_patch(patch) == {
        Path('/nested/file.txt'),
        Path('/link.txt'),
        Path('/link_directory'),
    }


def test_list_files_multiple_actions(tmp_path: Path, playground: Playground, setup_git: None) -> None:
    (tmp_path / '.gitignore').touch()
    (tmp_path / 'files' / 'nested').mkdir(parents=True, exist_ok=True)
    deleted_file = tmp_path / 'files' / 'deleted.txt'
    deleted_file.write_text('delete me')
    git_add(tmp_path, ['.'])
    git_commit(tmp_path, 'Initial commit')
    (tmp_path / 'files' / 'nested' / 'nested.txt').write_text('hello\nnested')
    (tmp_path / 'files' / 'file.txt').write_text('hello\nworld')
    (tmp_path / 'files' / 'file.txt').write_text('hello\nworld\nnew line')
    (tmp_path / 'files' / 'nested' / 'nested.txt').write_text('hello\nnested\nnew line')
    (tmp_path / 'files' / 'nested' / 'new.txt').write_text('hello\nnew')
    (tmp_path / 'files' / 'new.txt').write_text('hello\nnew')
    (tmp_path / 'files' / 'link.txt').symlink_to('./nested/nested.txt')
    (tmp_path / 'files' / 'link_directory').symlink_to('./nested')
    deleted_file.unlink()
    git_add(tmp_path, ['.'])
    git_commit(tmp_path, 'Modified files')
    diff = git_diff(tmp_path, "HEAD~1", "HEAD")

    patch = tmp_path / "changes.patch"
    patch.write_text(diff)

    assert playground.list_files_in_patch(patch) == {
        Path('/nested/nested.txt'),
        Path('/nested/new.txt'),
        Path('/file.txt'),
        Path('/new.txt'),
        Path('/deleted.txt'),
        Path('/link.txt'),
        Path('/link_directory'),
    }


def test_copy_files_from_filesystem_no_files(playground: Playground) -> None:
    playground.copy_files_from_filesystem([])
    assert not (playground.location / 'files').exists()


def test_copy_files_from_filesystem_absolute_file(tmp_path: Path, playground: Playground) -> None:
    file = tmp_path / 'file.txt'
    file.write_text('hello\nworld')
    file.chmod(0o777)
    playground.copy_files_from_filesystem([file])
    expected = playground.location / 'files' / Path(*tmp_path.parts[1:]) / 'file.txt'
    assert expected.read_text() == 'hello\nworld'
    assert (expected.stat().st_mode & 0o777) == 0o777


def test_copy_files_from_filesystem_relative_file(tmp_path: Path, playground: Playground) -> None:
    file = tmp_path / 'file.txt'
    file.write_text('hello\nworld')
    file.chmod(0o777)

    cwd = Path(".").resolve()
    num_parents = len(cwd.parts[1:])

    root_relative_to_cwd = Path("../" * num_parents)
    assert root_relative_to_cwd.resolve() == Path("/").resolve()
    relative_path = root_relative_to_cwd / Path(*file.parts[1:])
    assert relative_path.resolve() == file.resolve()

    playground.copy_files_from_filesystem([relative_path])
    expected = playground.location / 'files' / Path(*tmp_path.parts[1:]) / 'file.txt'
    assert expected.read_text() == 'hello\nworld'
    assert (expected.stat().st_mode & 0o777) == 0o777


def test_copy_files_from_filesystem_skip_directories(tmp_path: Path, playground: Playground) -> None:
    file = tmp_path / 'file.txt'
    file.write_text('hello\nworld')
    file.chmod(0o777)
    playground.copy_files_from_filesystem([file, file.parent])
    expected = playground.location / 'files' / Path(*tmp_path.parts[1:]) / 'file.txt'
    assert expected.read_text() == 'hello\nworld'
    assert (expected.stat().st_mode & 0o777) == 0o777


@patch('subprocess.run')
def test_copy_protected_file(mock_run: MagicMock, tmp_path: Path, playground: Playground) -> None:
    file = tmp_path / 'file.txt'
    file.write_text('hello\nworld')
    file.chmod(0o000)
    playground.copy_files_from_filesystem([file, file.parent])
    mock_run.assert_called_once_with(
        [
            "sudo",
            "cp",
            "-p",
            "-P",
            file.resolve(),
            Path(playground.location / 'files' / Path(*tmp_path.parts[1:]) / 'file.txt').resolve(),
        ],
        check=True,
        capture_output=True,
    )
    assert mock_run.call_count == 1


def test_copy_files_to_filesystem_no_files(tmp_path: Path, playground: Playground, mock_install: Mock) -> None:
    assert not (playground.location / 'files').exists()
    playground.copy_files_to_filesystem(dest=tmp_path)
    assert [p for p in tmp_path.glob('**/*')] == []


def test_copy_files_to_filesystem_only_directories(tmp_path: Path, playground: Playground, mock_install: Mock) -> None:
    (playground.location / 'files' / 'many' / 'nested' / 'dirs').mkdir(parents=True, exist_ok=True)
    playground.copy_files_to_filesystem(dest=tmp_path)
    assert [p for p in tmp_path.glob('**/*')] == []


def test_copy_files_to_filesystem_one_file(tmp_path: Path, playground: Playground, mock_install: Mock) -> None:
    file = playground.location / 'files' / 'file.txt'
    file.parent.mkdir(parents=True, exist_ok=True)
    file.write_text('file')
    existing = tmp_path / 'existing.txt'
    existing.write_text('existing')
    playground.copy_files_to_filesystem(dest=tmp_path)
    assert {p for p in tmp_path.glob('**/*')} == {
        Path(tmp_path / 'file.txt').resolve(),
        Path(tmp_path / 'existing.txt').resolve(),
    }
    assert (tmp_path / 'file.txt').read_text() == 'file'
    assert existing.read_text() == 'existing'


def test_copy_files_to_filesystem_creates_directories(
    tmp_path: Path, playground: Playground, mock_install: Mock
) -> None:
    # Create the test file
    file = playground.location / 'files' / 'etc' / 'nested' / 'file.txt'
    file.parent.mkdir(parents=True, exist_ok=True)
    file.write_text('file')
    file.chmod(0o777)

    # Set up the filesystem to have some existing files, but not nested
    (tmp_path / 'etc' / 'other').mkdir(parents=True, exist_ok=True)
    (tmp_path / 'etc' / 'etc.txt').write_text('etc')
    (tmp_path / 'etc' / 'other' / 'other.txt').write_text('other')

    playground.copy_files_to_filesystem(dest=tmp_path)
    assert set([p for p in tmp_path.glob('**/*') if p.is_file()]) == set(
        [
            Path(tmp_path / 'etc' / 'etc.txt').resolve(),
            Path(tmp_path / 'etc' / 'other' / 'other.txt').resolve(),
            Path(tmp_path / 'etc' / 'nested' / 'file.txt').resolve(),
        ]
    )

    actual = tmp_path / 'etc' / 'nested' / 'file.txt'
    assert actual.stat().st_mode & 0o777 == 0o777
    assert actual.read_text() == 'file'


def test_overwrites_existing_file(tmp_path: Path, playground: Playground, mock_install: Mock) -> None:
    file = playground.location / 'files' / 'etc' / 'nested' / 'file.txt'
    file.parent.mkdir(parents=True, exist_ok=True)
    file.write_text('file')
    file.chmod(0o777)

    existing = tmp_path / 'etc' / 'nested' / 'file.txt'
    existing.parent.mkdir(parents=True, exist_ok=True)
    existing.write_text('existing')
    existing.chmod(0o644)
    assert (existing.stat().st_mode & 0o777) == 0o644

    playground.copy_files_to_filesystem(dest=tmp_path)
    assert [p for p in tmp_path.glob('**/*') if p.is_file()] == [
        Path(tmp_path / 'etc' / 'nested' / 'file.txt').resolve(),
    ]

    assert existing.stat().st_mode & 0o777 == 0o777
    assert existing.read_text() == 'file'


@pytest.fixture
def patch_playground() -> Generator[Playground, None, None]:
    playground = Playground(prefix="unit_test_patch_playground")
    git_init(playground.location)
    subprocess.run(['git', 'config', 'user.name', 'myself'], cwd=playground.location, check=True)
    subprocess.run(['git', 'config', 'user.email', 'me@example.com'], cwd=playground.location, check=True)
    (playground.location / '.gitignore').touch()
    git_add(playground.location, ['.gitignore'])
    git_commit(playground.location, 'Initial commit')

    yield playground
    playground.cleanup()


@pytest.fixture
def file_patch(patch_playground: Playground, tmp_path: Path) -> Path:
    file = patch_playground.location / 'files' / 'file.txt'
    file.parent.mkdir(parents=True, exist_ok=True)
    file.write_text('file')
    git_add(patch_playground.location, ['files'])
    git_commit(patch_playground.location, 'Added file')
    patch_file = tmp_path / "file.patch"
    patch_file.write_text(git_diff(patch_playground.location, "HEAD~1", "HEAD"))
    bundle_file = tmp_path / "file.pack"
    git_bundle(patch_playground.location, bundle_file)
    return patch_file


@pytest.fixture
def file2_patch(patch_playground: Playground, tmp_path: Path) -> Path:
    file = patch_playground.location / 'files' / 'file2.txt'
    file.parent.mkdir(parents=True, exist_ok=True)
    file.write_text('file2')
    git_add(patch_playground.location, ['files'])
    git_commit(patch_playground.location, 'Added file2')
    patch_file = tmp_path / "file2.patch"
    patch_file.write_text(git_diff(patch_playground.location, "HEAD~1", "HEAD"))
    bundle_file = tmp_path / "file2.pack"
    git_bundle(patch_playground.location, bundle_file)
    return patch_file


def test_apply_patch_cleanly(playground: Playground, file_patch: Path, file2_patch: Path) -> None:
    assert playground.apply_patch(file_patch) == True
    assert (playground.location / 'files' / 'file.txt').read_text() == 'file'


FILE_MERGE_CONFLICT = """\
<<<<<<< ours
this is a conflict
EQUALS
file
>>>>>>> theirs
""".replace(
    "EQUALS", "=" * 7
)


def test_apply_patches_merge_conflict(playground: Playground, file_patch: Path) -> None:
    file = playground.location / 'files' / 'file.txt'
    file.parent.mkdir(parents=True, exist_ok=True)
    file.write_text('this is a conflict')
    git_add(playground.location, ['files'])
    git_commit(playground.location, 'Added file')
    assert playground.apply_patch(file_patch) == False
    assert file.read_text() == FILE_MERGE_CONFLICT


def test_apply_patches_other_error(tmp_path: Path, playground: Playground, file_patch: Path) -> None:
    backup_patch = tmp_path / "backup.patch"
    copy(file_patch, backup_patch)

    file_patch.write_text("THIS IS NOT A PATCH")
    with pytest.raises(subprocess.CalledProcessError):
        playground.apply_patch(file_patch)


def test_apply_patches_git_remote_fails(playground: Playground, file_patch: Path) -> None:
    rmtree(playground.location / '.git')
    with pytest.raises(subprocess.CalledProcessError):
        playground.apply_patch(file_patch)


def test_git_apply_without_bundle(playground: Playground, file_patch: Path) -> None:
    file_patch.with_suffix('.pack').unlink()

    assert playground.apply_patch(file_patch) == True
    assert (playground.location / 'files' / 'file.txt').read_text() == 'file'


def test_git_apply_merge_conflict_without_bundle(playground: Playground, file_patch: Path) -> None:
    file_patch.with_suffix('.pack').unlink()
    file = playground.location / 'files' / 'file.txt'
    file.parent.mkdir(parents=True, exist_ok=True)
    file.write_text('this is a conflict')
    git_add(playground.location, ['files'])
    git_commit(playground.location, 'Created file')

    assert playground.apply_patch(file_patch) == False
    assert (playground.location / 'files' / 'file.txt').read_text() == FILE_MERGE_CONFLICT
