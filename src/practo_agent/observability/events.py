"""JSON Lines events with a strict, privacy-safe field allowlist."""

import contextvars
import json
import logging
import os
import threading
import time
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator


_TRACE_ID: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "practo_trace_id",
    default=None,
)
_EVENT_FIELDS: dict[str, frozenset[str]] = {
    "request_completed": frozenset(
        {
            "transport",
            "operation",
            "outcome",
            "duration_ms",
            "status_code",
        }
    ),
    "workflow_routed": frozenset(
        {
            "retrieval_enabled",
            "lookup_enabled",
            "clarification_required",
        }
    ),
    "tool_completed": frozenset({"tool_name", "tool_status"}),
}
_REQUIRED_EVENT_FIELDS = {
    "request_completed": frozenset(
        {"transport", "operation", "outcome", "duration_ms"}
    ),
    "workflow_routed": frozenset(
        {
            "retrieval_enabled",
            "lookup_enabled",
            "clarification_required",
        }
    ),
    "tool_completed": frozenset({"tool_name", "tool_status"}),
}
_SAFE_STRING_VALUES = {
    "transport": frozenset({"http", "websocket"}),
    "operation": frozenset(
        {
            "health",
            "query",
            "unknown",
            "websocket_query",
            "websocket_connection",
        }
    ),
    "outcome": frozenset(
        {
            "answered",
            "abstained",
            "success",
            "client_error",
            "server_error",
            "invalid_request",
            "invalid_session",
            "disconnected",
        }
    ),
    "tool_name": frozenset(
        {
            "search_practo_knowledge_base",
            "check_appointment_status",
        }
    ),
    "tool_status": frozenset(
        {
            "success",
            "no_evidence",
            "not_found",
            "error",
        }
    ),
}


class JsonlEventLogger:
    """Append validated JSON objects as one record per line."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self._logger = logging.getLogger(
            f"practo_agent.jsonl.{uuid.uuid4().hex}"
        )
        self._logger.setLevel(logging.INFO)
        self._logger.propagate = False
        self.path.parent.mkdir(parents=True, exist_ok=True)
        handler = logging.FileHandler(self.path, encoding="utf-8")
        handler.setFormatter(logging.Formatter("%(message)s"))
        self._logger.addHandler(handler)

    def write(self, event: str, **fields: object) -> None:
        """Validate safe event fields and append a structured record."""

        allowed_fields = _EVENT_FIELDS.get(event)
        if allowed_fields is None:
            raise ValueError(f"Unsupported observability event: {event!r}.")
        unexpected = fields.keys() - allowed_fields
        if unexpected:
            raise ValueError(
                "Unsupported fields for observability event "
                f"{event!r}: {sorted(unexpected)}."
            )
        missing = _REQUIRED_EVENT_FIELDS[event] - fields.keys()
        if missing:
            raise ValueError(
                f"Missing required fields for observability event "
                f"{event!r}: {sorted(missing)}."
            )

        record: dict[str, object] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event": event,
        }
        trace_id = current_trace_id()
        if trace_id is not None:
            record["trace_id"] = trace_id

        for name, value in fields.items():
            if name in _SAFE_STRING_VALUES:
                if not isinstance(value, str) or value not in _SAFE_STRING_VALUES[name]:
                    raise ValueError(
                        f"Invalid safe value for observability field {name!r}."
                    )
            elif name in {
                "retrieval_enabled",
                "lookup_enabled",
                "clarification_required",
            }:
                if type(value) is not bool:
                    raise ValueError(
                        f"Observability field {name!r} must be a boolean."
                    )
            elif name == "duration_ms":
                if (
                    not isinstance(value, (int, float))
                    or isinstance(value, bool)
                    or value < 0
                ):
                    raise ValueError(
                        "Observability duration_ms must be non-negative."
                    )
            elif name == "status_code":
                if type(value) is not int or not 100 <= value <= 599:
                    raise ValueError(
                        "Observability status_code must be a valid HTTP status."
                    )
            record[name] = value

        self._logger.info(
            json.dumps(record, ensure_ascii=True, separators=(",", ":"))
        )

    def close(self) -> None:
        """Close and detach this logger's file handler."""

        for handler in self._logger.handlers[:]:
            handler.close()
            self._logger.removeHandler(handler)


_default_logger: JsonlEventLogger | None = None
_default_logger_path: Path | None = None
_DEFAULT_LOGGER_LOCK = threading.Lock()


def _get_default_logger() -> JsonlEventLogger:
    global _default_logger
    global _default_logger_path

    with _DEFAULT_LOGGER_LOCK:
        configured_path = Path(
            os.getenv("PRACTO_LOG_PATH", "logs/practo_agent.jsonl")
        )
        if _default_logger is None or configured_path != _default_logger_path:
            if _default_logger is not None:
                _default_logger.close()
            _default_logger = JsonlEventLogger(configured_path)
            _default_logger_path = configured_path
        return _default_logger


def log_event(event: str, **fields: object) -> None:
    """Write an allowlisted event to the configured JSONL log."""

    _get_default_logger().write(event, **fields)


def current_trace_id() -> str | None:
    """Return the active request trace ID, if one is set."""

    return _TRACE_ID.get()


class RequestTrace:
    """Request-scoped trace ID and completion timing."""

    def __init__(self, transport: str, operation: str) -> None:
        self.trace_id = uuid.uuid4().hex
        self.transport = transport
        self.operation = operation
        self._started_at = time.perf_counter()
        self._completed = False

    def complete(
        self,
        *,
        outcome: str,
        status_code: int | None = None,
    ) -> None:
        """Write one completion record for this request."""

        if self._completed:
            return
        fields: dict[str, object] = {
            "transport": self.transport,
            "operation": self.operation,
            "outcome": outcome,
            "duration_ms": round(
                (time.perf_counter() - self._started_at) * 1000,
                3,
            ),
        }
        if status_code is not None:
            fields["status_code"] = status_code
        log_event("request_completed", **fields)
        self._completed = True


@contextmanager
def request_trace(
    transport: str,
    operation: str,
) -> Iterator[RequestTrace]:
    """Set a trace ID for a request and guarantee a completion event."""

    trace = RequestTrace(transport, operation)
    token = _TRACE_ID.set(trace.trace_id)
    try:
        yield trace
    except Exception:
        trace.complete(outcome="server_error")
        raise
    finally:
        if not trace._completed:
            trace.complete(outcome="success")
        _TRACE_ID.reset(token)
