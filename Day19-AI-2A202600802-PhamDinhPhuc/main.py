import os
import networkx as nx
from config import OUTPUT_DIR
from src.utils import load_and_chunk_documents
from src.indexing import build_knowledge_graph_model
from src.graph import build_networkx_graph, visualize_graph
from src.flat_rag import FlatRAG
from src.graph_rag import GraphRAG
from src.evaluation import run_benchmark_and_eval, generate_report

def main():
    print("=" * 60)
    print("STARTING MODULAR GRAPHRAG LAB DAY 19 PIPELINE")
    print("=" * 60)
    
    # Step 1: Load and Chunk Documents
    chunks = load_and_chunk_documents()
    
    # Step 2: Extract Triples & Build Model
    triples_by_chunk, prompt_tokens, completion_tokens, build_time = build_knowledge_graph_model(chunks)
    
    # Step 3: Build NetworkX Graph
    graph = build_networkx_graph(triples_by_chunk)
    
    # Step 4: Visualize and save Graph
    visualize_graph(graph)
    
    # Save graph model in GML format (deliverable #1/2)
    graph_gml_path = os.path.join(OUTPUT_DIR, "knowledge_graph.gml")
    nx.write_gml(graph, graph_gml_path)
    print(f"Graph model saved in GML format to {graph_gml_path}")
    
    # Step 5: Initialize RAG Systems
    flat_rag = FlatRAG(chunks)
    graph_rag = GraphRAG(graph, chunks)
    
    # Step 6: Run Benchmark and Evaluation
    results = run_benchmark_and_eval(flat_rag, graph_rag)
    
    # Step 7: Generate Final Deliverable Report
    token_stats = {
        "total_chunks": len(chunks),
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "build_time": build_time
    }
    generate_report(results, token_stats)
    
    print("=" * 60)
    print("MODULAR GRAPHRAG LAB DAY 19 PIPELINE COMPLETED SUCCESSFULLY")
    print("=" * 60)

if __name__ == "__main__":
    main()
