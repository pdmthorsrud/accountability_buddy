"""Utility helpers for polling Vapi calls until structured outputs are available."""

from __future__ import annotations

import os
import time
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple


def parse_vapi_datetime(timestamp: Optional[str]) -> Optional[datetime]:
    """Parse an ISO 8601 timestamp from Vapi into a timezone-aware datetime."""
    if not timestamp:
        return None
    value = timestamp.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def _call_matches(
    call: object,
    *,
    assistant_id: str,
    target_number: str,
    base_time: Optional[datetime] = None,
    time_tolerance: Optional[timedelta] = None,
) -> bool:
    """Return True if the call matches the assistant/number/time constraints."""
    customer = getattr(call, "customer", None)
    if not customer:
        return False

    if isinstance(customer, dict):
        number = customer.get("number")
    else:
        number = getattr(customer, "number", None)

    if number != target_number:
        return False

    if getattr(call, "assistant_id", None) != assistant_id:
        return False

    if getattr(call, "status", None) != "ended":
        return False

    call_time: Optional[datetime] = None
    if base_time is not None:
        call_time = (
            parse_vapi_datetime(getattr(call, "ended_at", None))
            or parse_vapi_datetime(getattr(call, "started_at", None))
        )
        if not call_time:
            return False

        comparison_time = base_time
        if comparison_time.tzinfo is None:
            comparison_time = comparison_time.replace(tzinfo=timezone.utc)
        if call_time.tzinfo is None:
            call_time = call_time.replace(tzinfo=timezone.utc)

        same_day = call_time.astimezone(comparison_time.tzinfo).date() == comparison_time.date()
        if not same_day:
            return False

        if time_tolerance is not None:
            within_tolerance = (
                abs((call_time - comparison_time).total_seconds()) <= time_tolerance.total_seconds()
            )
            if not within_tolerance:
                return False

    artifact = getattr(call, "artifact", None)
    structured_outputs = getattr(artifact, "structured_outputs", {}) if artifact else {}
    return bool(structured_outputs)


def wait_for_structured_output(
    client: object,
    *,
    assistant_id: str,
    target_number: str,
    base_time: Optional[datetime] = None,
    poll_interval: float = 5.0,
    timeout: timedelta = timedelta(minutes=5),
    time_tolerance: timedelta = timedelta(hours=2),
) -> Optional[object]:
    """Poll Vapi for a completed call that has structured output for today.

    Args:
        client: The Vapi client instance.
        assistant_id: Assistant identifier to filter by.
        target_number: Phone number associated with the call.
        base_time: Timestamp the polling centres around (defaults to now in UTC).
        poll_interval: Seconds to wait between list calls.
        timeout: Maximum total time to wait before giving up. Use ``None`` for no timeout.
        time_tolerance: Acceptable delta from ``base_time`` for the call.

    Returns:
        The first call matching the filter criteria, or ``None`` if timed out.
    """
    comparison_time = base_time or datetime.now(timezone.utc)
    if comparison_time.tzinfo is None:
        comparison_time = comparison_time.replace(tzinfo=timezone.utc)

    deadline: Optional[float] = None
    if timeout is not None:
        deadline = time.monotonic() + timeout.total_seconds()

    attempt = 0
    while True:
        attempt += 1
        print(
            f"[VapiPolling] Attempt {attempt}: checking for structured output "
            f"({assistant_id=}, {target_number=})"
        )

        calls_list = client.calls.list()

        for entry in calls_list:
            if _call_matches(
                entry,
                assistant_id=assistant_id,
                target_number=target_number,
                base_time=comparison_time,
                time_tolerance=time_tolerance,
            ):
                full_call = client.calls.get(id=getattr(entry, "id", None))
                artifact = getattr(full_call, "artifact", None)
                structured_outputs = getattr(artifact, "structured_outputs", {}) if artifact else {}
                if structured_outputs:
                    print(
                        "[VapiPolling] Structured output found for call "
                        f"{getattr(full_call, 'id', 'unknown')} at "
                        f"{getattr(full_call, 'ended_at', getattr(full_call, 'started_at', 'unknown'))}"
                    )
                    return full_call

        if deadline is not None and time.monotonic() >= deadline:
            print("[VapiPolling] Timeout reached while waiting for structured output.")
            return None

        print(f"[VapiPolling] No matching structured output yet; sleeping {poll_interval} seconds.")
        time.sleep(poll_interval)


def _parse_number(value: Optional[str], default: float) -> float:
    if value is None:
        return default
    try:
        return float(value)
    except ValueError:
        print(f"[VapiPolling] Invalid numeric value '{value}'; falling back to {default}.")
        return default


def load_polling_configuration(
    *,
    poll_interval_default: float = 5.0,
    timeout_default_seconds: float = 0.0,
    tolerance_default_minutes: float = 120.0,
) -> Tuple[float, Optional[timedelta], timedelta]:
    """Load polling cadence/tolerance values from environment variables."""
    poll_interval = max(1.0, _parse_number(os.environ.get("VAPI_POLL_INTERVAL_SECONDS"), poll_interval_default))
    timeout_seconds = _parse_number(os.environ.get("VAPI_POLL_TIMEOUT_SECONDS"), timeout_default_seconds)
    tolerance_minutes = max(
        1.0,
        _parse_number(os.environ.get("VAPI_CALL_TIME_TOLERANCE_MINUTES"), tolerance_default_minutes),
    )

    timeout_delta = None
    if timeout_seconds > 0:
        timeout_delta = timedelta(seconds=timeout_seconds)

    tolerance_delta = timedelta(minutes=tolerance_minutes)
    return poll_interval, timeout_delta, tolerance_delta


def find_structured_call(
    client: object,
    *,
    assistant_id: str,
    target_number: str,
    base_time: Optional[datetime] = None,
    time_tolerance: Optional[timedelta] = None,
) -> Optional[object]:
    """Return the most recent call with structured outputs matching the filter."""
    calls_list = client.calls.list()
    for entry in calls_list:
        if _call_matches(
            entry,
            assistant_id=assistant_id,
            target_number=target_number,
            base_time=base_time,
            time_tolerance=time_tolerance,
        ):
            full_call = client.calls.get(id=getattr(entry, "id", None))
            artifact = getattr(full_call, "artifact", None)
            structured_outputs = getattr(artifact, "structured_outputs", {}) if artifact else {}
            if structured_outputs:
                return full_call
    return None
