import time
import os
import chromadb
from dotenv import load_dotenv
from tools.web_search_tool import WebSearchTool

load_dotenv()

def print_separator(char="=", length=75):
    print(char * length)

def main():
    print_separator()
    print("      WEB SEARCH CACHING BENCHMARK (CHROMADB EMBEDDINGS)")
    print_separator()
    
    db_path = "data/chroma_db"
    benchmark_collection_name = "benchmark_search_cache"
    benchmark_exact_cache_path = f"data/exact_cache_{benchmark_collection_name}.json"

    print(f"Cleaning database collection '{benchmark_collection_name}' at '{db_path}'...")
    try:
        client = chromadb.PersistentClient(path=db_path)
        client.delete_collection(benchmark_collection_name)
        print("Existing benchmark collection cleared.")
    except Exception:
        print("No existing benchmark collection to clear. Creating fresh one.")

    if os.path.exists(benchmark_exact_cache_path):
        os.remove(benchmark_exact_cache_path)
        print(f"Existing benchmark exact cache file removed: {benchmark_exact_cache_path}")

    tool_no_cache = WebSearchTool(max_results=3, use_cache=False)
    
    tool_cached = WebSearchTool(max_results=3, use_cache=True)
    
    if tool_cached._cache is not None:
        cache = tool_cached._cache
        cache.collection_name = benchmark_collection_name
        cache.collection = cache.client.get_or_create_collection(
            name=benchmark_collection_name,
            metadata={"hnsw:space": "cosine"}
        )
        cache.exact_cache_path = benchmark_exact_cache_path
        cache.exact_cache = {}

        if cache.redis_client is not None:
            pattern = cache._redis_key("*")
            stale_keys = list(cache.redis_client.scan_iter(match=pattern))
            if stale_keys:
                cache.redis_client.delete(*stale_keys)
                print(f"Existing benchmark Redis keys removed: {len(stale_keys)}")
    
    queries_flow = [
        {
            "description": "Standard Technical Query",
            "base_query": "python list vs tuple performance differences",
            "similar_query": "performance differences python list vs tuple"
        },
        {
            "description": "ML Concept Query",
            "base_query": "machine learning overfitting regularization techniques",
            "similar_query": "machine learning overfitting regularization technique"
        },
        {
            "description": "Behavioral Query",
            "base_query": "STAR method behavioral interview teamwork example",
            "similar_query": "STAR method behavioral interview teamwork examples"
        }
    ]
    
    results = []
    
    for item in queries_flow:
        desc = item["description"]
        base_q = item["base_query"]
        sim_q = item["similar_query"]
        
        print(f"\n--- Running scenarios for: {desc}")
        print(f"  Base query: {base_q!r}")
        print(f"  Similar query: {sim_q!r}")
        
        t_start = time.perf_counter()
        res_no_cache = tool_no_cache.run(base_q)
        t_no_cache = (time.perf_counter() - t_start) * 1000
        print(f"  [1/4] Live Search (No Cache)      -> Latency: {t_no_cache:.2f} ms")
        
        t_start = time.perf_counter()
        res_miss = tool_cached.run(base_q)
        t_miss = (time.perf_counter() - t_start) * 1000
        print(f"  [2/4] Cached Search (Cache MISS)  -> Latency: {t_miss:.2f} ms")
        
        t_start = time.perf_counter()
        res_hit = tool_cached.run(base_q)
        t_hit = (time.perf_counter() - t_start) * 1000
        print(f"  [3/4] Cached Search (Cache HIT)   -> Latency: {t_hit:.2f} ms")
        
        t_start = time.perf_counter()
        res_semantic = tool_cached.run(sim_q)
        t_semantic = (time.perf_counter() - t_start) * 1000
        print(f"  [4/4] Semantic Search (Cache HIT) -> Latency: {t_semantic:.2f} ms")
        
        results.append({
            "description": desc,
            "query": base_q,
            "t_no_cache": t_no_cache,
            "t_miss": t_miss,
            "t_hit": t_hit,
            "t_semantic": t_semantic
        })
        
    print_separator()
    print("                       BENCHMARK RESULTS SUMMARY")
    print_separator()
    print(f"{'Query Scenario':<25} | {'Live (ms)':<10} | {'Miss (ms)':<10} | {'Hit (ms)':<10} | {'Semantic (ms)':<13} | {'Speedup':<8}")
    print_separator("-")
    
    for r in results:
        speedup = r["t_no_cache"] / r["t_hit"] if r["t_hit"] > 0 else 0
        print(
            f"{r['description']:<25} | "
            f"{r['t_no_cache']:<10.2f} | "
            f"{r['t_miss']:<10.2f} | "
            f"{r['t_hit']:<10.2f} | "
            f"{r['t_semantic']:<13.2f} | "
            f"{speedup:.1f}x"
        )
    print_separator()

if __name__ == "__main__":
    main()