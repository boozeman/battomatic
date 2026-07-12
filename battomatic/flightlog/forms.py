from pathlib import Path

from django import forms
from django.conf import settings
from django.core.exceptions import ValidationError


def format_file_size(size: int) -> str:
    megabytes = size / (1024 * 1024)
    return f"{megabytes:g} MB"


class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultipleFileField(forms.FileField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", MultipleFileInput())
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        if not data:
            return [super().clean(data, initial)]

        if isinstance(data, (list, tuple)):
            return [
                super().clean(uploaded_file, initial)
                for uploaded_file in data
            ]

        return [super().clean(data, initial)]


class FlightLogUploadForm(forms.Form):
    CELL_COUNT_CHOICES = [
        (1, "1S"),
        (2, "2S"),
        (3, "3S"),
        (4, "4S"),
        (5, "5S"),
        (6, "6S"),
        (7, "7S"),
        (8, "8S"),
    ]

    CHEMISTRY_CHOICES = [
        ("lipo", "LiPo"),
        ("lihv", "LiHV"),
    ]

    cell_count = forms.TypedChoiceField(
        label="Cell Count",
        choices=CELL_COUNT_CHOICES,
        coerce=int,
        initial=4,
    )

    chemistry = forms.ChoiceField(
        label="Chemistry",
        choices=CHEMISTRY_CHOICES,
        initial="lihv",
    )

    files = MultipleFileField(
        label="Flight log CSV files",
        required=True,
        error_messages={
            "required": "Select one or more EdgeTX CSV log files.",
            "empty": "File is empty.",
        },
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["files"].help_text = (
            "Import only one model, cell count or chemistry logs at the time "            
            f"Max {settings.FLIGHTLOG_MAX_FILES} files, "
            f"{format_file_size(settings.FLIGHTLOG_MAX_FILE_SIZE)} "
            "for size of each and "
            f"{format_file_size(settings.FLIGHTLOG_MAX_TOTAL_SIZE)} "
            "files total."
        )

    def clean_files(self):
        files = self.cleaned_data["files"]

        max_files = settings.FLIGHTLOG_MAX_FILES
        max_file_size = settings.FLIGHTLOG_MAX_FILE_SIZE
        max_total_size = settings.FLIGHTLOG_MAX_TOTAL_SIZE

        if len(files) > max_files:
            raise ValidationError(
                f"You can import {max_files} files. "
                f"{len(files)} imported."
            )

        total_size = 0

        for uploaded_file in files:
            suffix = Path(uploaded_file.name).suffix.lower()

            if suffix != ".csv":
                raise ValidationError(
                    f"{uploaded_file.name}: "
                    "Not a csv-file"
                )

            if uploaded_file.size > max_file_size:
                raise ValidationError(
                    f"{uploaded_file.name}: too big file. "
                    "One file size limit is "
                    f"{format_file_size(max_file_size)}."
                )

            total_size += uploaded_file.size

        if total_size > max_total_size:
            raise ValidationError(
                "Too many files at once. "
                "Max files are "
                f"{format_file_size(max_total_size)}."
            )

        return files