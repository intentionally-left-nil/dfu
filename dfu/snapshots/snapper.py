import json
import subprocess
from dataclasses import dataclass
from pathlib import Path

from dfu.snapshots.snapper_diff import SnapperDiff


@dataclass
class SnapperConfigInfo:
    name: str
    mountpoint: Path


class Snapper:
    snapper_name: str

    @classmethod
    def get_configs(cls) -> list[SnapperConfigInfo]:
        data: list[dict]
        try:
            # When running without sudo, the exit code fails, however the config listing still succeeds
            # Try without sudo, see if the "configs" entry exist. Otherwise, fall-back to sudo
            result = subprocess.run(['snapper', '--jsonout', 'list-configs'], capture_output=True)
            data = json.loads(result.stdout)["configs"]
        except Exception:
            result = subprocess.run(['sudo', 'snapper', '--jsonout', 'list-configs'], capture_output=True, check=True)
            data = json.loads(result.stdout)["configs"]
        return [SnapperConfigInfo(name=config["config"], mountpoint=Path(config["subvolume"])) for config in data]

    def __init__(self, snapper_name: str) -> None:
        self.snapper_name = snapper_name

    def get_mountpoint(self) -> Path:
        result = subprocess.run(
            ['sudo', 'snapper', '-c', self.snapper_name, '--jsonout', 'get-config'], capture_output=True
        )
        config = json.loads(result.stdout)
        return Path(config['SUBVOLUME'])

    def create_snapshot(self, description: str) -> int:
        result = subprocess.run(
            [
                'sudo',
                'snapper',
                '-c',
                self.snapper_name,
                'create',
                '--type',
                'single',
                '--print-number',
                '--description',
                description,
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        return int(result.stdout.strip())

    def get_delta(self, pre_snapshot_id: int, post_snapshot_id: int) -> list[SnapperDiff]:
        result = subprocess.run(
            ['sudo', 'snapper', '-c', self.snapper_name, 'status', f'{pre_snapshot_id}..{post_snapshot_id}'],
            capture_output=True,
            text=True,
        )
        status_lines = result.stdout.splitlines()
        return [SnapperDiff.from_status(line) for line in status_lines]

    def get_snapshot_path(self, snapshot_id: int) -> Path:
        return self.get_mountpoint() / '.snapshots' / str(snapshot_id) / 'snapshot'
