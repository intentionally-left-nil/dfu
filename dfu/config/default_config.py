from dataclasses import dataclass, field
from pathlib import Path

from dfu.config.config import Config
from dfu.snapshots.snapper import Snapper, SnapperConfigInfo


@dataclass()
class Node:
    config: SnapperConfigInfo
    children: list['Node'] = field(default_factory=list)

    def insert(self, node: 'Node') -> bool:
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


def calculate_roots(configs: list[SnapperConfigInfo]) -> list[Node]:
    roots = []
    for config in configs:
        did_insert = False
        for root in roots:
            if root.insert(Node(config)):
                did_insert = True
                break

        if not did_insert:
            new_config = Node(config)
            new_roots = [new_config]
            for root in roots:
                if not new_config.insert(root):
                    new_roots.append(root)
            roots = new_roots
    roots.sort()
    return roots
