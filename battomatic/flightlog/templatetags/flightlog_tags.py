from datetime import timedelta

from django import template


register = template.Library()


@register.filter
def duration_human(value):
    """
    Format a timedelta value into a compact human-readable duration.

    Examples:
        0:00:05     -> 5 s
        0:05:32     -> 5 min 32 s
        1:08:14     -> 1 h 08 min 14 s
        2 days      -> 48 h 00 min 00 s
    """
    if value is None:
        return "—"

    if not isinstance(value, timedelta):
        return value

    total_seconds = max(0, int(value.total_seconds()))

    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)

    if hours:
        return f"{hours}:{minutes:02d}:{seconds:02d}"

    if minutes:
        return f"{minutes}:{seconds:02d}"

    return f"{minutes}:{seconds}"