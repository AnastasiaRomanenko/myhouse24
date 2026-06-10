from datetime import date
from random import randint


def generate_number() -> str:
    today = date.today()
    prefix = f"{today.month:02d}{today.day:02d}{today.year % 100:02d}"
    return f"{prefix}-{randint(0, 99999):05d}"
