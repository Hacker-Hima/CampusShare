import re
from datetime import datetime, timezone
from bson import ObjectId
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from database.connection import get_db
from utils.decorators import login_required
from utils.helpers import save_uploaded_file
from utils.trust import calculate_trust_score, calculate_user_badges, award_user_points

marketplace_bp = Blueprint('marketplace', __name__, url_prefix='/marketplace')

MARKETPLACE_CATEGORIES = [
    "Books", "Electronics", "Calculators", "Project Kits", 
    "Furniture", "Cycles", "Stationery", "Sports", "Other"
]

ITEM_CONDITIONS = ["Brand New", "Like New", "Good", "Fair"]

@marketplace_bp.route('/overview', methods=['GET'])
def marketplace_overview():
    """
    Public overview and details about how the Campus Marketplace works.
    Accessible without logging in.
    """
    db = get_db()
    total_listings = db['marketplace'].count_documents({"status": "available"})
    total_sold = db['marketplace'].count_documents({"status": "sold"})
    sample_items = list(db['marketplace'].find({"status": "available"}).sort("created_at", -1).limit(4))
    return render_template(
        'marketplace/overview.html',
        active_page='marketplace_overview',
        total_listings=total_listings,
        total_sold=total_sold,
        categories=MARKETPLACE_CATEGORIES,
        conditions=ITEM_CONDITIONS,
        sample_items=sample_items
    )

@marketplace_bp.route('', methods=['GET'])
@marketplace_bp.route('/', methods=['GET'])
def list_items():
    """
    Campus Marketplace catalog with multi-facet filters:
    category, condition, price range, free giveaway, exchange, and full-text search.
    """
    db = get_db()
    
    q = request.args.get('q', '').strip()
    category = request.args.get('category', '').strip()
    condition = request.args.get('condition', '').strip()
    free_only = request.args.get('free', '').strip()
    exchange_only = request.args.get('exchange', '').strip()
    max_price = request.args.get('max_price', '').strip()
    sort_by = request.args.get('sort', 'newest').strip().lower()

    query = {"status": {"$in": ["available", "reserved"]}}

    if q:
        safe_q = re.escape(q)
        regex = {"$regex": safe_q, "$options": "i"}
        query["$or"] = [
            {"title": regex},
            {"description": regex},
            {"category": regex},
            {"location": regex}
        ]

    if category and category in MARKETPLACE_CATEGORIES:
        query["category"] = category

    if condition and condition in ITEM_CONDITIONS:
        query["condition"] = condition

    if free_only in ['1', 'true', 'yes']:
        query["$or"] = [{"is_free": True}, {"price": 0}]

    if exchange_only in ['1', 'true', 'yes']:
        query["accept_exchange"] = True

    if max_price:
        try:
            val = float(max_price)
            query["price"] = {"$lte": val}
        except ValueError:
            pass

    sort_mapping = {
        'newest': ("created_at", -1),
        'price_asc': ("price", 1),
        'price_desc': ("price", -1),
        'views': ("views", -1)
    }
    sort_field, sort_dir = sort_mapping.get(sort_by, ("created_at", -1))

    items = list(db['marketplace'].find(query).sort(sort_field, sort_dir))

    # Calculate stats for marketplace banner
    total_count = db['marketplace'].count_documents({"status": "available"})
    free_count = db['marketplace'].count_documents({"status": "available", "$or": [{"is_free": True}, {"price": 0}]})
    exchange_count = db['marketplace'].count_documents({"status": "available", "accept_exchange": True})

    return render_template(
        'marketplace/list.html',
        active_page='marketplace',
        items=items,
        categories=MARKETPLACE_CATEGORIES,
        conditions=ITEM_CONDITIONS,
        current_filters={
            'q': q,
            'category': category,
            'condition': condition,
            'free': free_only,
            'exchange': exchange_only,
            'max_price': max_price,
            'sort': sort_by
        },
        stats={
            'total': total_count,
            'free': free_count,
            'exchange': exchange_count
        }
    )


@marketplace_bp.route('/item/<item_id>')
def view_item(item_id):
    """
    Marketplace listing detail page with seller reputation, trust score,
    negotiation offer form, and direct messaging CTA.
    """
    db = get_db()
    try:
        obj_id = ObjectId(item_id)
    except Exception:
        flash("Invalid item identifier.", "danger")
        return redirect(url_for('marketplace.list_items'))

    item = db['marketplace'].find_one({"_id": obj_id})
    if not item:
        flash("Marketplace listing not found.", "warning")
        return redirect(url_for('marketplace.list_items'))

    # Increment view count
    db['marketplace'].update_one({"_id": obj_id}, {"$inc": {"views": 1}})

    # Fetch seller info and trust score
    seller_id = item.get('seller_id')
    seller = None
    seller_trust_score = 75
    seller_badges = []
    seller_review_count = 0
    seller_avg_rating = 5.0

    if seller_id:
        try:
            seller = db['users'].find_one({"_id": ObjectId(seller_id)})
            seller_trust_score = calculate_trust_score(seller_id, db)
            seller_badges = calculate_user_badges(seller_id, db)

            rev_agg = list(db['user_reviews'].aggregate([
                {"$match": {"reviewee_id": seller_id}},
                {"$group": {"_id": None, "avg": {"$avg": "$rating"}, "count": {"$sum": 1}}}
            ]))
            if rev_agg and rev_agg[0]['count'] > 0:
                seller_avg_rating = round(float(rev_agg[0]['avg']), 1)
                seller_review_count = rev_agg[0]['count']
        except Exception:
            pass

    # Check if wishlisted by current user
    user_id = session.get('user_id')
    is_wishlisted = False
    user_offers = []
    if user_id:
        is_wishlisted = bool(db['marketplace_wishlists'].find_one({
            "user_id": user_id,
            "item_id": str(obj_id)
        }))
        if str(user_id) == str(seller_id):
            user_offers = list(db['marketplace_offers'].find({"item_id": str(obj_id)}).sort("created_at", -1))
        else:
            user_offers = list(db['marketplace_offers'].find({"item_id": str(obj_id), "buyer_id": user_id}))

    return render_template(
        'marketplace/detail.html',
        active_page='marketplace',
        item=item,
        seller=seller,
        seller_trust_score=seller_trust_score,
        seller_badges=seller_badges,
        seller_avg_rating=seller_avg_rating,
        seller_review_count=seller_review_count,
        is_wishlisted=is_wishlisted,
        user_offers=user_offers
    )


@marketplace_bp.route('/new', methods=['GET', 'POST'])
@login_required
def create_item():
    """
    Creates a new marketplace listing (Sell, Free giveaway, or Barter/Exchange).
    """
    db = get_db()
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        category = request.form.get('category', '').strip()
        condition = request.form.get('condition', 'Good').strip()
        price_raw = request.form.get('price', '0').strip()
        is_free = bool(request.form.get('is_free'))
        accept_exchange = bool(request.form.get('accept_exchange'))
        location = request.form.get('location', '').strip()
        description = request.form.get('description', '').strip()

        if not title or not category or not location:
            flash("Item Title, Category, and Campus Location are required.", "danger")
            return render_template('marketplace/create.html', categories=MARKETPLACE_CATEGORIES, conditions=ITEM_CONDITIONS, form=request.form)

        try:
            price = 0 if is_free else max(0, float(price_raw))
        except ValueError:
            price = 0

        # Optional photo upload
        saved_file, _ = save_uploaded_file(request.files.get('item_image'))

        user_id = session.get('user_id')
        new_item = {
            "title": title,
            "category": category,
            "condition": condition,
            "price": price,
            "is_free": is_free or (price == 0),
            "accept_exchange": accept_exchange,
            "location": location,
            "description": description,
            "image_path": saved_file,
            "seller_id": user_id,
            "seller_name": session.get('full_name') or session.get('username'),
            "seller_username": session.get('username'),
            "seller_dept": session.get('department', 'CSE'),
            "views": 0,
            "status": "available",
            "created_at": datetime.now(timezone.utc)
        }

        inserted_id = db['marketplace'].insert_one(new_item).inserted_id

        # Log Activity and Award Contributor Points
        award_user_points(user_id, 5, f"Listed '{title}' on Campus Marketplace", db)

        flash(f"'{title}' has been listed successfully on Campus Marketplace!", "success")
        return redirect(url_for('marketplace.view_item', item_id=str(inserted_id)))

    return render_template(
        'marketplace/create.html',
        active_page='marketplace',
        categories=MARKETPLACE_CATEGORIES,
        conditions=ITEM_CONDITIONS,
        form={}
    )


@marketplace_bp.route('/item/<item_id>/offer', methods=['POST'])
@login_required
def submit_offer(item_id):
    """
    Submits a purchase/exchange offer or price negotiation on a listing.
    """
    db = get_db()
    try:
        obj_id = ObjectId(item_id)
    except Exception:
        flash("Invalid item identifier.", "danger")
        return redirect(url_for('marketplace.list_items'))

    item = db['marketplace'].find_one({"_id": obj_id})
    if not item:
        flash("Listing not found.", "warning")
        return redirect(url_for('marketplace.list_items'))

    buyer_id = session.get('user_id')
    if buyer_id == item.get('seller_id'):
        flash("You cannot make an offer on your own listing.", "warning")
        return redirect(url_for('marketplace.view_item', item_id=item_id))

    offered_price_raw = request.form.get('offered_price', '0').strip()
    message = request.form.get('message', '').strip()

    try:
        offered_price = float(offered_price_raw)
    except ValueError:
        offered_price = item.get('price', 0)

    new_offer = {
        "item_id": str(obj_id),
        "item_title": item.get('title'),
        "buyer_id": buyer_id,
        "buyer_name": session.get('full_name') or session.get('username'),
        "buyer_username": session.get('username'),
        "seller_id": item.get('seller_id'),
        "offered_price": offered_price,
        "message": message or "I am interested in this item. Can we finalize the deal?",
        "status": "pending",  # pending, accepted, rejected, cancelled
        "created_at": datetime.now(timezone.utc)
    }

    db['marketplace_offers'].insert_one(new_offer)

    # Notify Seller
    db['notifications'].insert_one({
        "user_id": item.get('seller_id'),
        "title": f"New Offer for '{item.get('title')}'",
        "message": f"{session.get('full_name')} offered ₹{int(offered_price)} on your listing.",
        "category": "transactions",
        "is_read": False,
        "created_at": datetime.now(timezone.utc)
    })

    flash(f"Your offer of ₹{int(offered_price)} has been submitted to the seller!", "success")
    return redirect(url_for('marketplace.view_item', item_id=item_id))


@marketplace_bp.route('/offers', methods=['GET'])
@login_required
def manage_offers():
    """
    Displays received offers on user's listings and sent offers to other sellers.
    """
    db = get_db()
    user_id = session.get('user_id')

    incoming_offers = list(db['marketplace_offers'].find({"seller_id": user_id}).sort("created_at", -1))
    outgoing_offers = list(db['marketplace_offers'].find({"buyer_id": user_id}).sort("created_at", -1))

    return render_template(
        'marketplace/offers.html',
        active_page='marketplace',
        incoming_offers=incoming_offers,
        outgoing_offers=outgoing_offers
    )


@marketplace_bp.route('/offers/<offer_id>/<action>', methods=['POST'])
@login_required
def handle_offer(offer_id, action):
    """
    Accepts or rejects an incoming offer.
    """
    db = get_db()
    try:
        obj_id = ObjectId(offer_id)
    except Exception:
        flash("Invalid offer ID.", "danger")
        return redirect(url_for('marketplace.manage_offers'))

    offer = db['marketplace_offers'].find_one({"_id": obj_id})
    if not offer or offer.get('seller_id') != session.get('user_id'):
        flash("Offer not found or unauthorized.", "danger")
        return redirect(url_for('marketplace.manage_offers'))

    if action == 'accept':
        db['marketplace_offers'].update_one({"_id": obj_id}, {"$set": {"status": "accepted"}})
        db['marketplace'].update_one({"_id": ObjectId(offer['item_id'])}, {"$set": {"status": "reserved"}})

        # Notify buyer
        db['notifications'].insert_one({
            "user_id": offer.get('buyer_id'),
            "title": f"Offer Accepted for '{offer.get('item_title')}'",
            "message": f"Seller accepted your offer of ₹{offer.get('offered_price')}. Please coordinate meetup to collect the item.",
            "category": "transactions",
            "is_read": False,
            "created_at": datetime.now(timezone.utc)
        })
        flash("Offer accepted! Item is marked reserved. Coordinate collection with the buyer.", "success")
    elif action == 'reject':
        db['marketplace_offers'].update_one({"_id": obj_id}, {"$set": {"status": "rejected"}})
        flash("Offer declined.", "info")

    return redirect(url_for('marketplace.manage_offers'))


@marketplace_bp.route('/item/<item_id>/mark-sold', methods=['POST'])
@login_required
def mark_sold(item_id):
    """
    Marks a marketplace item as sold/completed.
    Awards +10 contribution points, updates transaction stats, and prompts review.
    """
    db = get_db()
    try:
        obj_id = ObjectId(item_id)
    except Exception:
        flash("Invalid item ID.", "danger")
        return redirect(url_for('marketplace.my_listings'))

    item = db['marketplace'].find_one({"_id": obj_id})
    if not item or item.get('seller_id') != session.get('user_id'):
        flash("Listing not found or unauthorized.", "danger")
        return redirect(url_for('marketplace.list_items'))

    db['marketplace'].update_one(
        {"_id": obj_id},
        {"$set": {"status": "sold", "sold_at": datetime.now(timezone.utc)}}
    )

    # Award points to seller
    user_id = session.get('user_id')
    award_user_points(user_id, 10, f"Completed sale of '{item.get('title')}'", db)

    flash(f"Congratulations! '{item.get('title')}' is marked as completed/sold. +10 points awarded!", "success")
    return redirect(url_for('marketplace.my_listings'))


@marketplace_bp.route('/my-listings')
@login_required
def my_listings():
    """
    Seller portal showing user's active, reserved, and sold listings.
    """
    db = get_db()
    user_id = session.get('user_id')

    listings = list(db['marketplace'].find({"seller_id": user_id}).sort("created_at", -1))
    return render_template(
        'marketplace/my_listings.html',
        active_page='marketplace',
        listings=listings
    )


@marketplace_bp.route('/item/<item_id>/wishlist', methods=['POST'])
@login_required
def toggle_wishlist(item_id):
    """
    Toggles saving an item in the user's personal wishlist.
    """
    db = get_db()
    user_id = session.get('user_id')

    existing = db['marketplace_wishlists'].find_one({"user_id": user_id, "item_id": item_id})
    if existing:
        db['marketplace_wishlists'].delete_one({"_id": existing['_id']})
        flash("Item removed from your wishlist.", "info")
    else:
        db['marketplace_wishlists'].insert_one({
            "user_id": user_id,
            "item_id": item_id,
            "created_at": datetime.now(timezone.utc)
        })
        flash("Item saved to your wishlist!", "success")

    return redirect(url_for('marketplace.view_item', item_id=item_id))


@marketplace_bp.route('/wishlist')
@login_required
def my_wishlist():
    """
    Displays items saved in user's wishlist.
    """
    db = get_db()
    user_id = session.get('user_id')

    saved_records = list(db['marketplace_wishlists'].find({"user_id": user_id}))
    item_ids = [ObjectId(r['item_id']) for r in saved_records if ObjectId.is_valid(r.get('item_id', ''))]

    items = list(db['marketplace'].find({"_id": {"$in": item_ids}})) if item_ids else []

    return render_template(
        'marketplace/wishlist.html',
        active_page='marketplace',
        items=items
    )
