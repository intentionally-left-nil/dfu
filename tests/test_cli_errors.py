import subprocess

import click
from click.testing import CliRunner

from dfu.helpers.handle_errors import handle_errors

dummy_handler_cmd = [
    'python',
    '-c',
    'import sys; print("stdout output"); print("stderr output", file=sys.stderr); sys.exit(1)',
]

success_handler_cmd = [
    'python',
    '-c',
    'print("success output")',
]


@handle_errors
def cli_with_failed_subprocess() -> None:
    """A dummy handler function that calls a subprocess that fails"""
    subprocess.run(
        dummy_handler_cmd,
        check=True,
        capture_output=True,
    )


@handle_errors
def cli_with_successful_subprocess() -> None:
    """A handler function that calls a subprocess that succeeds"""
    subprocess.run(
        success_handler_cmd,
        check=True,
        capture_output=True,
    )


@handle_errors
def cli_with_value_error() -> None:
    """A handler function that raises a ValueError"""
    raise ValueError("This is a test error")


@handle_errors
def cli_with_runtime_error() -> None:
    """A handler function that raises a RuntimeError"""
    raise RuntimeError("This is a test runtime error")


def test_handles_subprocess_errors() -> None:
    runner = CliRunner()

    @click.command()
    def test_command() -> None:
        cli_with_failed_subprocess()

    result = runner.invoke(test_command)

    assert result.exit_code == 1

    assert f"""Calling {' '.join(dummy_handler_cmd)} failed""" in result.output
    assert "stdout output" in result.output
    assert "stderr output" in result.output


def test_handles_successful_subprocess() -> None:
    runner = CliRunner()

    @click.command()
    def test_command() -> None:
        cli_with_successful_subprocess()

    result = runner.invoke(test_command)

    assert result.exit_code == 0


def test_handles_value_error_with_stack_trace() -> None:
    runner = CliRunner()

    @click.command()
    def test_command() -> None:
        cli_with_value_error()

    result = runner.invoke(test_command)

    assert result.exit_code == 1
    # The CLIRunner catches the errors and converts them to SystemExit
    assert isinstance(result.exception, SystemExit)


def test_runtime_error_shows_stack_trace() -> None:
    runner = CliRunner()

    @click.command()
    def test_command() -> None:
        cli_with_runtime_error()

    result = runner.invoke(test_command)

    assert result.exit_code == 1
    assert isinstance(result.exception, RuntimeError)
    assert "This is a test runtime error" in str(result.exception)
