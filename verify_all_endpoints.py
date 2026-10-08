import sys
import unittest
from bson import ObjectId
from app import create_app
from database.connection import get_db

class ComprehensiveSystemAudit(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app()
        cls.app.config['TESTING'] = True
        cls.client = cls.app.test_client()
        cls.db = get_db()

    def test_01_public_views(self):
        """Tests all unauthenticated public GET views."""
        endpoints = [
            '/',
            '/health',
            '/impact',
            '/auth/login',
            '/auth/register',
            '/resources',
            '/marketplace',
            '/lost-found',
            '/requests'
        ]
        for url in endpoints:
            with self.subTest(url=url):
                res = self.client.get(url)
                self.assertIn(res.status_code, [200, 302], f"Failed public URL {url} with {res.status_code}")

    def test_02_student_full_surface(self):
        """Tests all student views and parameterized endpoints."""
        # Login as student rahul
        login_res = self.client.post('/auth/login', data={'identifier': 'rahul_cse', 'password': 'Student@123'}, follow_redirects=True)
        self.assertEqual(login_res.status_code, 200)

        # Basic student URLs
        student_urls = [
            '/student/dashboard',
            '/student/notifications',
            '/profile',
            '/profile/edit',
            '/profile/change-password',
            '/resources',
            '/resources/upload',
            '/resources/my-uploads',
            '/marketplace',
            '/marketplace/new',
            '/marketplace/my-listings',
            '/marketplace/offers',
            '/marketplace/wishlist',
            '/messages',
            '/lost-found',
            '/lost-found/report-lost',
            '/lost-found/report-found',
            '/requests',
            '/requests/new',
            '/borrowings/my',
            '/reservations/my',
            '/reservations/schedule',
            '/notifications'
        ]
        for url in student_urls:
            with self.subTest(url=url):
                res = self.client.get(url)
                self.assertEqual(res.status_code, 200, f"Student URL {url} returned {res.status_code}")

        # Parameterized views:
        # 1. Resource detail
        sample_res = self.db['resources'].find_one({"status": "approved"})
        if sample_res:
            res = self.client.get(f'/resources/view/{str(sample_res["_id"])}')
            self.assertEqual(res.status_code, 200)

        # 2. Marketplace detail
        sample_mkt = self.db['marketplace'].find_one()
        if sample_mkt:
            res = self.client.get(f'/marketplace/item/{str(sample_mkt["_id"])}')
            self.assertEqual(res.status_code, 200)

        # 3. Message thread
        sample_conv = self.db['conversations'].find_one()
        if sample_conv:
            res = self.client.get(f'/messages/c/{str(sample_conv["_id"])}')
            self.assertEqual(res.status_code, 200)

        # 4. Lost & Found detail
        sample_lf = self.db['lost_found'].find_one()
        if sample_lf:
            res = self.client.get(f'/lost-found/item/{str(sample_lf["_id"])}')
            self.assertEqual(res.status_code, 200)

        # 5. Request view
        sample_req = self.db['resource_requests'].find_one()
        if sample_req:
            res = self.client.get(f'/requests/view/{str(sample_req["_id"])}')
            self.assertEqual(res.status_code, 200)

        # 6. Public reputation profile of another user
        ananya = self.db['users'].find_one({"username": "ananya_ece"})
        if ananya:
            res = self.client.get(f'/profile/user/{str(ananya["_id"])}')
            self.assertEqual(res.status_code, 200)

        self.client.get('/auth/logout')

    def test_03_faculty_full_surface(self):
        """Tests all faculty portal views."""
        # Login as prof_sharma
        self.client.post('/auth/login', data={'identifier': 'prof_sharma', 'password': 'Faculty@123'}, follow_redirects=True)
        faculty_urls = [
            '/faculty/dashboard',
            '/faculty/notifications',
            '/borrowings/manage',
            '/notifications'
        ]
        for url in faculty_urls:
            with self.subTest(url=url):
                res = self.client.get(url)
                self.assertEqual(res.status_code, 200, f"Faculty URL {url} returned {res.status_code}")

        self.client.get('/auth/logout')

    def test_04_admin_full_surface(self):
        """Tests all administrator management, analytics, and moderation views."""
        # Login as admin
        self.client.post('/auth/login', data={'identifier': 'admin', 'password': 'Admin@123'}, follow_redirects=True)
        admin_urls = [
            '/admin/dashboard',
            '/admin/users',
            '/admin/resources',
            '/admin/categories',
            '/admin/reports',
            '/admin/marketplace',
            '/admin/lost-found',
            '/admin/disputes',
            '/admin/announcements',
            '/admin/analytics',
            '/admin/borrowings',
            '/admin/reservations',
            '/admin/requests'
        ]
        for url in admin_urls:
            with self.subTest(url=url):
                res = self.client.get(url)
                self.assertEqual(res.status_code, 200, f"Admin URL {url} returned {res.status_code}")

        self.client.get('/auth/logout')

    def test_05_marketplace_lifecycle(self):
        """Tests complete marketplace lifecycle: create, offer, wishlist, and mark-sold."""
        # Student login
        self.client.post('/auth/login', data={'identifier': 'rahul_cse', 'password': 'Student@123'}, follow_redirects=True)

        # 1. Post new marketplace item
        res = self.client.post('/marketplace/new', data={
            'title': 'Test Scientific Calculator fx-82MS',
            'category': 'Calculators',
            'condition': 'Like New',
            'price': '400',
            'location': 'CSE Block Room 204',
            'description': 'Working condition with slide cover.'
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)

        # Find the created item
        created_item = self.db['marketplace'].find_one({"title": "Test Scientific Calculator fx-82MS"})
        self.assertIsNotNone(created_item)
        item_id = str(created_item['_id'])

        # 2. Wishlist toggle
        res_wl = self.client.post(f'/marketplace/item/{item_id}/wishlist', follow_redirects=True)
        self.assertEqual(res_wl.status_code, 200)

        # 3. Another student makes an offer
        self.client.get('/auth/logout')
        self.client.post('/auth/login', data={'identifier': 'ananya_ece', 'password': 'Student@123'}, follow_redirects=True)

        res_offer = self.client.post(f'/marketplace/item/{item_id}/offer', data={
            'offered_price': '350',
            'message': 'Can I take it for 350?'
        }, follow_redirects=True)
        self.assertEqual(res_offer.status_code, 200)

        # 4. Seller accepts the offer
        self.client.get('/auth/logout')
        self.client.post('/auth/login', data={'identifier': 'rahul_cse', 'password': 'Student@123'}, follow_redirects=True)

        offer = self.db['marketplace_offers'].find_one({"item_id": item_id})
        self.assertIsNotNone(offer)
        res_accept = self.client.post(f'/marketplace/offers/{str(offer["_id"])}/accept', follow_redirects=True)
        self.assertEqual(res_accept.status_code, 200)

        # 5. Seller marks item as sold
        res_sold = self.client.post(f'/marketplace/item/{item_id}/mark-sold', follow_redirects=True)
        self.assertEqual(res_sold.status_code, 200)

        # Clean up test item and offer
        self.db['marketplace'].delete_one({"_id": created_item['_id']})
        self.db['marketplace_offers'].delete_many({"item_id": item_id})
        self.client.get('/auth/logout')

    def test_06_messaging_and_smart_matching(self):
        """Tests messaging initialization, replies, and smart matching on wanted board."""
        self.client.post('/auth/login', data={'identifier': 'rahul_cse', 'password': 'Student@123'}, follow_redirects=True)

        # Start conversation with ananya
        ananya = self.db['users'].find_one({"username": "ananya_ece"})
        res_start = self.client.post('/messages/start', data={
            'to_user_id': str(ananya['_id']),
            'item_title': 'General Inquiry',
            'message': 'Hey Ananya, do you have the Unit 3 notes?'
        }, follow_redirects=True)
        self.assertEqual(res_start.status_code, 200)

        # Create wanted board request
        res_req = self.client.post('/requests/create', data={
            'title': 'Need Arduino Uno for IoT Mini Project',
            'category': 'Project Kits',
            'department': 'CSE',
            'urgency': 'high',
            'description': 'Urgent requirement for sensor interfacing lab.'
        }, follow_redirects=True)
        self.assertEqual(res_req.status_code, 200)

        # View request with smart matching
        req_doc = self.db['resource_requests'].find_one({"resource_name": "Need Arduino Uno for IoT Mini Project"})
        if req_doc:
            res_match = self.client.get(f'/requests/view/{str(req_doc["_id"])}')
            self.assertEqual(res_match.status_code, 200)
            # Cancel request
            res_cancel = self.client.post(f'/requests/cancel/{str(req_doc["_id"])}', follow_redirects=True)
            self.assertEqual(res_cancel.status_code, 200)
            updated_req = self.db['resource_requests'].find_one({"_id": req_doc['_id']})
            self.assertEqual(updated_req.get('status'), 'cancelled')

            self.db['resource_requests'].delete_one({"_id": req_doc['_id']})

        self.client.get('/auth/logout')

    def test_07_lost_found_lifecycle(self):
        """Tests reporting lost, reporting found, and submitting an ownership claim."""
        self.client.post('/auth/login', data={'identifier': 'ananya_ece', 'password': 'Student@123'}, follow_redirects=True)

        # Report lost
        res_lost = self.client.post('/lost-found/report-lost', data={
            'title': 'Scientific Calculator fx-991EX',
            'category': 'Calculators',
            'location': 'ECE Seminar Hall',
            'incident_date': '2026-10-08',
            'contact_info': 'ananya.ece@college.edu',
            'description': 'Left behind after microcontroller lecture.'
        }, follow_redirects=True)
        self.assertEqual(res_lost.status_code, 200)

        # Report found
        res_found = self.client.post('/lost-found/report-found', data={
            'title': 'Casio Scientific Calculator',
            'category': 'Calculators',
            'location': 'ECE Seminar Hall Seat 14',
            'incident_date': '2026-10-08',
            'contact_info': 'rahul@campusshare.edu',
            'custody_location': 'Security Post B',
            'description': 'Found black calculator under chair.'
        }, follow_redirects=True)
        self.assertEqual(res_found.status_code, 200)

        found_item = self.db['lost_found'].find_one({"title": "Casio Scientific Calculator"})
        self.assertIsNotNone(found_item)

        # Submit ownership claim
        res_claim = self.client.post(f'/lost-found/item/{str(found_item["_id"])}/claim', data={
            'proof_details': 'It has my initials AE etched on the back cover.'
        }, follow_redirects=True)
        self.assertEqual(res_claim.status_code, 200)

        # Clean up
        self.db['lost_found'].delete_one({"_id": found_item['_id']})
        self.client.get('/auth/logout')

    def test_08_borrowing_and_reservation_lifecycle(self):
        """Tests borrowing requests, returns, facility bookings, and conflict prevention."""
        self.client.post('/auth/login', data={'identifier': 'rahul_cse', 'password': 'Student@123'}, follow_redirects=True)

        # Equipment borrowing
        equip = self.db['resources'].find_one({"resource_type": "physical", "status": "approved"})
        if equip:
            res_borrow = self.client.post(f'/borrowings/request/{str(equip["_id"])}', data={
                'expected_return_date': '2026-11-20',
                'purpose': 'Capstone project testing'
            }, follow_redirects=True)
            self.assertEqual(res_borrow.status_code, 200)

        # Facility reservation
        hall = self.db['resources'].find_one({"resource_type": "campus", "status": "approved"})
        if hall:
            res_book = self.client.post(f'/reservations/new/{str(hall["_id"])}', data={
                'date': '2026-12-10',
                'start_time': '10:00',
                'end_time': '12:00',
                'purpose': 'ACM Student Chapter Workshop',
                'attendees': '40'
            }, follow_redirects=True)
            self.assertEqual(res_book.status_code, 200)

            # Test conflict prevention (same time slot)
            res_conflict = self.client.post(f'/reservations/new/{str(hall["_id"])}', data={
                'date': '2026-12-10',
                'start_time': '11:00',
                'end_time': '13:00',
                'purpose': 'Conflicting Workshop',
                'attendees': '30'
            }, follow_redirects=True)
            self.assertEqual(res_conflict.status_code, 200)
            self.assertIn(b'conflict', res_conflict.data.lower())

            # Clean up test reservation
            self.db['reservations'].delete_many({"purpose": "ACM Student Chapter Workshop"})

        self.client.get('/auth/logout')

    def test_09_moderation_and_admin_lifecycle(self):
        """Tests admin verification, announcements, and dispute resolution."""
        self.client.post('/auth/login', data={'identifier': 'admin', 'password': 'Admin@123'}, follow_redirects=True)

        # 1. Post broadcast announcement
        res_ann = self.client.post('/admin/announcements/create', data={
            'title': 'Campus Tech Symposium Next Week',
            'content': 'All project teams must submit their demos by Friday.',
            'priority': 'medium'
        }, follow_redirects=True)
        self.assertEqual(res_ann.status_code, 200)

        ann = self.db['announcements'].find_one({"title": "Campus Tech Symposium Next Week"})
        self.assertIsNotNone(ann)
        self.db['announcements'].delete_one({"_id": ann['_id']})

        # 2. Verify student user toggle
        student = self.db['users'].find_one({"username": "rahul_cse"})
        if student:
            res_v = self.client.post(f'/admin/users/verify/{str(student["_id"])}', follow_redirects=True)
            self.assertEqual(res_v.status_code, 200)

        self.client.get('/auth/logout')


if __name__ == '__main__':
    unittest.main()

