from io import BytesIO

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase

from .parser import parse_flight_log
from .forms import FlightLogUploadForm


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