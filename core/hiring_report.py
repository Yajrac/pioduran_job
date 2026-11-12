"""Extra context for Reports > Hired Records (presets, KPI tiles, breakdown bars)."""
from datetime import timedelta

from django.utils import timezone


def date_presets(current_from, current_to):
    today = timezone.localdate()
    presets = [
        ("This month", today.replace(day=1), today),
        ("Last 30 days", today - timedelta(days=29), today),
        ("This year", today.replace(month=1, day=1), today),
    ]
    rows = [{"label": label, "from": start.isoformat(), "to": end.isoformat(),
             "active": current_from == start.isoformat() and current_to == end.isoformat()}
            for label, start, end in presets]
    rows.append({"label": "All time", "from": "", "to": "", "active": not current_from and not current_to})
    return rows


def hiring_kpis(hired):
    measured = [item for item in hired if getattr(item, "time_to_hire_days", None) is not None]
    fastest = min(measured, key=lambda item: item.time_to_hire_days, default=None)
    slowest = max(measured, key=lambda item: item.time_to_hire_days, default=None)
    return {"total": len(hired), "measured": len(measured), "fastest": fastest, "slowest": slowest}


def breakdown_bars(stats):
    rows = sorted(stats.get("breakdown", []), key=lambda row: (row["average_days"], row["employer"].casefold()))
    longest = max([row["average_days"] for row in rows] + [0])
    for row in rows:
        row["percent"] = round(row["average_days"] / longest * 100) if longest else 0
    return rows
