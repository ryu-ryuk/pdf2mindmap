import matplotlib.pyplot as plt
import networkx as nx

def draw_mindmap(structure: dict, export_path="mindmap.png", show=True):
    """Draws and saves a mind map from structured PDF format

    Args:
        structure (dict: Output from parser module 
        export_path (str, optional): Where to save the image
        show (bool, optional): Whether to display the image
    """
    
    G = nx.Digraph()
    
    title = structure.get("title", "Document")
    G.add_node(title)
    
    
    for section in structure.get("sections", []):
        h1 = section.get("heading", "Section")
        G.add_node(h1)
        G.add_edge(title, h1)
        
        for subsection in section.get("subsections", []):
            subheading = subsection.get("subheading", "Subsection")
            G.add_node(subheading)
            G.add_edge(section_title, subheading)
            
            content = subsection.get("content", "")
            if content:
                G.add_node(content)
                G.add_edge(subheading, content)
                G.add_node(content, label=content)
                
    # pos = nx.spring_layout(G)
    # nx.draw(G, pos, with_labels=True, arrows=True, node_size=3000, node_color="lightblue", font_size=10)
    # plt.title("Mind Map")

    pos = nx.nx_agraph.graphviz_layout(G, prog="dot")  # tree layout
        
    node_colors  = []
    for node in G.nodes():
        if node == title:
            node_colors.append("lightgreen")
        elif "Section" in node:
            node_colors.append("lightblue")
        elif "Subsection" in node:
            node_colors.append("lightyellow")
        else:
            node_colors.append("lightgray")
            
            
    plt.figure(figsize=(12, 8))
    nx.draw(
        G,
        pos,
        with_labels=True,
        arrows=True,
        node_size=3000,
        node_color=node_colors,
        font_size=10,
        font_weight="bold",
        edge_color="gray",
    )
    
    plt.title("Mind Map", fontsize=14)
    plt.savefig(export_path, bbox_inches='tight')

    if show:
        plt.show()