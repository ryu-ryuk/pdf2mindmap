import networkx as nx
from typing import Dict


class AcademicMindmapBuilder:
    def __init__(self, title: str):
        self.graph = nx.DiGraph()
        self.graph.add_node(title, type="title", level=0)
        self.root = title
        self.node_stack = [title]
        self.level_stack = [0]

    def add_academic_node(self, section: Dict):
        """Add nodes with academic context"""
        heading = section["heading"]
        level = section.get("level", 1)
        content = section.get("content", "")

        # Manage hierarchy
        while self.level_stack and self.level_stack[-1] >= level:
            self.node_stack.pop()
            self.level_stack.pop()

        parent = self.node_stack[-1]
        self.graph.add_node(
            heading,
            type="section",
            level=level,
            summary=section.get("summary", ""),
            content=content,
            keywords=section.get("keywords", []),
        )
        self.graph.add_edge(parent, heading, type="structural")

        # Add conceptual relationships
        for src, tgt, rel in section.get("relationships", []):
            if src in self.graph and tgt in self.graph:
                self.graph.add_edge(src, tgt, type=rel, label=rel)

        self.node_stack.append(heading)
        self.level_stack.append(level)

    def optimize_layout(self):
        """Apply academic layout heuristics"""
        # Remove isolated nodes except title
        remove_nodes = [
            n for n in self.graph.nodes if self.graph.degree(n) == 0 and n != self.root
        ]
        self.graph.remove_nodes_from(remove_nodes)

        # Merge similar nodes
        entities = {}
        for node in list(self.graph.nodes):
            clean_name = node.lower().strip()
            if clean_name in entities:
                nx.contracted_nodes(self.graph, entities[clean_name], node)
            else:
                entities[clean_name] = node
