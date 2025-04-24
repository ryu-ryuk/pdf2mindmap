from Excalidraw_Interface import SketchBuilder
import networkx as nx

def create_excalidraw_mindmap(graph):
    """
    Creates an Excalidraw file from a NetworkX graph
    """
    sb = SketchBuilder(roughness=2)
    
    # Extract nodes and edges from the graph
    nodes = {node: graph.nodes[node].get('label', node) for node in graph.nodes()}
    edges = list(graph.edges())
    
    # Create node positions using a layout algorithm
    pos = nx.nx_agraph.graphviz_layout(graph, prog='dot')
    
    # Create node objects
    node_objects = {}
    for node, label in nodes.items():
        x, y = pos[node]
        node_objects[node] = sb.TextBox(
            str(label),
            x=x,
            y=y,
            rect_kwargs={
                "backgroundColor": "#E8F8F5",
                "strokeColor": "#1ABC9C",
                "strokeWidth": 2
            }
        )
    
    # Create edges
    for source, target in edges:
        sb.create_binding_arrows(
            node_objects[source],
            node_objects[target],
            strokeColor="#95A5A6",
            strokeWidth=2
        )
    
    # Export to Excalidraw file
    sb.export_to_file("mindmap.excalidraw")
    print("[✓] Excalidraw file created: mindmap.excalidraw")