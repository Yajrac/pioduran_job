from io import BytesIO
from xml.sax.saxutils import escape

from django.http import HttpResponse
from django.utils import timezone
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, LongTable, TableStyle


def download_demand_report(context):
    """PDF for the Job Demand Ranking (recommendation 9.2)."""
    output = BytesIO()
    doc = SimpleDocTemplate(output, pagesize=landscape(A4), rightMargin=28, leftMargin=28, topMargin=30, bottomMargin=34)
    styles = getSampleStyleSheet()
    cell = ParagraphStyle("ReportCell", parent=styles["Normal"], fontSize=8, leading=11, wordWrap="CJK")
    heading = ParagraphStyle("ReportHeader", parent=cell, textColor=colors.white, fontName="Helvetica-Bold")
    start = escape(context["demand_from"] or "Earliest available date")
    end = escape(context["demand_to"] or "Latest available date")
    trend_text = {"up": "Rising", "down": "Falling", "same": "Steady"}

    def table(headers, rows, weights):
        data = [[Paragraph(label, heading) for label in headers]]
        data += [[Paragraph(escape(str(value)), cell) for value in row] for row in rows]
        if not rows:
            data.append([Paragraph("No applications found for the selected date range.", cell)] + [""] * (len(headers) - 1))
        result = LongTable(data, colWidths=[doc.width * w for w in weights], repeatRows=1, hAlign="LEFT")
        commands = [("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e3a8a")), ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f2f4f7")]),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 8), ("TOPPADDING", (0, 0), (-1, -1), 8),
                    ("LINEBELOW", (0, 0), (-1, -1), .4, colors.HexColor("#dfe2e8"))]
        if not rows:
            commands.append(("SPAN", (0, 1), (-1, 1)))
        result.setStyle(TableStyle(commands))
        return result

    ranking_rows = [[row["rank"], row["label"], row["applications"], row["applicants"], row["hires"],
                     f"{row['success_rate']}%" if row["success_rate"] is not None else "No finished applications",
                     f"{trend_text[row['trend']]} ({row['previous']} to {row['recent']})", row["open_vacancies"]]
                    for row in context["demand"]]
    job_rows = [[n, job.title, job.employer.company_name, job.category_label, job.application_count]
                for n, job in enumerate(context["top_jobs"], 1)]
    story = [Paragraph("PESO Pio Duran", styles["Title"]), Paragraph("Job Demand Ranking", styles["Heading2"]),
             Paragraph(f"Application date range: {start} to {end}<br/>Generated: {context['report_date']}", styles["Normal"]),
             Spacer(1, 14),
             table(["Rank", "Job Category", "Applications", "Applicants", "Hired", "Success Rate", f"Trend (last {context['trend_days']} days)", "Open Vacancies"],
                   ranking_rows, [.06, .22, .11, .1, .08, .15, .17, .11]),
             Spacer(1, 10),
             Paragraph("Ranked by number of applications. Success rate = hired / (hired + rejected); withdrawn and declined "
                       "applications are excluded. Trend compares the last 30 days with the 30 days before.", cell),
             Spacer(1, 18), Paragraph("Most Applied Job Posts", styles["Heading2"]),
             table(["Rank", "Job Title", "Employer", "Category", "Applications"], job_rows, [.06, .34, .26, .2, .14])]

    def footer(canvas, document):
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.drawRightString(document.pagesize[0] - 28, 18, f"Page {document.page}")
        canvas.restoreState()

    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    response = HttpResponse(output.getvalue(), content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="peso-job-demand-{timezone.localdate().isoformat()}.pdf"'
    return response


def download_report(key, context):
    titles = {"employers": "Employer Records", "applicants": "Applicant Records", "jobs": "Job Post Records", "hired": "Successful Applications - Hired Records"}
    headers = {
        "hired": ["No.", "Applicant", "Employer", "Job Title", "Application Date", "Hiring Date", "Days to Hire"],
        "employers": ["No.", "Company", "Business Permit", "Contact", "Status", "Date Registered"],
        "applicants": ["No.", "Applicant Name", "Email", "Phone", "Date Registered"],
        "jobs": ["No.", "Job Title", "Employer", "Location", "Salary (PHP)", "Status", "Date Posted"],
    }

    def date(value):
        return timezone.localtime(value).strftime("%b %d, %Y") if value else "-"

    records = []
    for n, item in enumerate(context[key], 1):
        if key == "employers":
            row = [n, item.company_name, "Uploaded" if item.business_permit_file else (item.business_permit_no or "-"), item.contact_no, "Active" if item.is_active else "Suspended", date(item.created_at)]
        elif key == "applicants":
            row = [n, " ".join(filter(None, [item.first_name, item.middle_name, item.last_name])), item.email, item.phone_number, date(item.user.date_joined)]
        elif key == 'hired':
            person = item.applicant
            days = getattr(item, 'time_to_hire_days', None)
            row = [n, ' '.join(filter(None, [person.first_name, person.middle_name, person.last_name])), item.job.employer.company_name, item.job.title, date(item.applied_at), date(item.hired_at), days if days is not None else 'Not available']
        else:
            row = [n, item.title, item.employer.company_name, item.location, f"{item.salary:,.2f} / {item.salary_period or 'month'}" if item.salary is not None else "Not specified", item.get_status_display(), date(item.created_at)]
        records.append(row)

    output = BytesIO()
    doc = SimpleDocTemplate(output, pagesize=landscape(A4), rightMargin=28, leftMargin=28, topMargin=30, bottomMargin=34)
    styles = getSampleStyleSheet()
    cell = ParagraphStyle("ReportCell", parent=styles["Normal"], fontSize=8, leading=11, wordWrap="CJK")
    heading = ParagraphStyle("ReportHeader", parent=cell, textColor=colors.white, fontName="Helvetica-Bold")
    start = escape(context[key + "_from"] or "Earliest available date")
    end = escape(context[key + "_to"] or "Latest available date")
    story = [Paragraph("PESO Pio Duran", styles["Title"]), Paragraph(titles[key], styles["Heading2"]),
             Paragraph(f"Date range: {start} to {end}<br/>Generated: {context['report_date']}<br/>Records: {len(records)}", styles["Normal"]), Spacer(1, 16)]
    data = [[Paragraph(label, heading) for label in headers[key]]]
    for row in records:
        data.append([Paragraph(escape(str(value)), cell) for value in row])
    if not records:
        data.append([Paragraph("No records found for the selected date range.", cell)] + [""] * (len(headers[key]) - 1))
    weights = {"hired": [.04, .18, .16, .22, .14, .14, .12], "employers": [.05, .23, .25, .15, .12, .20], "applicants": [.05, .25, .30, .18, .22], "jobs": [.05, .23, .18, .17, .12, .11, .14]}[key]
    table = LongTable(data, colWidths=[doc.width * weight for weight in weights], repeatRows=1, hAlign="LEFT")
    commands = [("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e3a8a")), ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f2f3f6")]),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 9), ("TOPPADDING", (0, 0), (-1, -1), 9),
                ("LINEBELOW", (0, 0), (-1, -1), .4, colors.HexColor("#dfe2e8"))]
    if not records:
        commands.append(("SPAN", (0, 1), (-1, 1)))
    table.setStyle(TableStyle(commands))
    story.append(table)
    stats = context.get('hiring_stats')
    if key == 'hired' and stats:
        story.extend([Spacer(1, 18), Paragraph('Time-to-Hire Analytics', styles['Heading2'])])
        average = f"{stats['average_days']} days" if stats['average_days'] is not None else 'Not available'
        story.append(Paragraph(f"Average: {average}. Measured hires: {stats['measured_count']}. Excluded records: {stats['excluded_count']}.<br/>Elapsed time from application to offer acceptance. Missing or reversed dates are excluded.", styles['Normal']))
        if stats['breakdown']:
            breakdown = [[Paragraph(label, heading) for label in ['Employer', 'Job', 'Measured Hires', 'Average Days']]]
            for group in stats['breakdown']:
                breakdown.append([Paragraph(escape(str(group[field])), cell) for field in ['employer', 'job', 'count', 'average_days']])
            summary = LongTable(breakdown, colWidths=[doc.width * weight for weight in [.3, .4, .15, .15]], repeatRows=1)
            summary.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1e3a8a')), ('VALIGN', (0, 0), (-1, -1), 'TOP'), ('TOPPADDING', (0, 0), (-1, -1), 8), ('BOTTOMPADDING', (0, 0), (-1, -1), 8)]))
            story.extend([Spacer(1, 12), summary])

    def footer(canvas, document):
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.drawRightString(document.pagesize[0] - 28, 18, f"Page {document.page}")
        canvas.restoreState()

    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    response = HttpResponse(output.getvalue(), content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="peso-{key}-{timezone.localdate().isoformat()}.pdf"'
    return response


def download_employer_report(context):
    """Employer report PDF: summary counts, per-job breakdown and time to hire."""
    report, stats, employer = context["report"], context["hiring_stats"], context["employer"]
    output = BytesIO()
    doc = SimpleDocTemplate(output, pagesize=landscape(A4), rightMargin=28, leftMargin=28, topMargin=30, bottomMargin=34)
    styles = getSampleStyleSheet()
    # Same palette as the employer portal: navy ink, blue accent, light blue-grey surfaces.
    ink, accent, muted = colors.HexColor("#15284b"), colors.HexColor("#2563eb"), colors.HexColor("#475569")
    head_bg, stripe, line = colors.HexColor("#eff6ff"), colors.HexColor("#f8fafc"), colors.HexColor("#e0e3e8")
    cell = ParagraphStyle("ReportCell", parent=styles["Normal"], fontSize=8.5, leading=11, wordWrap="CJK", textColor=ink)
    heading = ParagraphStyle("ReportHeader", parent=cell, textColor=accent, fontName="Helvetica-Bold")
    bold = ParagraphStyle("ReportBold", parent=cell, fontName="Helvetica-Bold")
    title = ParagraphStyle("EmpTitle", parent=styles["Title"], textColor=ink)
    subtitle = ParagraphStyle("EmpSubtitle", parent=styles["Heading2"], textColor=ink)
    section = ParagraphStyle("EmpSection", parent=styles["Heading3"], textColor=accent, fontName="Helvetica-Bold")
    meta = ParagraphStyle("EmpMeta", parent=styles["Normal"], textColor=muted)
    start = escape(context["date_from"] or "Earliest available date")
    end = escape(context["date_to"] or "Latest available date")
    header_style = [("BACKGROUND", (0, 0), (-1, 0), head_bg), ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, stripe]),
                    ("TOPPADDING", (0, 0), (-1, -1), 8), ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                    ("LINEABOVE", (0, 0), (-1, 0), 1.2, accent),
                    ("LINEBELOW", (0, 0), (-1, -1), .4, line), ("BOX", (0, 0), (-1, -1), .4, line)]

    def table(headers, rows, weights, extra=()):
        data = [[Paragraph(label, heading) for label in headers]]
        data += [[value if isinstance(value, Paragraph) else Paragraph(escape(str(value)), cell) for value in row] for row in rows]
        result = LongTable(data, colWidths=[doc.width * w for w in weights], repeatRows=1, hAlign="LEFT")
        result.setStyle(TableStyle(header_style + list(extra)))
        return result

    totals = report["totals"]
    story = [Paragraph("PESO Pio Duran", title), Paragraph(f"Employer Report - {escape(employer.company_name)}", subtitle),
             Paragraph(f"Date range: {start} to {end}<br/>Generated: {context['report_date']}", meta), Spacer(1, 14),
             Paragraph("Per Job Post", section)]

    def date(value):
        return timezone.localtime(value).strftime("%b %d, %Y") if value else "-"

    rows = [[n, job.title, date(job.created_at), job.get_status_display(), job.n_applications, job.n_in_progress, job.n_rejected, job.n_hired]
            for n, job in enumerate(report["rows"], 1)]
    weights = [.05, .31, .13, .11, .1, .1, .1, .1]
    if rows:
        rows.append(["", Paragraph("Total", bold), "", "", Paragraph(str(totals["applications"]), bold), Paragraph(str(totals["in_progress"]), bold),
                     Paragraph(str(totals["rejected"]), bold), Paragraph(str(totals["hired"]), bold)])
        story.append(table(["No.", "Job Post", "Date Posted", "Status", "Applicants", "In Progress", "Rejected", "Hired"], rows, weights,
                           [("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#edf0f5")), ("LINEABOVE", (0, -1), (-1, -1), .8, ink)]))
    else:
        story.append(Paragraph("No job posts or applications in this period.", cell))

    average = f"{stats['average_days']} days" if stats["average_days"] is not None else "Not available"
    story += [Spacer(1, 14), Paragraph("Time to Hire", section),
              Paragraph(f"Average: {average}. Measured hires: {stats['measured_count']}. Excluded records: {stats['excluded_count']}. "
                        "Elapsed time from application to offer acceptance.", cell)]
    if stats["breakdown"]:
        story += [Spacer(1, 8), table(["Job", "Measured Hires", "Average Days"],
                                      [[g["job"], g["count"], g["average_days"]] for g in stats["breakdown"]], [.5, .25, .25])]

    def footer(canvas, document):
        canvas.saveState()
        canvas.setFillColor(accent)
        canvas.rect(0, document.pagesize[1] - 6, document.pagesize[0], 6, stroke=0, fill=1)
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(muted)
        canvas.drawRightString(document.pagesize[0] - 28, 18, f"Page {document.page}")
        canvas.restoreState()

    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    response = HttpResponse(output.getvalue(), content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="employer-report-{timezone.localdate().isoformat()}.pdf"'
    return response
