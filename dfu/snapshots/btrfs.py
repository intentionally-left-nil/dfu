import subprocess


def get_all_subvolumes():
    command = '''for p in $(mount | awk '{print $3}'); do sudo btrfs subvolume show "$p" >/dev/null 2>&1 && echo "$p"; done; true'''
    result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
    return [line.strip() for line in result.stdout.splitlines() if line]
