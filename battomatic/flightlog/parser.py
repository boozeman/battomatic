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


def build_parsed_log(
    *,
    filename,
    model,
    first_row,
    last_row,
) -> ParsedFlightLog:
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
            "Lokin loppuaika on ennen aloitusaikaa."
        )

    try:
        start_voltage = Decimal(first_row["RxBt(V)"].strip())
        end_voltage = Decimal(last_row["RxBt(V)"].strip())
    except (AttributeError, ArithmeticError, ValueError) as error:
        raise FlightLogParseError(
            "RxBt(V)-kentässä on virheellinen jännitearvo."
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


def parse_flight_logs(uploaded_file) -> list[ParsedFlightLog]:
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
            raise FlightLogParseError(
                "CSV-tiedostosta puuttuu otsikkorivi."
            )

        required_fields = {"Date", "Time", "RxBt(V)"}
        missing_fields = required_fields.difference(reader.fieldnames)

        if missing_fields:
            missing = ", ".join(sorted(missing_fields))
            raise FlightLogParseError(
                f"CSV-tiedostosta puuttuvat kentät: {missing}"
            )

        parsed_logs = []
        first_row = None
        last_row = None

        for row in reader:
            if not any(row.values()):
                continue

            voltage_value = row.get("RxBt(V)", "").strip()

            try:
                voltage = Decimal(voltage_value)
            except (ArithmeticError, ValueError):
                voltage = Decimal("0")

            if voltage <= 0:
                if first_row is not None and last_row is not None:
                    parsed_logs.append(
                        build_parsed_log(
                            filename=filename,
                            model=model,
                            first_row=first_row,
                            last_row=last_row,
                        )
                    )

                    first_row = None
                    last_row = None

                continue

            if first_row is None:
                first_row = row

            last_row = row

        if first_row is not None and last_row is not None:
            parsed_logs.append(
                build_parsed_log(
                    filename=filename,
                    model=model,
                    first_row=first_row,
                    last_row=last_row,
                )
            )

        if not parsed_logs:
            raise FlightLogParseError(
                "CSV-tiedostossa ei ole kelvollisia lentorivejä."
            )

        return parsed_logs

    finally:
        text_stream.detach()


def parse_flight_log(uploaded_file) -> ParsedFlightLog:
    parsed_logs = parse_flight_logs(uploaded_file)

    if len(parsed_logs) != 1:
        raise FlightLogParseError(
            f"CSV-tiedosto sisältää {len(parsed_logs)} lentojaksoa."
        )

    return parsed_logs[0]