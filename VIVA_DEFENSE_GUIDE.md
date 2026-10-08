# CAMPUSSHARE – Comprehensive Project & Viva Defense Guide
**Dual Course Integration:** Web Frameworks using Python (WFP) & NoSQL Database (MongoDB)

---

## 1. Executive Project Summary

**CAMPUSSHARE** is a full-featured, university-level academic resource sharing and management platform. It addresses the common challenge of fragmented campus assets (lecture notes, past question papers, lab kits, IoT hardware, and seminar facilities) by unifying them into a single centralized digital catalog.

### Technical Pillars:
1. **Web Frameworks with Python (WFP):**
   - **Framework:** Flask (v3.1.2) using the Application Factory Pattern (`create_app()`).
   - **Rendering Engine:** Jinja2 Server-Side Rendering (SSR).
   - **Authentication & Security:** Werkzeug password hashing (`scrypt`), secure server-side sessions, custom role-based access control (RBAC) decorators.
   - **Strict Architectural Rule:** **Zero JavaScript (100% SSR)**. All form submissions, state mutations, filtering, search, and modal actions utilize native HTML GET/POST forms, HTTP 302 redirects, and pure CSS.
2. **NoSQL Database (MongoDB):**
   - **Database Driver:** PyMongo (v4.11.2) directly communicating with local/remote MongoDB instances.
   - **Data Modeling:** Balanced hybrid architecture featuring Document Embedding (tags, categories) and Document Referencing (`user_id`, `resource_id`) to prevent unbounded array growth and document bloat beyond MongoDB's 16MB document limit.
   - **Indexing Strategies:** B-Tree unique indexes, compound indexes, and text indexes verified via query execution stats (`IXSCAN`).
   - **Aggregation Framework:** Multi-stage pipelines using `$group`, `$sort`, `$project`, `$sum`, `$avg`, and `$lookup` for reporting and real-time dashboards.

---

## 2. Default Demo Credentials

All accounts are pre-seeded upon first application startup (`database/seed.py`):

| Role | Username | Password | Department | Primary Responsibilities |
|---|---|---|---|---|
| **Administrator** | `admin` | `Admin@123` | CSE | User status management, content moderation, reports resolution, analytics |
| **Faculty** | `prof_sharma` | `Faculty@123` | CSE | Resource publishing, student request fulfillment, departmental oversight |
| **Student** | `rahul_cse` | `Student@123` | CSE | Resource downloads, borrowing requests, facility reservations, reviews |

---

## 3. MongoDB Schema Architecture & NoSQL Design Decisions

### A. Collections Overview

1. **`users`**
   - Stores user credentials, hashed passwords, departmental affiliation, roles, and status flags.
   - *Sample Document:*
     ```json
     {
       "_id": ObjectId("..."),
       "username": "rahul_cse",
       "email": "rahul@campusshare.edu",
       "password_hash": "scrypt:32768:8:1$...",
       "full_name": "Rahul Verma",
       "role": "student",
       "department": "CSE",
       "year": "3",
       "section": "A",
       "is_active": true,
       "created_at": ISODate("2026-10-07T12:00:00Z")
     }
     ```

2. **`resources`**
   - Stores cataloged academic materials, physical equipment, and campus facilities.
   - *Design Decision (Embedding vs Referencing):* Keywords and tags are embedded as an array (`tags: ["DBMS", "SQL", "Normalization"]`) because their cardinality is small and bounded. Owner details reference the `users` collection (`owner_id`) to keep user profile updates decoupled.
   - *Sample Document:*
     ```json
     {
       "_id": ObjectId("..."),
       "title": "DBMS Comprehensive Lecture Notes (Unit 1-5)",
       "description": "Complete classroom notes covering Relational Algebra, ER Models...",
       "resource_type": "academic",
       "category": "Notes",
       "department": "CSE",
       "subject": "Database Management Systems",
       "tags": ["DBMS", "SQL", "ER-Model", "Normalization"],
       "file_path": "dbms_lecture_notes_sample.pdf",
       "file_size": 2621440,
       "owner_id": "6ac67e6ca5baacdeccea838e",
       "owner_name": "Prof. Rajesh Sharma",
       "owner_role": "faculty",
       "status": "approved",
       "downloads": 48,
       "views": 182,
       "rating": 4.9,
       "created_at": ISODate("2026-10-07T12:00:00Z")
     }
     ```

3. **`borrowings`**
   - Implements physical equipment checkout state machine: `requested` $\rightarrow$ `approved` $\rightarrow$ `borrowed` $\rightarrow$ `returned` (or `rejected`).
   - Uses referencing (`user_id`, `resource_id`).

4. **`reservations`**
   - Manages time-slotted facility bookings (Seminar Halls, IoT Labs).
   - Interval conflict query detects time collisions:
     ```python
     {
         "resource_id": resource_id,
         "date": booking_date,
         "status": "confirmed",
         "start_time": {"$lt": req_end_time},
         "end_time": {"$gt": req_start_time}
     }
     ```

5. **`reviews`**
   - One review per user per resource. Stores rating (1–5) and commentary.
   - Whenever a review is inserted, an atomic MongoDB aggregation recalculates average score:
     ```python
     avg_pipeline = [
         {"$match": {"resource_id": resource_id}},
         {"$group": {"_id": "$resource_id", "avg_rating": {"$avg": "$rating"}}}
     ]
     ```

6. **`notifications`**
   - Fast notification feed for status updates, request completions, and moderation alerts.
   - Unread count injected globally into every Jinja2 template via `@app.context_processor`.

7. **`reports`**
   - Moderation flags submitted by users against copyrighted or erroneous content.

---

## 4. MongoDB Indexing Strategy (database/indexes.py)

| Collection | Index Name | Key Specification | Optimization Purpose |
|---|---|---|---|
| `users` | `idx_users_username_unique` | `{"username": 1}` (Unique) | O(1) user login lookup and uniqueness enforcement |
| `users` | `idx_users_email_unique` | `{"email": 1}` (Unique) | Guarantees single account per university email |
| `resources` | `idx_resources_text_search` | `{"title": "text", "description": "text", "subject": "text", "tags": "text"}` | Multi-field full-text search across academic catalog |
| `resources` | `idx_resources_status_dept` | `{"status": 1, "department": 1}` | Compound index for filtered catalog browsing |
| `resources` | `idx_resources_status_cat` | `{"status": 1, "category": 1}` | Fast retrieval by resource category |
| `reservations` | `idx_reservations_conflict` | `{"resource_id": 1, "date": 1, "status": 1}` | Zero-latency interval overlap checking |
| `notifications` | `idx_notifications_user_unread` | `{"user_id": 1, "is_read": 1}` | Powers top navbar unread notification badge |

### Verification of IXSCAN vs COLLSCAN:
When running `python -m database.indexes`, MongoDB's query planner verifies:
- Winning plan: **`IXSCAN`**
- Documents examined: Match exact returned documents count.
- Execution time: **0 ms**.

---

## 5. Web Frameworks with Python (WFP) Concepts Demonstrated

1. **Application Factory Pattern:**
   `create_app()` initializes configurations, ensures upload directories exist, loads context processors, connects to MongoDB, and registers blueprints.
2. **Modular Blueprints:**
   11 discrete blueprints (`auth_bp`, `student_bp`, `faculty_bp`, `admin_bp`, `resources_bp`, `requests_bp`, `borrowings_bp`, `reservations_bp`, `reviews_bp`, `notifications_bp`, `reports_bp`, `profile_bp`).
3. **Session Management & Custom Decorators:**
   - `@login_required`: Checks `session['user_id']`.
   - `@guest_only`: Blocks authenticated users from login/registration forms.
   - `@role_required('admin')`: Restricts administrative routes.
4. **Jinja2 Template Inheritance:**
   Single root `templates/base.html` providing navigation, sidebar, flash alert container, and dynamic context variables.
5. **Zero JavaScript Architecture:**
   - Form submissions: Native `<form method="POST">`.
   - Action triggers: `<input type="hidden" name="action" value="...">`.
   - Progress bars: Pure CSS inline styles `style="width: {{ pct }}%;"`.
   - Search & filtering: `<form method="GET">` with URL query strings.

---

---

## 6. CampusShare Ecosystem Innovations

CampusShare expands from a basic academic repository into a complete campus social and resource economy:

1. **Campus Marketplace (Buy / Sell / Free / Exchange / Bidding):**
   - Enables students to buy, sell, exchange, or giveaway semester essentials (calculators, lab kits, engineering instruments, bicycles, textbooks).
   - Features negotiation offers (`marketplace_offers`) with accept/reject state transitions and a student wishlist.
2. **Smart Resource Matching Engine (`utils/trust.py`):**
   - When a student posts on the **Wanted Board**, the system automatically scans both the **Academic Library** and **Marketplace** collections using keyword tokenization, regex, and category matching to suggest existing available items immediately.
3. **Trust & Reputation Engine (Score 0–100 & Badges):**
   - Evaluates verification status (+25 pts), peer reviews (+5 pts/star), completed transactions (+10 pts), library uploads (+5 pts), minus penalty deductions for open disputes (-20 pts).
   - Dynamically awards badges: *Resource Contributor*, *Trusted Member*, and *Campus Champion*.
4. **Server-Side Rendered Messaging (`/messages/`):**
   - Full conversational messaging with zero JavaScript. Thread navigation, unread message badges, and replies are managed via standard HTTP POST forms and redirects.
5. **Campus Lost & Found Board (`/lost-found/`):**
   - Centralized reporting of lost and found campus belongings with photo upload, security logging, and ownership claim verification workflows.
6. **Campus Impact & Sustainability Metrics (`/impact`):**
   - Tracks eco-friendly campus metrics: items kept in circulation, successful peer exchanges, and cumulative student monetary savings (₹).
7. **Admin Moderation Hub:**
   - One-click student account verification, dispute resolution management, marketplace listings audit, and priority campus broadcast announcements.

---

## 7. Top Viva Questions & Model Answers

### Q1: Why did you choose MongoDB instead of MySQL or PostgreSQL for this project?
> **Answer:** "In an academic campus ecosystem, resources vary wildly in attributes. Lecture notes have file formats, page counts, and download counts; physical equipment has serial numbers, conditions, and return dates; campus facilities have room capacities and time slots; marketplace items have prices and conditions. A relational schema would require multiple sparse tables, complex junction tables, and expensive multi-table JOINs. MongoDB's flexible document schema allows polymorphic modeling, fast key-value lookups, and embedded tags within a single document while PyMongo offers seamless Python integration."

### Q2: What is the difference between Embedding and Referencing in NoSQL, and where did you use each?
> **Answer:** "Embedding nests related documents or arrays directly inside a parent document. We used embedding for **resource tags** (`tags: ["DBMS", "SQL"]`) and **categories** because they are bounded and query-bound with the resource. Referencing stores only the `ObjectId` of another document. We used referencing for **user ownership** (`owner_id`), **borrowings** (`user_id`, `resource_id`), **marketplace offers** (`buyer_id`, `seller_id`), and **reviews** to avoid MongoDB's 16MB document size limit and eliminate write-heavy array re-allocations."

### Q3: How do you verify that your queries are using indexes in MongoDB?
> **Answer:** "We use MongoDB's `.explain()` method on the query cursor. Under `executionStats` and `queryPlanner`, the `winningPlan.stage` must display `IXSCAN` (Index Scan) rather than `COLLSCAN` (Collection Scan). In our test suite, `idx_resources_status_dept` and `idx_marketplace_status_cat` ensure that querying approved items checks only the relevant index keys in 0 ms."

### Q4: How did you implement real-time unread notifications and messaging without any JavaScript or AJAX?
> **Answer:** "Through Flask's `@app.context_processor`. Before rendering any template, Flask queries `db['notifications'].count_documents({"user_id": session['user_id'], "is_read": False})` and unread messages count using indexed compound lookups `{"user_id": 1, "is_read": 1}`. The counts are injected into the Jinja2 context and rendered into the navbar badge with zero client-side scripts."

### Q5: How do you prevent overlapping bookings in the facility reservation system?
> **Answer:** "We use an interval comparison query against MongoDB. Two time intervals $[S_1, E_1)$ and $[S_2, E_2)$ collide if and only if $S_1 < E_2$ and $E_1 > S_2$. In PyMongo, before confirming a reservation, we query:
```python
db['reservations'].find_one({
    'resource_id': res_id,
    'date': booking_date,
    'status': 'confirmed',
    'start_time': {'$lt': req_end_time},
    'end_time': {'$gt': req_start_time}
})
```
If a conflicting document is returned, the reservation is rejected with an explanatory flash message."

### Q6: How does the Smart Resource Matching Engine work in CampusShare?
> **Answer:** "When a student posts a wanted request, our smart matching utility tokenizes the request title and tags, filters stop-words, and runs multi-collection queries across both `resources` (for academic lecture notes, past papers, lab manuals) and `marketplace` (for calculators, lab kits, books). It builds case-insensitive `$regex` matching patterns with departmental boost filters to surface relevant resources with zero latency."

### Q7: How is the Trust Score calculated and maintained?
> **Answer:** "The Trust Score is a normalized 0–100 reputation score calculated on-demand via `utils/trust.py`. It factors in:
1. Account verification status (+25 pts)
2. Average peer star rating (up to +25 pts)
3. Volume of positive platform contributions (library uploads, marketplace completions, lost item returns, +30 pts)
4. Absence of unresolved disputes or disciplinary flags (disputes deduct -20 pts each)
This creates transparency and incentivizes safe, respectful campus sharing."

---

## 8. Commands to Run & Verify

```powershell
# 1. Activate Virtual Environment (Windows PowerShell)
.\venv\Scripts\Activate.ps1

# 2. Build & Verify MongoDB Indexes (17 Indexes across 10 Collections)
python database/indexes.py

# 3. Seed Demo Campus Data (Users, Marketplace, Notes, Messages, Announcements)
python database/seed.py

# 4. Execute Complete Automated Test Suite (All 10 E2E Test Modules)
python test_suite.py

# 5. Start the Application Server
python app.py
```
Open your browser at `http://127.0.0.1:5000` to interact with the platform.

