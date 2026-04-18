from datetime import time

PAIR_SLOTS = [
    {"number": 1, "start": time(8, 0), "end": time(9, 20)},
    {"number": 2, "start": time(9, 30), "end": time(10, 50)},
    {"number": 3, "start": time(11, 10), "end": time(12, 30)},
    {"number": 4, "start": time(12, 40), "end": time(14, 0)},
    {"number": 5, "start": time(14, 10), "end": time(15, 30)},
    {"number": 6, "start": time(15, 40), "end": time(17, 0)},
    {"number": 7, "start": time(17, 10), "end": time(18, 30)},
    {"number": 8, "start": time(18, 40), "end": time(20, 0)},
]


def get_booking_pair_numbers(start_dt, end_dt):
    found = []

    for pair in PAIR_SLOTS:
        pair_start = pair["start"]
        pair_end = pair["end"]

        booking_start = start_dt.time()
        booking_end = end_dt.time()

        overlaps = booking_start < pair_end and booking_end > pair_start
        if overlaps:
            found.append(pair["number"])

    return found


def get_booking_pair_label(start_dt, end_dt):
    numbers = get_booking_pair_numbers(start_dt, end_dt)

    if not numbers:
        return "Поза сіткою пар"

    if len(numbers) == 1:
        return f"{numbers[0]} пара"

    return f"{numbers[0]}–{numbers[-1]} пари"