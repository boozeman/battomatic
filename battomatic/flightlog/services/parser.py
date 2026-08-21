import csv
import io
import math
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

def format_duration(duration: timedelta) -> str:
    total_seconds = max(0, int(duration.total_seconds()))

    minutes, seconds = divmod(total_seconds, 60)

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
    max_altitude_m: Decimal | None = None
    max_distance_m: Decimal | None = None
    distance_flown_m: Decimal | None = None
    max_speed_kmh: Decimal | None = None
    average_speed_kmh: Decimal | None = None
    max_satellites: int | None = None

    @property
    def date(self):
        return self.start_datetime.date()

    @property
    def start_time(self):
        return self.start_datetime.time()

    @property
    def end_time(self):
        return self.end_datetime.time()

    @property
    def formatted_flight_time(self):
        return format_duration(self.flight_time)


def parse_model_name(filename: str) -> str:
    basename = Path(filename).name
    match = FILENAME_PATTERN.match(basename)

    if not match:
        raise FlightLogParseError(
            "File name must be "
            "ModelName-YYYY-MM-DD-HHmmSS.csv."
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
    rows,
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
            "Log Ending time Before Starting time."
        )

    try:
        start_voltage = Decimal(first_row["RxBt(V)"].strip())
        end_voltage = Decimal(last_row["RxBt(V)"].strip())
    except (AttributeError, ArithmeticError, ValueError) as error:
        raise FlightLogParseError(
            "RxBt(V)-field has incorrect Voltage value."
        ) from error

    gps_metrics = calculate_gps_metrics(rows)

    return ParsedFlightLog(
        filename=filename,
        model=model,
        start_datetime=start_datetime,
        end_datetime=end_datetime,
        flight_time=end_datetime - start_datetime,
        start_voltage=start_voltage,
        end_voltage=end_voltage,
        **gps_metrics,
    )


EARTH_RADIUS_M = 6_371_008.8
MAX_GPS_SPEED_KMH = 500


def _distance_m(first, second) -> float:
    lat1, lon1 = map(math.radians, first)
    lat2, lon2 = map(math.radians, second)
    latitude_delta = lat2 - lat1
    longitude_delta = lon2 - lon1
    haversine = (
        math.sin(latitude_delta / 2) ** 2
        + math.cos(lat1)
        * math.cos(lat2)
        * math.sin(longitude_delta / 2) ** 2
    )
    return 2 * EARTH_RADIUS_M * math.asin(math.sqrt(haversine))


def _parse_gps_row(row):
    try:
        latitude, longitude = map(float, row["GPS"].split())
        altitude = float(row["GAlt(m)"])
        satellites = int(float(row["Sats"]))
        timestamp = parse_log_datetime(row["Date"], row["Time"])
    except (AttributeError, KeyError, TypeError, ValueError):
        return None

    if not (
        math.isfinite(latitude)
        and math.isfinite(longitude)
        and math.isfinite(altitude)
        and -90 <= latitude <= 90
        and -180 <= longitude <= 180
        and (latitude != 0 or longitude != 0)
        and satellites > 0
    ):
        return None

    return timestamp, (latitude, longitude), altitude


def calculate_gps_metrics(rows) -> dict:
    points = []
    speeds = []
    satellite_counts = []

    for row in rows:
        point = _parse_gps_row(row)
        if point is not None:
            points.append(point)

        try:
            speed = float(row["GSpd(kmh)"])
            if math.isfinite(speed) and 0 <= speed <= MAX_GPS_SPEED_KMH:
                speeds.append(speed)
        except (KeyError, TypeError, ValueError):
            pass

        try:
            satellites = int(float(row["Sats"]))
            if satellites >= 0:
                satellite_counts.append(satellites)
        except (KeyError, TypeError, ValueError):
            pass

    def rounded_decimal(value):
        return Decimal(str(round(max(0, value), 1)))

    telemetry_metrics = {
        "max_speed_kmh": (
            rounded_decimal(max(speeds)) if speeds else None
        ),
        "average_speed_kmh": (
            rounded_decimal(sum(speeds) / len(speeds)) if speeds else None
        ),
        "max_satellites": max(satellite_counts) if satellite_counts else None,
    }

    if not points:
        return {
            "max_altitude_m": None,
            "max_distance_m": None,
            "distance_flown_m": None,
            **telemetry_metrics,
        }

    accepted = [points[0]]
    for point in points[1:]:
        elapsed_seconds = (point[0] - accepted[-1][0]).total_seconds()
        if elapsed_seconds <= 0:
            continue

        segment_distance = _distance_m(accepted[-1][1], point[1])
        speed_kmh = segment_distance / elapsed_seconds * 3.6
        if speed_kmh <= MAX_GPS_SPEED_KMH:
            accepted.append(point)

    start_position = accepted[0][1]
    start_altitude = accepted[0][2]
    max_altitude = max(point[2] - start_altitude for point in accepted)
    max_distance = max(
        _distance_m(start_position, point[1])
        for point in accepted
    )
    distance_flown = sum(
        _distance_m(first[1], second[1])
        for first, second in zip(accepted, accepted[1:])
    )

    return {
        "max_altitude_m": rounded_decimal(max_altitude),
        "max_distance_m": rounded_decimal(max_distance),
        "distance_flown_m": rounded_decimal(distance_flown),
        **telemetry_metrics,
    }


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
                "CSV-file has no Header."
            )

        required_fields = {"Date", "Time", "RxBt(V)"}
        missing_fields = required_fields.difference(reader.fieldnames)

        if missing_fields:
            missing = ", ".join(sorted(missing_fields))
            raise FlightLogParseError(
                f"CSV-file has missing fields: {missing}"
            )

        parsed_logs = []
        first_row = None
        last_row = None
        current_rows = []

        for row in reader:
            if not any(row.values()):
                continue

            voltage_value = row.get("RxBt(V)", "").strip()

            try:
                voltage = Decimal(voltage_value)
            except (ArithmeticError, ValueError):
                voltage = Decimal("0")

            if voltage <= 0:
                continue

            if first_row is None:
                first_row = row

            last_row = row
            current_rows.append(row)

        if first_row is not None and last_row is not None:
            parsed_logs.append(
                build_parsed_log(
                    filename=filename,
                    model=model,
                    first_row=first_row,
                    last_row=last_row,
                    rows=current_rows,
                )
            )

        if not parsed_logs:
            raise FlightLogParseError(
                "CSV-file does not Contain Meaningful Flight Data."
            )

        return parsed_logs

    finally:
        text_stream.detach()


def parse_flight_log(uploaded_file) -> ParsedFlightLog:
    parsed_logs = parse_flight_logs(uploaded_file)

    if len(parsed_logs) != 1:
        raise FlightLogParseError(
            f"CSV-file contains {len(parsed_logs)} Flights."
        )

    return parsed_logs[0]


def format_duration(duration: timedelta) -> str:
    total_seconds = max(0, int(duration.total_seconds()))

    minutes, seconds = divmod(total_seconds, 60)

    return f"{minutes:02d}:{seconds:02d}"
