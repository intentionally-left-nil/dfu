from dataclasses import dataclass, field

from dfu.config.config import Btrfs, Config
from dfu.snapshots.snapper import Snapper, SnapperConfigInfo


def get_default_config() -> Config:
    roots = _calculate_roots(Snapper.get_configs())
    config_names = _breadth_first_search(roots)
    return Config(btrfs=Btrfs(snapper_configs=config_names))


@dataclass()
class _Node:
    config: SnapperConfigInfo
    children: list['_Node'] = field(default_factory=list)

    def insert(self, node: '_Node') -> bool:
        if node.config.mountpoint.is_relative_to(self.config.mountpoint):
            for child in self.children:
                if child.insert(node):
                    return True
            new_children = [node]
            for child in self.children:
                if not node.insert(child):
                    new_children.append(child)
            self.children = new_children
            self.children.sort()
            return True
        return False

    def __eq__(self, other):
        return self.config == other.config and self.children == other.children

    def __lt__(self, other):
        return f"{self.config.mountpoint}_{self.config.name}" < f"{other.config.mountpoint}_{other.config.name}"


def _calculate_roots(configs: list[SnapperConfigInfo]) -> list[_Node]:
    roots = []
    for config in configs:
        did_insert = False
        for root in roots:
            if root.insert(_Node(config)):
                did_insert = True
                break

        if not did_insert:
            new_config = _Node(config)
            new_roots = [new_config]
            for root in roots:
                if not new_config.insert(root):
                    new_roots.append(root)
            roots = new_roots
    roots.sort()
    return roots


def _breadth_first_search(roots: list[_Node]) -> list[str]:
    queue = roots.copy()
    names = []
    while queue:
        node = queue.pop(0)
        names.append(node.config.name)
        queue.extend(node.children)
    return names
