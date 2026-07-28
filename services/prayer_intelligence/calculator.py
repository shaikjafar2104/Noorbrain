from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo


@dataclass(frozen=True)
class PrayerSettings:
    latitude: float
    longitude: float
    timezone: str
    fajr_angle: float = 18.0
    isha_angle: float = 17.0
    asr_factor: float = 1.0
    dhuhr_offset_minutes: int = 2
    maghrib_offset_minutes: int = 0


def _fix_angle(value: float) -> float:
    return value % 360.0


def _fix_hour(value: float) -> float:
    return value % 24.0


def _julian_day(day: date) -> float:
    year = day.year
    month = day.month
    d = day.day

    if month <= 2:
        year -= 1
        month += 12

    a = year // 100
    b = 2 - a + (a // 4)

    return (
        math.floor(365.25 * (year + 4716))
        + math.floor(30.6001 * (month + 1))
        + d
        + b
        - 1524.5
    )


def _sun_position(jd: float) -> tuple[float, float]:
    days = jd - 2451545.0
    g = _fix_angle(357.529 + 0.98560028 * days)
    q = _fix_angle(280.459 + 0.98564736 * days)
    longitude = _fix_angle(
        q
        + 1.915 * math.sin(math.radians(g))
        + 0.020 * math.sin(math.radians(2 * g))
    )

    obliquity = 23.439 - 0.00000036 * days
    right_ascension = math.degrees(
        math.atan2(
            math.cos(math.radians(obliquity))
            * math.sin(math.radians(longitude)),
            math.cos(math.radians(longitude)),
        )
    ) / 15.0
    right_ascension = _fix_hour(right_ascension)

    declination = math.degrees(
        math.asin(
            math.sin(math.radians(obliquity))
            * math.sin(math.radians(longitude))
        )
    )

    equation = q / 15.0 - right_ascension
    return declination, equation


def _midday(jd: float, longitude: float) -> float:
    _, equation = _sun_position(jd)
    return _fix_hour(12.0 - equation - longitude / 15.0)


def _hour_angle(latitude: float, declination: float, altitude: float) -> float:
    numerator = (
        math.sin(math.radians(altitude))
        - math.sin(math.radians(latitude))
        * math.sin(math.radians(declination))
    )
    denominator = (
        math.cos(math.radians(latitude))
        * math.cos(math.radians(declination))
    )

    value = max(-1.0, min(1.0, numerator / denominator))
    return math.degrees(math.acos(value)) / 15.0


def _asr_altitude(latitude: float, declination: float, factor: float) -> float:
    angle = math.degrees(
        math.atan(
            1.0
            / (
                factor
                + math.tan(
                    math.radians(abs(latitude - declination))
                )
            )
        )
    )
    return angle


def _timezone_offset(day: date, timezone_name: str) -> float:
    zone = ZoneInfo(timezone_name)
    probe = datetime.combine(day, time(12, 0), tzinfo=zone)
    offset = probe.utcoffset()
    return (offset.total_seconds() / 3600.0) if offset else 0.0


def _to_datetime(day: date, decimal_hour: float, timezone_name: str) -> datetime:
    zone = ZoneInfo(timezone_name)
    decimal_hour = _fix_hour(decimal_hour)
    hour = int(decimal_hour)
    minute_float = (decimal_hour - hour) * 60.0
    minute = int(minute_float)
    second = int(round((minute_float - minute) * 60.0))

    if second >= 60:
        second = 0
        minute += 1

    if minute >= 60:
        minute = 0
        hour = (hour + 1) % 24

    return datetime.combine(
        day,
        time(hour, minute, second),
        tzinfo=zone,
    )


def calculate_prayer_times(
    day: date,
    settings: PrayerSettings,
) -> dict[str, datetime]:
    jd = _julian_day(day)
    declination, _ = _sun_position(jd)
    noon_utc = _midday(jd, settings.longitude)

    sunrise_angle = -0.833
    sunrise_hour_angle = _hour_angle(
        settings.latitude,
        declination,
        sunrise_angle,
    )
    fajr_hour_angle = _hour_angle(
        settings.latitude,
        declination,
        -abs(settings.fajr_angle),
    )
    isha_hour_angle = _hour_angle(
        settings.latitude,
        declination,
        -abs(settings.isha_angle),
    )
    asr_angle = _asr_altitude(
        settings.latitude,
        declination,
        settings.asr_factor,
    )
    asr_hour_angle = _hour_angle(
        settings.latitude,
        declination,
        asr_angle,
    )

    tz_offset = _timezone_offset(day, settings.timezone)

    raw = {
        "fajr": noon_utc - fajr_hour_angle + tz_offset,
        "sunrise": noon_utc - sunrise_hour_angle + tz_offset,
        "dhuhr": noon_utc
        + tz_offset
        + settings.dhuhr_offset_minutes / 60.0,
        "asr": noon_utc + asr_hour_angle + tz_offset,
        "maghrib": noon_utc
        + sunrise_hour_angle
        + tz_offset
        + settings.maghrib_offset_minutes / 60.0,
        "isha": noon_utc + isha_hour_angle + tz_offset,
    }

    return {
        name: _to_datetime(day, value, settings.timezone)
        for name, value in raw.items()
    }
