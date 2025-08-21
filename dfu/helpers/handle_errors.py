import subprocess
import sys
from functools import wraps
from typing import Callable, ParamSpec, TypeVar

import click

P = ParamSpec('P')
R = TypeVar('R')


def handle_errors(func: Callable[P, R]) -> Callable[P, R]:
    @wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        try:
            return func(*args, **kwargs)
        except subprocess.CalledProcessError as e:
            click.echo(click.style(f"Calling {" ".join(e.cmd)} failed", fg="red"))

            if e.stdout:
                click.echo(e.stdout)
            if e.stderr:
                click.echo(e.stderr)
            sys.exit(1)
        except ValueError as e:
            click.echo(click.style(str(e), fg="red"))
            sys.exit(1)
        except RuntimeError:
            # Let RuntimeError bubble up to be handled by Click's CliRunner
            raise

    return wrapper
