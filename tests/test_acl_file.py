from pathlib import Path
from tempfile import TemporaryDirectory
from textwrap import dedent

import pytest

from dfu.package.acl_file import AclEntry, AclFile


class TestAclFile:
    def test_from_string_simple(self) -> None:
        content = dedent("""
            /usr/bin/python 755 root root
            /usr/bin/bash 755 root root
        """)

        acl_file = AclFile.from_string(content)
        assert len(acl_file.entries) == 2

        expected_python = AclEntry(Path("/usr/bin/python"), "755", "root", "root")
        expected_bash = AclEntry(Path("/usr/bin/bash"), "755", "root", "root")

        assert acl_file.entries[Path("/usr/bin/python")] == expected_python
        assert acl_file.entries[Path("/usr/bin/bash")] == expected_bash

    def test_from_string_with_spaces_in_path(self) -> None:
        content = dedent("""
            /usr/local/bin/my script 755 root root
            /var/log/my log 644 root root
        """)

        acl_file = AclFile.from_string(content)
        assert len(acl_file.entries) == 2

        expected_script = AclEntry(Path("/usr/local/bin/my script"), "755", "root", "root")
        expected_log = AclEntry(Path("/var/log/my log"), "644", "root", "root")

        assert acl_file.entries[Path("/usr/local/bin/my script")] == expected_script
        assert acl_file.entries[Path("/var/log/my log")] == expected_log

    def test_from_string_invalid_line_too_few_parts(self) -> None:
        content = dedent("""
            /usr/bin/python 755 root
            /usr/bin/bash 755 root root
        """)

        with pytest.raises(ValueError, match="Invalid line"):
            AclFile.from_string(content)

    def test_from_string_empty_lines_ignored(self) -> None:
        content = dedent("""
            /usr/bin/python 755 root root

            /usr/bin/bash 755 root root
        """)

        acl_file = AclFile.from_string(content)
        assert len(acl_file.entries) == 2

        expected_python = AclEntry(Path("/usr/bin/python"), "755", "root", "root")
        expected_bash = AclEntry(Path("/usr/bin/bash"), "755", "root", "root")

        assert acl_file.entries[Path("/usr/bin/python")] == expected_python
        assert acl_file.entries[Path("/usr/bin/bash")] == expected_bash

    def test_from_string_empty_content(self) -> None:
        acl_file = AclFile.from_string("")
        assert len(acl_file.entries) == 0

    def test_from_string_relative_path_raises_error(self) -> None:
        content = dedent("""
            relative/path 755 root root
        """)

        with pytest.raises(ValueError, match="must be an absolute path"):
            AclFile.from_string(content)

    def test_from_string_empty_path_raises_error(self) -> None:
        content = dedent("""
             755 root root
        """)

        with pytest.raises(ValueError, match="Invalid line"):
            AclFile.from_string(content)

    def test_from_string_invalid_mode_letters_raises_error(self) -> None:
        content = dedent("""
            /usr/bin/python abc root root
        """)

        with pytest.raises(ValueError, match="must be octal digits only"):
            AclFile.from_string(content)

    def test_from_string_invalid_mode_mixed_raises_error(self) -> None:
        content = dedent("""
            /usr/bin/python 7a5 root root
        """)

        with pytest.raises(ValueError, match="must be octal digits only"):
            AclFile.from_string(content)

    def test_from_string_invalid_mode_non_octal_digits_raises_error(self) -> None:
        content = dedent("""
            /usr/bin/python 859 root root
        """)

        with pytest.raises(ValueError, match="must be octal digits only"):
            AclFile.from_string(content)

    def test_from_string_empty_mode_raises_error(self) -> None:
        content = dedent("""
            /usr/bin/python  root root
        """)

        with pytest.raises(ValueError, match="Invalid line"):
            AclFile.from_string(content)

    def test_from_string_invalid_uid_special_chars_raises_error(self) -> None:
        content = dedent("""
            /usr/bin/python 755 user@123 root
        """)

        with pytest.raises(ValueError, match="must be alphanumeric"):
            AclFile.from_string(content)

    def test_from_string_invalid_uid_spaces_raises_error(self) -> None:
        content = dedent("""
            /usr/bin/python 755 user name root
        """)

        with pytest.raises(ValueError, match="must be octal digits only"):
            AclFile.from_string(content)

    def test_from_string_invalid_gid_special_chars_raises_error(self) -> None:
        content = dedent("""
            /usr/bin/python 755 root group@123
        """)

        with pytest.raises(ValueError, match="must be alphanumeric"):
            AclFile.from_string(content)

    def test_from_string_invalid_gid_spaces_raises_error(self) -> None:
        content = dedent("""
            /usr/bin/python 755 root group name
        """)

        with pytest.raises(ValueError, match="must be octal digits only"):
            AclFile.from_string(content)

    def test_from_string_empty_uid_raises_error(self) -> None:
        content = dedent("""
            /usr/bin/python 755  root
        """)

        with pytest.raises(ValueError, match="Invalid line"):
            AclFile.from_string(content)

    def test_from_string_empty_gid_raises_error(self) -> None:
        content = dedent("""
            /usr/bin/python 755 root 
        """)

        with pytest.raises(ValueError, match="Invalid line"):
            AclFile.from_string(content)

    def test_from_string_valid_uid_with_hyphens(self) -> None:
        content = dedent("""
            /usr/bin/python 755 user-name root
        """)

        acl_file = AclFile.from_string(content)
        assert len(acl_file.entries) == 1

        expected_entry = AclEntry(Path("/usr/bin/python"), "755", "user-name", "root")
        assert acl_file.entries[Path("/usr/bin/python")] == expected_entry

    def test_from_string_valid_uid_with_underscores(self) -> None:
        content = dedent("""
            /usr/bin/python 755 user_name root
        """)

        acl_file = AclFile.from_string(content)
        assert len(acl_file.entries) == 1

        expected_entry = AclEntry(Path("/usr/bin/python"), "755", "user_name", "root")
        assert acl_file.entries[Path("/usr/bin/python")] == expected_entry

    def test_from_string_valid_gid_with_hyphens(self) -> None:
        content = dedent("""
            /usr/bin/python 755 root group-name
        """)

        acl_file = AclFile.from_string(content)
        assert len(acl_file.entries) == 1

        expected_entry = AclEntry(Path("/usr/bin/python"), "755", "root", "group-name")
        assert acl_file.entries[Path("/usr/bin/python")] == expected_entry

    def test_from_string_valid_gid_with_underscores(self) -> None:
        content = dedent("""
            /usr/bin/python 755 root group_name
        """)

        acl_file = AclFile.from_string(content)
        assert len(acl_file.entries) == 1

        expected_entry = AclEntry(Path("/usr/bin/python"), "755", "root", "group_name")
        assert acl_file.entries[Path("/usr/bin/python")] == expected_entry

    def test_from_string_path_with_special_chars(self) -> None:
        content = dedent("""
            /tmp/file-with-dashes_and_underscores 644 user group
        """)

        acl_file = AclFile.from_string(content)
        assert len(acl_file.entries) == 1

        expected_entry = AclEntry(Path("/tmp/file-with-dashes_and_underscores"), "644", "user", "group")
        assert acl_file.entries[Path("/tmp/file-with-dashes_and_underscores")] == expected_entry

    def test_from_string_strips_whitespace_from_fields(self) -> None:
        content = dedent("""
            /usr/bin/python  755  root  root
            /usr/bin/bash  644  user  group
        """)

        acl_file = AclFile.from_string(content)
        assert len(acl_file.entries) == 2

        expected_python = AclEntry(Path("/usr/bin/python"), "755", "root", "root")
        expected_bash = AclEntry(Path("/usr/bin/bash"), "644", "user", "group")

        assert acl_file.entries[Path("/usr/bin/python")] == expected_python
        assert acl_file.entries[Path("/usr/bin/bash")] == expected_bash

    def test_from_string_strips_whitespace_from_path_with_spaces(self) -> None:
        content = dedent("""
            /usr/local/bin/my script  755  root  root
        """)

        acl_file = AclFile.from_string(content)
        assert len(acl_file.entries) == 1

        expected_entry = AclEntry(Path("/usr/local/bin/my script"), "755", "root", "root")
        assert acl_file.entries[Path("/usr/local/bin/my script")] == expected_entry

    def test_from_file_smoke_test(self) -> None:
        content = dedent("""
            /usr/bin/python 755 root root
            /usr/bin/bash 755 root root
        """)

        with TemporaryDirectory() as temp_dir:
            acl_path = Path(temp_dir) / "acl.txt"
            with open(acl_path, "w") as f:
                f.write(content)

            acl_file = AclFile.from_file(acl_path)
            assert len(acl_file.entries) == 2
            assert Path("/usr/bin/python") in acl_file.entries
            assert Path("/usr/bin/bash") in acl_file.entries

    def test_from_file_empty_file_smoke_test(self) -> None:
        with TemporaryDirectory() as temp_dir:
            acl_path = Path(temp_dir) / "acl.txt"
            with open(acl_path, "w") as f:
                f.write("")

            acl_file = AclFile.from_file(acl_path)
            assert len(acl_file.entries) == 0

    def test_write_simple(self) -> None:
        entries = {
            Path("/usr/bin/python"): AclEntry(Path("/usr/bin/python"), "755", "root", "root"),
            Path("/usr/bin/bash"): AclEntry(Path("/usr/bin/bash"), "755", "root", "root"),
        }
        acl_file = AclFile(entries)

        with TemporaryDirectory() as temp_dir:
            acl_path = Path(temp_dir) / "acl.txt"
            acl_file.write(acl_path)

            with open(acl_path, "r") as f:
                content = f.read()

            expected_lines = [
                "/usr/bin/bash 755 root root\n",
                "/usr/bin/python 755 root root\n",
            ]
            assert content == "".join(expected_lines)

    def test_write_with_spaces_in_path(self) -> None:
        entries = {
            Path("/usr/local/bin/my script"): AclEntry(Path("/usr/local/bin/my script"), "755", "root", "root"),
            Path("/var/log/my log"): AclEntry(Path("/var/log/my log"), "644", "root", "root"),
        }
        acl_file = AclFile(entries)

        with TemporaryDirectory() as temp_dir:
            acl_path = Path(temp_dir) / "acl.txt"
            acl_file.write(acl_path)

            with open(acl_path, "r") as f:
                content = f.read()

            expected_lines = [
                "/usr/local/bin/my script 755 root root\n",
                "/var/log/my log 644 root root\n",
            ]
            assert content == "".join(expected_lines)

    def test_round_trip_serialization(self) -> None:
        original_entries = {
            Path("/usr/bin/python"): AclEntry(Path("/usr/bin/python"), "755", "root", "root"),
            Path("/usr/local/bin/my script"): AclEntry(Path("/usr/local/bin/my script"), "755", "user", "group"),
            Path("/var/log/my log"): AclEntry(Path("/var/log/my log"), "644", "root", "root"),
        }
        original_acl_file = AclFile(original_entries)

        with TemporaryDirectory() as temp_dir:
            acl_path = Path(temp_dir) / "acl.txt"
            original_acl_file.write(acl_path)

            with open(acl_path, "r") as f:
                content = f.read()

            loaded_acl_file = AclFile.from_string(content)
            assert len(loaded_acl_file.entries) == len(original_acl_file.entries)

            for path, entry in original_acl_file.entries.items():
                assert path in loaded_acl_file.entries
                assert loaded_acl_file.entries[path] == entry

    def test_round_trip_with_complex_paths(self) -> None:
        original_entries = {
            Path("/tmp/file-with-dashes"): AclEntry(Path("/tmp/file-with-dashes"), "644", "user-name", "group-name"),
            Path("/var/log/file_with_underscores"): AclEntry(
                Path("/var/log/file_with_underscores"), "644", "user_name", "group_name"
            ),
            Path("/usr/local/bin/script with spaces"): AclEntry(
                Path("/usr/local/bin/script with spaces"), "755", "root", "root"
            ),
            Path("/home/user/dot.file"): AclEntry(Path("/home/user/dot.file"), "600", "user", "user"),
        }
        original_acl_file = AclFile(original_entries)

        with TemporaryDirectory() as temp_dir:
            acl_path = Path(temp_dir) / "acl.txt"
            original_acl_file.write(acl_path)

            with open(acl_path, "r") as f:
                content = f.read()

            loaded_acl_file = AclFile.from_string(content)
            assert len(loaded_acl_file.entries) == len(original_acl_file.entries)

            for path, entry in original_acl_file.entries.items():
                assert path in loaded_acl_file.entries
                assert loaded_acl_file.entries[path] == entry

    def test_write_empty_file(self) -> None:
        acl_file = AclFile({})

        with TemporaryDirectory() as temp_dir:
            acl_path = Path(temp_dir) / "acl.txt"
            acl_file.write(acl_path)

            with open(acl_path, "r") as f:
                content = f.read()

            assert content == ""

    def test_entries_sorted_by_path(self) -> None:
        entries = {
            Path("/usr/bin/zsh"): AclEntry(Path("/usr/bin/zsh"), "755", "root", "root"),
            Path("/usr/bin/bash"): AclEntry(Path("/usr/bin/bash"), "755", "root", "root"),
            Path("/usr/bin/python"): AclEntry(Path("/usr/bin/python"), "755", "root", "root"),
        }
        acl_file = AclFile(entries)

        with TemporaryDirectory() as temp_dir:
            acl_path = Path(temp_dir) / "acl.txt"
            acl_file.write(acl_path)

            with open(acl_path, "r") as f:
                lines = f.readlines()

            expected_order = ["/usr/bin/bash", "/usr/bin/python", "/usr/bin/zsh"]
            for i, expected_path in enumerate(expected_order):
                assert lines[i].startswith(expected_path)
