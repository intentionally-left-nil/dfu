import random
import shutil
import time
import uuid
from pathlib import Path

from dfu.config import Config


def get_version_number(config: Config, retry_count=0) -> int:
    """Returns an atomic, monotonically increasing number. The returned value is guaranteed to be unique, across multiple processes and in the future.
    This is accomplished by very carefully taking advantage that renaming a folder is an atomic operation"""
    # This is accomplished with the following algorithm:
    # Initially, /package_ver/version folder does not exist
    # During the first run, the algorith creates /package_ver/version/0/do_not_delete.txt
    # Then, the algorithm enumerates /package_ver/version, sees that the only folder is 0, and atomically renames it to package_ver/version/1
    # The algorithm returns 1, and this is the only call that can use 1 as the version number.
    # The next time get_version_number is called, it will see that package_ver/version/1 exists, and will atomically rename it to package_ver/version/2, etc, etc.
    if retry_count > 5:
        raise RuntimeError("Too many failures trying to determine the version number")

    if retry_count == 0:
        _try_create_version_directory(config)

    version_dir = _get_version_directory(config)
    version = int(version_dir.name)
    try:
        # If there's a race here, then only one process will succeed in renaming the directory.
        # The next process will no longer have a valid source directory, and should fail with (src) FileNotFoundError
        version_dir.replace(version_dir.parent / str(version + 1))
        return version + 1
    except (FileNotFoundError, OSError) as e:
        # We lost the race. This isn't a fatal error, just try again
        # Increment retry_count to prevent infinitely looping
        time.sleep(random.uniform(0, 0.5))
        return get_version_number(config, retry_count=retry_count + 1)


def _try_create_version_directory(config: Config):
    # This bootstraps the version directory atomically, in case there's a race condition where two processes try to create the first version
    # To do so, we always create a temp directory with the correct initial conditions, and then atomically rename it to the correct location
    # This will only succeed once. Any subsequent attempts will fail with OSError or FileExistsError (which is a good thing)

    # Note: Create the temp directory in the same folder as the version directory, to ensure they are on the same filesystem. Otherwise this isn't guaranteed to be atomic
    temp_dir = Path(config.package_dir) / f"version_{uuid.uuid4()}"
    dest_dir = Path(config.package_dir) / "version"
    # N.B. it's important to set up the temp dir correctly before the rename, since that is the atomic operation
    (temp_dir / "0").mkdir(parents=True, exist_ok=False)
    # N.B. Make sure the directory is non-empty, to ensure it's atomic.
    # That's my understanding of https://docs.python.org/3/library/os.html#os.rename : If that turns out not to be the case, then this file creation can be removed
    with open(temp_dir / "0" / "do_not_delete.txt", "w") as f:
        f.write(
            "This file is used to ensure the folder is not empty\n This is necessary to ensure atomic folder operations"
        )
    try:
        # atomically move package_dir/version_aa-bbb-ccc-ddd to package_dir/version, failing if that directory already exists
        temp_dir.replace(dest_dir)
    except (FileExistsError, OSError):
        # Creating the directory failed. Most likely it already exists, and this will be validated later
        pass

    finally:
        if temp_dir.exists():
            shutil.rmtree(temp_dir)


def _get_version_directory(config: Config) -> Path:
    parent_dir = Path(config.package_dir) / "version"
    if not parent_dir.exists() or not parent_dir.is_dir():
        raise ValueError(f"Expected {parent_dir} to exist and be a directory")

    subdirs = [x for x in parent_dir.iterdir() if x.is_dir()]
    if len(subdirs) != 1:
        raise ValueError(f"Expected exactly one folder in {parent_dir}")

    version_dir = subdirs[0]
    if not version_dir.name.isnumeric():
        raise ValueError(f"Expected {version_dir} to be a number")

    if next(version_dir.iterdir(), None) is None:
        raise ValueError(f"Expected {version_dir} to contain files")
    return version_dir
