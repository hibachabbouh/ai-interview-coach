import json
import time
import uuid
import os
import chromadb
import numpy as np
from chromadb.utils.embedding_functions import ONNXMiniLM_L6_V2

from utils.logger import get_logger

logger = get_logger(__name__)

class SearchCache:

    def __init__(self, db_path="data/chroma_db", collection_name="web_search_cache",
                 exact_ttl_seconds=86400, semantic_ttl_seconds=86400,
                 redis_host=None, redis_port=6379, redis_db=0,
                 chroma_host=None, chroma_port=8000):

        self.collection_name = collection_name
        self.exact_ttl_seconds = exact_ttl_seconds
        self.semantic_ttl_seconds = semantic_ttl_seconds
        self.client = None

        if chroma_host:
            self.client = self._try_http_client(chroma_host, chroma_port, db_path)

        if self.client is None:
            os.makedirs(db_path, exist_ok=True)
            self.client = chromadb.PersistentClient(path=db_path)
            logger.info("Chroma client: local embedded mode (%s)", db_path)

        self.embedding_fn = ONNXMiniLM_L6_V2()
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"}
        )
        self.exact_cache_path = f"data/exact_cache_{collection_name}.json"
        self.exact_cache = {}
        self.redis_client = None

        if redis_host:
            try:
                import redis
                self.redis_client = redis.Redis(
                    host=redis_host, port=redis_port, db=redis_db,
                    decode_responses=True, socket_connect_timeout=2
                )
                self.redis_client.ping()
                logger.info("Exact cache backend: Redis (%s:%s)", redis_host, redis_port)
            except Exception as e:
                logger.warning("Redis unreachable (%s); falling back to local JSON exact cache.", e)
                self.redis_client = None

        if self.redis_client is None:
            self._load_exact_cache()
        self.embedding_cache = {}

    def _try_http_client(self, host: str, port: int, db_path: str):
        try:
            client = chromadb.HttpClient(host=host, port=port)
            client.heartbeat()
            logger.info("Chroma client: HTTP server mode (%s:%s)", host, port)
            return client
        except Exception as e:
            logger.warning(
                "Chroma HTTP server unreachable (%s:%s): %s — falling back to embedded.",
                host, port, e
            )
            return None

    def _redis_key(self, key: str) -> str:
        return f"searchcache:{self.collection_name}:{key}"

    def _load_exact_cache(self):
        if os.path.exists(self.exact_cache_path):
            try:
                with open(self.exact_cache_path, "r", encoding="utf-8") as f:
                    self.exact_cache = json.load(f)
                logger.info("Loaded exact cache (JSON fallback): %d items", len(self.exact_cache))
            except Exception as e:
                logger.warning("Exact cache load failed: %s", e)

    def _save_exact_cache(self):
        try:
            with open(self.exact_cache_path, "w", encoding="utf-8") as f:
                json.dump(self.exact_cache, f)
        except Exception as e:
            logger.warning("Exact cache save failed: %s", e)

    @staticmethod
    def _is_expired(timestamp, ttl_seconds):
        if ttl_seconds is None or timestamp is None:
            return False
        return (time.time() - timestamp) > ttl_seconds

    def _cache_score(self, query: str) -> int:
        q = query.lower()
        score = 0

        if len(q.split()) >= 4:
            score += 2
        if len(q) >= 25:
            score += 1
        if any(k in q for k in ["compare", "difference", "why", "how", "explain"]):
            score += 2

        return score

    def _use_semantic(self, query: str) -> bool:
        return self._cache_score(query) >= 3

    def _get_embedding(self, query: str) -> np.ndarray:
        q = query.lower().strip()

        if q in self.embedding_cache:
            return self.embedding_cache[q]

        emb = self.embedding_fn([query])[0]
        emb = np.array(emb, dtype=np.float32)

        norm = np.linalg.norm(emb)
        if norm > 0:
            emb = emb / norm

        self.embedding_cache[q] = emb
        return emb

    def _key(self, query, domains, max_results, depth):
        domains_str = ",".join(sorted(domains)) if domains else ""
        return f"{query.strip().lower()}||{domains_str}||{max_results}||{depth}"

    def lookup(self, query, domains=None, max_results=5, search_depth="basic", threshold=0.15):

        key = self._key(query, domains, max_results, search_depth)

        if self.redis_client is not None:
            try:
                raw = self.redis_client.get(self._redis_key(key))
                if raw is not None:
                    logger.info("EXACT HIT (redis): %s", query)
                    return json.loads(raw)
            except Exception as e:
                logger.warning("Redis read error, falling back to live for this call: %s", e)
        else:
            cached_entry = self.exact_cache.get(key)
            if cached_entry is not None:
                if isinstance(cached_entry, dict) and "results" in cached_entry:
                    if self._is_expired(cached_entry.get("timestamp"), self.exact_ttl_seconds):
                        logger.info("EXACT EXPIRED: %s", query)
                        del self.exact_cache[key]
                        self._save_exact_cache()
                    else:
                        logger.info("EXACT HIT (json): %s", query)
                        return cached_entry["results"]
                else:
                    logger.info("EXACT HIT (legacy, no TTL): %s", query)
                    return cached_entry

        if not self._use_semantic(query):
            logger.info("CACHE BYPASS: %s", query)
            return None

        if self.collection.count() == 0:
            return None

        q_emb = self._get_embedding(query)

        where_filter = {
            "$and": [
                {"max_results": {"$eq": max_results}},
                {"search_depth": {"$eq": search_depth}},
            ]
        }

        try:
            result = self.collection.query(
                query_embeddings=[q_emb.tolist()],
                n_results=5,
                where=where_filter,
                include=["documents", "metadatas", "distances"]
            )
        except Exception as e:
            logger.error("Semantic query error: %s", e)
            return None

        ids = result.get("ids", [[]])[0]
        documents = result.get("documents", [[]])[0]
        metadatas = result.get("metadatas", [[]])[0]
        distances = result.get("distances", [[]])[0]

        for doc_id, doc_query, meta, dist in zip(ids, documents, metadatas, distances):
            if self._is_expired(meta.get("timestamp"), self.semantic_ttl_seconds):
                logger.info("SEMANTIC EXPIRED (evicted): %s", doc_query)
                try:
                    self.collection.delete(ids=[doc_id])
                except Exception as e:
                    logger.warning("Semantic eviction failed: %s", e)
                continue

            if dist <= threshold:
                logger.info(
                    "SEMANTIC HIT: %s | matched=%s | dist=%.4f",
                    query, doc_query, dist
                )
                return json.loads(meta["results_json"])

            break

        return None

    def save(self, query, results_list, domains=None, max_results=5, search_depth="basic"):

        key = self._key(query, domains, max_results, search_depth)
        now = time.time()

        if self.redis_client is not None:
            try:
                self.redis_client.set(
                    self._redis_key(key),
                    json.dumps(results_list),
                    ex=self.exact_ttl_seconds
                )
            except Exception as e:
                logger.warning("Redis write error: %s", e)
        else:
            self.exact_cache[key] = {"timestamp": now, "results": results_list}
            self._save_exact_cache()

        if not self._use_semantic(query):
            return

        emb = self._get_embedding(query)

        metadata = {
            "domains_str": ",".join(sorted(domains)) if domains else "",
            "max_results": max_results,
            "search_depth": search_depth,
            "timestamp": now,
            "results_json": json.dumps(results_list)
        }

        try:
            self.collection.add(
                documents=[query],
                embeddings=[emb.tolist()],
                metadatas=[metadata],
                ids=[str(uuid.uuid4())]
            )
            logger.debug("Saved: %s", query)

        except Exception as e:
            logger.error("Save error: %s", e)