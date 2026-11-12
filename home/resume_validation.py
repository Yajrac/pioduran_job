"""Conservative text screening; unreadable/scanned documents remain unclassified."""
import re
from pathlib import Path
from zipfile import ZipFile
from xml.etree import ElementTree

NOT_RESUME = "This file does not appear to be a resume."


def extract_resume_text(upload):
    """Read bounded PDF/DOCX text without changing the file position."""
    try:
        upload.seek(0)
        extension = Path(upload.name).suffix.lower()
        if upload.size > 5 * 1024 * 1024:
            return ""
        if extension == ".pdf":
            from pypdf import PdfReader
            reader = PdfReader(upload)
            return "\n".join(page.extract_text() or "" for page in reader.pages[:15])[:200000]
        if extension == ".docx":
            with ZipFile(upload) as archive:
                info = archive.getinfo("word/document.xml")
                if info.file_size > 5 * 1024 * 1024:
                    return ""
                root = ElementTree.fromstring(archive.read(info))
                return " ".join(root.itertext())[:200000]
        return ""
    finally:
        upload.seek(0)


def inspect_resume(upload):
    if not upload:
        return {"error": "", "warning": ""}
    if upload.size > 5 * 1024 * 1024:
        return {"error": "The file must not exceed 5 MB.", "warning": ""}
    extension = Path(upload.name).suffix.lower()
    if extension not in {".pdf", ".docx", ".doc"}:
        return {"error": NOT_RESUME, "warning": ""}
    warning = "The file could not be read clearly. Its resume content could not be verified."
    try:
        upload.seek(0)
        text = extract_resume_text(upload)
        if len(text.strip()) < 80:
            return {"error": "", "warning": warning}
        text = text.casefold()
        groups = [r"\b(resume|résumé|curriculum vitae|biodata)\b", r"\b(education|educational background|school|university|college)\b", r"\b(skills|competencies|qualifications)\b", r"\b(work experience|employment history|professional experience|internship)\b", r"\b(career objective|professional summary|personal information|references|certifications)\b"]
        matches = sum(bool(re.search(pattern, text)) for pattern in groups)
        return {"error": NOT_RESUME if matches < 2 else "", "warning": ""}
    except Exception:
        return {"error": "", "warning": warning}
    finally:
        upload.seek(0)
