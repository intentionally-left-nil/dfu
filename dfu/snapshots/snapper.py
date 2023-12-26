import json
import os
import subprocess
from pathlib import Path

from dfu.snapshots.snapper_diff import SnapperDiff


class Snapper:
    snapper_name: str

    def __init__(self, snapper_name: str) -> None:
        self.snapper_name = snapper_name

    def get_mountpoint(self) -> Path:
        result = subprocess.run(['snapper', '-c', self.snapper_name, '--jsonout', 'get-config'], capture_output=True)
        config = json.loads(result.stdout)
        return Path(config['SUBVOLUME'])

    def create_pre_snapshot(self, description: str) -> int:
        result = subprocess.run(
            [
                'snapper',
                '-c',
                self.snapper_name,
                'create',
                '--type',
                'pre',
                '--print-number',
                '--description',
                description,
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        return int(result.stdout.strip())

    def create_post_snapshot(self, pre_snapshot_id: int, description: str) -> int:
        result = subprocess.run(
            [
                'snapper',
                '-c',
                self.snapper_name,
                'create',
                '--type',
                'post',
                '--pre-number',
                str(pre_snapshot_id),
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
            ['snapper', '-c', self.snapper_name, 'status', f'{pre_snapshot_id}..{post_snapshot_id}'],
            capture_output=True,
            text=True,
        )
        status_lines = result.stdout.splitlines()
        return [SnapperDiff.from_status(line) for line in status_lines]

    def get_snapshot_path(self, snapshot_id: int) -> Path:
        return self.get_mountpoint() / '.snapshots' / str(snapshot_id) / 'snapshot'
