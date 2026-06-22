
from __future__ import annotations

import json
import time
from typing import Any, Dict, Optional

from utils.logger import get_logger

logger = get_logger(__name__)

_SESSION_TTL = 7200
_PREFIX = "interviewsession:"


class SessionStore:

    def __init__(self, redis_host: Optional[str] = None,
                 redis_port: int = 6379, redis_db: int = 0):
        self._redis = None
        self._mem: Dict[str, Dict[str, Any]] = {}  

        if redis_host:
            try:
                import redis
                client = redis.Redis(
                    host=redis_host, port=redis_port, db=redis_db,
                    decode_responses=True, socket_connect_timeout=2,
                )
                client.ping()
                self._redis = client
                logger.info("SessionStore: Redis (%s:%s)", redis_host, redis_port)
            except Exception as e:
                logger.warning("SessionStore: Redis unavailable (%s), using in-memory.", e)

        if self._redis is None:
            logger.info("SessionStore: in-memory fallback")

    

    def _key(self, session_id: str) -> str:
        return f"{_PREFIX}{session_id}"

   
    def get(self, session_id: str) -> Dict[str, Any]:
        """Return session dict, or empty dict if not found."""
        try:
            if self._redis:
                raw = self._redis.get(self._key(session_id))
                return json.loads(raw) if raw else {}
            return self._mem.get(session_id, {})
        except Exception as e:
            logger.warning("SessionStore.get error: %s", e)
            return {}

    def set(self, session_id: str, data: Dict[str, Any]) -> None:
        """Persist session dict."""
        try:
            if self._redis:
                self._redis.set(
                    self._key(session_id),
                    json.dumps(data),
                    ex=_SESSION_TTL,
                )
            else:
                self._mem[session_id] = data
        except Exception as e:
            logger.warning("SessionStore.set error: %s", e)

    def update(self, session_id: str, patch: Dict[str, Any]) -> Dict[str, Any]:
        """Merge patch into existing session and persist. Returns updated dict."""
        data = self.get(session_id)
        data.update(patch)
        self.set(session_id, data)
        return data

    def delete(self, session_id: str) -> None:
        try:
            if self._redis:
                self._redis.delete(self._key(session_id))
            else:
                self._mem.pop(session_id, None)
        except Exception as e:
            logger.warning("SessionStore.delete error: %s", e)

   

    def add_score(self, session_id: str, score: float) -> None:
        data = self.get(session_id)
        history = data.get("score_history", [])
        history.append(round(score, 3))
        data["score_history"] = history
        self.set(session_id, data)

    def add_asked_question(self, session_id: str, question: str) -> None:
        data = self.get(session_id)
        asked = data.get("asked_questions", [])
        if question not in asked:
            asked.append(question)
        data["asked_questions"] = asked
        self.set(session_id, data)

    def increment_question_count(self, session_id: str) -> int:
        data = self.get(session_id)
        count = data.get("question_count", 0) + 1
        data["question_count"] = count
        self.set(session_id, data)
        return count

    def average_score(self, session_id: str) -> Optional[float]:
        data = self.get(session_id)
        history = data.get("score_history", [])
        return round(sum(history) / len(history), 3) if history else None