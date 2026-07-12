from datetime import datetime, timedelta
from django.test import SimpleTestCase, override_settings
from decimal import Decimal
from .preview import find_duplicate_flights

from django.db import IntegrityError, transaction
from django.test import TestCase
from .models import Flight, FlightSession


from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase
from django.urls import reverse

from .forms import FlightLogUploadForm
from .parser import (
    format_duration,
    parse_flight_log,
    parse_flight_logs,
)

from .session_builder import (
    FlightSessionBuildError,
    get_new_battery_voltage_threshold,
)

from datetime import datetime
from decimal import Decimal

from .parser import ParsedFlightLog
from .session_builder import (
    FlightSessionBuildError,
    build_flight_sessions,
    get_new_battery_voltage_threshold,
)

from .import_service import build_import_preview

CSV_CONTENT = """Date,Time,FM,Ptch(rad),Roll(rad),Yaw(rad),RxBt(V),Curr(A),Capa(mAh),Bat%(%)
2026-07-10,16:39:41.300,"AIR",0.00,0.00,0.57,17.1,0.5,4,99
2026-07-10,16:39:42.300,"AIR",0.00,0.00,0.57,17.1,0.8,4,99
"""

@override_settings(
    STORAGES={
        "default": {
            "BACKEND": "django.core.files.storage.FileSystemStorage",
        },
        "staticfiles": {
            "BACKEND": (
                "django.contrib.staticfiles.storage.StaticFilesStorage"
            ),
        },
    }
)
class FlightLogParserTests(SimpleTestCase):
    def make_file(
        self,
        name="ModelName-2026-07-10-163941.csv",
        content=CSV_CONTENT,
    ):
        return SimpleUploadedFile(
            name=name,
            content=content.encode("utf-8"),
            content_type="text/csv",
        )

    def test_parse_flight_log(self):
        uploaded_file = self.make_file()

        result = parse_flight_log(uploaded_file)

        self.assertEqual(result.filename, uploaded_file.name)
        self.assertEqual(result.model, "ModelName")
        self.assertEqual(
            result.start_datetime.isoformat(),
            "2026-07-10T16:39:41.300000",
        )
        self.assertEqual(
            result.end_datetime.isoformat(),
            "2026-07-10T16:39:42.300000",
        )
        self.assertEqual(result.flight_time.total_seconds(), 1)
        self.assertEqual(str(result.start_voltage), "17.1")
        self.assertEqual(str(result.end_voltage), "17.1")

    def test_model_name_can_contain_hyphens(self):
        uploaded_file = self.make_file(
            name="Flywoo-Firefly-2S-2026-07-10-163941.csv",
        )

        result = parse_flight_log(uploaded_file)

        self.assertEqual(result.model, "Flywoo-Firefly-2S")

    def test_splits_log_when_zero_voltage_separates_flights(self):
        csv_content = """Date,Time,RxBt(V)
2026-07-10,16:39:41.300,17.1
2026-07-10,16:39:42.300,16.9
2026-07-10,16:39:43.300,16.8
2026-07-10,16:39:44.300,0
2026-07-10,16:39:45.300,0
2026-07-10,16:39:46.300,0
2026-07-10,16:40:20.300,17.3
2026-07-10,16:40:21.300,17.1
2026-07-10,16:40:22.300,16.9
"""

        uploaded_file = self.make_file(content=csv_content)

        results = parse_flight_logs(uploaded_file)

        self.assertEqual(len(results), 2)

        first_flight = results[0]

        self.assertEqual(
            first_flight.start_datetime.isoformat(),
            "2026-07-10T16:39:41.300000",
        )
        self.assertEqual(
            first_flight.end_datetime.isoformat(),
            "2026-07-10T16:39:43.300000",
        )
        self.assertEqual(first_flight.flight_time.total_seconds(), 2)
        self.assertEqual(str(first_flight.start_voltage), "17.1")
        self.assertEqual(str(first_flight.end_voltage), "16.8")

        second_flight = results[1]

        self.assertEqual(
            second_flight.start_datetime.isoformat(),
            "2026-07-10T16:40:20.300000",
        )
        self.assertEqual(
            second_flight.end_datetime.isoformat(),
            "2026-07-10T16:40:22.300000",
        )
        self.assertEqual(second_flight.flight_time.total_seconds(), 2)
        self.assertEqual(str(second_flight.start_voltage), "17.3")
        self.assertEqual(str(second_flight.end_voltage), "16.9")


@override_settings(
    STORAGES={
        "default": {
            "BACKEND": "django.core.files.storage.FileSystemStorage",
        },
        "staticfiles": {
            "BACKEND": (
                "django.contrib.staticfiles.storage.StaticFilesStorage"
            ),
        },
    }
)
class FlightLogUploadFormTests(SimpleTestCase):
    def make_file(
        self,
        name="ModelName-2026-07-10-163941.csv",
        content=b"Date,Time,RxBt(V)\n"
        b"2026-07-10,16:39:41.300,17.1\n",
    ):
        return SimpleUploadedFile(
            name=name,
            content=content,
            content_type="text/csv",
        )

    def make_form(self, uploaded_files, **data):
        form_data = {
            "cell_count": "4",
            "chemistry": "lihv",
        }
        form_data.update(data)

        return FlightLogUploadForm(
            data=form_data,
            files={
                "files": uploaded_files,
            },
        )

    def test_accepts_one_csv_file(self):
        form = self.make_form(
            self.make_file(),
        )

        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(
            len(form.cleaned_data["files"]),
            1,
        )

    def test_accepts_multiple_csv_files(self):
        first_file = self.make_file(
            name="Model-A-2026-07-10-163941.csv",
        )
        second_file = self.make_file(
            name="Model-B-2026-07-10-164500.csv",
        )

        form = self.make_form(
            [first_file, second_file],
        )

        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(
            len(form.cleaned_data["files"]),
            2,
        )

    def test_rejects_non_csv_file(self):
        uploaded_file = self.make_file(
            name="flight-log.txt",
        )

        form = self.make_form(uploaded_file)

        self.assertFalse(form.is_valid())
        self.assertIn("files", form.errors)
        self.assertIn(
            "Not a csv-file",
            form.errors["files"][0],
        )

    def test_rejects_empty_file(self):
        uploaded_file = self.make_file(
            content=b"",
        )

        form = self.make_form(uploaded_file)

        self.assertFalse(form.is_valid())
        self.assertIn("files", form.errors)
        self.assertIn(
            "File is empty.",
            form.errors["files"][0],
        )

    def test_cell_count_is_converted_to_integer(self):
        form = self.make_form(
            self.make_file(),
            cell_count="4",
        )

        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(
            form.cleaned_data["cell_count"],
            4,
        )
        self.assertIsInstance(
            form.cleaned_data["cell_count"],
            int,
        )

    def test_accepts_lipo_chemistry(self):
        form = self.make_form(
            self.make_file(),
            cell_count="6",
            chemistry="lipo",
        )

        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(
            form.cleaned_data["cell_count"],
            6,
        )
        self.assertEqual(
            form.cleaned_data["chemistry"],
            "lipo",
        )

    def test_requires_cell_count(self):
        form = FlightLogUploadForm(
            data={
                "chemistry": "lihv",
            },
            files={
                "files": self.make_file(),
            },
        )

        self.assertFalse(form.is_valid())
        self.assertIn("cell_count", form.errors)

    def test_requires_chemistry(self):
        form = FlightLogUploadForm(
            data={
                "cell_count": "4",
            },
            files={
                "files": self.make_file(),
            },
        )

        self.assertFalse(form.is_valid())
        self.assertIn("chemistry", form.errors)

    def test_session_preview_is_displayed(self):
        response = self.client.post(
            reverse("flightlog:upload"),
            data={
                "cell_count": "4",
                "chemistry": "lihv",
                "files": self.make_file(),
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Battery session 1")
        self.assertContains(response, "17.00 V")
        self.assertContains(
            response,
            "First flight on logset",
        )
        self.assertContains(response, "Total flight time")
        self.assertContains(response, "Longest flight")
        self.assertContains(response, "Shortest flight")        

    @override_settings(
        FLIGHTLOG_MAX_FILES=2,
        FLIGHTLOG_MAX_FILE_SIZE=1024,
        FLIGHTLOG_MAX_TOTAL_SIZE=4096,
    )
    def test_rejects_too_many_files(self):
        files = [
            self.make_file(
                name="Model-A-2026-07-10-100000.csv",
            ),
            self.make_file(
                name="Model-B-2026-07-10-101000.csv",
            ),
            self.make_file(
                name="Model-C-2026-07-10-102000.csv",
            ),
        ]

        form = self.make_form(files)

        self.assertFalse(form.is_valid())
        self.assertIn("files", form.errors)
        self.assertIn(
            "import 2 files",
            form.errors["files"][0],
        )

    @override_settings(
        FLIGHTLOG_MAX_FILES=10,
        FLIGHTLOG_MAX_FILE_SIZE=20,
        FLIGHTLOG_MAX_TOTAL_SIZE=1000,
    )
    def test_rejects_file_that_is_too_large(self):
        uploaded_file = self.make_file(
            content=b"x" * 21,
        )

        form = self.make_form(uploaded_file)

        self.assertFalse(form.is_valid())
        self.assertIn("files", form.errors)
        self.assertIn(
            "One file size limit is",
            form.errors["files"][0],
        )

    @override_settings(
        FLIGHTLOG_MAX_FILES=10,
        FLIGHTLOG_MAX_FILE_SIZE=100,
        FLIGHTLOG_MAX_TOTAL_SIZE=30,
    )
    def test_rejects_excessive_total_size(self):
        first_file = self.make_file(
            name="Model-A-2026-07-10-100000.csv",
            content=b"x" * 20,
        )
        second_file = self.make_file(
            name="Model-B-2026-07-10-101000.csv",
            content=b"x" * 20,
        )

        form = self.make_form(
            [first_file, second_file],
        )

        self.assertFalse(form.is_valid())
        self.assertIn("files", form.errors)
        self.assertIn(
            "Too many files at once.",
            form.errors["files"][0],
        )

class FlightTimeFormattingTests(SimpleTestCase):
    def test_formats_minutes_and_seconds(self):
        duration = timedelta(minutes=3, seconds=42)

        self.assertEqual(format_duration(duration), "03:42")

    def test_ignores_fractional_seconds(self):
        duration = timedelta(
            minutes=4,
            seconds=12,
            milliseconds=900,
        )

        self.assertEqual(format_duration(duration), "04:12")

    def test_supports_more_than_one_hour(self):
        duration = timedelta(
            hours=1,
            minutes=7,
            seconds=15,
        )

        self.assertEqual(format_duration(duration), "67:15")

    def test_formats_zero_duration(self):
        self.assertEqual(
            format_duration(timedelta()),
            "00:00",
        )

@override_settings(
    STORAGES={
        "default": {
            "BACKEND": "django.core.files.storage.FileSystemStorage",
        },
        "staticfiles": {
            "BACKEND": (
                "django.contrib.staticfiles.storage.StaticFilesStorage"
            ),
        },
    }
)

class FlightLogUploadViewTests(SimpleTestCase):
    def make_file(
        self,
        name="Modelname-2026-07-10-163941.csv",
        content=None,
    ):
        if content is None:
            content = """Date,Time,RxBt(V)
2026-07-10,16:39:41.300,17.1
2026-07-10,16:43:23.300,15.8
"""

        return SimpleUploadedFile(
            name=name,
            content=content.encode("utf-8"),
            content_type="text/csv",
        )

    def test_upload_page_opens(self):
        response = self.client.get(
            reverse("flightlog:upload"),
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response,
            "flightlog/upload.html",
        )

    def test_uploaded_log_is_displayed(self):
        response = self.client.post(
            reverse("flightlog:upload"),
            data={
                "cell_count": "4",
                "chemistry": "lihv",
                "files": self.make_file(),
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Model")
        self.assertContains(response, "03:42")
        self.assertContains(response, "17.1 V")
        self.assertContains(response, "15.8 V")
        self.assertEqual(len(response.context["flight_sessions"]), 1,)

    def test_invalid_log_error_is_displayed(self):
        uploaded_file = self.make_file(
            content="""Wrong,Header
foo,bar
""",
        )

        response = self.client.post(
            reverse("flightlog:upload"),
            data={
                "cell_count": "4",
                "chemistry": "lihv",
                "files": uploaded_file,
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            "CSV-file has missing fields:",
        )

    def test_log_with_zero_voltage_gap_displays_two_flights(self):
        csv_content = """Date,Time,RxBt(V)
2026-07-10,16:39:41.300,17.1
2026-07-10,16:39:43.300,16.8
2026-07-10,16:39:44.300,0
2026-07-10,16:40:20.300,17.3
2026-07-10,16:40:22.300,16.9
"""

        response = self.client.post(
            reverse("flightlog:upload"),
            data={
                "cell_count": "4",
                "chemistry": "lihv",
                "files": self.make_file(content=csv_content),
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            len(response.context["parsed_logs"]),
            2,
        )

    def test_duplicate_flights_prevent_session_preview(self):
        first_file = self.make_file(
            name="Mallinimi-2026-07-10-163941.csv",
        )
        second_file = self.make_file(
            name="Mallinimi-2026-07-10-163941.csv",
        )

        response = self.client.post(
            reverse("flightlog:upload"),
            data={
                "cell_count": "4",
                "chemistry": "lihv",
                "files": [
                    first_file,
                    second_file,
                ],
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            len(response.context["duplicate_flights"]),
            1,
        )
        self.assertEqual(
            response.context["flight_sessions"],
            (),
        )
        self.assertContains(
            response,
            "Duplicate flights detected",
        )

    def test_view_exposes_import_preview(self):
        response = self.client.post(
            reverse("flightlog:upload"),
            data={
                "cell_count": "4",
                "chemistry": "lihv",
                "files": self.make_file(),
            },
        )

        preview = response.context["preview"]

        self.assertIsNotNone(preview)
        self.assertTrue(preview.is_valid)
        self.assertEqual(preview.flight_count, 1)
        self.assertEqual(preview.session_count, 1)


@override_settings(
    STORAGES={
        "default": {
            "BACKEND": "django.core.files.storage.FileSystemStorage",
        },
        "staticfiles": {
            "BACKEND": (
                "django.contrib.staticfiles.storage.StaticFilesStorage"
            ),
        },
    }
)
class FlightSessionVoltageThresholdTests(SimpleTestCase):
    def test_four_cell_lipo_threshold(self):
        threshold = get_new_battery_voltage_threshold(
            cell_count=4,
            chemistry="lipo",
        )

        self.assertEqual(str(threshold), "16.00")

    def test_four_cell_lihv_threshold(self):
        threshold = get_new_battery_voltage_threshold(
            cell_count=4,
            chemistry="lihv",
        )

        self.assertEqual(str(threshold), "17.00")

    def test_six_cell_lipo_threshold(self):
        threshold = get_new_battery_voltage_threshold(
            cell_count=6,
            chemistry="lipo",
        )

        self.assertEqual(str(threshold), "24.00")

    def test_six_cell_lihv_threshold(self):
        threshold = get_new_battery_voltage_threshold(
            cell_count=6,
            chemistry="lihv",
        )

        self.assertEqual(str(threshold), "25.50")

    def test_rejects_unknown_chemistry(self):
        with self.assertRaises(FlightSessionBuildError):
            get_new_battery_voltage_threshold(
                cell_count=4,
                chemistry="nimh",
            )

    def test_rejects_zero_cell_count(self):
        with self.assertRaises(FlightSessionBuildError):
            get_new_battery_voltage_threshold(
                cell_count=0,
                chemistry="lipo",
            )

@override_settings(
    STORAGES={
        "default": {
            "BACKEND": "django.core.files.storage.FileSystemStorage",
        },
        "staticfiles": {
            "BACKEND": (
                "django.contrib.staticfiles.storage.StaticFilesStorage"
            ),
        },
    }
)
class FlightSessionBuilderTests(SimpleTestCase):
    def make_flight(
        self,
        *,
        start_time,
        duration_seconds,
        start_voltage,
        end_voltage,
        model="ModelName",
        date="2026-07-10",
    ):
        start_datetime = datetime.fromisoformat(
            f"{date}T{start_time}"
        )
        end_datetime = start_datetime + timedelta(
            seconds=duration_seconds
        )

        return ParsedFlightLog(
            filename=(
                f"{model}-{date}-"
                f"{start_datetime.strftime('%H%M%S')}.csv"
            ),
            model=model,
            start_datetime=start_datetime,
            end_datetime=end_datetime,
            flight_time=end_datetime - start_datetime,
            start_voltage=Decimal(start_voltage),
            end_voltage=Decimal(end_voltage),
        )

    def test_groups_flights_with_same_battery(self):
        flights = [
            self.make_flight(
                start_time="10:00:00",
                duration_seconds=180,
                start_voltage="17.30",
                end_voltage="15.90",
            ),
            self.make_flight(
                start_time="10:05:00",
                duration_seconds=200,
                start_voltage="16.20",
                end_voltage="15.40",
            ),
            self.make_flight(
                start_time="10:10:00",
                duration_seconds=160,
                start_voltage="15.80",
                end_voltage="15.10",
            ),
        ]

        sessions = build_flight_sessions(
            flights,
            cell_count=4,
            chemistry="lihv",
        )

        self.assertEqual(len(sessions), 1)
        self.assertEqual(sessions[0].session_count, 3)
        self.assertEqual(
            sessions[0].formatted_total_flight_time,
            "09:00",
        )
        self.assertEqual(
            sessions[0].formatted_longest_flight_time,
            "03:20",
        )
        self.assertEqual(
            sessions[0].formatted_shortest_flight_time,
            "02:40",
        )

    def test_starts_new_session_at_full_battery_voltage(self):
        flights = [
            self.make_flight(
                start_time="10:00:00",
                duration_seconds=180,
                start_voltage="17.30",
                end_voltage="15.80",
            ),
            self.make_flight(
                start_time="10:05:00",
                duration_seconds=190,
                start_voltage="16.10",
                end_voltage="15.30",
            ),
            self.make_flight(
                start_time="10:20:00",
                duration_seconds=210,
                start_voltage="17.20",
                end_voltage="15.70",
            ),
        ]

        sessions = build_flight_sessions(
            flights,
            cell_count=4,
            chemistry="lihv",
        )

        self.assertEqual(len(sessions), 2)
        self.assertEqual(sessions[0].session_count, 2)
        self.assertEqual(sessions[1].session_count, 1)
        self.assertEqual(
            sessions[1].start_reason,
            "voltage_threshold",
        )

    def test_sorts_flights_before_grouping(self):
        flights = [
            self.make_flight(
                start_time="10:20:00",
                duration_seconds=210,
                start_voltage="17.20",
                end_voltage="15.70",
            ),
            self.make_flight(
                start_time="10:00:00",
                duration_seconds=180,
                start_voltage="17.30",
                end_voltage="15.80",
            ),
            self.make_flight(
                start_time="10:05:00",
                duration_seconds=190,
                start_voltage="16.10",
                end_voltage="15.30",
            ),
        ]

        sessions = build_flight_sessions(
            flights,
            cell_count=4,
            chemistry="lihv",
        )

        self.assertEqual(len(sessions), 2)
        self.assertEqual(
            sessions[0].flights[0].start_time.isoformat(),
            "10:00:00",
        )
        self.assertEqual(
            sessions[1].flights[0].start_time.isoformat(),
            "10:20:00",
        )

    def test_returns_empty_list_for_no_flights(self):
        sessions = build_flight_sessions(
            [],
            cell_count=4,
            chemistry="lihv",
        )

        self.assertEqual(sessions, [])

    def test_starts_new_session_when_model_changes(self):
        flights = [
            self.make_flight(
                start_time="10:00:00",
                duration_seconds=180,
                start_voltage="17.30",
                end_voltage="15.80",
                model="Model-A",
            ),
            self.make_flight(
                start_time="10:05:00",
                duration_seconds=190,
                start_voltage="16.10",
                end_voltage="15.30",
                model="Model-B",
            ),
        ]

        sessions = build_flight_sessions(
            flights,
            cell_count=4,
            chemistry="lihv",
        )

        self.assertEqual(len(sessions), 2)
        self.assertEqual(
            sessions[1].start_reason,
            "model_changed",
        )

    def test_starts_new_session_when_date_changes(self):
        flights = [
            self.make_flight(
                date="2026-07-10",
                start_time="23:55:00",
                duration_seconds=180,
                start_voltage="17.30",
                end_voltage="15.80",
            ),
            self.make_flight(
                date="2026-07-11",
                start_time="00:05:00",
                duration_seconds=190,
                start_voltage="16.10",
                end_voltage="15.30",
            ),
        ]

        sessions = build_flight_sessions(
            flights,
            cell_count=4,
            chemistry="lihv",
        )

        self.assertEqual(len(sessions), 2)
        self.assertEqual(
            sessions[1].start_reason,
            "date_changed",
        )

    def test_session_exposes_voltage_threshold(self):
        flights = [
            self.make_flight(
                start_time="10:00:00",
                duration_seconds=180,
                start_voltage="17.30",
                end_voltage="15.80",
            ),
        ]

        sessions = build_flight_sessions(
            flights,
            cell_count=4,
            chemistry="lihv",
        )

        self.assertEqual(
            str(sessions[0].voltage_threshold),
            "17.00",
        )
        self.assertEqual(
            str(sessions[0].start_voltage),
            "17.30",
        )

    def test_first_session_has_first_flight_reason(self):
        flights = [
            self.make_flight(
                start_time="10:00:00",
                duration_seconds=180,
                start_voltage="17.30",
                end_voltage="15.80",
            ),
        ]

        sessions = build_flight_sessions(
            flights,
            cell_count=4,
            chemistry="lihv",
        )

        self.assertEqual(
            sessions[0].start_reason,
            "first_flight",
        )
        self.assertEqual(
            sessions[0].start_reason_label,
            "First flight on logset",
        )

class FlightSessionModelTests(TestCase):
    def setUp(self):
        self.session = FlightSession.objects.create(
            aircraft_name="Mallinimi",
            cell_count=4,
            chemistry=FlightSession.Chemistry.LIHV,
            voltage_threshold=Decimal("17.00"),
        )

    def create_flight(
        self,
        *,
        start_datetime,
        duration_seconds,
        start_voltage,
        end_voltage,
        filename,
    ):
        end_datetime = start_datetime + timedelta(
            seconds=duration_seconds
        )

        return Flight.objects.create(
            session=self.session,
            start_datetime=start_datetime,
            end_datetime=end_datetime,
            flight_time=end_datetime - start_datetime,
            start_voltage=Decimal(start_voltage),
            end_voltage=Decimal(end_voltage),
            filename=filename,
        )

    def test_session_string_representation(self):
        self.assertEqual(
            str(self.session),
            "Mallinimi - 4S LiHV",
        )

    def test_session_has_no_flights_initially(self):
        self.assertIsNone(self.session.first_flight)
        self.assertIsNone(self.session.date)
        self.assertIsNone(self.session.start_voltage)
        self.assertEqual(self.session.flight_count, 0)
        self.assertEqual(
            self.session.total_flight_time,
            timedelta(),
        )
        self.assertIsNone(
            self.session.longest_flight_time
        )
        self.assertIsNone(
            self.session.shortest_flight_time
        )

    def test_session_uses_first_flight_for_date_and_voltage(self):
        later_flight = self.create_flight(
            start_datetime=datetime(
                2026,
                7,
                10,
                16,
                50,
                0,
            ),
            duration_seconds=180,
            start_voltage="16.20",
            end_voltage="15.40",
            filename=(
                "Mallinimi-2026-07-10-165000.csv"
            ),
        )

        first_flight = self.create_flight(
            start_datetime=datetime(
                2026,
                7,
                10,
                16,
                39,
                41,
            ),
            duration_seconds=200,
            start_voltage="17.30",
            end_voltage="15.80",
            filename=(
                "Mallinimi-2026-07-10-163941.csv"
            ),
        )

        self.assertEqual(
            self.session.first_flight,
            first_flight,
        )
        self.assertNotEqual(
            self.session.first_flight,
            later_flight,
        )
        self.assertEqual(
            self.session.date.isoformat(),
            "2026-07-10",
        )
        self.assertEqual(
            self.session.start_voltage,
            Decimal("17.30"),
        )

    def test_session_calculates_flight_summary(self):
        self.create_flight(
            start_datetime=datetime(
                2026,
                7,
                10,
                16,
                39,
                41,
            ),
            duration_seconds=180,
            start_voltage="17.30",
            end_voltage="15.80",
            filename=(
                "Mallinimi-2026-07-10-163941.csv"
            ),
        )

        self.create_flight(
            start_datetime=datetime(
                2026,
                7,
                10,
                16,
                50,
                0,
            ),
            duration_seconds=200,
            start_voltage="16.20",
            end_voltage="15.40",
            filename=(
                "Mallinimi-2026-07-10-165000.csv"
            ),
        )

        self.create_flight(
            start_datetime=datetime(
                2026,
                7,
                10,
                17,
                0,
                0,
            ),
            duration_seconds=160,
            start_voltage="15.80",
            end_voltage="15.10",
            filename=(
                "Mallinimi-2026-07-10-170000.csv"
            ),
        )

        self.assertEqual(
            self.session.flight_count,
            3,
        )
        self.assertEqual(
            self.session.total_flight_time,
            timedelta(seconds=540),
        )
        self.assertEqual(
            self.session.longest_flight_time,
            timedelta(seconds=200),
        )
        self.assertEqual(
            self.session.shortest_flight_time,
            timedelta(seconds=160),
        )

    def test_deleting_session_deletes_its_flights(self):
        self.create_flight(
            start_datetime=datetime(
                2026,
                7,
                10,
                16,
                39,
                41,
            ),
            duration_seconds=180,
            start_voltage="17.30",
            end_voltage="15.80",
            filename=(
                "Mallinimi-2026-07-10-163941.csv"
            ),
        )

        self.assertEqual(
            Flight.objects.count(),
            1,
        )

        self.session.delete()

        self.assertEqual(
            Flight.objects.count(),
            0,
        )


class FlightModelTests(TestCase):
    def setUp(self):
        self.session = FlightSession.objects.create(
            aircraft_name="Mallinimi",
            cell_count=4,
            chemistry=FlightSession.Chemistry.LIHV,
            voltage_threshold=Decimal("17.00"),
        )

    def create_flight(
        self,
        *,
        filename=(
            "Mallinimi-2026-07-10-163941.csv"
        ),
        start_datetime=None,
        end_datetime=None,
    ):
        if start_datetime is None:
            start_datetime = datetime(
                2026,
                7,
                10,
                16,
                39,
                41,
            )

        if end_datetime is None:
            end_datetime = start_datetime + timedelta(
                seconds=180
            )

        return Flight.objects.create(
            session=self.session,
            start_datetime=start_datetime,
            end_datetime=end_datetime,
            flight_time=(
                end_datetime - start_datetime
            ),
            start_voltage=Decimal("17.30"),
            end_voltage=Decimal("15.80"),
            filename=filename,
        )

    def test_flight_string_representation(self):
        flight = self.create_flight()

        self.assertEqual(
            str(flight),
            (
                "Mallinimi - "
                "2026-07-10 16:39:41"
            ),
        )

    def test_flights_are_ordered_by_start_datetime(self):
        later_flight = self.create_flight(
            filename=(
                "Mallinimi-2026-07-10-170000.csv"
            ),
            start_datetime=datetime(
                2026,
                7,
                10,
                17,
                0,
                0,
            ),
            end_datetime=datetime(
                2026,
                7,
                10,
                17,
                3,
                0,
            ),
        )

        earlier_flight = self.create_flight(
            filename=(
                "Mallinimi-2026-07-10-163941.csv"
            ),
            start_datetime=datetime(
                2026,
                7,
                10,
                16,
                39,
                41,
            ),
            end_datetime=datetime(
                2026,
                7,
                10,
                16,
                42,
                41,
            ),
        )

        flights = list(Flight.objects.all())

        self.assertEqual(
            flights,
            [
                earlier_flight,
                later_flight,
            ],
        )

    def test_duplicate_imported_flight_is_rejected(self):
        flight = self.create_flight()

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Flight.objects.create(
                    session=self.session,
                    start_datetime=(
                        flight.start_datetime
                    ),
                    end_datetime=flight.end_datetime,
                    flight_time=flight.flight_time,
                    start_voltage=Decimal("17.30"),
                    end_voltage=Decimal("15.80"),
                    filename=flight.filename,
                )

class FlightPreviewDuplicateTests(SimpleTestCase):
    def make_flight(
        self,
        *,
        filename="Mallinimi-2026-07-10-163941.csv",
        start_time="16:39:41",
        duration_seconds=180,
    ):
        start_datetime = datetime.fromisoformat(
            f"2026-07-10T{start_time}"
        )
        end_datetime = start_datetime + timedelta(
            seconds=duration_seconds
        )

        return ParsedFlightLog(
            filename=filename,
            model="Mallinimi",
            start_datetime=start_datetime,
            end_datetime=end_datetime,
            flight_time=end_datetime - start_datetime,
            start_voltage=Decimal("17.30"),
            end_voltage=Decimal("15.80"),
        )

    def test_finds_duplicate_flight(self):
        flight = self.make_flight()

        duplicates = find_duplicate_flights(
            [flight, flight]
        )

        self.assertEqual(len(duplicates), 1)
        self.assertEqual(
            duplicates[0].filename,
            flight.filename,
        )
        self.assertEqual(
            duplicates[0].start_datetime,
            flight.start_datetime,
        )

    def test_different_flights_are_not_duplicates(self):
        flights = [
            self.make_flight(
                start_time="16:39:41",
            ),
            self.make_flight(
                filename="Mallinimi-2026-07-10-165000.csv",
                start_time="16:50:00",
            ),
        ]

        duplicates = find_duplicate_flights(flights)

        self.assertEqual(duplicates, [])

    def test_same_filename_with_different_segments_is_allowed(self):
        flights = [
            self.make_flight(
                start_time="16:39:41",
                duration_seconds=180,
            ),
            self.make_flight(
                start_time="16:50:00",
                duration_seconds=200,
            ),
        ]

        duplicates = find_duplicate_flights(flights)

        self.assertEqual(duplicates, [])

class ImportPreviewTests(SimpleTestCase):
    def make_file(
        self,
        *,
        name="Mallinimi-2026-07-10-163941.csv",
        content=None,
    ):
        if content is None:
            content = """Date,Time,RxBt(V)
2026-07-10,16:39:41.300,17.1
2026-07-10,16:43:23.300,15.8
"""

        return SimpleUploadedFile(
            name=name,
            content=content.encode("utf-8"),
            content_type="text/csv",
        )

    def test_builds_valid_preview(self):
        preview = build_import_preview(
            uploaded_files=[
                self.make_file(),
            ],
            cell_count=4,
            chemistry="lihv",
        )

        self.assertTrue(preview.is_valid)
        self.assertEqual(preview.flight_count, 1)
        self.assertEqual(preview.session_count, 1)
        self.assertEqual(preview.errors, ())
        self.assertEqual(preview.duplicates, ())

    def test_collects_parser_errors(self):
        preview = build_import_preview(
            uploaded_files=[
                self.make_file(
                    content="""Wrong,Header
foo,bar
""",
                ),
            ],
            cell_count=4,
            chemistry="lihv",
        )

        self.assertFalse(preview.is_valid)
        self.assertEqual(preview.flight_count, 0)
        self.assertEqual(preview.session_count, 0)
        self.assertEqual(len(preview.errors), 1)
        self.assertEqual(preview.duplicates, ())

    def test_duplicate_flights_prevent_sessions(self):
        first_file = self.make_file()
        second_file = self.make_file()

        preview = build_import_preview(
            uploaded_files=[
                first_file,
                second_file,
            ],
            cell_count=4,
            chemistry="lihv",
        )

        self.assertFalse(preview.is_valid)
        self.assertEqual(preview.flight_count, 2)
        self.assertEqual(preview.session_count, 0)
        self.assertEqual(len(preview.duplicates), 1)
        self.assertEqual(preview.errors, ())

    def test_parser_error_prevents_sessions(self):
        valid_file = self.make_file()
        invalid_file = self.make_file(
            name="Broken-2026-07-10-164500.csv",
            content="""Wrong,Header
foo,bar
""",
        )

        preview = build_import_preview(
            uploaded_files=[
                valid_file,
                invalid_file,
            ],
            cell_count=4,
            chemistry="lihv",
        )

        self.assertFalse(preview.is_valid)
        self.assertEqual(preview.flight_count, 1)
        self.assertEqual(preview.session_count, 0)
        self.assertEqual(len(preview.errors), 1)