import networkx as nx
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from typing import Dict, List, Any
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

COLORS = {
    "title": "lightblue",
    "section": "lightgreen",
    "subsection": "lightyellow",
    "topic": "lavender",
    "connection_edge": "red"
}

def draw_mindmap(structure: Dict[str, Any], export_path: str = "mindmap.png", show: bool = False) -> None:
    """
    Generates a mind map from the structured document and saves it as an image.
    """
    try:
        G = nx.DiGraph()
        pos = {}
        labels = {}
        node_colors = []
        title = structure.get("title", "Document")
        G.add_node(title)
        pos[title] = (0, 0)  # Placeholder, will be updated by layout
        labels[title] = title
        node_colors.append(COLORS["title"])

        # Add section nodes
        section_nodes = []
        for i, section in enumerate(structure.get("sections", [])):
            section_title = section.get("heading", f"Section {i + 1}")
            section_id = f"section_{i}"
            G.add_node(section_id)
            G.add_edge(title, section_id)
            labels[section_id] = section_title
            node_colors.append(COLORS["section"])
            section_nodes.append(section_id)

            # Add subsection nodes
            subsection_nodes = []
            for j, subsection in enumerate(section.get("subsections", [])):
                subsection_title = subsection.get("heading", f"Subsection {j + 1}")
                subsection_id = f"subsection_{i}_{j}"
                G.add_node(subsection_id)
                G.add_edge(section_id, subsection_id)
                labels[subsection_id] = subsection_title
                node_colors.append(COLORS["subsection"])
                subsection_nodes.append(subsection_id)

                # Add topic nodes
                for k, topic in enumerate(subsection.get("topics", [])):
                    topic_title = topic.get("title", f"Topic {k + 1}")
                    topic_id = f"topic_{i}_{j}_{k}"
                    G.add_node(topic_id)
                    G.add_edge(subsection_id, topic_id)
                    labels[topic_id] = topic_title
                    node_colors.append(COLORS["topic"])

        # Add topic connections
        topic_connections = structure.get("topic_connections", [])
        for conn in topic_connections:
            topic1 = conn.get("topic1")
            topic2 = conn.get("topic2")
            if topic1 and topic2:
                # Find nodes with matching topic titles
                topic1_id = next((n for n, l in labels.items() if l == topic1), None)
                topic2_id = next((n for n, l in labels.items() if l == topic2), None)
                if topic1_id and topic2_id:
                    G.add_edge(topic1_id, topic2_id, style="dashed", color=COLORS["connection_edge"])

        # Layout the graph
        try:
            pos = nx.drawing.nx_agraph.graphviz_layout(
                G, prog="dot", args="-Goverlap=scale -Gnodesep=0.5 -Granksep=1.5"
            )
        except Exception as e:
            logger.warning(f"Graphviz layout failed: {e}, falling back to spring layout")
            pos = nx.spring_layout(G, k=0.5, iterations=50)

        # Draw the mind map
        plt.figure(figsize=(12, 8))
        edge_styles = [(e, G.edges[e].get("style", "solid")) for e in G.edges]
        edge_colors = [G.edges[e].get("color", "black") for e in G.edges]

        # Draw nodes
        nx.draw_networkx_nodes(G, pos, node_color=node_colors, node_size=3000, node_shape="s")
        nx.draw_networkx_labels(G, pos, labels, font_size=8)

        # Draw edges
        for (u, v), style in edge_styles:
            nx.draw_networkx_edges(
                G, pos, edgelist=[(u, v)], edge_color=G.edges[(u, v)].get("color", "black"),
                style=style, arrows=True, arrowsize=10
            )

        # Create legend
        legend_elements = [
            mpatches.Patch(color=COLORS["title"], label="Title"),
            mpatches.Patch(color=COLORS["section"], label="Section"),
            mpatches.Patch(color=COLORS["subsection"], label="Subsection"),
            mpatches.Patch(color=COLORS["topic"], label="Topic"),
            plt.Line2D([0], [0], color=COLORS["connection_edge"], linestyle="--", label="Topic Connection")
        ]
        plt.legend(handles=legend_elements, loc="best")

        # Save and show
        plt.savefig(export_path, format="png", bbox_inches="tight", dpi=300)
        logger.info(f"Mind map saved to {export_path}")
        if show:
            plt.show()
        plt.close()

    except Exception as e:
        logger.error(f"Error generating mind map: {e}")
        raise