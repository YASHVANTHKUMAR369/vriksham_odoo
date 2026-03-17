from datetime import datetime, date, time, timedelta


def ist_to_utc(ist_time):
    if not ist_time:  # if ist_time is False or None
        return None
    return ist_time - timedelta(hours=5, minutes=30)


def utc_to_ist(utc_time):
    if not utc_time:  # if utc_time is False or None
        return None
    return utc_time + timedelta(hours=5, minutes=30)
