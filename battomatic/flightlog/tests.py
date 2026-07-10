from io import BytesIO
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase

from .forms import FlightLogUploadForm
from .parser import parse_flight_log, parse_flight_logs

from datetime import timedelta

from .parser import format_duration

CSV_CONTENT = """Date,Time,FM,Ptch(rad),Roll(rad),Yaw(rad),RxBt(V),Curr(A),Capa(mAh),Bat%(%)
2026-07-10,16:39:41.300,"AIR",0.00,0.00,0.57,17.1,0.5,4,99
2026-07-10,16:39:42.300,"AIR",0.00,0.00,0.57,17.1,0.8,4,99
"""


class FlightLogParserTests(SimpleTestCase):
    def test_parse_flight_log(self):
        uploaded_file = SimpleUploadedFile(
            name="Mallinimi-2026-07-10-163941.csv",
            content=CSV_CONTENT.encode("utf-8"),
            content_type="text/csv",
        )

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
        uploaded_file = SimpleUploadedFile(
            name="Flywoo-Firefly-2S-2026-07-10-163941.csv",
            content=CSV_CONTENT.encode("utf-8"),
            content_type="text/csv",
        )

        result = parse_flight_log(uploaded_file)

        self.assertEqual(result.model, "Flywoo-Firefly-2S")



class FlightLogUploadFormTests(SimpleTestCase):
    def make_file(
        self,
        name="Mallinimi-2026-07-10-163941.csv",
        content=b"Date,Time,RxBt(V)\n2026-07-10,16:39:41.300,17.1\n",
    ):
        return SimpleUploadedFile(
            name=name,
            content=content,
            content_type="text/csv",
        )

    def test_accepts_one_csv_file(self):
        uploaded_file = self.make_file()

        form = FlightLogUploadForm(
            data={},
            files={"files": uploaded_file},
        )

        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(len(form.cleaned_data["files"]), 1)

    def test_accepts_multiple_csv_files(self):
        first_file = self.make_file(
            name="Model-A-2026-07-10-163941.csv"
        )
        second_file = self.make_file(
            name="Model-B-2026-07-10-164500.csv"
        )

        form = FlightLogUploadForm(
            data={},
            files={
                "files": [
                    first_file,
                    second_file,
                ]
            },
        )

        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(len(form.cleaned_data["files"]), 2)

    def test_rejects_non_csv_file(self):
        uploaded_file = self.make_file(
            name="flight-log.txt"
        )

        form = FlightLogUploadForm(
            data={},
            files={"files": uploaded_file},
        )

        self.assertFalse(form.is_valid())
        self.assertIn("files", form.errors)

    def test_rejects_empty_file(self):
        uploaded_file = self.make_file(
            content=b"",
        )

        form = FlightLogUploadForm(
            data={},
            files={"files": uploaded_file},
        )

        self.assertFalse(form.is_valid())
        self.assertIn("files", form.errors)


def test_splits_log_when_zero_voltage_gap_separates_flights(self):
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

    uploaded_file = SimpleUploadedFile(
        name="Mallinimi-2026-07-10-163941.csv",
        content=csv_content.encode("utf-8"),
        content_type="text/csv",
    )

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


class FlightTimeFormattingTests(SimpleTestCase):
    def test_formats_minutes_and_seconds(self):
        duration = timedelta(minutes=3, seconds=42)

        self.assertEqual(format_duration(duration), "03:42")

    def test_ignores_fractional_seconds(self):
        duration = timedelta(minutes=4, seconds=12, milliseconds=900)

        self.assertEqual(format_duration(duration), "04:12")

    def test_supports_more_than_one_hour(self):
        duration = timedelta(hours=1, minutes=7, seconds=15)

        self.assertEqual(format_duration(duration), "67:15")

    def test_formats_zero_duration(self):
        self.assertEqual(format_duration(timedelta()), "00:00")

class FlightLogUploadViewTests(SimpleTestCase):
    def test_upload_page_opens(self):
        response = self.client.get(
            reverse("flightlog:upload")
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response,
            "flightlog/upload.html",
        )

    def test_uploaded_log_is_displayed(self):
        csv_content = """Date,Time,RxBt(V)
2026-07-10,16:39:41.300,17.1
2026-07-10,16:43:23.300,15.8
"""

        uploaded_file = SimpleUploadedFile(
            name="Mallinimi-2026-07-10-163941.csv",
            content=csv_content.encode("utf-8"),
            content_type="text/csv",
        )

        response = self.client.post(
            reverse("flightlog:upload"),
            data={
                "files": uploaded_file,
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Mallinimi")
        self.assertContains(response, "03:42")
        self.assertContains(response, "17.1 V")
        self.assertContains(response, "15.8 V")

    def test_invalid_log_error_is_displayed(self):
        uploaded_file = SimpleUploadedFile(
            name="Mallinimi-2026-07-10-163941.csv",
            content=b"Wrong,Header\nfoo,bar\n",
            content_type="text/csv",
        )

        response = self.client.post(
            reverse("flightlog:upload"),
            data={
                "files": uploaded_file,
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            "CSV-tiedostosta puuttuvat kentät",
        )        