import csv
import io
import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import BinaryIO, TextIO


FILENAME_PATTERN = re.compile(
    r"^(?P<model>.+)-"
    r"(?P<date>\d{4}-\d{2}-\d{2})-"
    r"(?P<time>\d{6})\.csv$",
    re.IGNORECASE,
)


class FlightLogParseError(ValueError):
    """Raised when a flight log cannot be parsed."""


@dataclass(frozen=True)
class ParsedFlightLog:
    filename: str
    model: str
    start_datetime: datetime
    end_datetime: datetime
    flight_time: timedelta
    start_voltage: Decimal
    end_voltage: Decimal

    @property
    def date(self):
        return self.start_datetime.date()

    @property
    def start_time(self):
        return self.start_datetime.time()

    @property
    def end_time(self):
        return self.end_datetime.time()


def parse_model_name(filename: str) -> str:
    basename = Path(filename).name
    match = FILENAME_PATTERN.match(basename)

    if not match:
        raise FlightLogParseError(
            "Tiedostonimen pitää olla muodossa "
            "Mallinimi-YYYY-MM-DD-HHmmSS.csv."
        )

    return match.group("model")


def parse_log_datetime(date_value: str, time_value: str) -> datetime:
    value = f"{date_value.strip()} {time_value.strip()}"

    try:
        return datetime.strptime(value, "%Y-%m-%d %H:%M:%S.%f")
    except ValueError:
        try:
            return datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
        except ValueError as error:
            raise FlightLogParseError(
                f"Incorrect date- or timeformat: {value}"
            ) from error


def parse_flight_log(uploaded_file) -> ParsedFlightLog:
    filename = Path(uploaded_file.name).name
    model = parse_model_name(filename)

    uploaded_file.seek(0)

    text_stream = io.TextIOWrapper(
        uploaded_file,
        encoding="utf-8-sig",
        newline="",
    )

    try:
        reader = csv.DictReader(text_stream)

        if reader.fieldnames is None:
            raise FlightLogParseError("CSV-header is missing.")

        required_fields = {"Date", "Time", "RxBt(V)"}
        missing_fields = required_fields.difference(reader.fieldnames)

        if missing_fields:
            missing = ", ".join(sorted(missing_fields))
            raise FlightLogParseError(
                f"CSV-file has no fields: {missing}"
            )

        first_row = None
        last_row = None

        for row in reader:
            if not any(row.values()):
                continue

            if first_row is None:
                first_row = row

            last_row = row

        if first_row is None or last_row is None:
            raise FlightLogParseError(
                "CSV-file has no datarows."
            )

        start_datetime = parse_log_datetime(
            first_row["Date"],
            first_row["Time"],
        )

        end_datetime = parse_log_datetime(
            last_row["Date"],
            last_row["Time"],
        )

        if end_datetime < start_datetime:
            raise FlightLogParseError(
                "Log stopping time before starting time"
            )

        try:
            start_voltage = Decimal(first_row["RxBt(V)"].strip())
            end_voltage = Decimal(last_row["RxBt(V)"].strip())
        except Exception as error:
            raise FlightLogParseError(
                "RxBt(V)-field has incorrect Voltage value."
            ) from error

        return ParsedFlightLog(
            filename=filename,
            model=model,
            start_datetime=start_datetime,
            end_datetime=end_datetime,
            flight_time=end_datetime - start_datetime,
            start_voltage=start_voltage,
            end_voltage=end_voltage,
        )

    finally:
        text_stream.detach()