"""Time helpers for the OLS app.

`datetime.utcnow()` is deprecated (and scheduled for removal) because it returns
a naive datetime that silently claims to be local time. The whole app, however,
stores and compares naive UTC datetimes (the ORM columns are plain `DateTime`,
not `DateTime(timezone=True)`). Switching to timezone-aware datetimes wholesale
would make those values non-comparable with existing naive values and raise
`TypeError` at runtime.

`utcnow()` keeps the exact previous semantics — a naive datetime in UTC — while
using the non-deprecated, explicit computation.
"""

from datetime import datetime, timezone

__all__ = ["utcnow"]


def utcnow() -> datetime:
    """Return the current UTC time as a naive datetime (no tzinfo).

    Drop-in replacement for the deprecated ``datetime.utcnow()``.
    """
    return datetime.now(timezone.utc).replace(tzinfo=None)
