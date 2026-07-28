from __future__ import annotations

from typing import Iterable


def point_in_polygon(
    x: float,
    y: float,
    points: Iterable[dict[str, float]],
) -> bool:
    polygon = list(points)

    if len(polygon) < 3:
        return False

    inside = False
    j = len(polygon) - 1

    for i in range(len(polygon)):
        xi = float(polygon[i]["x"])
        yi = float(polygon[i]["y"])
        xj = float(polygon[j]["x"])
        yj = float(polygon[j]["y"])

        intersects = (
            (yi > y) != (yj > y)
            and x
            < (xj - xi)
            * (y - yi)
            / ((yj - yi) or 1e-12)
            + xi
        )

        if intersects:
            inside = not inside

        j = i

    return inside
