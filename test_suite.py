"""
CAMPUSSHARE End-to-End Automated Test Suite & Integrity Verifier
================================================================
Covers:
1. Architectural compliance (Zero JavaScript assertion across all templates)
2. MongoDB database indexing & aggregation pipeline verification
3. Full multi-role authentication & RBAC flow (Student, Faculty, Admin)
4. Resource CRUD, Search & Filtering (WFP Forms & NoSQL queries)
5. Request, Borrowing, Reservation, Rating, Notification, and Moderation flows
"""

import os
import re
import unittest
from bson import ObjectId
from app import create_app
from database.connection import get_db
from database.indexes import create_indexes, demonstrate_query_plan


class CampusShareE2ETestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app()
        cls.app.config['TESTING'] = True
        cls.db = get_db()
        create_indexes(cls.db)

    def setUp(self):
        self.client = self.app.test_client()

    # =========================================================================
    # 1. Zero JavaScript Compliance Rule Verification
    # =========================================================================
    def test_01_zero_javascript_compliance(self):
        """Verifies that NO <script> tags or external script references exist in HTML templates."""
        template_dir = os.path.join(self.app.root_path, 'templates')
        script_pattern = re.compile(r'<\s*script\b', re.IGNORECASE)
        violating_files = []

        for root, _, files in os.walk(template_dir):
            for file in files:
                if file.endswith('.html'):
                    file_path = os.path.join(root, file)
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        if script_pattern.search(content):
                            violating_files.append(file_path)

        self.assertEqual(len(violating_files), 0, f"Found <script> tags violating the No-JS constraint in: {violating_files}")
        print("\n[OK] Rule 1 Passed: 100% Zero JavaScript compliance across all templates.")

    # =========================================================================
    # 2. Public Endpoints & Health Check
    # =========================================================================
    def test_02_public_endpoints(self):
        """Tests health check, index landing page, login and register views."""
        # Health check
        res = self.client.get('/health')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json.get('database'), 'connected')

        # Home page
        res = self.client.get('/')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'CAMPUSSHARE', res.data)

        # Login page
        res = self.client.get('/auth/login')
        self.assertEqual(res.status_code, 200)

        # Register page
        res = self.client.get('/auth/register')
        self.assertEqual(res.status_code, 200)
        print("[OK] Public endpoints verified.")

    # =========================================================================
    # 3. Student Workflow
    # =========================================================================
    def test_03_student_workflow(self):
        """Tests student authentication, dashboard, catalog browsing, and profile."""
        # Login as student
        res = self.client.post('/auth/login', data={
            'identifier': 'rahul_cse',
            'password': 'Student@123'
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)

        # Student Dashboard
        res = self.client.get('/student/dashboard')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Student Portal', res.data)

        # Catalog Search & Filter
        res = self.client.get('/resources?q=Database&department=CSE')
        self.assertEqual(res.status_code, 200)

        # View single resource
        sample_res = self.db['resources'].find_one({"status": "approved"})
        self.assertIsNotNone(sample_res)
        res_id = str(sample_res['_id'])

        res = self.client.get(f'/resources/view/{res_id}')
        self.assertEqual(res.status_code, 200)

        # Post a Review
        review_res = self.client.post(f'/reviews/add/{res_id}', data={
            'rating': '5',
            'comment': 'Exceptional course notes with clear diagrams.'
        }, follow_redirects=True)
        self.assertEqual(review_res.status_code, 200)

        # Submit a Resource Request
        req_res = self.client.post('/requests/create', data={
            'title': 'Compiler Design Notes Unit 4',
            'department': 'CSE',
            'subject': 'Compiler Design',
            'urgency': 'high',
            'description': 'Need detailed notes for LR parser construction.'
        }, follow_redirects=True)
        self.assertEqual(req_res.status_code, 200)

        # Submit Equipment Borrowing Request
        equip = self.db['resources'].find_one({"resource_type": "physical", "status": "approved"})
        if equip:
            borrow_res = self.client.post(f'/borrowings/request/{str(equip["_id"])}', data={
                'due_date': '2026-11-15',
                'purpose': 'Microcontroller laboratory project demo'
            }, follow_redirects=True)
            self.assertEqual(borrow_res.status_code, 200)

        # View Profile
        prof_res = self.client.get('/profile')
        self.assertEqual(prof_res.status_code, 200)
        self.assertIn(b'Rahul Verma', prof_res.data)

        # Logout
        self.client.get('/auth/logout')
        print("[OK] Student workflow verified.")

    # =========================================================================
    # 4. Faculty Workflow
    # =========================================================================
    def test_04_faculty_workflow(self):
        """Tests faculty login, dashboard, request fulfillment, and notifications."""
        # Login as faculty
        res = self.client.post('/auth/login', data={
            'identifier': 'prof_sharma',
            'password': 'Faculty@123'
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)

        # Faculty Dashboard
        res = self.client.get('/faculty/dashboard')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Faculty Academic Workspace', res.data)

        # Check Notifications
        notif_res = self.client.get('/notifications')
        self.assertEqual(notif_res.status_code, 200)

        # Logout
        self.client.get('/auth/logout')
        print("[OK] Faculty workflow verified.")

    # =========================================================================
    # 5. Administrator Workflow & Aggregations
    # =========================================================================
    def test_05_admin_workflow(self):
        """Tests admin dashboard, user moderation, reports, and analytics aggregation pipeline."""
        # Login as admin
        res = self.client.post('/auth/login', data={
            'identifier': 'admin',
            'password': 'Admin@123'
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)

        # Admin Dashboard
        res = self.client.get('/admin/dashboard')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'System Control Center', res.data)

        # Users Management
        res = self.client.get('/admin/users')
        self.assertEqual(res.status_code, 200)

        # Resources Moderation
        res = self.client.get('/admin/resources')
        self.assertEqual(res.status_code, 200)

        # Categories
        res = self.client.get('/admin/categories')
        self.assertEqual(res.status_code, 200)

        # Reports View
        res = self.client.get('/admin/reports')
        self.assertEqual(res.status_code, 200)

        # Advanced Analytics (MongoDB Aggregation Pipelines)
        res = self.client.get('/admin/analytics')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Platform Analytics', res.data)
        self.assertIn(b'Live Campus Metrics', res.data)

        # Logout
        self.client.get('/auth/logout')
        print("[OK] Admin workflow & aggregations verified.")

    # =========================================================================
    # 6. MongoDB Query Optimization & Index Scan Test
    # =========================================================================
    def test_06_mongodb_indexing_ixscan(self):
        """Verifies that MongoDB queries utilize IXSCAN (B-Tree index) rather than COLLSCAN."""
        plan = demonstrate_query_plan({"status": "approved", "department": "CSE"})
        self.assertEqual(plan['execution_stage'], 'IXSCAN', f"Expected IXSCAN stage but got {plan['execution_stage']}")
        self.assertGreaterEqual(plan['totalKeysExamined'], 1)
        print(f"[OK] MongoDB Indexing verified: Winning plan utilized stage '{plan['execution_stage']}'.")

    # =========================================================================
    # 7. Campus Marketplace Workflow (Buy/Sell/Offer/Wishlist)
    # =========================================================================
    def test_07_marketplace_workflow(self):
        """Tests browsing marketplace items, filtering, placing offers, and wishlist."""
        # Login as student rahul
        self.client.post('/auth/login', data={'identifier': 'rahul_cse', 'password': 'Student@123'}, follow_redirects=True)

        # Marketplace catalog
        res = self.client.get('/marketplace/')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Campus Marketplace', res.data)

        # Filter by sell listing type
        res_filter = self.client.get('/marketplace/?listing_type=sell')
        self.assertEqual(res_filter.status_code, 200)

        # Retrieve a marketplace item
        item = self.db['marketplace'].find_one({"status": "available"})
        self.assertIsNotNone(item, "Expected at least one available marketplace item")
        item_id = str(item['_id'])

        # View item detail
        res_detail = self.client.get(f'/marketplace/item/{item_id}')
        self.assertEqual(res_detail.status_code, 200)

        # Place an offer
        res_offer = self.client.post(f'/marketplace/item/{item_id}/offer', data={
            'offered_price': '750',
            'message': 'Hi, is this available for handover near Block B?'
        }, follow_redirects=True)
        self.assertEqual(res_offer.status_code, 200)

        # Wishlist toggle
        res_wishlist_toggle = self.client.post(f'/marketplace/item/{item_id}/wishlist', follow_redirects=True)
        self.assertEqual(res_wishlist_toggle.status_code, 200)

        # View wishlist
        res_wishlist = self.client.get('/marketplace/wishlist')
        self.assertEqual(res_wishlist.status_code, 200)

        # View offers dashboard
        res_offers = self.client.get('/marketplace/offers')
        self.assertEqual(res_offers.status_code, 200)

        self.client.get('/auth/logout')
        print("[OK] Marketplace workflow (catalog, filters, offers, wishlist) verified.")

    # =========================================================================
    # 8. Server-Rendered Messaging & Wanted Board Smart Matching
    # =========================================================================
    def test_08_messaging_and_smart_matching(self):
        """Tests server-rendered message inbox, conversation thread, and AI Smart Resource Matching."""
        # Login as rahul
        self.client.post('/auth/login', data={'identifier': 'rahul_cse', 'password': 'Student@123'}, follow_redirects=True)

        # View inbox
        res_inbox = self.client.get('/messages/')
        self.assertEqual(res_inbox.status_code, 200)
        self.assertIn(b'Messages', res_inbox.data)

        # Check existing conversation thread
        conv = self.db['conversations'].find_one()
        if conv:
            conv_id = str(conv['_id'])
            res_thread = self.client.get(f'/messages/c/{conv_id}')
            self.assertEqual(res_thread.status_code, 200)

            # Send server-rendered reply
            res_reply = self.client.post(f'/messages/c/{conv_id}', data={
                'message_text': 'Sounds good! See you near the library entrance.'
            }, follow_redirects=True)
            self.assertEqual(res_reply.status_code, 200)

        # Test Wanted Board Smart Resource Matching
        req = self.db['resource_requests'].find_one()
        if req:
            req_id = str(req['_id'])
            res_req = self.client.get(f'/requests/view/{req_id}')
            self.assertEqual(res_req.status_code, 200)
            self.assertIn(b'Smart Resource Matches', res_req.data)

        self.client.get('/auth/logout')
        print("[OK] Messaging & Smart Resource Matching verified.")

    # =========================================================================
    # 9. Lost & Found and Trust Reputation Verification
    # =========================================================================
    def test_09_lost_and_found_and_reputation(self):
        """Tests Lost & Found posting and Public Reputation Profile with Trust Score."""
        # Login as ananya
        self.client.post('/auth/login', data={'identifier': 'ananya_ece', 'password': 'Student@123'}, follow_redirects=True)

        # Lost & Found Directory
        res_lf = self.client.get('/lost-found/')
        self.assertEqual(res_lf.status_code, 200)

        # Report Lost Item
        res_report = self.client.post('/lost-found/report-lost', data={
            'title': 'Blue Steel Water Bottle',
            'category': 'Clothing & Accessories',
            'location': 'Central Library 2nd Floor',
            'incident_date': '2026-10-08',
            'contact_info': 'ananya.ece@college.edu',
            'description': 'Milton flask with ECE sticker on base.'
        }, follow_redirects=True)
        self.assertEqual(res_report.status_code, 200)

        # View Public Reputation Profile of Rahul
        rahul = self.db['users'].find_one({"username": "rahul_cse"})
        self.assertIsNotNone(rahul)
        rahul_id = str(rahul['_id'])

        res_rep = self.client.get(f'/profile/user/{rahul_id}')
        self.assertEqual(res_rep.status_code, 200)
        self.assertIn(b'Trust Score', res_rep.data)

        # Submit Peer Review for Rahul
        res_review = self.client.post(f'/reviews/user/{rahul_id}', data={
            'rating': '5',
            'comment': 'Prompt handover and pristine condition of the calculator.'
        }, follow_redirects=True)
        self.assertEqual(res_review.status_code, 200)

        self.client.get('/auth/logout')
        print("[OK] Lost & Found and Trust Reputation verified.")

    # =========================================================================
    # 10. Campus Impact & Admin 2.0 Moderation Hub
    # =========================================================================
    def test_10_admin_2_0_moderation_and_campus_impact(self):
        """Tests Campus Impact sustainability page and Admin 2.0 moderation panels."""
        # Public Campus Impact page
        res_impact = self.client.get('/impact')
        self.assertEqual(res_impact.status_code, 200)
        self.assertIn(b'Campus Impact', res_impact.data)

        # Admin login
        self.client.post('/auth/login', data={'identifier': 'admin', 'password': 'Admin@123'}, follow_redirects=True)

        # Admin marketplace moderation
        res_mkt = self.client.get('/admin/marketplace')
        self.assertEqual(res_mkt.status_code, 200)

        # Admin lost & found moderation
        res_lf = self.client.get('/admin/lost-found')
        self.assertEqual(res_lf.status_code, 200)

        # Admin disputes moderation
        res_disp = self.client.get('/admin/disputes')
        self.assertEqual(res_disp.status_code, 200)

        # Admin one-click user verification
        student = self.db['users'].find_one({"role": "student"})
        if student:
            res_verify = self.client.post(f'/admin/users/verify/{str(student["_id"])}', follow_redirects=True)
            self.assertEqual(res_verify.status_code, 200)

        self.client.get('/auth/logout')
        print("[OK] Campus Impact & Admin 2.0 Moderation Hub verified.")


if __name__ == '__main__':
    unittest.main()

