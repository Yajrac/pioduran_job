from pathlib import Path
from django import forms
from PIL import Image
from pypdf import PdfReader
from applicant.models import ApplicantCertificate


class CertificateForm(forms.ModelForm):
    class Meta:
        model = ApplicantCertificate
        fields = ["title", "file"]
        widgets = {"title": forms.TextInput(attrs={"placeholder": "e.g. Food Safety Training"}),
                   "file": forms.ClearableFileInput(attrs={"accept": ".pdf,.jpg,.jpeg,.png"})}

    def clean_title(self):
        title = self.cleaned_data["title"].strip()
        if not title:
            raise forms.ValidationError("Enter a certificate title.")
        return title

    def clean_file(self):
        upload = self.cleaned_data["file"]
        if upload.size > 5 * 1024 * 1024:
            raise forms.ValidationError("The file must not exceed 5 MB.")
        extension = Path(upload.name).suffix.lower()
        if extension not in {".pdf", ".jpg", ".jpeg", ".png"}:
            raise forms.ValidationError("Upload a PDF, JPG, or PNG certificate.")
        try:
            if extension == ".pdf":
                reader = PdfReader(upload)
                if reader.is_encrypted or not len(reader.pages):
                    raise ValueError()
            else:
                image = Image.open(upload)
                if image.format not in {"JPEG", "PNG"}:
                    raise ValueError()
                image.verify()
        except Exception:
            raise forms.ValidationError("This file could not be read. Upload a valid PDF, JPG, or PNG.")
        finally:
            upload.seek(0)
        return upload
