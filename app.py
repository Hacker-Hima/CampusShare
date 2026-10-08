import os
from bson import ObjectId
from flask import Flask, jsonify, render_template, session, redirect, url_for
from config import Config
from database.connection import get_db
from database.seed import seed_database
from database.indexes import create_indexes
from routes.auth import auth_bp
from routes.student import student_bp
from routes.faculty import faculty_bp
from routes.admin import admin_bp
from routes.resources import resources_bp
from routes.requests import requests_bp
from routes.borrowings import borrowings_bp
from routes.reservations import reservations_bp
from routes.reviews import reviews_bp
from routes.notifications import notifications_bp
from routes.reports import reports_bp
from routes.profile import profile_bp
from routes.marketplace import marketplace_bp
from routes.messages import messages_bp
from routes.lost_found import lost_found_bp

def create_app():
    """
    Application factory pattern for CampusShare 2.0.
    Initializes Flask application, configuration, and registers blueprints.
    """
    app = Flask(__name__)
    app.config.from_object(Config)

    # Ensure uploads directory exists
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    # Context processor to make app configurations, notification counts, and unread messages available globally
    @app.context_processor
    def inject_global_template_vars():
        unread_notifs = 0
        unread_msgs = 0
        active_announcements = []
        user_trust = 75
        if 'user_id' in session:
            try:
                db = get_db()
                unread_notifs = db['notifications'].count_documents({
                    "user_id": session['user_id'],
                    "is_read": False
                })
                unread_msgs = db['messages'].count_documents({
                    "receiver_id": session['user_id'],
                    "is_read": False
                })
                active_announcements = list(db['announcements'].find({"is_active": True}).sort("created_at", -1).limit(2))
                u = db['users'].find_one({"_id": ObjectId(session['user_id'])}) if ObjectId.is_valid(session['user_id']) else None
                if u:
                    user_trust = u.get('trust_score', 85)
            except Exception:
                unread_notifs = 0
                unread_msgs = 0

        return {
            'app_name': 'CAMPUSSHARE 2.0',
            'registered_blueprints': list(app.blueprints.keys()),
            'unread_notifications_count': unread_notifs,
            'unread_messages_count': unread_msgs,
            'active_announcements': active_announcements,
            'current_user_trust_score': user_trust
        }

    # Verify MongoDB connection and seed database upon application startup
    with app.app_context():
        try:
            db = get_db()
            print(f"[Startup] Connected to MongoDB database '{db.name}' successfully.")
            seed_database()
            create_indexes(db)
        except Exception as e:
            print(f"[Startup Warning] Could not connect or seed MongoDB: {e}")

    # Register Blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(student_bp)
    app.register_blueprint(faculty_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(resources_bp)
    app.register_blueprint(requests_bp)
    app.register_blueprint(borrowings_bp)
    app.register_blueprint(reservations_bp)
    app.register_blueprint(reviews_bp)
    app.register_blueprint(notifications_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(profile_bp)
    app.register_blueprint(marketplace_bp)
    app.register_blueprint(messages_bp)
    app.register_blueprint(lost_found_bp)

    # Landing / Home Page
    @app.route('/')
    def index():
        db = get_db()
        featured_resources = list(db['resources'].find({"status": "approved"}).sort("downloads", -1).limit(4))
        featured_marketplace = list(db['marketplace'].find({"status": "available"}).sort("created_at", -1).limit(4))
        recent_wanted = list(db['resource_requests'].find({"status": {"$in": ["open", "pending"]}}).sort("created_at", -1).limit(3))
        
        # Campus Impact metrics
        total_downloads = sum([r.get('downloads', 0) for r in db['resources'].find({})])
        completed_sales = db['marketplace'].count_documents({"status": "sold"})
        completed_borrows = db['borrowings'].count_documents({"status": "returned"})
        fulfilled_reqs = db['resource_requests'].count_documents({"status": "fulfilled"})
        
        impact = {
            'reused': total_downloads + completed_borrows + completed_sales,
            'exchanges': completed_sales + completed_borrows + fulfilled_reqs,
            'savings': (total_downloads * 150) + (completed_sales * 350) + 12000,
            'circulation': db['marketplace'].count_documents({"status": "available"}) + db['borrowings'].count_documents({"status": "borrowed"}) + 15
        }

        return render_template(
            'index.html',
            active_page='home',
            featured_resources=featured_resources,
            featured_marketplace=featured_marketplace,
            recent_wanted=recent_wanted,
            impact=impact
        )

    # Campus Impact Public Showcase Page
    @app.route('/impact')
    def campus_impact():
        db = get_db()
        total_downloads = sum([r.get('downloads', 0) for r in db['resources'].find({})])
        completed_sales = db['marketplace'].count_documents({"status": "sold"})
        completed_borrows = db['borrowings'].count_documents({"status": "returned"})
        fulfilled_reqs = db['resource_requests'].count_documents({"status": "fulfilled"})
        
        impact = {
            'reused': total_downloads + completed_borrows + completed_sales,
            'exchanges': completed_sales + completed_borrows + fulfilled_reqs,
            'savings': (total_downloads * 150) + (completed_sales * 350) + 15000,
            'circulation': db['marketplace'].count_documents({"status": "available"}) + db['borrowings'].count_documents({"status": "borrowed"}) + 20
        }

        # Top student contributors
        top_users = list(db['users'].find({"role": "student"}).sort("points", -1).limit(5))

        return render_template('impact.html', active_page='impact', impact=impact, top_users=top_users)

    # Public Informational About Page (No login required)
    @app.route('/about', endpoint='about_page')
    def about_page():
        db = get_db()
        total_students = db['users'].count_documents({"role": "student"})
        total_resources = db['resources'].count_documents({"status": "approved"})
        total_items = db['marketplace'].count_documents({})
        return render_template(
            'about.html', 
            active_page='about',
            total_students=total_students,
            total_resources=total_resources,
            total_items=total_items
        )



    # Root Level Authentication URL Aliases
    @app.route('/login')
    def login_redirect():
        return redirect(url_for('auth.login'))

    @app.route('/register')
    def register_redirect():
        return redirect(url_for('auth.register'))

    @app.route('/logout')
    def logout_redirect():
        return redirect(url_for('auth.logout'))

    # Health check API endpoint
    @app.route('/health')
    def health():
        try:
            db = get_db()
            db.command('ping')
            mongo_status = "connected"
        except Exception as e:
            mongo_status = f"error: {str(e)}"
            
        return jsonify({
            "status": "healthy",
            "app": "CAMPUSSHARE",
            "database": mongo_status,
            "upload_folder": app.config['UPLOAD_FOLDER']
        })

    # =========================================================================
    # Error Handlers (Server-Side Rendered Error Pages)
    # =========================================================================
    @app.errorhandler(404)
    def not_found_error(error):
        return render_template('errors/404.html'), 404

    @app.errorhandler(403)
    def forbidden_error(error):
        return render_template('errors/403.html'), 403

    @app.errorhandler(413)
    def request_entity_too_large(error):
        return render_template('errors/413.html'), 413

    @app.errorhandler(500)
    def internal_server_error(error):
        return render_template('errors/500.html'), 500

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(host='127.0.0.1', port=5000, debug=True)
