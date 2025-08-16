import subprocess
import sys
from functools import wraps

import click


def handle_errors(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except subprocess.CalledProcessError as e:
            click.echo(click.style(f"Calling {" ".join(e.cmd)} failed", fg="red"))

            if e.stdout:
                click.echo(e.stdout)
            if e.stderr:
                click.echo(e.stderr)
            sys.exit(1)

    return wrapper
