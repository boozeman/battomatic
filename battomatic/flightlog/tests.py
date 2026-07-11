from datetime import timedelta
from django.test import SimpleTestCase, override_settings

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase
from django.urls import reverse

from .forms import FlightLogUploadForm
from .parser import (
    format_duration,
    parse_flight_log,
    parse_flight_logs,
)


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
        name="Mallinimi-2026-07-10-163941.csv",
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
        self.assertEqual(result.model, "Mallinimi")
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
        name="Mallinimi-2026-07-10-163941.csv",
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
            files={"files": uploaded_files},
        )

    def test_accepts_one_csv_file(self):
        form = self.make_form(self.make_file())

        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(len(form.cleaned_data["files"]), 1)

    def test_accepts_multiple_csv_files(self):
        first_file = self.make_file(
            name="Model-A-2026-07-10-163941.csv",
        )
        second_file = self.make_file(
            name="Model-B-2026-07-10-164500.csv",
        )

        form = self.make_form([first_file, second_file])

        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(len(form.cleaned_data["files"]), 2)

    def test_rejects_non_csv_file(self):
        uploaded_file = self.make_file(
            name="flight-log.txt",
        )

        form = self.make_form(uploaded_file)

        self.assertFalse(form.is_valid())
        self.assertIn("files", form.errors)

    def test_rejects_empty_file(self):
        uploaded_file = self.make_file(content=b"")

        form = self.make_form(uploaded_file)

        self.assertFalse(form.is_valid())
        self.assertIn("files", form.errors)

    def test_cell_count_is_converted_to_integer(self):
        form = self.make_form(
            self.make_file(),
            cell_count="4",
        )

        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data["cell_count"], 4)
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
        self.assertEqual(form.cleaned_data["cell_count"], 6)
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
        self.assertContains(response, "Mallinimi")
        self.assertContains(response, "03:42")
        self.assertContains(response, "17.1 V")
        self.assertContains(response, "15.8 V")

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
            "CSV-tiedostosta puuttuvat kentät",
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