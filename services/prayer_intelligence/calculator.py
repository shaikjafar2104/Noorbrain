from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo


# Kaaba coordinates
KAABA_LATITUDE = 21.422487
KAABA_LONGITUDE = 39.826206


def calculate_qibla_direction(
    latitude: float,
    longitude: float,
) -> float:
    """Calculate Qibla compass bearing (degrees from North) toward the Kaaba.

    Uses the great-circle initial bearing formula. Returns 0–360 degrees.
    """
    lat1 = math.radians(latitude)
    lon1 = math.radians(longitude)
    lat2 = math.radians(KAABA_LATITUDE)
    lon2 = math.radians(KAABA_LONGITUDE)

    d_lon = lon2 - lon1
    y = math.sin(d_lon) * math.cos(lat2)
    x = (
        math.sin(lat2) * math.cos(lat1)
        - math.sin(lat1) * math.cos(lat2) * math.cos(d_lon)
    )
    bearing = math.degrees(math.atan2(y, x))
    return _fix_angle(bearing)


def to_hijri_date(gregorian: date) -> dict[str, str | int]:
    """Convert a Gregorian date to Hijri (Islamic) date using tabular method.

    Uses the algorithm from the University of Umm Al-Qura algorithm.
    Returns a dict with: year, month, day, month_name, month_name_arabic.
    """
    hijri_months = [
        "Muharram", "Safar", "Rabi al-Awwal", "Rabi al-Thani",
        "Jumada al-Awwal", "Jumada al-Thani", "Rajab", "Sha'ban",
        "Ramadan", "Shawwal", "Dhu al-Qi'dah", "Dhu al-Hijjah",
    ]
    hijri_months_arabic = [
        "المحرم", "الصفر", "ربيع الأول", "ربيع الثاني",
        "جمادى الأولى", "جمادى الآخرة", "رجب", "شعبان",
        "رمضان", "شوال", "ذو القعدة", "ذو الحجة",
    ]

    # Tabular Islamic calendar: Hijri year 1 = 622-07-16 (Julian day 1948439.5)
    # Each year is 354 or 355 days. Leap years: year%30 in {2,5,7,10,13,16,18,21,24,26,29}
    def hijri_to_jd(year: int, month: int, day: int) -> float:
        """Convert Hijri date to Julian day."""
        return day + _days_from_hijri_year(year) + 1948439.5

    def _days_from_hijri_year(year: int) -> int:
        """Total days from Hijri year 1 to start of given year."""
        total = 0
        for y in range(1, year):
            total += 354 + (1 if _is_hijri_leap(y) else 0)
        return total

    def _is_hijri_leap(year: int) -> bool:
        return (year * 11 + 14) % 30 < 11

    def _hijri_month_length(year: int, month: int) -> int:
        """Length of Hijri month (1-indexed): 30 for odd, 29 for even, last=30 if leap."""
        if month < 1 or month > 12:
            return 29
        if month == 12 and _is_hijri_leap(year):
            return 30
        return 30 if month % 2 == 1 else 29

    # Start with approximate Hijri year
    jd = _julian_day(gregorian)
    hijri_year = int((jd - 1948439.5) / 354.375) + 1

    # Refine year
    while hijri_to_jd(hijri_year, 1, 1) > jd:
        hijri_year -= 1
    while hijri_to_jd(hijri_year + 1, 1, 1) <= jd:
        hijri_year += 1

    # Find month and day
    month = 1
    day_in_year = int(jd - hijri_to_jd(hijri_year, 1, 1) + 1)
    for m in range(1, 13):
        mlen = _hijri_month_length(hijri_year, m)
        if day_in_year <= mlen:
            month = m
            day = day_in_year
            break
        day_in_year -= mlen
    else:
        month = 1
        day = 1

    return {
        "year": hijri_year,
        "month": month,
        "day": day,
        "month_name": hijri_months[month - 1],
        "month_name_arabic": hijri_months_arabic[month - 1],
        "is_leap_year": _is_hijri_leap(hijri_year),
    }


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
