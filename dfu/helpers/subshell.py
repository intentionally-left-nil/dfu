import os
import subprocess
from pathlib import Path


def subshell(cwd: Path | str) -> subprocess.CompletedProcess:
    shell = os.environ.get('SHELL', '/bin/bash')
    return subprocess.run([shell], cwd=cwd)
