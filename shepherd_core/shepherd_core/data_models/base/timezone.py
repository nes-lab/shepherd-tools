"""Helper-functions for better support of timezones."""

import time
from datetime import datetime
from datetime import timedelta
from datetime import timezone


def local_tz() -> timezone:
    """Query the local timezone of the user."""
    if time.daylight:
        return timezone(timedelta(seconds=-time.altzone), time.tzname[1])
    return timezone(timedelta(seconds=-time.timezone), time.tzname[0])


def local_now() -> datetime:
    """Query the local date-time of the user."""
    return datetime.now(tz=local_tz())


def local_iso_date() -> str:
    """Query the local date-time of the user as a ISO 8601 date."""
    return local_now().date().isoformat()
