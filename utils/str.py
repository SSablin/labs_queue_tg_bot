months = {
    "January": 1,
    "February": 2,
    "March": 3,
    "April": 4,
    "May": 5,
    "June": 6,
    "July": 7,
    "August": 8,
    "September": 9,
    "October": 10,
    "November": 11,
    "December": 12,
}


async def parse_str_date(input_text: str) -> dict[str, str] | None:
    if not input_text:
        return None

    parts = input_text.split()
    if len(parts) != 7:
        return None

    try:
        month = months.get(parts[0])
        day = int(parts[1][:-1])  # Remove the comma
        year = int(parts[2])
        time = parts[4]
        time_of_day = parts[5]

        if month is None:
            return None
    except (ValueError, IndexError):
        return None

    if time_of_day == "PM":
        hour, minute, second = map(int, time.split(":"))
        if hour != 12:
            hour += 12
        time = f"{hour}:{minute:02d}:{second:02d}"
    elif time_of_day == "AM":
        hour, minute, second = map(int, time.split(":"))
        if hour == 12:
            hour = 0
        time = f"{hour}:{minute:02d}:{second:02d}"

    return {"date": f"{day:02d}.{month:02d}.{year:04d}", "time": f"{time}"}
