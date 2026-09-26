import dateparser


def parse_str_date(input_text: str) -> dict[str, str] | None:
    if not input_text:
        return None

    # settings={"PREFER_DAY_OF_MONTH": "current"} helps parse incomplete dates
    dt = dateparser.parse(input_text, settings={"PREFER_DAY_OF_MONTH": "current"})

    if not dt:
        return None

    return {"Date": dt.strftime("%d.%m.%Y"), "Time": dt.strftime("%H:%M:%S")}
