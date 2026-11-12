"""Sample data for demos and thesis presentations (works on SQLite and MySQL).

    python manage.py seed_demo_data          # add (or refresh) the sample data
    python manage.py seed_demo_data --clear  # remove the sample data only

Creates 15 employers, 15 job posts (all in Pio Duran, Albay) and 15
applicants, with logos, photos, resumes, cover letters, work experience,
certificates, applications, hires and probation results, so the demand
ranking (9.2), benchmarks (9.4), reports and dashboards all have data.

Every sample account has an @pioduran-demo.test email (a reserved, fake
domain) and --clear deletes only those accounts and their files, so real
accounts are never touched. All sample accounts use the password below.
"""
import io
import random
from datetime import timedelta

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from applicant.models import Applicant, ApplicantCertificate, WorkExperience
from employer.models import ApplicantAssessment, Employer, JobApplication, JobPost
from user.models import User

DOMAIN = "pioduran-demo.test"
PASSWORD = "Testing@123"
OLD_SEED = Q(username__startswith="demo_", email__endswith="@demo.pioduran.invalid")  # earlier version

# (key, company, barangay, about, colour)
EMPLOYERS = [
    ("rawis", "Rawis General Merchandise", "Rawis", "A family-owned general merchandise store selling groceries, school supplies and household goods to Rawis and nearby barangays.", "#1d4ed8"),
    ("malidong", "Malidong Minimart", "Malidong", "A neighborhood minimart open daily from 6 AM, serving residents, tricycle drivers and sari-sari store owners.", "#0f766e"),
    ("oringon", "Oringon Trading Center", "Oringon", "Wholesale and retail trading of rice, dried fish and coconut products from local farmers and fisherfolk.", "#7c3aed"),
    ("baybay", "Baybay Seaside Eatery", "Poblacion", "A seaside carinderia and catering service known for Bicol express, laing and fresh grilled seafood.", "#b45309"),
    ("panganiran", "Panganiran Bakeshop", "Panganiran", "A local bakeshop baking pandesal, ensaymada and pasalubong breads every morning for the town.", "#be123c"),
    ("kapehan", "Kapehan sa Pantalan", "Poblacion", "A small coffee shop near the port serving brewed coffee, snacks and light meals to travelers.", "#92400e"),
    ("mayon", "Mayon View Bookkeeping Services", "Poblacion", "Bookkeeping, payroll and BIR filing assistance for small businesses and cooperatives in Pio Duran.", "#334155"),
    ("coop", "Pio Duran Farmers Multi-Purpose Cooperative", "Caratagan", "A farmers' cooperative offering rice and coconut trading, farm inputs and savings services to its members.", "#15803d"),
    ("express", "Albay Coastal Express Delivery", "Poblacion", "Same-day parcel and grocery delivery within Pio Duran and to Ligao City and Guinobatan.", "#c2410c"),
    ("builders", "Buyo Builders and Construction Supply", "Buyo", "Construction services and hardware supply for houses, small buildings and barangay projects.", "#57534e"),
    ("resort", "Marigondon Beach Resort", "Marigondon", "A beach resort with cottages, rooms and a function hall for family outings and events.", "#0369a1"),
    ("fishers", "Salvacion Fisherfolk Association", "Salvacion", "An association of small fishers handling fish landing, drying and selling of the daily catch.", "#0e7490"),
    ("clinic", "Pio Duran Community Health Clinic", "Poblacion", "A private outpatient clinic offering consultations, laboratory tests and home care services.", "#be185d"),
    ("security", "Sukip Security Services", "Sukip", "Security guard services for stores, schools and private establishments in the second district of Albay.", "#1e3a8a"),
    ("compute", "Tibabo Computer and Printing Shop", "Tibabo", "Computer repair, internet, printing and photocopy services for students and offices.", "#4338ca"),
]

# (employer key, title, category, required skills, experience needed, salary, vacancies, job type, status)
JOBS = [
    ("rawis", "Sales Clerk", "sales_retail", "Customer Service, Cashiering, Inventory, Sales", False, 12000, 3, "full_time", "approved"),
    ("malidong", "Store Cashier", "sales_retail", "Cashiering, Customer Service, Basic Math", False, 11500, 2, "full_time", "approved"),
    ("oringon", "Merchandiser", "sales_retail", "Sales, Inventory, Customer Service", False, 12500, 2, "full_time", "approved"),
    ("baybay", "Line Cook", "food_service", "Cooking, Food Safety, Food Preparation", True, 13000, 2, "full_time", "approved"),
    ("panganiran", "Baker Helper", "food_service", "Baking, Food Preparation, Cleaning", False, 11000, 2, "full_time", "approved"),
    ("kapehan", "Barista / Service Crew", "food_service", "Customer Service, Food Preparation, Teamwork", False, 11000, 2, "part_time", "approved"),
    ("mayon", "Office Clerk", "office_admin", "MS Office, Filing, Data Entry, Communication", False, 13500, 1, "full_time", "approved"),
    ("coop", "Bookkeeper", "office_admin", "Bookkeeping, MS Excel, Basic Accounting", True, 15000, 1, "full_time", "approved"),
    ("express", "Delivery Rider", "driving_delivery", "Driving, Motorcycle, Navigation", True, 12000, 3, "full_time", "approved"),
    ("builders", "Construction Worker", "construction_trades", "Masonry, Carpentry, Physical Fitness", False, 14000, 5, "contract", "approved"),
    ("resort", "Front Desk Staff", "hospitality_tourism", "Customer Service, Communication, MS Office", False, 13000, 1, "full_time", "approved"),
    ("fishers", "Fish Vendor / Helper", "agriculture_fishery", "Fish Handling, Sales, Physical Fitness", False, 10500, 2, "temporary", "approved"),
    ("clinic", "Caregiver", "health_care", "Caregiving, First Aid, Communication", True, 14500, 1, "full_time", "approved"),
    ("security", "Security Guard", "security", "Security, Physical Fitness, Communication", True, 14000, 2, "full_time", "pending"),
    ("compute", "Computer Technician", "it_technical", "Computer Repair, Troubleshooting, MS Office", False, 13000, 1, "full_time", "pending"),
]
PENDING_EMPLOYERS = {"compute"}  # shows the employer approval flow

# (first, middle, last, barangay, skills, previous job or None)
APPLICANTS = [
    ("Maria", "Santos", "Dela Cruz", "Rawis", "Customer Service, Cashiering, Inventory, Sales, Basic Math", ("Sales Helper", "Ligao Public Market Store")),
    ("Jose", "Reyes", "Bautista", "Malidong", "Cashiering, Customer Service, Basic Math, Sales", ("Cashier", "Guinobatan Grocery")),
    ("Ana", "Lopez", "Garcia", "Oringon", "Sales, Inventory, Customer Service, Communication", ("Promodiser", "Legazpi City Mall")),
    ("Mark", "Villanueva", "Mendoza", "Poblacion", "Customer Service, Sales, Teamwork", None),
    ("Kristine", "Aquino", "Ramos", "Buyo", "Cashiering, Basic Math, MS Office", None),
    ("Paolo", "Navarro", "Castillo", "Poblacion", "Cooking, Food Safety, Food Preparation, Teamwork", ("Cook", "Daraga Carinderia")),
    ("Grace", "Morales", "Belen", "Panganiran", "Baking, Food Preparation, Cleaning, Food Safety", ("Baker Assistant", "Ligao Bakery")),
    ("Carlo", "Rivera", "Balingit", "Poblacion", "Customer Service, Food Preparation, Teamwork, Cooking", ("Service Crew", "Legazpi Food Park")),
    ("Rhea", "Santos", "Llamas", "Salvacion", "Cooking, Cleaning, Food Preparation", None),
    ("Miguel", "Ortiz", "Abante", "Poblacion", "MS Office, Filing, Data Entry, Communication, MS Excel", ("Office Assistant", "Municipal Hall OJT")),
    ("Angel", "Cruz", "Saballa", "Marigondon", "Customer Service, Communication, MS Office, English", ("Front Desk Trainee", "Legazpi Hotel")),
    ("Dennis", "Bonga", "Nuñez", "Sukip", "Driving, Motorcycle, Navigation, Customer Service", ("Tricycle Driver", "Pio Duran TODA")),
    ("Lovely", "Dacara", "Brioso", "Caratagan", "Bookkeeping, MS Excel, Basic Accounting, Data Entry", None),
    ("Jerome", "Nidea", "Oco", "Buyo", "Masonry, Carpentry, Physical Fitness", ("Construction Helper", "Barangay Road Project")),
    ("Camille", "Bañares", "Pura", "Tibabo", "Computer Repair, Troubleshooting, MS Office, Communication", None),
]

# (applicant #, job #, outcome). Outcomes: passed / failed / started = hired with a
# probation result; rejected; pending / reviewing / shortlisted / offered = still open.
APPLICATIONS = [
    (1, 1, "passed"), (1, 2, "rejected"),
    (2, 2, "passed"), (2, 1, "rejected"),
    (3, 3, "passed"), (3, 1, "rejected"),
    (4, 1, "pending"), (4, 3, "reviewing"), (4, 2, "rejected"),
    (5, 2, "shortlisted"), (5, 7, "pending"),
    (6, 4, "passed"), (6, 6, "rejected"),
    (7, 5, "passed"), (7, 4, "rejected"),
    (8, 6, "passed"), (8, 4, "reviewing"),
    (9, 4, "failed"), (9, 5, "rejected"),
    (10, 7, "passed"), (10, 11, "rejected"),
    (11, 11, "offered"), (11, 1, "pending"),
    (12, 9, "started"),
    (13, 8, "shortlisted"), (13, 7, "reviewing"),
    (14, 10, "pending"), (14, 12, "reviewing"),
    (15, 7, "pending"), (15, 11, "pending"),
]
HIRED = {"passed", "failed", "started"}


def _png(text, colour, size=240, round_=False):
    from PIL import Image, ImageDraw, ImageFont
    image = Image.new("RGB", (size, size), colour)
    draw = ImageDraw.Draw(image)
    try:
        font = ImageFont.load_default(size=size // 3)
    except TypeError:  # very old Pillow
        font = ImageFont.load_default()
    box = draw.textbbox((0, 0), text, font=font)
    draw.text(((size - (box[2] - box[0])) / 2 - box[0], (size - (box[3] - box[1])) / 2 - box[1]), text, fill="white", font=font)
    out = io.BytesIO()
    image.save(out, "PNG")
    return out.getvalue()


def _pdf(title, lines):
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
    out = io.BytesIO()
    pdf = canvas.Canvas(out, pagesize=A4)
    y = A4[1] - 72
    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(72, y, title)
    pdf.setFont("Helvetica", 11)
    for line in lines:
        y -= 18 if line else 10
        pdf.drawString(72, y, line)
    pdf.showPage()
    pdf.save()
    return out.getvalue()


class Command(BaseCommand):
    help = "Add 15 sample employers, jobs and applicants in Pio Duran, Albay (use --clear to remove them)."

    def add_arguments(self, parser):
        parser.add_argument("--clear", action="store_true", help="Remove the sample data and stop.")
        parser.add_argument("--force", action="store_true", help="Allow running when DEBUG is off (e.g. on the VPS).")

    def handle(self, *args, clear=False, force=False, **options):
        if not settings.DEBUG and not force:
            raise CommandError("DEBUG is off. Pass --force to add or remove sample data on this server.")
        removed = self.clear()
        if clear:
            self.stdout.write(self.style.SUCCESS(f"Removed {removed} sample account(s) and their files."))
            return
        clash = User.objects.filter(username__in=self.usernames()).exclude(email__endswith="@" + DOMAIN)
        if clash.exists():
            raise CommandError("These usernames are already used by real accounts: "
                               + ", ".join(clash.values_list("username", flat=True)))
        with transaction.atomic():
            counts = self.seed(random.Random(2026))
        self.stdout.write(self.style.SUCCESS(
            f"Added {counts['employers']} employers, {counts['jobs']} jobs, {counts['applicants']} applicants and "
            f"{counts['applications']} applications ({counts['hired']} hired, {counts['passed']} passed probation)."))
        self.stdout.write(f"Logins (password for all: {PASSWORD}):")
        self.stdout.write("  employers:  employer01 ... employer15")
        self.stdout.write("  applicants: applicant01 ... applicant15")
        self.stdout.write("Remove it all later with: python manage.py seed_demo_data --clear")

    @staticmethod
    def usernames():
        return [f"employer{i:02d}" for i in range(1, 16)] + [f"applicant{i:02d}" for i in range(1, 16)]

    # ------------------------------------------------------------------ clear
    def clear(self):
        users = User.objects.filter(Q(email__endswith="@" + DOMAIN) | OLD_SEED)
        for applicant in Applicant.objects.filter(user__in=users):
            for certificate in applicant.certificates.all():
                certificate.file.delete(save=False)
            for field in (applicant.resume, applicant.cover_letter, applicant.profile_photo):
                if field:
                    field.delete(save=False)
        for employer in Employer.objects.filter(employer__in=users):
            if employer.company_logo:
                employer.company_logo.delete(save=False)
        count = users.count()
        users.delete()  # cascades to employers, jobs, applicants, applications, assessments
        return count

    # ------------------------------------------------------------------- seed
    def user(self, username, email, role, first="", last=""):
        user = User(username=username, email=email, role=role, first_name=first, last_name=last)
        user.set_password(PASSWORD)
        user.save()
        return user

    def seed(self, rng):
        now = timezone.now()
        today = timezone.localdate()
        counts = dict(employers=0, jobs=0, applicants=0, applications=0, hired=0, passed=0)

        employers = {}
        for index, (key, name, barangay, about, colour) in enumerate(EMPLOYERS, 1):
            slug = key.replace(" ", "")
            pending = key in PENDING_EMPLOYERS
            employer = Employer(
                employer=self.user(f"employer{index:02d}", f"hr.{slug}@{DOMAIN}", "employer"),
                company_name=name, description=f"{about} Located in Brgy. {barangay}, Pio Duran, Albay.",
                business_permit_no=f"PD-BP-2026-{index:03d}", contact_no=f"0998900{index:04d}",
                approval_status="pending" if pending else "approved", reviewed_at=None if pending else now)
            initials = "".join(word[0] for word in name.split() if word[0].isupper())[:2]
            employer.company_logo.save(f"{slug}.png", ContentFile(_png(initials, colour)), save=False)
            employer.save()
            employers[key] = (employer, barangay)
            counts["employers"] += 1

        jobs = []
        for key, title, category, required, needs_experience, salary, vacancies, job_type, status in JOBS:
            employer, barangay = employers[key]
            job = JobPost.objects.create(
                employer=employer, title=title, category=category, required_skills=required,
                experience_required=needs_experience, location=f"Brgy. {barangay}, Pio Duran, Albay",
                job_type=job_type, salary=salary, vacancies=vacancies, status=status,
                approved_at=now if status == "approved" else None,
                deadline=today + timedelta(days=rng.randint(14, 50)),
                description=(f"{employer.company_name} is hiring a {title} for our branch in Brgy. {barangay}, "
                             f"Pio Duran, Albay. Residents of Pio Duran and nearby towns are encouraged to apply."),
                qualifications=("At least high school graduate. Physically fit and willing to work in Pio Duran. "
                                + ("At least 6 months of related work experience." if needs_experience else "No experience needed; training is provided.")),
                responsibilities=f"Perform the daily tasks of a {title.lower()}, follow company policies and assist customers and co-workers.")
            jobs.append(job)
            counts["jobs"] += 1

        applicants = []
        for index, (first, middle, last, barangay, skills, previous) in enumerate(APPLICANTS, 1):
            local = f"{first}.{last}".lower().replace(" ", "").replace("ñ", "n")
            email = f"{local}@{DOMAIN}"
            applicant = Applicant(
                user=self.user(f"applicant{index:02d}", email, "applicant", first, last),
                first_name=first, middle_name=middle, last_name=last, email=email,
                phone_number=f"0917800{index:04d}", skills=skills)
            colour = rng.choice(["#1d4ed8", "#0f766e", "#7c3aed", "#b45309", "#be123c", "#334155"])
            applicant.profile_photo.save(f"applicant{index:02d}.png", ContentFile(_png(first[0] + last[0], colour)), save=False)
            lines = [f"Brgy. {barangay}, Pio Duran, Albay", f"{email}  |  0917800{index:04d}", "",
                     "SKILLS", *[f"- {s.strip()}" for s in skills.split(",")], "", "WORK EXPERIENCE"]
            lines += [f"- {previous[0]}, {previous[1]}"] if previous else ["- Fresh graduate"]
            lines += ["", "EDUCATION", "- Pio Duran National High School"]
            applicant.resume.save(f"resume_applicant{index:02d}.pdf", ContentFile(_pdf(f"{first} {middle} {last}", lines)), save=False)
            letter = [f"To the Hiring Manager,", "",
                      "I am a resident of Pio Duran, Albay and I would like to apply for a position in your company.",
                      f"My skills include {skills.lower()}.", "I am hardworking, honest and willing to learn.", "",
                      "Thank you for considering my application.", "", f"{first} {last}"]
            applicant.cover_letter.save(f"cover_applicant{index:02d}.pdf", ContentFile(_pdf("Application Letter", letter)), save=False)
            applicant.save()
            if previous:
                start = today - timedelta(days=rng.randint(500, 1400))
                WorkExperience.objects.create(
                    applicant=applicant, job_title=previous[0], company=previous[1], start_date=start,
                    end_date=start + timedelta(days=rng.randint(180, 420)),
                    description=f"Worked as {previous[0].lower()}: {skills.split(',')[0].strip().lower()} and daily operations.")
            if index % 3 == 1:  # every third applicant has a training certificate
                certificate = ApplicantCertificate(applicant=applicant, title="TESDA National Certificate II")
                certificate.file.save("certificate.png", ContentFile(_png("NC II", "#15803d")), save=False)
                certificate.save()
            applicants.append(applicant)
            counts["applicants"] += 1

        for applicant_no, job_no, outcome in APPLICATIONS:
            application = JobApplication.objects.create(
                job=jobs[job_no - 1], applicant=applicants[applicant_no - 1],
                message="I am interested in this position and available to start immediately.")
            counts["applications"] += 1
            if outcome in ("passed", "failed"):
                applied = now - timedelta(days=rng.randint(130, 175))
            elif outcome == "started":
                applied = now - timedelta(days=rng.randint(35, 60))
            elif outcome == "rejected":
                applied = now - timedelta(days=rng.randint(20, 150))
            else:
                applied = now - timedelta(days=rng.randint(0, 25))
            fields = {"applied_at": applied}
            if outcome in HIRED:
                hired_at = applied + timedelta(days=rng.randint(6, 24))
                fields.update(status="hired", hired_at=hired_at)
                counts["hired"] += 1
                counts["passed"] += outcome == "passed"
                self.assess(application, outcome, hired_at.date(), today, rng)
            else:
                fields["status"] = outcome
            JobApplication.objects.filter(pk=application.pk).update(**fields)
        return counts

    def assess(self, application, outcome, hired_on, today, rng):
        started_on = hired_on + timedelta(days=rng.randint(2, 7))
        if outcome == "passed":
            scores, note = (rng.randint(4, 5), rng.randint(4, 5)), "Met the probation targets. Recommended for regular employment."
        elif outcome == "failed":
            scores, note = (rng.randint(2, 3), rng.randint(2, 3)), "Did not meet the attendance and performance targets during probation."
        else:
            scores, note = (rng.randint(3, 5), rng.randint(3, 5)), ""
        ApplicantAssessment.objects.create(
            application=application, skills_score=scores[0], interview_score=scores[1],
            assessment_notes="Skills test and interview done at the store.", outcome=outcome, started_on=started_on,
            evaluated_on=min(started_on + timedelta(days=90), today) if outcome in ("passed", "failed") else None,
            outcome_notes=note)
