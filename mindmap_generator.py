import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
import matplotlib.patches as mpatches
from matplotlib.colors import LinearSegmentedColormap
import textwrap
import logging
import random
from matplotlib.path import Path
import matplotlib.patheffects as PathEffects
import re

# Setting up logging
logger = logging.getLogger(__name__)

# Custom color palette - soft pastel colors
COLORS = {
    "background": "#f9f9f9",
    "title": "#f8c3cd",  # Soft pink
    "section": "#a5d7e8",  # Soft blue
    "subsection": "#d0e7d2",  # Soft green
    "content": "#f9ebc8",  # Soft yellow
    "edge": "#a9a9a9",  # Soft gray
    "text": "#333333",  # Dark gray for text
}


def sanitize_node_label(label):
    """
    Sanitize node labels to avoid Graphviz parsing issues.
    Remove or escape problematic characters.
    """
    if not isinstance(label, str):
        return str(label)

    # Replace quotes with a safe character
    sanitized = label.replace('"', "'")
    # Replace colons, which can cause issues in some cases
    sanitized = sanitized.replace(":", "-")
    # Replace other problematic characters
    sanitized = re.sub(r"[\\<>{}|]", "", sanitized)

    return sanitized


def draw_mindmap(structure: dict, export_path="mindmap.png", show=True):
    """
    Draws and saves a beautiful mind map from structured document format.

    Args:
        structure (dict): Output from parser and enrichers.
        export_path (str): Where to save the image.
        show (bool): Whether to display the image.
    """
    logger.info("Generating mind map...")

    if not structure.get("title") or not structure.get("sections"):
        logger.error("Invalid structure format, missing title or sections.")
        return

    # Create directed graph
    G = nx.DiGraph()

    # Add title node with sanitized label
    title = sanitize_node_label(structure.get("title", "Document"))
    G.add_node(title, type="title", original=structure.get("title", "Document"))

    # Track node types for styling
    node_types = {title: "title"}
    original_texts = {title: structure.get("title", "Document")}

    # Add section nodes and edges
    for i, section in enumerate(structure.get("sections", [])):
        h1 = sanitize_node_label(section.get("heading", f"Section {i + 1}"))
        # Make sure node labels are unique
        if h1 in G.nodes():
            h1 = f"{h1}_{i}"

        G.add_node(
            h1, type="section", original=section.get("heading", f"Section {i + 1}")
        )
        G.add_edge(title, h1)
        node_types[h1] = "section"
        original_texts[h1] = section.get("heading", f"Section {i + 1}")

        # Add subsection nodes and edges
        for j, subsection in enumerate(section.get("subsections", [])):
            subheading = sanitize_node_label(
                subsection.get("heading", f"Subsection {i + 1}.{j + 1}")
            )
            # Make sure node labels are unique
            if subheading in G.nodes():
                subheading = f"{subheading}_{i}_{j}"

            G.add_node(
                subheading,
                type="subsection",
                original=subsection.get("heading", f"Subsection {i + 1}.{j + 1}"),
            )
            G.add_edge(h1, subheading)
            node_types[subheading] = "subsection"
            original_texts[subheading] = subsection.get(
                "heading", f"Subsection {i + 1}.{j + 1}"
            )

            # Add content as nodes (truncated for display)
            content = subsection.get("content", "")
            if content:
                # Truncate and sanitize content for display
                short_content = textwrap.shorten(content, width=50, placeholder="...")
                sanitized_content = sanitize_node_label(short_content)
                # Make sure node labels are unique
                if sanitized_content in G.nodes():
                    sanitized_content = f"{sanitized_content}_{i}_{j}"

                G.add_node(
                    sanitized_content,
                    type="content",
                    original=short_content,
                    full_content=content,
                )
                G.add_edge(subheading, sanitized_content)
                node_types[sanitized_content] = "content"
                original_texts[sanitized_content] = short_content

    # If using graphviz layout, we need to try/except and fall back to a simpler layout if it fails
    try:
        # Try using graphviz layout
        pos = nx.drawing.nx_agraph.graphviz_layout(G, prog="twopi", root=title)
    except Exception as e:
        logger.warning(
            f"Graphviz layout failed: {str(e)}. Falling back to spring layout."
        )
        # Fall back to spring layout
        pos = nx.spring_layout(G, k=0.5, iterations=50, seed=42)

    # Create figure with custom background
    plt.figure(figsize=(16, 12), facecolor=COLORS["background"])
    ax = plt.gca()
    ax.set_facecolor(COLORS["background"])

    # Draw edges with slight curve for Excalidraw-like appearance
    for edge in G.edges():
        start, end = edge
        start_pos, end_pos = pos[start], pos[end]

        # Calculate control point for curved edge
        mid_x = (start_pos[0] + end_pos[0]) / 2
        mid_y = (start_pos[1] + end_pos[1]) / 2

        # Add slight random offset for natural hand-drawn look
        offset = 15
        control_x = mid_x + random.uniform(-offset, offset)
        control_y = mid_y + random.uniform(-offset, offset)

        # Create Bezier curve path
        verts = [
            (start_pos[0], start_pos[1]),  # start
            (control_x, control_y),  # control point
            (end_pos[0], end_pos[1]),  # end
        ]
        codes = [Path.MOVETO, Path.CURVE3, Path.CURVE3]

        # Draw the path with hand-drawn effect
        path = Path(verts, codes)
        patch = mpatches.PathPatch(
            path,
            facecolor="none",
            edgecolor=COLORS["edge"],
            alpha=0.7,
            linewidth=1.5,
            linestyle="-",
        )
        ax.add_patch(patch)

        # Add arrow to show direction
        arrow_pos = 0.7  # Position along the path
        arrow_point = path.interpolated(20).vertices[int(20 * arrow_pos)]
        if int(20 * arrow_pos) + 1 < len(path.interpolated(20).vertices):
            dx = (
                path.interpolated(20).vertices[int(20 * arrow_pos) + 1][0]
                - arrow_point[0]
            )
            dy = (
                path.interpolated(20).vertices[int(20 * arrow_pos) + 1][1]
                - arrow_point[1]
            )

            arrow_length = 15
            ax.arrow(
                arrow_point[0],
                arrow_point[1],
                dx / 10,
                dy / 10,
                head_width=8,
                head_length=arrow_length,
                fc=COLORS["edge"],
                ec=COLORS["edge"],
                alpha=0.7,
            )

    # Node sizes based on hierarchy
    node_sizes = []
    for node in G.nodes():
        if node_types[node] == "title":
            node_sizes.append(8000)
        elif node_types[node] == "section":
            node_sizes.append(5000)
        elif node_types[node] == "subsection":
            node_sizes.append(3500)
        else:  # content
            node_sizes.append(2500)

    # Node colors based on type
    node_colors = []
    for node in G.nodes():
        node_colors.append(COLORS[node_types[node]])

    # Draw nodes with hand-drawn effect
    for i, node in enumerate(G.nodes()):
        x, y = pos[node]
        node_type = node_types[node]
        color = COLORS[node_type]
        size = node_sizes[i]

        # Use original text for display (not sanitized version)
        display_text = original_texts.get(node, node)

        # Draw node with slight irregularity for hand-drawn effect
        radius = np.sqrt(size) / 2
        irregularity = 0.05  # 5% irregularity

        # Create slightly irregular circle (hand-drawn effect)
        theta = np.linspace(0, 2 * np.pi, 30)
        r = radius * (1 + irregularity * np.sin(theta * 5))
        circle_x = x + r * np.cos(theta)
        circle_y = y + r * np.sin(theta)

        # Fill with pastel color
        plt.fill(circle_x, circle_y, color=color, alpha=0.9, zorder=2)

        # Add subtle shadow for depth
        shadow = plt.fill(circle_x + 5, circle_y - 5, color="gray", alpha=0.1, zorder=1)

        # Add border with hand-drawn effect
        border = plt.plot(
            circle_x, circle_y, color="#555555", alpha=0.7, linewidth=1.5, zorder=3
        )

        # Wrap text for better display
        wrapped_text = textwrap.fill(display_text, width=20)

        # Add text with slight offset for hand-drawn effect
        text_obj = plt.text(
            x + random.uniform(-2, 2),
            y + random.uniform(-2, 2),
            wrapped_text,
            horizontalalignment="center",
            verticalalignment="center",
            fontsize=11 if node_type == "content" else 13,
            fontweight="bold" if node_type in ["title", "section"] else "normal",
            color=COLORS["text"],
            wrap=True,
            zorder=4,
        )

        # Add subtle text shadow for better readability
        text_obj.set_path_effects(
            [PathEffects.withStroke(linewidth=3, foreground="white", alpha=0.8)]
        )

    # Remove axes for cleaner look
    plt.axis("off")

    # Add a subtle grid for Excalidraw feel
    ax.grid(color="gray", linestyle="-", linewidth=0.1, alpha=0.2)

    # Add legend
    legend_elements = [
        mpatches.Patch(facecolor=COLORS["title"], edgecolor="#555555", label="Title"),
        mpatches.Patch(
            facecolor=COLORS["section"], edgecolor="#555555", label="Section"
        ),
        mpatches.Patch(
            facecolor=COLORS["subsection"], edgecolor="#555555", label="Subsection"
        ),
        mpatches.Patch(
            facecolor=COLORS["content"], edgecolor="#555555", label="Content"
        ),
    ]
    plt.legend(handles=legend_elements, loc="lower right", framealpha=0.7)

    # Add subtle watermark
    plt.figtext(
        0.5,
        0.02,
        "Generated with PDF-to-Mindmap",
        ha="center",
        fontsize=8,
        color="gray",
        alpha=0.5,
    )

    # Adjust layout and save with high DPI for crisp output
    plt.tight_layout(pad=1.5)
    plt.savefig(
        export_path, dpi=300, bbox_inches="tight", facecolor=COLORS["background"]
    )

    logger.info(f"Mind map saved to {export_path}")

    if show:
        plt.show()
    else:
        plt.close()
