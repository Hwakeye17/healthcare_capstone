"""Context-aware in-process caching for structured agent responses."""

import hashlib
import json
import re
import threading
import unicodedata
from collections.abc import Callable

from practo_agent.schemas import AgentResponse, ResponseStatus


_WHITESPACE_PATTERN = re.compile(r"\s+")


def normalize_query(query: str) -> str:
    """Normalize equivalent query strings for deterministic cache keys."""

    if not isinstance(query, str) or not query.strip():
        raise ValueError("query must be a non-empty string.")

    normalized = unicodedata.normalize("NFKC", query)
    return _WHITESPACE_PATTERN.sub(" ", normalized.casefold()).strip()


class ResponseCache:
    """Cache answered responses by normalized query and relevant context.

    Context and scope are part of the key so that conversation turns and
    separate sessions cannot reuse a response generated in a different
    context. Only answered responses are cached.
    """

    def __init__(self) -> None:
        self._responses: dict[str, AgentResponse] = {}
        self._lock = threading.RLock()
        self._hits = 0
        self._misses = 0
        self._compute_invocations = 0

    @staticmethod
    def make_key(
        query: str,
        *,
        context: str = "",
        scope: str = "",
    ) -> str:
        """Return a deterministic digest for query, context, and scope."""

        normalized_query = normalize_query(query)
        if not isinstance(context, str):
            raise TypeError("context must be a string.")
        if not isinstance(scope, str):
            raise TypeError("scope must be a string.")

        key_data = json.dumps(
            {
                "query": normalized_query,
                "context": _normalize_context(context),
                "scope": unicodedata.normalize("NFKC", scope),
            },
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(key_data.encode("utf-8")).hexdigest()

    def get_or_compute(
        self,
        query: str,
        compute: Callable[[], AgentResponse],
        *,
        context: str = "",
        scope: str = "",
    ) -> tuple[AgentResponse, bool]:
        """Return a cached response or compute and optionally cache one.

        The boolean indicates whether the response came from the cache.
        Computation runs outside the lock; concurrent misses may therefore
        compute the same key independently, but never block unrelated keys.
        """

        if not callable(compute):
            raise TypeError("compute must be callable.")

        key = self.make_key(query, context=context, scope=scope)
        with self._lock:
            cached_response = self._responses.get(key)
            if cached_response is not None:
                self._hits += 1
                return cached_response, True
            self._misses += 1
            self._compute_invocations += 1

        response = compute()
        if not isinstance(response, AgentResponse):
            raise TypeError("compute must return an AgentResponse.")

        if response.status == ResponseStatus.ANSWERED:
            with self._lock:
                self._responses[key] = response

        return response, False

    @property
    def stats(self) -> dict[str, int]:
        """Return a consistent snapshot of cache activity."""

        with self._lock:
            return {
                "hits": self._hits,
                "misses": self._misses,
                "compute_invocations": self._compute_invocations,
                "entries": len(self._responses),
            }

    def clear(self) -> None:
        """Remove cached responses and reset activity counters."""

        with self._lock:
            self._responses.clear()
            self._hits = 0
            self._misses = 0
            self._compute_invocations = 0


def _normalize_context(context: str) -> str:
    normalized = unicodedata.normalize("NFKC", context)
    return _WHITESPACE_PATTERN.sub(" ", normalized.casefold()).strip()
