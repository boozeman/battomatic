from pathlib import Path

from django import forms
from django.core.exceptions import ValidationError


class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultipleFileField(forms.FileField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", MultipleFileInput())
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        single_file_clean = super().clean

        if isinstance(data, (list, tuple)):
            return [
                single_file_clean(file, initial)
                for file in data
            ]

        return [single_file_clean(data, initial)]


class FlightLogUploadForm(forms.Form):
    files = MultipleFileField(
        label="Flight log CSV files",
        help_text="Select one or more EdgeTX CSV log files.",
    )

    def clean_files(self):
        files = self.cleaned_data["files"]

        for uploaded_file in files:
            suffix = Path(uploaded_file.name).suffix.lower()

            if suffix != ".csv":
                raise ValidationError(
                    f"{uploaded_file.name}: file must be a CSV file."
                )

            if uploaded_file.size == 0:
                raise ValidationError(
                    f"{uploaded_file.name}: file is empty."
                )

        return files