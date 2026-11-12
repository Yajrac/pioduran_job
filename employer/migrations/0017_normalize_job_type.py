from django.db import migrations

LABELS = {
    "full time": "full_time", "part time": "part_time", "contract": "contract",
    "internship": "internship", "temporary": "temporary",
}


def normalize(apps, schema_editor):
    JobPost = apps.get_model("employer", "JobPost")
    for job in JobPost.objects.exclude(job_type__in=LABELS.values()):
        job.job_type = LABELS.get(job.job_type.strip().lower().replace("_", " "), "full_time")
        job.save(update_fields=["job_type"])


class Migration(migrations.Migration):
    dependencies = [("employer", "0016_predictiverankingmodel")]
    operations = [migrations.RunPython(normalize, migrations.RunPython.noop)]
