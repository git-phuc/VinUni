import os
import networkx as nx
import matplotlib.pyplot as plt
from config import OUTPUT_DIR
from src.indexing import normalize_entity_name

def build_networkx_graph(triples_by_chunk):
    # Process & Deduplicate Graph Elements
    graph = nx.DiGraph()
    entity_descriptions = {}
    entity_types = {}
    
    for chunk_id, data in triples_by_chunk.items():
        # Process entities
        for ent in data.get("entities", []):
            raw_name = ent.get("name", "")
            if not raw_name:
                continue
            name = normalize_entity_name(raw_name)
            etype = ent.get("type", "General")
            desc = ent.get("description", "")
            
            entity_types[name] = etype
            
            if name not in entity_descriptions:
                entity_descriptions[name] = []
            if desc and desc not in entity_descriptions[name]:
                entity_descriptions[name].append(desc)
                
        # Process triples
        for trip in data.get("triples", []):
            subj_raw = trip.get("subject", "")
            obj_raw = trip.get("object", "")
            rel = trip.get("relation", "CONNECTED_TO").strip().upper()
            
            if not subj_raw or not obj_raw:
                continue
                
            subj = normalize_entity_name(subj_raw)
            obj = normalize_entity_name(obj_raw)
            
            if subj == obj:
                continue
                
            if graph.has_edge(subj, obj):
                existing = graph[subj][obj].get("relations", [])
                if rel not in existing:
                    existing.append(rel)
                graph[subj][obj]["relations"] = existing
                
                # Update chunk ids
                existing_chunks = graph[subj][obj].get("chunk_ids", [])
                if chunk_id not in existing_chunks:
                    existing_chunks.append(chunk_id)
                graph[subj][obj]["chunk_ids"] = existing_chunks
            else:
                graph.add_edge(subj, obj, relations=[rel], chunk_ids=[chunk_id])
                
    # Add attributes to nodes
    for node in graph.nodes():
        etype = entity_types.get(node, "General")
        descs = entity_descriptions.get(node, ["Entity mentioned in tech corpus"])
        combined_desc = " ".join(descs[:2]) # Keep top 2 descriptions
        graph.nodes[node]["type"] = etype
        graph.nodes[node]["description"] = combined_desc
        
    print(f"Graph model built: {graph.number_of_nodes()} nodes, {graph.number_of_edges()} edges.")
    return graph

def visualize_graph(graph):
    print("Generating optimized graph visualization...")
    # Clean up figure state
    plt.clf()
    plt.close('all')
    
    fig, ax = plt.subplots(figsize=(18, 15))
    
    # Filter top connected nodes
    degrees = dict(graph.degree())
    sorted_nodes = sorted(degrees.items(), key=lambda x: x[1], reverse=True)
    top_nodes = [node for node, deg in sorted_nodes[:35]] # Take top 35 nodes
    
    subgraph = graph.subgraph(top_nodes)
    
    # Increase k spacing from 0.35 to 0.65 to space nodes out dramatically
    pos = nx.spring_layout(subgraph, k=0.65, iterations=60, seed=42)
    
    node_types = [subgraph.nodes[node].get("type", "General") for node in subgraph.nodes()]
    unique_types = list(set(node_types))
    
    colors_map = {
        "Company": "#4EA8DE",
        "Person": "#70E000",
        "Product": "#FF9F1C",
        "Sector": "#9B5DE5",
        "FinancialMetric": "#F15BB5",
        "Technology": "#00F5D4",
        "General": "#A0A0A0"
    }
    
    node_colors = []
    for node in subgraph.nodes():
        ntype = subgraph.nodes[node].get("type", "General")
        node_colors.append(colors_map.get(ntype, colors_map["General"]))
        
    # Cap node sizes cleanly to prevent overlaps
    node_sizes = [min(max(degrees[node]*120, 500), 2000) for node in subgraph.nodes()]
    
    # Draw nodes with soft shadow borders
    nx.draw_networkx_nodes(
        subgraph, pos, 
        node_color=node_colors, 
        node_size=node_sizes, 
        alpha=0.9,
        edgecolors="#2B2D42",
        linewidths=1.2,
        ax=ax
    )
    
    # Draw curved edges (connectionstyle="arc3,rad=0.15") to look premium and separate dual links
    nx.draw_networkx_edges(
        subgraph, pos, 
        edge_color="#A2A2A2", 
        width=1.2, 
        alpha=0.45,
        arrows=True,
        arrowsize=10,
        connectionstyle="arc3,rad=0.15",
        ax=ax
    )
    
    # Draw labels with small offset and clean white boxes with transparent borders
    labels = {node: node for node in subgraph.nodes()}
    nx.draw_networkx_labels(
        subgraph, pos, 
        labels=labels, 
        font_size=8, 
        font_family="sans-serif",
        font_weight="bold",
        font_color="#1D3557",
        bbox=dict(facecolor="#FFFFFF", edgecolor="#E5E5E5", boxstyle="round,pad=0.25", alpha=0.85),
        ax=ax
    )
    
    # Legend
    legend_handles = []
    for t in colors_map:
        if t in unique_types:
            legend_handles.append(plt.Line2D([0], [0], marker='o', color='w', markerfacecolor=colors_map[t], markersize=10, label=t))
            
    ax.legend(handles=legend_handles, loc="upper right", frameon=True, facecolor="#FFFFFF", edgecolor="#E5E5E5", fontsize=10)
    ax.set_title("Tech Company Corpus - Knowledge Graph (Top 35 Entities)", fontsize=16, fontweight="bold", pad=20, color="#1D3557")
    ax.axis("off")
    
    # Save visualization
    image_path = os.path.join(OUTPUT_DIR, "knowledge_graph.png")
    plt.tight_layout()
    plt.savefig(image_path, dpi=300, facecolor="#F8F9FA", bbox_inches='tight')
    plt.close()
    print(f"Graph visualization saved to {image_path}")
