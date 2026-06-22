
import logging
import sys
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

LOG_FILE     = LOG_DIR / "interview_coach.log"
ERROR_FILE   = LOG_DIR / "errors.log"
SESSION_FILE = LOG_DIR / "sessions.jsonl" 



class ColorFormatter(logging.Formatter):

    COLORS = {
        logging.DEBUG:    "\033[36m",    # cyan
        logging.INFO:     "\033[32m",    # green
        logging.WARNING:  "\033[33m",    # yellow
        logging.ERROR:    "\033[31m",    # red
        logging.CRITICAL: "\033[1;31m",  # bold red
    }
    RESET = "\033[0m"

    FMT = "[{levelname:<8}] {asctime} | {name:<30} | {message}"

    def format(self, record: logging.LogRecord) -> str:
        color = self.COLORS.get(record.levelno, "")

        formatter = logging.Formatter(
            color + self.FMT + self.RESET,
            datefmt="%H:%M:%S",
            style="{",
        )
        return formatter.format(record)



class JSONFormatter(logging.Formatter):

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts":      datetime.now(timezone.utc).isoformat(),
            "level":   record.levelname,
            "logger":  record.name,
            "msg":     record.getMessage(),
        }
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        if hasattr(record, "extra"):
            payload.update(record.extra)
        return json.dumps(payload, ensure_ascii=False)




def _setup_root_logger() -> None:
    root = logging.getLogger()
    if root.handlers:          
        return

    root.setLevel(logging.DEBUG)
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.INFO)
    ch.setFormatter(ColorFormatter())
    root.addHandler(ch)
    fh = logging.FileHandler(LOG_FILE, encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(JSONFormatter())
    root.addHandler(fh)

    eh = logging.FileHandler(ERROR_FILE, encoding="utf-8")
    eh.setLevel(logging.WARNING)
    eh.setFormatter(JSONFormatter())
    root.addHandler(eh)


_setup_root_logger()




def get_logger(name: str) -> logging.Logger:
  
    return logging.getLogger(name)




def log_session_event(event: str, session_id: str, **kwargs: Any) -> None:
   
    record: dict[str, Any] = {
        "ts":         datetime.now(timezone.utc).isoformat(),
        "event":      event,
        "session_id": session_id,
        **kwargs,
    }
    with SESSION_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")

    get_logger("session").debug("session_event | %s | %s", event, session_id,
                                extra={"extra": record})


def log_llm_call(
    session_id: str,
    agent: str,
    model: str,
    prompt_tokens: int,
    completion_tokens: int,
    latency_ms: float,
    complexity: str = "medium",
) -> None:

    log_session_event(
        "llm_call",
        session_id,
        agent=agent,
        model=model,
        complexity=complexity,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=prompt_tokens + completion_tokens,
        latency_ms=round(latency_ms, 1),
    )


def log_agent_result(
    session_id: str,
    agent: str,
    score: float | None = None,
    feedback_len: int = 0,
    **kwargs: Any,
) -> None:
   
    log_session_event(
        "agent_result",
        session_id,
        agent=agent,
        score=score,
        feedback_len=feedback_len,
        **kwargs,
    )