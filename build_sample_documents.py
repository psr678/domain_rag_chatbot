"""
Generates 4 fictional HR policy PDF documents used as the sample document
set for the Domain-Specific RAG Chatbot project.

Company name "Solstice Retail Pvt Ltd" and all policy details below are
entirely fictional -- created for this project, not copied from any real
company's documents.

Each document uses an explicit PageBreak between sections so that the page
number of every fact is known ahead of time -- this makes it possible to
write an accurate tests/test_questions.csv "Expected Source" column.
"""
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, ListFlowable, ListItem
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
import os

styles = getSampleStyleSheet()
styles.add(ParagraphStyle(name='DocTitle', fontSize=18, leading=22, spaceAfter=6, textColor=colors.HexColor('#1a3d5c')))
styles.add(ParagraphStyle(name='Sec', parent=styles['Heading2'], fontSize=13, textColor=colors.HexColor('#2c5a7c'), spaceBefore=6, spaceAfter=8))
styles.add(ParagraphStyle(name='Body', parent=styles['Normal'], fontSize=10.3, leading=15, spaceAfter=8))

OUT_DIR = "documents"
os.makedirs(OUT_DIR, exist_ok=True)


def build_pdf(filename, title, sections):
    """sections: list of (heading, [body_paragraphs]) -- each section starts on its own page."""
    story = [Paragraph(title, styles['DocTitle']),
             Paragraph("Solstice Retail Pvt Ltd -- Internal HR Document (fictional company, for training/demo use only)",
                        styles['Body']),
             Spacer(1, 6)]
    for i, (heading, paras) in enumerate(sections):
        if i > 0:
            story.append(PageBreak())
        story.append(Paragraph(heading, styles['Sec']))
        for p in paras:
            if isinstance(p, list):
                story.append(ListFlowable([ListItem(Paragraph(x, styles['Body'])) for x in p],
                                           bulletType='bullet', leftIndent=14))
            else:
                story.append(Paragraph(p, styles['Body']))
    doc = SimpleDocTemplate(os.path.join(OUT_DIR, filename), pagesize=letter,
                             topMargin=0.7*inch, bottomMargin=0.7*inch,
                             leftMargin=0.75*inch, rightMargin=0.75*inch,
                             title=title, author="Solstice Retail Pvt Ltd")
    doc.build(story)
    print(f"Built {filename} ({len(sections)} pages)")


# ---------------------------------------------------------------------------
# 1. Employee_Handbook.pdf
# ---------------------------------------------------------------------------
build_pdf("Employee_Handbook.pdf", "Employee Handbook", [
    ("Welcome and Purpose", [
        "This handbook introduces new employees of Solstice Retail Pvt Ltd to the company's "
        "culture, working practices, and expectations. It applies to all full-time and "
        "part-time staff across every store and warehouse location.",
        "The handbook is reviewed annually by the HR department and updates are communicated "
        "by email at least two weeks before they take effect.",
    ]),
    ("Working Hours", [
        "Standard working hours are 9:30 AM to 6:30 PM, Monday to Friday, with a 60-minute "
        "unpaid lunch break. Store staff on rotational shifts follow the shift roster shared "
        "by their store manager at the start of each month.",
        "Employees are expected to log in through the company attendance portal at the start "
        "and end of each working day. See the Attendance Policy document for full details on "
        "how attendance is calculated.",
    ]),
    ("Employee Benefits Overview", [
        "Solstice Retail provides the following benefits to all confirmed employees:",
        ["Group health insurance covering the employee and up to 3 dependents.",
         "Employee discount of 20% on all in-store purchases.",
         "Annual performance bonus based on manager evaluation and company profitability.",
         "Reimbursement of approved professional certification costs up to Rs. 15,000 per year."],
        "Benefit enrollment is completed through the HR portal within 30 days of joining.",
    ]),
    ("IT and Email Usage", [
        "Company email accounts must be used for official communication only. Employees "
        "must not share their login credentials with anyone, including colleagues and "
        "managers.",
        "Personal use of company laptops for non-work purposes should be minimal and must "
        "never involve installing unauthorized software.",
    ]),
    ("Grievance Redressal", [
        "Any employee with a workplace concern should first raise it with their direct "
        "manager. If unresolved within 10 working days, the concern can be escalated to the "
        "HR helpdesk at hr-support@solsticeretail.example.",
        "All grievances are handled confidentially and Solstice Retail maintains a strict "
        "non-retaliation policy for employees who raise concerns in good faith.",
    ]),
])

# ---------------------------------------------------------------------------
# 2. Leave_Policy.pdf
# ---------------------------------------------------------------------------
build_pdf("Leave_Policy.pdf", "Leave Policy", [
    ("Types of Leave", [
        "Solstice Retail Pvt Ltd offers the following categories of paid leave to confirmed "
        "employees:",
        ["Casual Leave (CL): 12 days per calendar year, for short personal needs.",
         "Sick Leave (SL): 10 days per calendar year, for illness or medical appointments.",
         "Earned Leave (EL): 15 days per calendar year, accrued monthly and can be carried "
         "forward up to 30 days.",
         "Maternity Leave: 26 weeks as per applicable statutory guidelines.",
         "Paternity Leave: 10 working days within 3 months of the child's birth."],
    ]),
    ("Leave Accrual and Carry Forward", [
        "Earned Leave accrues at 1.25 days per completed month of service. Unused Earned "
        "Leave beyond 30 days at year-end is automatically encashed at the employee's basic "
        "daily rate in the December payroll cycle.",
        "Casual Leave and Sick Leave do not carry forward to the next calendar year and "
        "cannot be encashed.",
    ]),
    ("How to Apply for Leave", [
        "All leave requests must be submitted through the HR portal at least 3 working days "
        "in advance, except for sick leave, which may be applied for on the day of absence "
        "with manager notification.",
        "Leave requests are approved or rejected by the employee's direct manager within 2 "
        "working days. Unapproved absences are recorded as Loss of Pay (LOP).",
    ]),
    ("Public Holidays", [
        "Solstice Retail observes 12 public holidays each year, published in a company-wide "
        "calendar circulated every January. Store employees required to work on a public "
        "holiday receive a compensatory day off within the following 30 days.",
    ]),
])

# ---------------------------------------------------------------------------
# 3. Attendance_Policy.pdf
# ---------------------------------------------------------------------------
build_pdf("Attendance_Policy.pdf", "Attendance Policy", [
    ("Attendance Tracking Method", [
        "Attendance is tracked using the company's biometric terminals at warehouse "
        "locations and the mobile attendance app for store and office staff. Every clock-in "
        "and clock-out is timestamped and stored for payroll processing.",
    ]),
    ("How Attendance Is Calculated", [
        "Daily attendance is calculated as the total hours between clock-in and clock-out, "
        "minus the standard 60-minute lunch break, compared against the expected 8-hour "
        "shift. An employee is marked 'Present (Full Day)' if logged hours are 7.5 hours or "
        "more.",
        "An employee is marked 'Present (Half Day)' if logged hours are between 4 and 7.5 "
        "hours, and 'Absent' if logged hours are below 4 hours with no approved leave on "
        "record.",
        "Monthly attendance percentage is calculated as (days marked Present, including half "
        "days weighted at 0.5) divided by total working days in that month, multiplied by "
        "100.",
    ]),
    ("Late Arrival and Early Departure", [
        "Arriving more than 15 minutes after the shift start time is recorded as a late "
        "arrival. Three or more late arrivals in a calendar month trigger an automatic email "
        "notice to the employee and their manager.",
        "Employees needing to leave early must inform their manager in advance; unapproved "
        "early departures are treated the same as late arrivals for policy purposes.",
    ]),
])

# ---------------------------------------------------------------------------
# 4. Code_of_Conduct.pdf
# ---------------------------------------------------------------------------
build_pdf("Code_of_Conduct.pdf", "Code of Conduct", [
    ("Professional Behavior", [
        "All employees are expected to treat colleagues, customers, and vendors with "
        "courtesy and respect. Discriminatory remarks or behavior based on gender, religion, "
        "caste, disability, or any other protected characteristic are strictly prohibited.",
    ]),
    ("Anti-Harassment Policy", [
        "Solstice Retail maintains a zero-tolerance policy toward workplace harassment of "
        "any kind, including verbal, physical, and online harassment. Complaints can be "
        "raised confidentially with the Internal Complaints Committee (ICC) at "
        "icc@solsticeretail.example.",
        "The ICC is required to acknowledge a complaint within 3 working days and complete "
        "an initial review within 30 days, in line with applicable workplace harassment "
        "regulations.",
    ]),
    ("Conflict of Interest", [
        "Employees must disclose any outside business activity, financial interest, or "
        "family relationship that could reasonably create a conflict of interest with their "
        "role at Solstice Retail. Disclosures are made annually through the HR portal.",
    ]),
    ("Confidentiality", [
        "Employees must not share confidential business information -- including pricing "
        "strategy, supplier contracts, and unreleased product plans -- with anyone outside "
        "the company without written authorization from their department head.",
    ]),
    ("Disciplinary Action", [
        "Violations of this Code of Conduct are handled through a progressive disciplinary "
        "process: verbal warning, written warning, final written warning, and termination, "
        "depending on the severity of the violation. Serious violations such as harassment, "
        "fraud, or theft may result in immediate termination regardless of prior warnings.",
    ]),
])

print("\nAll 4 sample HR documents generated in documents/.")
