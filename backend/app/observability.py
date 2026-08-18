"""Safe, request-local latency observations for backend integration diagnosis."""

from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar, Token
from dataclasses import dataclass, field
from time import perf_counter
from typing import Iterator


@dataclass(frozen=True)
class TimingEvent:
    """One completed stage with no prompt, evidence, or credential content."""

    stage: str
    start_ms: int
    end_ms: int
    duration_ms: int
    success: bool
    error_type: str | None = None


@dataclass
class RequestTiming:
    """A request-local timeline measured from the HTTP route entry."""

    _started_at: float = field(default_factory=perf_counter)
    events: list[TimingEvent] = field(default_factory=list)

    def elapsed_ms(self) -> int:
        return round((perf_counter() - self._started_at) * 1000)

    def as_safe_dict(self) -> dict[str, object]:
        return {
            "total_ms": self.elapsed_ms(),
            "events": [
                {
                    "stage": event.stage,
                    "start_ms": event.start_ms,
                    "end_ms": event.end_ms,
                    "duration_ms": event.duration_ms,
                    "success": event.success,
                    "error_type": event.error_type,
                }
                for event in self.events
            ],
        }


_request_timing: ContextVar[RequestTiming | None] = ContextVar("request_timing", default=None)
_active_stage: ContextVar[str | None] = ContextVar("active_timing_stage", default=None)


@contextmanager
def request_timing() -> Iterator[RequestTiming]:
    """Make a timing collector available to this synchronous request flow only."""

    timing = RequestTiming()
    token: Token[RequestTiming | None] = _request_timing.set(timing)
    try:
        yield timing
    finally:
        _request_timing.reset(token)


def active_stage() -> str | None:
    """Return the current business stage without carrying request content."""

    return _active_stage.get()


@contextmanager
def time_stage(stage: str) -> Iterator[None]:
    """Record the duration and failure type of a named, content-free stage."""

    timing = _request_timing.get()
    stage_token: Token[str | None] = _active_stage.set(stage)
    started_at = perf_counter()
    start_ms = timing.elapsed_ms() if timing is not None else 0
    try:
        yield
    except Exception as exc:
        if timing is not None:
            end_ms = timing.elapsed_ms()
            timing.events.append(
                TimingEvent(
                    stage=stage,
                    start_ms=start_ms,
                    end_ms=end_ms,
                    duration_ms=round((perf_counter() - started_at) * 1000),
                    success=False,
                    error_type=type(exc).__name__,
                )
            )
        raise
    else:
        if timing is not None:
            end_ms = timing.elapsed_ms()
            timing.events.append(
                TimingEvent(
                    stage=stage,
                    start_ms=start_ms,
                    end_ms=end_ms,
                    duration_ms=round((perf_counter() - started_at) * 1000),
                    success=True,
                )
            )
    finally:
        _active_stage.reset(stage_token)
