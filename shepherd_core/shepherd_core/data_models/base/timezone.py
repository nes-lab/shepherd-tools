import time
from datetime import datetime
from datetime import timedelta
from datetime import timezone


def local_tz() -> timezone:
    if time.daylight:
        return timezone(timedelta(seconds=-time.altzone), time.tzname[1])
    return timezone(timedelta(seconds=-time.timezone), time.tzname[0])


def local_now() -> datetime:
    return datetime.now(tz=local_tz())


def local_iso_date() -> str:
    return local_now().date().isoformat()
