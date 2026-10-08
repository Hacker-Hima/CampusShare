import os
import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml import parse_xml
from docx.oxml.ns import nsdecls

def create_report():
    doc = docx.Document()

    # Configure Margins: 1.25 inch Left (Binding), 1.0 inch Top, Bottom, Right
    for section in doc.sections:
        section.top_margin = Inches(1.0)
        section.bottom_margin = Inches(1.0)
        section.left_margin = Inches(1.25)
        section.right_margin = Inches(1.0)
        section.header_distance = Inches(0.5)
        section.footer_distance = Inches(0.5)

        # Margin border lines in black
        sectPr = section._sectPr
        pgBorders = parse_xml(
            '<w:pgBorders xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" w:offsetFrom="page">'
            '<w:top w:val="single" w:sz="8" w:space="24" w:color="000000"/>'
            '<w:left w:val="single" w:sz="8" w:space="24" w:color="000000"/>'
            '<w:bottom w:val="single" w:sz="8" w:space="24" w:color="000000"/>'
            '<w:right w:val="single" w:sz="8" w:space="24" w:color="000000"/>'
            '</w:pgBorders>'
        )
        sectPr.append(pgBorders)

    # Base Normal Style
    style_normal = doc.styles['Normal']
    style_normal.font.name = 'Times New Roman'
    style_normal.font.size = Pt(12)

    # Paragraph Helper with Justification and First-Line Indent
    def add_para(text, size=12, bold=False, italic=False, align=WD_ALIGN_PARAGRAPH.JUSTIFY, space_after=6, space_before=0, line_spacing=1.15, first_line_indent=0.0, left_indent=0.0):
        p = doc.add_paragraph()
        p.alignment = align
        p.paragraph_format.space_before = Pt(space_before)
        p.paragraph_format.space_after = Pt(space_after)
        p.paragraph_format.line_spacing = line_spacing
        if first_line_indent != 0.0:
            p.paragraph_format.first_line_indent = Inches(first_line_indent)
        if left_indent != 0.0:
            p.paragraph_format.left_indent = Inches(left_indent)
        if text:
            run = p.add_run(text)
            run.font.name = 'Times New Roman'
            run.font.size = Pt(size)
            run.bold = bold
            run.italic = italic
        return p

    def add_body_para(text, space_after=6):
        # Academic standard body paragraph: strictly justified with 0.5 inch first-line indent
        return add_para(text, size=12, bold=False, italic=False, align=WD_ALIGN_PARAGRAPH.JUSTIFY, space_after=space_after, space_before=0, line_spacing=1.15, first_line_indent=0.5)

    def add_chapter_title(chapter_num, title_text):
        p1 = add_para(f"CHAPTER {chapter_num}", size=15, bold=True, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=2, space_before=4)
        p2 = add_para(title_text.upper(), size=15, bold=True, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=14, space_before=0)
        return p2

    def add_section_heading(heading_text):
        return add_para(heading_text, size=13.5, bold=True, align=WD_ALIGN_PARAGRAPH.LEFT, space_after=6, space_before=10)

    def add_code_snippet(filename_label, code_text):
        # In sample report, code is NOT in boxes or tables! It is simple indented code text!
        p_fn = doc.add_paragraph()
        p_fn.paragraph_format.space_before = Pt(4)
        p_fn.paragraph_format.space_after = Pt(2)
        r_fn = p_fn.add_run(filename_label)
        r_fn.font.name = 'Times New Roman'
        r_fn.font.size = Pt(11)
        r_fn.bold = True

        for line in code_text.strip().splitlines():
            p_code = doc.add_paragraph()
            p_code.paragraph_format.space_before = Pt(0)
            p_code.paragraph_format.space_after = Pt(0)
            p_code.paragraph_format.line_spacing = 1.05
            p_code.paragraph_format.left_indent = Inches(0.2)
            r_code = p_code.add_run(line if line.strip() else " ")
            r_code.font.name = 'Consolas'
            r_code.font.size = Pt(9.5)
            r_code.font.color.rgb = RGBColor(20, 20, 20)

        p_spacer = doc.add_paragraph()
        p_spacer.paragraph_format.space_before = Pt(0)
        p_spacer.paragraph_format.space_after = Pt(4)

    def add_result_figure(image_path, caption_text, width_inch=4.65):
        if os.path.exists(image_path):
            p_img = doc.add_paragraph()
            p_img.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p_img.paragraph_format.space_before = Pt(4)
            p_img.paragraph_format.space_after = Pt(2)
            p_img.add_run().add_picture(image_path, width=Inches(width_inch))
            
            p_cap = doc.add_paragraph()
            p_cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p_cap.paragraph_format.space_before = Pt(1)
            p_cap.paragraph_format.space_after = Pt(6)
            run = p_cap.add_run(caption_text)
            run.font.name = 'Times New Roman'
            run.font.size = Pt(9.5)
            run.bold = True
            run.font.color.rgb = RGBColor(30, 41, 59)

    # =========================================================================
    # PAGE 1: TITLE / COVER PAGE (Matches Sample Page 1 Exactly)
    # =========================================================================
    add_para("23CS11E - WEBFRAMEWORK USING PYTHON", size=14, bold=True, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=18, space_before=10)
    add_para("Micro Project Report", size=13, bold=True, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=4)
    add_para("On", size=12, bold=True, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=6)
    
    add_para("CampusShare: Smart Campus Resource Sharing, Marketplace & Community Platform", 
             size=15, bold=True, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=20)

    # Logo
    if os.path.exists("report/college_logo.png"):
        p_logo = doc.add_paragraph()
        p_logo.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_logo.paragraph_format.space_before = Pt(2)
        p_logo.paragraph_format.space_after = Pt(16)
        p_logo.add_run().add_picture("report/college_logo.png", width=Inches(1.75))

    add_para("Submitted by", size=11, bold=True, italic=True, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=4)
    add_para("Himachalam C", size=13, bold=True, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=2)
    add_para("2403957610421111", size=12, bold=True, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=22)

    add_para("In partial fulfillment for the award of the degree of", size=11, italic=True, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=4)
    add_para("BACHELOR OF ENGINEERING", size=13, bold=True, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=2)
    add_para("in", size=11, italic=True, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=2)
    add_para("COMPUTER SCIENCE AND ENGINEERING", size=13, bold=True, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=22)

    add_para("NATIONAL ENGINEERING COLLEGE", size=14, bold=True, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=2)
    add_para("(An Autonomous Institution affiliated to Anna University, Chennai)", size=10.5, italic=True, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=2)
    add_para("K.R.NAGAR, KOVILPATTI – 628503", size=11, bold=True, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=4)
    add_para("OCTOBER – 2026", size=11, bold=True, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=0)

    doc.add_page_break()

    # =========================================================================
    # PAGE 2: BONAFIDE CERTIFICATE (Matches Sample Page 2 Exactly - NO BOXES!)
    # =========================================================================
    add_para("NATIONAL ENGINEERING COLLEGE", size=14, bold=True, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=2, space_before=10)
    add_para("K.R.NAGAR, KOVILPATTI – 628503", size=11, bold=True, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=14)

    if os.path.exists("report/college_logo.png"):
        p_logo = doc.add_paragraph()
        p_logo.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_logo.paragraph_format.space_before = Pt(2)
        p_logo.paragraph_format.space_after = Pt(14)
        p_logo.add_run().add_picture("report/college_logo.png", width=Inches(1.5))

    add_para("BONAFIDE CERTIFICATE", size=14, bold=True, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=20)

    cert_text = (
        "This is to certify that this project report is a Bonafide record of Himachalam C (2403957610421111) "
        "work done for the course 23CS11E - WEBFRAMEWORK USING PYTHON at the NATIONAL ENGINEERING COLLEGE, "
        "K.R. NAGAR, during the academic year 2025 – 2026 who carried out the project work under my supervision."
    )
    add_para(cert_text, size=12, align=WD_ALIGN_PARAGRAPH.JUSTIFY, space_after=80, line_spacing=1.35, first_line_indent=0.5)

    # EXACT MATCH TO SAMPLE: Plain text signature on left, NO boxes, NO borders!
    p_inst = doc.add_paragraph()
    p_inst.paragraph_format.space_before = Pt(60)
    p_inst.paragraph_format.space_after = Pt(0)
    p_inst.paragraph_format.left_indent = Inches(0.0)
    r_inst = p_inst.add_run("Course Instructor/Guide")
    r_inst.font.name = 'Times New Roman'
    r_inst.font.size = Pt(12)
    r_inst.bold = True

    doc.add_page_break()

    # =========================================================================
    # PAGE 3: TABLE OF CONTENTS (Matches Sample Page 3 Exactly - ONLY 4 CHAPTERS!)
    # =========================================================================
    add_para("TABLE OF CONTENTS", size=14, bold=True, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=24, space_before=10)

    # 4 columns tab alignment matching sample report: CHAPTER NO. | TITLE | PAGE NO
    toc_table = doc.add_table(rows=5, cols=3)
    toc_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    toc_table.autofit = False

    col_widths = [Inches(1.5), Inches(3.8), Inches(1.0)]
    for row in toc_table.rows:
        for i, w in enumerate(col_widths):
            row.cells[i].width = w

    # Header row
    hdr_cells = toc_table.rows[0].cells
    for i, t in enumerate(["CHAPTER NO.", "TITLE", "PAGE NO"]):
        p = hdr_cells[i].paragraphs[0]
        p.paragraph_format.space_after = Pt(12)
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER if i != 1 else WD_ALIGN_PARAGRAPH.LEFT
        r = p.add_run(t)
        r.font.name = 'Times New Roman'
        r.font.size = Pt(11)
        r.bold = True

    # 4 Chapter items exactly matching sample report
    items = [
        ("1", "INTRODUCTION", "5"),
        ("2", "IMPLEMENTATION", "8"),
        ("3", "IMPLEMENTATION RESULTS", "19"),
        ("4", "CONCLUSION", "23")
    ]

    for idx, (ch, title, pg) in enumerate(items):
        row_cells = toc_table.rows[idx + 1].cells
        p0 = row_cells[0].paragraphs[0]
        p0.paragraph_format.space_after = Pt(10)
        p0.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r0 = p0.add_run(ch)
        r0.font.name = 'Times New Roman'
        r0.font.size = Pt(11)

        p1 = row_cells[1].paragraphs[0]
        p1.paragraph_format.space_after = Pt(10)
        p1.alignment = WD_ALIGN_PARAGRAPH.LEFT
        r1 = p1.add_run(title)
        r1.font.name = 'Times New Roman'
        r1.font.size = Pt(11)

        p2 = row_cells[2].paragraphs[0]
        p2.paragraph_format.space_after = Pt(10)
        p2.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r2 = p2.add_run(pg)
        r2.font.name = 'Times New Roman'
        r2.font.size = Pt(11)

    # Remove all visible borders from table to match sample
    for row in toc_table.rows:
        for cell in row.cells:
            tcPr = cell._tc.get_or_add_tcPr()
            tcBorders = parse_xml(f'''
                <w:tcBorders {nsdecls("w")}>
                    <w:top w:val="none"/>
                    <w:left w:val="none"/>
                    <w:bottom w:val="none"/>
                    <w:right w:val="none"/>
                </w:tcBorders>
            ''')
            tcPr.append(tcBorders)

    doc.add_page_break()

    # =========================================================================
    # PAGE 4: ABSTRACT (Matches Sample Page 4 Exactly)
    # =========================================================================
    add_para("ABSTRACT", size=15, bold=True, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=16, space_before=6)

    abs_text = (
        "The CampusShare platform is a web-based application designed to streamline and automate the campus resource "
        "sharing and peer-to-peer exchange process by providing an integrated platform where students, faculty, and administrators "
        "can efficiently interact. Through the portal, students can register, build profiles, browse categorized study materials, "
        "trade secondhand academic equipment with zero commissions, post wanted requests with smart keyword matching, and track "
        "their campus reputation through a transparent Trust Score meter. The system's functionality is driven by five key modules: "
        "User & Role Management for secure access, Campus Marketplace for peer-to-peer textbook and kit exchanges, Academic Notes Library "
        "with faculty verification badges, Wanted Request Board with smart resource discovery, and Circular Campus Impact analytics.\n\n"
        "Built on a modern technology stack featuring Python 3.14, Flask, and MongoDB, and supported by PyMongo indexing and semantic "
        "Bootstrap 5 CSS, the portal strictly adheres to an architectural Zero-JavaScript constraint. All page rendering, state management, "
        "and multi-facet catalog filtering are executed server-side to guarantee maximum security, instant loading, and universal accessibility. "
        "By eliminating manual notice board bottlenecks and unmoderated social media trading groups, CampusShare ultimately empowers "
        "colleges with a centralized, automated, and sustainable platform that significantly enhances student collaboration and simplifies "
        "campus resource management."
    )
    for p_block in abs_text.split('\n\n'):
        add_body_para(p_block, space_after=10)

    doc.add_page_break()

    # =========================================================================
    # CHAPTER 1: INTRODUCTION (Pages 5, 6, 7)
    # =========================================================================
    add_chapter_title("1", "INTRODUCTION")

    # Page 5: 1.1 Introduction
    add_section_heading("1.1 INTRODUCTION")
    intro_text1 = (
        "Higher education campuses represent vibrant ecosystems where thousands of students and faculty members interact daily, "
        "requiring continuous access to diverse academic tools, study materials, textbooks, hardware components, and laboratory gear. "
        "Throughout an undergraduate curriculum, students invest substantially in specialized textbooks, engineering drawing drafters, "
        "scientific calculators, microcontroller trainer kits, and reference literature. Typically, these resources remain active for a single "
        "semester of 4 to 6 months, after which they become idle as students advance into higher coursework. Simultaneously, newly enrolled "
        "students entering the department are required to purchase the exact same resources anew, creating unnecessary financial strain "
        "and exacerbating environmental resource consumption."
    )
    add_body_para(intro_text1, space_after=10)

    intro_text2 = (
        "Although informal channels such as campus bulletin boards, WhatsApp groups, and general social media pages exist, they suffer "
        "from severe operational shortcomings. Information is scattered, listings expire quickly without archiving, fraud risks are high due to "
        "anonymous profiles, and there is no institutional mechanism to verify academic materials or track resource condition. "
        "CampusShare was conceived and developed as a modern, centralized institutional web portal to systematically solve these "
        "challenges. Built upon Python's Flask framework, it delivers a secure, accessible, and structured environment where students can "
        "browse verified notes, trade secondhand campus equipment with zero fees, submit wanted requests with automated smart matching, "
        "and track verified reputation metrics within the safe boundaries of the college community."
    )
    add_body_para(intro_text2, space_after=14)

    doc.add_page_break()

    # Page 6: 1.2 Problem Statement
    add_section_heading("1.2 PROBLEM STATEMENT")
    prob_p1 = (
        "The existing campus resource sharing and textbook exchange process in many colleges is largely manual and fragmented, "
        "resulting in inefficient communication between students, faculty, and administrative coordinators. This creates significant "
        "difficulty in managing resource listings, verify academic notes, and track secondhand equipment across multiple engineering departments. "
        "The heavy reliance on informal social media groups is highly susceptible to scams, spam, and unverified accounts, often leading to "
        "lost time, financial loss, and safety concerns for participating students."
    )
    add_body_para(prob_p1, space_after=10)

    prob_p2 = (
        "The tracking of wanted materials and coordinating physical handovers becomes a time-consuming burden. When students urgently require "
        "a specific calculator or lab component, manual notice boards offer no searchability or matching, creating anxiety and delays in academic "
        "work. Furthermore, the complete absence of a standardized reputation system means students cannot gauge seller trustworthiness. "
        "Additionally, widespread reliance on heavy client-side JavaScript frameworks introduces security vulnerabilities, high data overhead, "
        "and slow render times on mobile devices. Therefore, there is a clear and urgent need for an automated, server-rendered system to manage "
        "the entire campus sharing ecosystem in a structured, efficient, and transparent manner."
    )
    add_body_para(prob_p2, space_after=14)

    doc.add_page_break()

    # Page 7: 1.3 Objectives
    add_section_heading("1.3 OBJECTIVES")
    obj_p1 = (
        "The primary objective of the CampusShare Portal is to establish a centralized platform that efficiently manages all campus "
        "resource sharing, peer-to-peer marketplace transactions, and academic collaboration. It provides an easy-to-use, accessible interface "
        "for students to handle registration, profile management, resource uploads, and item listings, while simultaneously allowing faculty "
        "and administrators to verify academic notes and oversee institutional integrity."
    )
    add_body_para(obj_p1, space_after=10)

    obj_p2 = (
        "The system features advanced automation, including keyword-based smart matching algorithms for wanted requests, dynamic trust "
        "scoring algorithms based on verified handovers and peer reviews, and multi-facet filtering for secondhand marketplace listings. "
        "Furthermore, the portal operates under a strict Zero-JavaScript architectural constraint, ensuring that all UI rendering, form validation, "
        "and authentication flows execute securely on the server with Jinja2 templates. To keep all members informed, it delivers real-time notifications "
        "and campus messaging. Ultimately, it furnishes administrators with powerful analytics tools to track student participation, resource circulation, "
        "and circular environmental savings across the institution."
    )
    add_body_para(obj_p2, space_after=14)

    doc.add_page_break()

    # =========================================================================
    # CHAPTER 2: IMPLEMENTATION (Pages 8-18)
    # =========================================================================
    add_chapter_title("2", "IMPLEMENTATION")

    # Page 8: 2.1 Project Structure
    add_section_heading("2.1 PROJECT STRUCTURE")
    add_body_para(
        "CampusShare is architected as an enterprise-grade modular Python Flask web application. It partitions business logic, "
        "routing blueprints, database persistence, and presentation templates into independent, cohesive packages as shown in Figure 2.1:",
        space_after=4
    )

    add_result_figure("report/screenshots/fig2_1_project_structure.png", "Figure 2.1: CampusShare Modular Project Directory Structure", width_inch=5.3)

    add_body_para(
        "The structure comprises the application factory (app.py), configuration settings (config.py), PyMongo persistence layer (database/), "
        "modular route blueprints (routes/), server-side Jinja2 templates (templates/), and a custom academic design system (static/).",
        space_after=10
    )

    doc.add_page_break()

    # Pages 9 to 18: 2.2 Project Code (Clean Code Listings - NO BOXES!)
    add_section_heading("2.2 PROJECT CODE")

    # Page 9: app.py
    code_p9 = """from flask import Flask, jsonify, render_template, session, redirect, url_for
from config import Config
from database.connection import get_db
from database.seed import seed_database
from database.indexes import create_indexes
from routes.auth import auth_bp
from routes.student import student_bp
from routes.faculty import faculty_bp
from routes.admin import admin_bp
from routes.marketplace import marketplace_bp
import os

app = Flask(__name__)
app.config.from_object(Config)
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

@app.context_processor
def inject_global_template_vars():
    unread_msgs = 0
    user_trust = 75
    if 'user_id' in session:
        try:
            db = get_db()
            unread_msgs = db['messages'].count_documents({"receiver_id": session['user_id'], "is_read": False})
            u = db['users'].find_one({"_id": ObjectId(session['user_id'])})
            if u: user_trust = u.get('trust_score', 85)
        except Exception: pass
    return {'unread_messages_count': unread_msgs, 'current_user_trust_score': user_trust}

app.register_blueprint(auth_bp)
app.register_blueprint(student_bp)
app.register_blueprint(faculty_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(marketplace_bp)"""
    add_code_snippet("app.py:", code_p9)
    doc.add_page_break()

    # Page 10: routes/auth.py
    code_p10 = """from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from werkzeug.security import check_password_hash, generate_password_hash
from database.connection import get_db

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        identifier = request.form.get('identifier', '').strip()
        password = request.form.get('password', '').strip()
        db = get_db()
        user = db['users'].find_one({"$or": [
            {"username": identifier}, {"email": identifier}, {"roll_no": identifier}
        ]})
        if user and check_password_hash(user.get('password', ''), password):
            session.clear()
            session['user_id'] = str(user['_id'])
            session['username'] = user.get('username')
            session['role'] = user.get('role', 'student')
            session['full_name'] = user.get('full_name')
            role_dest = {'admin': 'admin.dashboard', 'faculty': 'faculty.dashboard'}.get(user.get('role'), 'student.dashboard')
            return redirect(url_for(role_dest))
        flash("Invalid institutional credentials. Please verify your ID and password.", "danger")
    return render_template('auth/login.html')

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()
        role = request.form.get('role', 'student')
        db = get_db()
        hashed = generate_password_hash(password, method='pbkdf2:sha256')
        db['users'].insert_one({
            "username": username, "email": email, "password": hashed,
            "role": role, "trust_score": 75, "is_verified": False
        })
        flash("Account created! Please sign in with your credentials.", "success")
        return redirect(url_for('auth.login'))
    return render_template('auth/register.html')"""
    add_code_snippet("routes/auth.py:", code_p10)
    doc.add_page_break()

    # Page 11: utils/decorators.py
    code_p11 = """from functools import wraps
from flask import session, redirect, url_for, flash, request

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash("Please sign in to access this page.", "warning")
            return redirect(url_for('auth.login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

def role_required(*allowed_roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                flash("Authentication required.", "warning")
                return redirect(url_for('auth.login'))
            if session.get('role') not in allowed_roles:
                flash("Access denied: Insufficient institutional permissions.", "danger")
                return redirect(url_for('index'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def student_required(f):
    return role_required('student', 'admin')(f)

def faculty_required(f):
    return role_required('faculty', 'admin')(f)

def admin_required(f):
    return role_required('admin')(f)"""
    add_code_snippet("utils/decorators.py:", code_p11)
    doc.add_page_break()

    # Page 12: routes/student.py
    code_p12 = """from bson import ObjectId
from flask import Blueprint, render_template, session
from database.connection import get_db
from utils.decorators import student_required
from utils.trust import calculate_trust_score

student_bp = Blueprint('student', __name__, url_prefix='/student')

@student_bp.route('/dashboard')
@student_required
def dashboard():
    db = get_db()
    user_id = session['user_id']
    u = db['users'].find_one({"_id": ObjectId(user_id)})
    trust = calculate_trust_score(user_id, db)
    
    my_resources = list(db['resources'].find({"uploader_id": user_id}).limit(5))
    my_listings = list(db['marketplace'].find({"seller_id": user_id}).limit(5))
    my_requests = list(db['resource_requests'].find({"requester_id": user_id}).limit(5))
    my_borrows = list(db['borrowings'].find({"borrower_id": user_id, "status": "borrowed"}))
    
    stats = {
        'uploads': db['resources'].count_documents({"uploader_id": user_id}),
        'marketplace_active': db['marketplace'].count_documents({"seller_id": user_id, "status": "available"}),
        'requests_open': db['resource_requests'].count_documents({"requester_id": user_id, "status": "open"}),
        'trust_score': trust,
        'points': u.get('points', 0) if u else 0
    }
    return render_template(
        'student/dashboard.html',
        user=u, stats=stats, my_resources=my_resources,
        my_listings=my_listings, my_requests=my_requests, my_borrows=my_borrows
    )"""
    add_code_snippet("routes/student.py:", code_p12)
    doc.add_page_break()

    # Page 13: routes/marketplace.py (List Catalog)
    code_p13 = """import re
from flask import Blueprint, render_template, request, session
from database.connection import get_db

marketplace_bp = Blueprint('marketplace', __name__, url_prefix='/marketplace')
MARKETPLACE_CATEGORIES = ["Books", "Electronics", "Calculators", "Project Kits", "Furniture", "Cycles", "Other"]

@marketplace_bp.route('', methods=['GET'])
@marketplace_bp.route('/', methods=['GET'])
def list_items():
    db = get_db()
    q = request.args.get('q', '').strip()
    category = request.args.get('category', '').strip()
    condition = request.args.get('condition', '').strip()
    free_only = request.args.get('free', '').strip()
    
    query = {"status": {"$in": ["available", "reserved"]}}
    if q:
        safe_q = re.escape(q)
        regex = {"$regex": safe_q, "$options": "i"}
        query["$or"] = [{"title": regex}, {"description": regex}, {"category": regex}]
    if category and category in MARKETPLACE_CATEGORIES:
        query["category"] = category
    if condition:
        query["condition"] = condition
    if free_only in ['1', 'true', 'yes']:
        query["$or"] = [{"is_free": True}, {"price": 0}]

    items = list(db['marketplace'].find(query).sort("created_at", -1))
    return render_template('marketplace/list.html', items=items, categories=MARKETPLACE_CATEGORIES)"""
    add_code_snippet("routes/marketplace.py (Catalog Filters):", code_p13)
    doc.add_page_break()

    # Page 14: routes/marketplace.py (Offers)
    code_p14 = """from datetime import datetime
from bson import ObjectId
from flask import request, redirect, url_for, flash, session
from database.connection import get_db
from utils.decorators import login_required

@marketplace_bp.route('/offer/<item_id>', methods=['POST'])
@login_required
def submit_offer(item_id):
    db = get_db()
    offered_price = float(request.form.get('offered_price', 0))
    message = request.form.get('message', '').strip()
    item = db['marketplace'].find_one({"_id": ObjectId(item_id)})
    if not item:
        flash("Item not found.", "danger")
        return redirect(url_for('marketplace.list_items'))

    offer_doc = {
        "item_id": str(item_id),
        "item_title": item.get('title'),
        "seller_id": str(item.get('seller_id')),
        "buyer_id": session['user_id'],
        "buyer_name": session.get('full_name') or session.get('username'),
        "offered_price": offered_price,
        "message": message,
        "status": "pending",
        "created_at": datetime.utcnow()
    }
    db['marketplace_offers'].insert_one(offer_doc)
    flash(f"Your offer of ₹{offered_price:.0f} was sent to {item.get('seller_name')}.", "success")
    return redirect(url_for('marketplace.item_detail', item_id=item_id))"""
    add_code_snippet("routes/marketplace.py (Negotiation Offers):", code_p14)
    doc.add_page_break()

    # Page 15: routes/resources.py
    code_p15 = """from datetime import datetime
from bson import ObjectId
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from database.connection import get_db
from utils.decorators import login_required
from utils.helpers import save_uploaded_file

resources_bp = Blueprint('resources', __name__, url_prefix='/resources')

@resources_bp.route('/upload', methods=['GET', 'POST'])
@login_required
def upload_resource():
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        subject = request.form.get('subject', '').strip()
        department = request.form.get('department', '').strip()
        semester = request.form.get('semester', '1')
        doc_file = request.files.get('file')
        
        saved_name, original_name = save_uploaded_file(doc_file)
        db = get_db()
        db['resources'].insert_one({
            "title": title, "subject": subject, "department": department,
            "semester": int(semester), "filename": saved_name,
            "original_filename": original_name, "uploader_id": session['user_id'],
            "uploader_name": session.get('full_name'), "status": "approved",
            "downloads": 0, "created_at": datetime.utcnow()
        })
        flash("Study resource uploaded successfully and published to department vault.", "success")
        return redirect(url_for('resources.list_resources'))
    return render_template('resources/upload.html')"""
    add_code_snippet("routes/resources.py (Academic Notes):", code_p15)
    doc.add_page_break()

    # Page 16: routes/requests.py
    code_p16 = """from datetime import datetime
from bson import ObjectId
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from database.connection import get_db
from utils.decorators import login_required

requests_bp = Blueprint('requests', __name__, url_prefix='/requests')

@requests_bp.route('/new', methods=['GET', 'POST'])
@login_required
def create_request():
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        category = request.form.get('category', '').strip()
        urgency = request.form.get('urgency', 'medium')
        description = request.form.get('description', '').strip()
        
        db = get_db()
        db['resource_requests'].insert_one({
            "title": title, "category": category, "urgency": urgency,
            "description": description, "requester_id": session['user_id'],
            "requester_name": session.get('full_name'), "status": "open",
            "created_at": datetime.utcnow()
        })
        flash("Wanted listing posted! Smart matching will notify potential lenders.", "success")
        return redirect(url_for('requests.list_requests'))
    return render_template('requests/create.html')"""
    add_code_snippet("routes/requests.py (Wanted Board):", code_p16)
    doc.add_page_break()

    # Page 17: utils/trust.py
    code_p17 = """from bson import ObjectId
from database.connection import get_db

def calculate_trust_score(user_id, db=None):
    if db is None: db = get_db()
    user = db['users'].find_one({"_id": ObjectId(user_id)})
    if not user: return 75
    
    score = 70.0  # Base institutional rating
    if user.get('is_verified', False): score += 10.0
    
    # Points earned through completed exchanges
    points = user.get('points', 0)
    score += min(10.0, (points / 20.0))
    
    # Peer Reviews Weighted Mean
    reviews = list(db['user_reviews'].find({"reviewee_id": str(user_id)}))
    if reviews:
        avg_rating = sum([r.get('rating', 5.0) for r in reviews]) / len(reviews)
        score += (avg_rating - 3.0) * 5.0
        
    # Moderation penalty for verified misconduct
    reports = db['moderation_reports'].count_documents({"reported_user_id": str(user_id), "status": "resolved_action_taken"})
    score -= (reports * 15.0)
    
    final_score = int(max(10, min(100, round(score))))
    db['users'].update_one({"_id": ObjectId(user_id)}, {"$set": {"trust_score": final_score}})
    return final_score"""
    add_code_snippet("utils/trust.py (Reputation Scoring):", code_p17)
    doc.add_page_break()

    # Page 18: database/indexes.py
    code_p18 = """from pymongo import ASCENDING, DESCENDING, TEXT

def create_indexes(db):
    # Unique Roll Number & Username Indexes
    db['users'].create_index([("username", ASCENDING)], unique=True)
    db['users'].create_index([("email", ASCENDING)], unique=True)
    db['users'].create_index([("roll_no", ASCENDING)], unique=True, sparse=True)
    
    # Marketplace Full-Text and Multi-Facet Indexes
    db['marketplace'].create_index([("title", TEXT), ("description", TEXT), ("category", TEXT)])
    db['marketplace'].create_index([("status", ASCENDING), ("created_at", DESCENDING)])
    db['marketplace'].create_index([("category", ASCENDING), ("price", ASCENDING)])
    
    # Academic Resources Text & Download Indexes
    db['resources'].create_index([("title", TEXT), ("subject", TEXT), ("department", TEXT)])
    db['resources'].create_index([("status", ASCENDING), ("downloads", DESCENDING)])
    
    # Wanted Request Board Urgency Index
    db['resource_requests'].create_index([("status", ASCENDING), ("urgency", ASCENDING)])
    print("[MongoDB Indexes] Successfully synchronized all B-Tree & Text indexes.")"""
    add_code_snippet("database/indexes.py (B-Tree & Text Indexes):", code_p18)
    doc.add_page_break()

    # =========================================================================
    # CHAPTER 3: IMPLEMENTATION RESULTS (Pages 19-22: Exactly 2 Figures Per Page)
    # =========================================================================
    add_chapter_title("3", "IMPLEMENTATION RESULTS")

    # Page 19: Figures 3.1 & 3.2
    add_result_figure("report/screenshots/fig3_1_homepage.png", "Figure 3.1: NEC CampusShare Portal Homepage with Professional Landing Interface", width_inch=4.65)
    add_result_figure("report/screenshots/fig3_2_login.png", "Figure 3.2: NEC CampusShare User Authentication (Login) Interface with Frosted Glass Aesthetics", width_inch=4.65)
    doc.add_page_break()

    # Page 20: Figures 3.3 & 3.4
    add_result_figure("report/screenshots/fig3_3_student_dashboard.png", "Figure 3.3: NEC CampusShare Student Dashboard with Recent Activities & Reputation Vault", width_inch=4.65)
    add_result_figure("report/screenshots/fig3_4_marketplace.png", "Figure 3.4: NEC CampusShare Student Marketplace Listings with Multi-Facet Filters", width_inch=4.65)
    doc.add_page_break()

    # Page 21: Figures 3.5 & 3.6
    add_result_figure("report/screenshots/fig3_5_wanted_board.png", "Figure 3.5: NEC CampusShare Wanted Resource Request Board with Smart Match Engine", width_inch=4.65)
    add_result_figure("report/screenshots/fig3_6_about_page.png", "Figure 3.6: NEC CampusShare Informational Platform Architecture & Circular Campus Overview", width_inch=4.65)
    doc.add_page_break()

    # Page 22: Figures 3.7 & 3.8
    add_result_figure("report/screenshots/fig3_7_faculty_dashboard.png", "Figure 3.7: NEC CampusShare Faculty Workspace & Resource Moderation System", width_inch=4.65)
    add_result_figure("report/screenshots/fig3_8_admin_dashboard.png", "Figure 3.8: NEC CampusShare Admin Control Center with Campus Impact Analytics", width_inch=4.65)
    doc.add_page_break()

    # =========================================================================
    # CHAPTER 4: CONCLUSION (Page 23)
    # =========================================================================
    add_chapter_title("4", "CONCLUSION")

    conc_text1 = (
        "The CampusShare platform has been successfully designed and developed to automate and simplify the traditional, manual "
        "campus resource sharing and textbook exchange process. The system integrates students, faculty, and administrators onto a single "
        "digital platform, ensuring smooth interaction and efficient management of all sharing-related activities. By leveraging Python Flask "
        "for a secure and scalable backend, Jinja2 for server-rendered interfaces under a strict Zero-JavaScript constraint, and MongoDB for scalable "
        "NoSQL persistence, the portal delivers a dependable, high-performance solution for the college community."
    )
    add_body_para(conc_text1, space_after=10)

    conc_text2 = (
        "Through modules like the Zero-Commission Marketplace, Academic Notes Library, Wanted Request Board with smart matching, and the dynamic "
        "Campus Trust Scoring engine, the system eliminates communication barriers and promotes a circular, sustainable academic economy. "
        "Real-time notifications and campus impact metrics further enhance institutional transparency. In conclusion, CampusShare modernizes "
        "campus resource sharing, providing an automated, fair, and scalable system that empowers students and enhances collegiate collaboration."
    )
    add_body_para(conc_text2, space_after=14)

    primary_file = "report/CampusShare_WFP_Micro_Project_Report.docx"
    backup_file = "report/CampusShare_WFP_Micro_Project_Report_Updated.docx"
    
    saved_file = primary_file
    try:
        doc.save(primary_file)
        print(f"Report document successfully saved to: {primary_file}")
    except PermissionError:
        print(f"Warning: {primary_file} is currently open and locked by another application (e.g. WPS Office).")
        doc.save(backup_file)
        saved_file = backup_file
        print(f"Saved to alternative path: {backup_file}")
    
    # Also export to PDF using Word COM if available
    try:
        import win32com.client
        word = win32com.client.Dispatch("Word.Application")
        word.Visible = False
        abs_in = os.path.abspath(saved_file)
        abs_out = os.path.abspath("report/CampusShare_WFP_Micro_Project_Report.pdf")
        doc_com = word.Documents.Open(abs_in)
        doc_com.SaveAs(abs_out, FileFormat=17) # wdFormatPDF = 17
        doc_com.Close()
        word.Quit()
        print(f"Successfully exported PDF to: {abs_out}")
    except Exception as e:
        print(f"Word COM PDF export notice: {e}")

if __name__ == '__main__':
    create_report()
