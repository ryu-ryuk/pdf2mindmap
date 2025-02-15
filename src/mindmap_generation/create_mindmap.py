"""
Generates a mind map from keywords using networkx and matplotlib
"""



import networkx as nx
import matplotlib.pyplot as plt

def create_mindmap(keywords, title):
    
    try:
        
        # Create a graph with central node
        
        G = nx.Graph()
        
        central_node = "Document Overview: " + title
        
        G.add_node(central_node)
        
        
        # Add the keywords as nodes and connect them to central node
        
        
        for keyword in keywords:
            G.add_node(keyword)
            G.add_edge(central_node, keyword)
            
            
            # Inter keyword edges if relationship are known
            # later to be added
            
            
            # Draw the graph
            pos = nx.spring_layout(G) # Determines node position for visualization 
            
            nx.draw(G, pos, with_labels=True, node_size =3000, node_color="lightblue",
                    font_size=10, font_weight="bold") # Draws the graph
            
            plt.title("Mind Map for Document: " + title)
            
            plt.show() # for local debugging purposes
            
    except Exception as e:
        print(f"Error during mind map creation: {e}")
        
        