import sys
import os
from datetime import datetime, timezone, timedelta
from bson import ObjectId
from werkzeug.security import generate_password_hash

# Ensure project root is in sys.path when executed directly
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from database.connection import get_db

def seed_database():
    """
    Seeds default administrative categories, demo user accounts,
    and realistic sample resources, borrowings, and requests for viva demonstration.
    """
    db = get_db()
    users_col = db['users']
    categories_col = db['categories']
    resources_col = db['resources']
    requests_col = db['resource_requests']
    borrowings_col = db['borrowings']
    reservations_col = db['reservations']
    activities_col = db['activities']
    notifications_col = db['notifications']

    # 1. Seed Core Categories if empty
    if categories_col.count_documents({}) == 0:
        default_categories = [
            {"name": "Notes", "type": "academic", "description": "Subject lecture notes & summaries"},
            {"name": "Question Papers", "type": "academic", "description": "Mid-term & semester question papers"},
            {"name": "Lab Manuals", "type": "academic", "description": "Practical and lab experiment guidelines"},
            {"name": "E-books & PPTs", "type": "academic", "description": "Electronic textbooks and presentations"},
            {"name": "Project Kits", "type": "physical", "description": "Arduino, Raspberry Pi and sensor kits"},
            {"name": "Lab Equipment", "type": "physical", "description": "Multimeters, oscilloscopes & calculators"},
            {"name": "Seminar Halls", "type": "campus", "description": "Air-conditioned halls for events"},
            {"name": "Projectors & Labs", "type": "campus", "description": "Digital displays and departmental computer labs"}
        ]
        categories_col.insert_many(default_categories)
        print("[Database Seed] Seeded default resource categories.")

    # 2. Seed Default Accounts
    admin_user = users_col.find_one({"username": "admin"})
    if not admin_user:
        admin_id = users_col.insert_one({
            "username": "admin",
            "email": "admin@campusshare.edu",
            "password_hash": generate_password_hash("Admin@123"),
            "full_name": "System Administrator",
            "role": "admin",
            "department": "CSE",
            "phone": "9876543210",
            "bio": "Central platform administrator for CampusShare.",
            "is_active": True,
            "created_at": datetime.now(timezone.utc)
        }).inserted_id
    else:
        admin_id = admin_user['_id']

    faculty_user = users_col.find_one({"username": "prof_sharma"})
    if not faculty_user:
        faculty_id = users_col.insert_one({
            "username": "prof_sharma",
            "email": "sharma@campusshare.edu",
            "password_hash": generate_password_hash("Faculty@123"),
            "full_name": "Prof. Rajesh Sharma",
            "role": "faculty",
            "department": "CSE",
            "phone": "9876543211",
            "bio": "Associate Professor, Department of Computer Science & Engineering.",
            "is_active": True,
            "created_at": datetime.now(timezone.utc)
        }).inserted_id
    else:
        faculty_id = faculty_user['_id']

    student_user = users_col.find_one({"username": "rahul_cse"})
    if not student_user:
        student_id = users_col.insert_one({
            "username": "rahul_cse",
            "email": "rahul@campusshare.edu",
            "password_hash": generate_password_hash("Student@123"),
            "full_name": "Rahul Verma",
            "role": "student",
            "department": "CSE",
            "year": "3",
            "section": "A",
            "phone": "9876543212",
            "bio": "Pre-final year CSE student enthusiastic about Web Systems & NoSQL.",
            "is_active": True,
            "created_at": datetime.now(timezone.utc)
        }).inserted_id
    else:
        student_id = student_user['_id']

    # 3. Seed Sample Resources if empty
    if resources_col.count_documents({}) == 0:
        sample_resources = [
            {
                "title": "DBMS Comprehensive Lecture Notes (Unit 1-5)",
                "description": "Complete handwritten notes covering Relational Algebra, ER Modeling, Normalization up to BCNF, and Concurrency Control.",
                "category": "Notes",
                "resource_type": "academic",
                "subject": "Database Management Systems",
                "department": "CSE",
                "semester": "5",
                "tags": ["DBMS", "SQL", "Normalization", "Transactions"],
                "owner_id": str(faculty_id),
                "owner_name": "Prof. Rajesh Sharma",
                "availability": "available",
                "file_path": None,
                "file_name": "dbms_complete_notes.pdf",
                "location": None,
                "downloads": 48,
                "views": 132,
                "rating": 4.8,
                "review_count": 5,
                "status": "approved",
                "created_at": datetime.now(timezone.utc) - timedelta(days=5)
            },
            {
                "title": "Operating Systems Previous Year End-Sem QP (2022-2025)",
                "description": "Solved question papers for OS containing process synchronization, paging, and deadlocks with answer schemes.",
                "category": "Question Papers",
                "resource_type": "academic",
                "subject": "Operating Systems",
                "department": "CSE",
                "semester": "4",
                "tags": ["OS", "Deadlock", "Memory Management", "Past Papers"],
                "owner_id": str(student_id),
                "owner_name": "Rahul Verma",
                "availability": "available",
                "file_path": None,
                "file_name": "os_solved_qp_archive.pdf",
                "location": None,
                "downloads": 32,
                "views": 89,
                "rating": 4.6,
                "review_count": 3,
                "status": "approved",
                "created_at": datetime.now(timezone.utc) - timedelta(days=3)
            },
            {
                "title": "Arduino Uno Starter Kit with Sensor Modules",
                "description": "Original Arduino Rev3 board with breadboard, ultrasonic sensors, jumper cables, and motor drivers for embedded projects.",
                "category": "Project Kits",
                "resource_type": "physical",
                "subject": "IoT & Embedded Systems",
                "department": "ECE",
                "semester": "6",
                "tags": ["Arduino", "Hardware", "Sensors", "Robotics"],
                "owner_id": str(faculty_id),
                "owner_name": "Prof. Rajesh Sharma",
                "availability": "borrowed",
                "file_path": None,
                "file_name": None,
                "location": "Hardware Lab - Room 304, Tech Block",
                "downloads": 0,
                "views": 45,
                "rating": 5.0,
                "review_count": 2,
                "status": "approved",
                "created_at": datetime.now(timezone.utc) - timedelta(days=8)
            },
            {
                "title": "Central Campus Seminar Hall - Block B",
                "description": "State-of-the-art 250-seater auditorium equipped with dual laser projectors, podium microphone, and surround acoustics.",
                "category": "Seminar Halls",
                "resource_type": "campus",
                "subject": "Campus Facility",
                "department": "CSE",
                "semester": "All",
                "tags": ["Seminar", "Events", "Auditorium", "Audio-Visual"],
                "owner_id": str(admin_id),
                "owner_name": "System Administrator",
                "availability": "available",
                "file_path": None,
                "file_name": None,
                "location": "Main Administrative Block, 2nd Floor",
                "downloads": 0,
                "views": 70,
                "rating": 4.9,
                "review_count": 4,
                "status": "approved",
                "created_at": datetime.now(timezone.utc) - timedelta(days=12)
            },
            {
                "title": "Digital Signal Processing Lab Manual",
                "description": "MATLAB simulation experiments and DSP processor architecture lab tasks with sample inputs and verified graphs.",
                "category": "Lab Manuals",
                "resource_type": "academic",
                "subject": "Digital Signal Processing",
                "department": "ECE",
                "semester": "5",
                "tags": ["DSP", "MATLAB", "Signals", "Lab"],
                "owner_id": str(faculty_id),
                "owner_name": "Prof. Rajesh Sharma",
                "availability": "available",
                "file_path": None,
                "file_name": "dsp_lab_manual_v3.pdf",
                "location": None,
                "downloads": 19,
                "views": 52,
                "rating": 4.3,
                "review_count": 1,
                "status": "approved",
                "created_at": datetime.now(timezone.utc) - timedelta(days=2)
            }
        ]
        inserted = resources_col.insert_many(sample_resources)
        res_ids = inserted.inserted_ids
        print(f"[Database Seed] Seeded {len(sample_resources)} sample resources.")

        # 4. Seed a sample borrowing
        borrowings_col.insert_one({
            "resource_id": str(res_ids[2]), # Arduino kit
            "resource_title": "Arduino Uno Starter Kit with Sensor Modules",
            "user_id": str(student_id),
            "username": "rahul_cse",
            "user_name": "Rahul Verma",
            "request_date": datetime.now(timezone.utc) - timedelta(days=2),
            "expected_return_date": (datetime.now(timezone.utc) + timedelta(days=5)).strftime("%Y-%m-%d"),
            "actual_return_date": None,
            "status": "borrowed",
            "notes": "Borrowed for IoT semester capstone project."
        })

        # 5. Seed a sample resource request
        requests_col.insert_one({
            "user_id": str(student_id),
            "username": "rahul_cse",
            "user_name": "Rahul Verma",
            "resource_name": "Computer Networks Kurose 8th Edition E-Book",
            "category": "E-books & PPTs",
            "department": "CSE",
            "description": "Looking for the 8th edition textbook with socket programming problem solutions.",
            "required_date": (datetime.now(timezone.utc) + timedelta(days=3)).strftime("%Y-%m-%d"),
            "status": "pending",
            "created_at": datetime.now(timezone.utc) - timedelta(days=1)
        })

        # 6. Seed a sample reservation
        reservations_col.insert_one({
            "resource_id": str(res_ids[3]), # Seminar Hall
            "resource_title": "Central Campus Seminar Hall - Block B",
            "user_id": str(student_id),
            "username": "rahul_cse",
            "user_name": "Rahul Verma",
            "date": (datetime.now(timezone.utc) + timedelta(days=2)).strftime("%Y-%m-%d"),
            "start_time": "14:00",
            "end_time": "16:00",
            "purpose": "ACM Student Chapter Technical Workshop on NoSQL Architectures",
            "status": "confirmed",
            "created_at": datetime.now(timezone.utc)
        })

        # 7. Seed activities
        activities_col.insert_many([
            {
                "user_id": str(student_id),
                "username": "rahul_cse",
                "action": "UPLOADED_RESOURCE",
                "description": "Uploaded 'Operating Systems Previous Year End-Sem QP'",
                "created_at": datetime.now(timezone.utc) - timedelta(days=3)
            },
            {
                "user_id": str(student_id),
                "username": "rahul_cse",
                "action": "BORROWED_ITEM",
                "description": "Borrowed 'Arduino Uno Starter Kit with Sensor Modules'",
                "created_at": datetime.now(timezone.utc) - timedelta(days=2)
            },
            {
                "user_id": str(faculty_id),
                "username": "prof_sharma",
                "action": "UPLOADED_RESOURCE",
                "description": "Uploaded 'DBMS Comprehensive Lecture Notes'",
                "created_at": datetime.now(timezone.utc) - timedelta(days=5)
            }
        ])

        # 8. Seed notifications
        notifications_col.insert_many([
            {
                "user_id": str(student_id),
                "title": "Borrow Request Approved",
                "message": "Your borrow request for 'Arduino Uno Starter Kit' was approved. Expected return is in 5 days.",
                "category": "borrowing",
                "is_read": False,
                "created_at": datetime.now(timezone.utc) - timedelta(days=2)
            },
            {
                "user_id": str(student_id),
                "title": "Reservation Confirmed",
                "message": "Seminar Hall Block B booking confirmed for ACM NoSQL workshop.",
                "category": "reservations",
                "is_read": True,
                "created_at": datetime.now(timezone.utc) - timedelta(days=1)
            }
        ])
        print("[Database Seed] Seeded sample borrowings, requests, reservations, activities & notifications.")

    # 4. Ensure demo student accounts have complete 2.0 reputation profile
    users_col.update_one({"username": "rahul_cse"}, {"$set": {
        "student_id": "22CSE1048",
        "is_verified": True,
        "verification_status": "verified",
        "skills": "Python, IoT, NoSQL, Flask, Embedded C",
        "trust_score": 94,
        "points": 45,
        "badges": ["Resource Contributor", "Helpful Student", "Trusted Member", "Campus Reuser"],
        "transactions_count": 12,
        "shared_count": 24,
        "borrowed_count": 8
    }})

    users_col.update_one({"username": "prof_sharma"}, {"$set": {
        "faculty_id": "FAC-CSE-019",
        "is_verified": True,
        "verification_status": "verified",
        "trust_score": 98,
        "points": 80,
        "badges": ["Resource Contributor", "Trusted Member"]
    }})

    # Seed Second Student: Ananya Sen (ECE)
    ananya_user = users_col.find_one({"username": "ananya_ece"})
    if not ananya_user:
        ananya_id = users_col.insert_one({
            "username": "ananya_ece",
            "email": "ananya@campusshare.edu",
            "password_hash": generate_password_hash("Student@123"),
            "full_name": "Ananya Sen",
            "role": "student",
            "department": "ECE",
            "year": "3",
            "section": "B",
            "phone": "9876543213",
            "bio": "Robotics & Embedded Systems enthusiast. Looking to exchange lab project kits and notes.",
            "student_id": "22ECE1012",
            "is_verified": True,
            "verification_status": "verified",
            "skills": "Arduino, Raspberry Pi, Verilog, Circuit Design",
            "trust_score": 89,
            "points": 35,
            "badges": ["Helpful Student", "Trusted Member", "Campus Reuser"],
            "transactions_count": 8,
            "shared_count": 14,
            "borrowed_count": 5,
            "is_active": True,
            "created_at": datetime.now(timezone.utc) - timedelta(days=20)
        }).inserted_id
    else:
        ananya_id = ananya_user['_id']

    # 5. Seed Campus Marketplace if empty
    marketplace_col = db['marketplace']
    if marketplace_col.count_documents({}) == 0:
        sample_listings = [
            {
                "title": "Casio Scientific Calculator fx-991EX ClassWiz",
                "description": "Natural textbook display, 552 functions, QR code generator. Perfect for engineering mathematics, matrices, and equation solving.",
                "category": "Calculators",
                "price": 500,
                "is_free": False,
                "accept_exchange": True,
                "condition": "Good",
                "location": "CSE Block, 2nd Floor",
                "seller_id": str(student_id),
                "seller_name": "Rahul Verma",
                "seller_username": "rahul_cse",
                "seller_dept": "CSE",
                "image_path": None,
                "views": 42,
                "status": "available",
                "created_at": datetime.now(timezone.utc) - timedelta(days=2)
            },
            {
                "title": "Arduino UNO Rev3 with Breadboard & Jumper Wires",
                "description": "Original ATmega328P microcontroller board with breadboard and sensor pack. Giving away or exchanging for Raspberry Pi Pico kit.",
                "category": "Project Kits",
                "price": 0,
                "is_free": True,
                "accept_exchange": True,
                "condition": "Like New",
                "location": "Tech Block, Hardware Lab 304",
                "seller_id": str(ananya_id),
                "seller_name": "Ananya Sen",
                "seller_username": "ananya_ece",
                "seller_dept": "ECE",
                "image_path": None,
                "views": 68,
                "status": "available",
                "created_at": datetime.now(timezone.utc) - timedelta(days=3)
            },
            {
                "title": "Digital Design 5th Edition – M. Morris Mano",
                "description": "Prescribed textbook for Digital Electronics & Logic Design. Clean pages with minimal pencil highlights.",
                "category": "Books",
                "price": 350,
                "is_free": False,
                "accept_exchange": False,
                "condition": "Good",
                "location": "Central Library Entrance",
                "seller_id": str(student_id),
                "seller_name": "Rahul Verma",
                "seller_username": "rahul_cse",
                "seller_dept": "CSE",
                "image_path": None,
                "views": 29,
                "status": "available",
                "created_at": datetime.now(timezone.utc) - timedelta(days=4)
            },
            {
                "title": "Firefox Target 21-Speed Mountain Bicycle",
                "description": "Shimano gear set, front suspension, dual disc brakes. Great for commuting between hostel and department blocks.",
                "category": "Cycles",
                "price": 2800,
                "is_free": False,
                "accept_exchange": False,
                "condition": "Good",
                "location": "Hostel 3 Cycle Stand",
                "seller_id": str(ananya_id),
                "seller_name": "Ananya Sen",
                "seller_username": "ananya_ece",
                "seller_dept": "ECE",
                "image_path": None,
                "views": 95,
                "status": "available",
                "created_at": datetime.now(timezone.utc) - timedelta(days=6)
            },
            {
                "title": "Mini Drafter & Engineering Drawing Set",
                "description": "High-accuracy stainless steel rod mini drafter with clips and plastic sheet protector for Engineering Graphics.",
                "category": "Stationery",
                "price": 250,
                "is_free": False,
                "accept_exchange": True,
                "condition": "Good",
                "location": "Mechanical Workshop Block",
                "seller_id": str(student_id),
                "seller_name": "Rahul Verma",
                "seller_username": "rahul_cse",
                "seller_dept": "CSE",
                "image_path": None,
                "views": 18,
                "status": "available",
                "created_at": datetime.now(timezone.utc) - timedelta(days=1)
            }
        ]
        inserted_items = marketplace_col.insert_many(sample_listings)
        calc_item_id = str(inserted_items.inserted_ids[0])

        # Sample offer on the Calculator
        db['marketplace_offers'].insert_one({
            "item_id": calc_item_id,
            "item_title": "Casio Scientific Calculator fx-991EX ClassWiz",
            "buyer_id": str(ananya_id),
            "buyer_name": "Ananya Sen",
            "buyer_username": "ananya_ece",
            "seller_id": str(student_id),
            "offered_price": 450,
            "message": "Hi Rahul, can I collect this today afternoon from CSE Block for ₹450?",
            "status": "pending",
            "created_at": datetime.now(timezone.utc) - timedelta(hours=5)
        })
        print(f"[Database Seed] Seeded {len(sample_listings)} marketplace items and sample offer.")

    # 6. Seed Wanted Board Requests if empty
    if requests_col.count_documents({"urgency": {"$exists": True}}) == 0:
        requests_col.insert_many([
            {
                "user_id": str(student_id),
                "username": "rahul_cse",
                "user_name": "Rahul Verma",
                "resource_name": "Arduino UNO Rev3 Board",
                "category": "Project Kits",
                "department": "CSE",
                "urgency": "high",
                "required_date": (datetime.now(timezone.utc) + timedelta(days=4)).strftime("%Y-%m-%d"),
                "description": "Urgent requirement for IoT Capstone prototype demo with ultrasonic distance sensor.",
                "status": "open",
                "created_at": datetime.now(timezone.utc) - timedelta(days=1)
            },
            {
                "user_id": str(ananya_id),
                "username": "ananya_ece",
                "user_name": "Ananya Sen",
                "resource_name": "Digital Signal Processing by Proakis",
                "category": "Books",
                "department": "ECE",
                "urgency": "medium",
                "required_date": (datetime.now(timezone.utc) + timedelta(days=7)).strftime("%Y-%m-%d"),
                "description": "Looking for physical textbook or detailed handwritten solutions for Unit 3 filter design.",
                "status": "open",
                "created_at": datetime.now(timezone.utc) - timedelta(days=2)
            }
        ])
        print("[Database Seed] Seeded sample Wanted Board posts.")

    # 7. Seed Server-Rendered Messaging if empty
    conversations_col = db['conversations']
    messages_col = db['messages']
    if conversations_col.count_documents({}) == 0:
        conv_id = conversations_col.insert_one({
            "participants": [str(student_id), str(ananya_id)],
            "participant_names": {"rahul_cse": "Rahul Verma", "ananya_ece": "Ananya Sen"},
            "subject": "Regarding Casio Scientific Calculator fx-991EX",
            "item_title": "Casio Scientific Calculator fx-991EX ClassWiz",
            "context_type": "marketplace",
            "last_message": "Yes Ananya! You can collect it from CSE block around 3:30 PM.",
            "last_updated": datetime.now(timezone.utc) - timedelta(hours=2),
            "unread_count": 0
        }).inserted_id

        messages_col.insert_many([
            {
                "conversation_id": str(conv_id),
                "sender_id": str(ananya_id),
                "sender_name": "Ananya Sen",
                "sender_username": "ananya_ece",
                "receiver_id": str(student_id),
                "message_text": "Hi Rahul! Is your Casio fx-991EX scientific calculator still available?",
                "created_at": datetime.now(timezone.utc) - timedelta(hours=3),
                "is_read": True
            },
            {
                "conversation_id": str(conv_id),
                "sender_id": str(student_id),
                "sender_name": "Rahul Verma",
                "sender_username": "rahul_cse",
                "receiver_id": str(ananya_id),
                "message_text": "Yes Ananya! You can collect it from CSE block around 3:30 PM.",
                "created_at": datetime.now(timezone.utc) - timedelta(hours=2),
                "is_read": True
            }
        ])
        print("[Database Seed] Seeded sample conversations and messages.")

    # 8. Seed Lost & Found items if empty
    lf_col = db['lost_found']
    if lf_col.count_documents({}) == 0:
        lf_col.insert_many([
            {
                "item_type": "lost",
                "title": "Casio fx-991MS Scientific Calculator",
                "category": "Calculators",
                "location": "Central Library 2nd Floor Reading Hall",
                "incident_date": (datetime.now(timezone.utc) - timedelta(days=2)).strftime("%Y-%m-%d"),
                "description": "Black Casio calculator with silver sticker 'RV' on the back cover. Left on table 12.",
                "reporter_id": str(student_id),
                "reporter_name": "Rahul Verma",
                "contact_info": "Room 304, Tech Block or Message via CampusShare",
                "status": "lost",
                "created_at": datetime.now(timezone.utc) - timedelta(days=2)
            },
            {
                "item_type": "found",
                "title": "Boat Airdopes Wireless Earbuds (Royal Blue Case)",
                "category": "Electronics",
                "location": "Campus Cafeteria Counter 2",
                "incident_date": (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%d"),
                "description": "Found blue charging case with both earbuds inside. Deposited safely at Campus Security Desk.",
                "reporter_id": str(ananya_id),
                "reporter_name": "Ananya Sen",
                "storage_location": "Main Gate Campus Security Desk (Desk Guard on Duty)",
                "status": "found",
                "created_at": datetime.now(timezone.utc) - timedelta(days=1)
            }
        ])
        print("[Database Seed] Seeded sample Lost & Found items.")

    # 9. Seed Peer Reviews & Campus Announcements if empty
    user_reviews_col = db['user_reviews']
    if user_reviews_col.count_documents({}) == 0:
        user_reviews_col.insert_one({
            "reviewee_id": str(student_id),
            "reviewee_name": "Rahul Verma",
            "reviewer_id": str(ananya_id),
            "reviewer_name": "Ananya Sen",
            "rating": 5,
            "comment": "Resource was exactly as described and handover was very punctual. Great student collaborator!",
            "transaction_type": "marketplace",
            "created_at": datetime.now(timezone.utc) - timedelta(days=5)
        })

    announcements_col = db['announcements']
    if announcements_col.count_documents({}) == 0:
        announcements_col.insert_one({
            "title": "🌱 CampusShare 2.0 Eco-Reuse & Resource Sharing Drive",
            "content": "Join our campus sustainability mission! Share unused lab kits, scientific calculators, and semester notes to keep resources in circulation and earn Campus Champion badges.",
            "author_id": str(admin_id),
            "author_name": "System Administrator",
            "priority": "high",
            "is_active": True,
            "created_at": datetime.now(timezone.utc) - timedelta(days=1)
        })
        print("[Database Seed] Seeded sample user reviews and campus announcements.")


if __name__ == '__main__':
    seed_database()


