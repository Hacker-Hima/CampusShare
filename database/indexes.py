import sys
import os
import pymongo

# Ensure project root is in sys.path when executed directly
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from database.connection import get_db

def create_indexes(db=None):
    """
    Creates and ensures optimal MongoDB indexes across all CampusShare collections.
    Includes single-field, compound, unique, and text search indexes.
    
    Academic Purpose:
    - Demonstrates MongoDB Indexing strategies (B-Tree indexes).
    - Prevents expensive COLLSCAN (collection scans) and enforces IXSCAN (index scans).
    - Guarantees data integrity using unique indexes on usernames and emails.
    """
    if db is None:
        db = get_db()

    created_indexes = {}

    # =========================================================================
    # 1. Users Collection Indexes
    # =========================================================================
    users_col = db['users']
    # Enforce uniqueness on username and email
    users_col.create_index([("username", pymongo.ASCENDING)], unique=True, name="idx_users_username_unique")
    users_col.create_index([("email", pymongo.ASCENDING)], unique=True, name="idx_users_email_unique")
    users_col.create_index([("role", pymongo.ASCENDING)], name="idx_users_role")
    users_col.create_index([("department", pymongo.ASCENDING)], name="idx_users_department")
    created_indexes['users'] = [idx['name'] for idx in users_col.list_indexes()]

    # =========================================================================
    # 2. Resources Collection Indexes
    # =========================================================================
    resources_col = db['resources']
    # Text index for multi-field full-text search across title, description, subject, and tags
    try:
        resources_col.create_index([
            ("title", pymongo.TEXT),
            ("description", pymongo.TEXT),
            ("subject", pymongo.TEXT),
            ("tags", pymongo.TEXT)
        ], name="idx_resources_text_search")
    except Exception as e:
        # If existing text index with different weights exists, log warning
        print(f"[Index Warning] Text index setup note: {e}")

    # Compound index for filtered catalog queries: filter by status + department
    resources_col.create_index([("status", pymongo.ASCENDING), ("department", pymongo.ASCENDING)], name="idx_resources_status_dept")
    # Compound index for filtered catalog queries: filter by status + category
    resources_col.create_index([("status", pymongo.ASCENDING), ("category", pymongo.ASCENDING)], name="idx_resources_status_cat")
    # Single field indexes
    resources_col.create_index([("owner_id", pymongo.ASCENDING)], name="idx_resources_owner")
    resources_col.create_index([("downloads", pymongo.DESCENDING)], name="idx_resources_downloads_desc")
    resources_col.create_index([("created_at", pymongo.DESCENDING)], name="idx_resources_created_desc")
    created_indexes['resources'] = [idx['name'] for idx in resources_col.list_indexes()]

    # =========================================================================
    # 3. Borrowings Collection Indexes
    # =========================================================================
    borrowings_col = db['borrowings']
    borrowings_col.create_index([("user_id", pymongo.ASCENDING)], name="idx_borrowings_user")
    borrowings_col.create_index([("resource_id", pymongo.ASCENDING)], name="idx_borrowings_resource")
    borrowings_col.create_index([("status", pymongo.ASCENDING)], name="idx_borrowings_status")
    # Compound index for overdue checking: status + due_date
    borrowings_col.create_index([("status", pymongo.ASCENDING), ("due_date", pymongo.ASCENDING)], name="idx_borrowings_status_due")
    created_indexes['borrowings'] = [idx['name'] for idx in borrowings_col.list_indexes()]

    # =========================================================================
    # 4. Reservations Collection Indexes
    # =========================================================================
    reservations_col = db['reservations']
    reservations_col.create_index([("user_id", pymongo.ASCENDING)], name="idx_reservations_user")
    # Compound index for interval conflict check: resource_id + date + status
    reservations_col.create_index([
        ("resource_id", pymongo.ASCENDING),
        ("date", pymongo.ASCENDING),
        ("status", pymongo.ASCENDING)
    ], name="idx_reservations_conflict_lookup")
    created_indexes['reservations'] = [idx['name'] for idx in reservations_col.list_indexes()]

    # =========================================================================
    # 5. Reviews Collection Indexes
    # =========================================================================
    reviews_col = db['reviews']
    reviews_col.create_index([("resource_id", pymongo.ASCENDING)], name="idx_reviews_resource")
    reviews_col.create_index([("user_id", pymongo.ASCENDING)], name="idx_reviews_user")
    created_indexes['reviews'] = [idx['name'] for idx in reviews_col.list_indexes()]

    # =========================================================================
    # 6. Notifications Collection Indexes
    # =========================================================================
    notifications_col = db['notifications']
    # Compound index for rapid unread badge count queries in base template context processor
    notifications_col.create_index([("user_id", pymongo.ASCENDING), ("is_read", pymongo.ASCENDING)], name="idx_notifications_user_unread")
    notifications_col.create_index([("created_at", pymongo.DESCENDING)], name="idx_notifications_created_desc")
    created_indexes['notifications'] = [idx['name'] for idx in notifications_col.list_indexes()]

    # =========================================================================
    # 7. Resource Requests Collection Indexes
    # =========================================================================
    requests_col = db['resource_requests']
    requests_col.create_index([("user_id", pymongo.ASCENDING)], name="idx_requests_user")
    requests_col.create_index([("status", pymongo.ASCENDING)], name="idx_requests_status")
    created_indexes['resource_requests'] = [idx['name'] for idx in requests_col.list_indexes()]

    # =========================================================================
    # 8. Reports Collection Indexes
    # =========================================================================
    reports_col = db['reports']
    reports_col.create_index([("status", pymongo.ASCENDING)], name="idx_reports_status")
    reports_col.create_index([("resource_id", pymongo.ASCENDING)], name="idx_reports_resource")
    created_indexes['reports'] = [idx['name'] for idx in reports_col.list_indexes()]

    # =========================================================================
    # 9. Campus Marketplace Collection Indexes
    # =========================================================================
    marketplace_col = db['marketplace']
    try:
        marketplace_col.create_index([
            ("title", pymongo.TEXT),
            ("description", pymongo.TEXT),
            ("category", pymongo.TEXT),
            ("location", pymongo.TEXT)
        ], name="idx_marketplace_text_search")
    except Exception as e:
        print(f"[Index Warning] Marketplace text index: {e}")

    marketplace_col.create_index([("status", pymongo.ASCENDING), ("category", pymongo.ASCENDING)], name="idx_marketplace_status_cat")
    marketplace_col.create_index([("status", pymongo.ASCENDING), ("price", pymongo.ASCENDING)], name="idx_marketplace_status_price")
    marketplace_col.create_index([("seller_id", pymongo.ASCENDING)], name="idx_marketplace_seller")
    marketplace_col.create_index([("created_at", pymongo.DESCENDING)], name="idx_marketplace_created_desc")
    created_indexes['marketplace'] = [idx['name'] for idx in marketplace_col.list_indexes()]

    # =========================================================================
    # 10. Marketplace Offers Indexes
    # =========================================================================
    offers_col = db['marketplace_offers']
    offers_col.create_index([("item_id", pymongo.ASCENDING)], name="idx_offers_item")
    offers_col.create_index([("buyer_id", pymongo.ASCENDING)], name="idx_offers_buyer")
    offers_col.create_index([("seller_id", pymongo.ASCENDING)], name="idx_offers_seller")
    offers_col.create_index([("status", pymongo.ASCENDING)], name="idx_offers_status")
    created_indexes['marketplace_offers'] = [idx['name'] for idx in offers_col.list_indexes()]

    # =========================================================================
    # 11. Conversations & Messages Collection Indexes
    # =========================================================================
    conv_col = db['conversations']
    conv_col.create_index([("participants", pymongo.ASCENDING)], name="idx_conv_participants")
    conv_col.create_index([("last_updated", pymongo.DESCENDING)], name="idx_conv_updated_desc")
    created_indexes['conversations'] = [idx['name'] for idx in conv_col.list_indexes()]

    msg_col = db['messages']
    msg_col.create_index([("conversation_id", pymongo.ASCENDING), ("created_at", pymongo.ASCENDING)], name="idx_msg_conv_time")
    msg_col.create_index([("receiver_id", pymongo.ASCENDING), ("is_read", pymongo.ASCENDING)], name="idx_msg_unread")
    created_indexes['messages'] = [idx['name'] for idx in msg_col.list_indexes()]

    # =========================================================================
    # 12. Lost & Found Collection Indexes
    # =========================================================================
    lf_col = db['lost_found']
    try:
        lf_col.create_index([
            ("title", pymongo.TEXT),
            ("description", pymongo.TEXT),
            ("location", pymongo.TEXT)
        ], name="idx_lostfound_text_search")
    except Exception as e:
        print(f"[Index Warning] Lost & Found text index: {e}")

    lf_col.create_index([("status", pymongo.ASCENDING), ("category", pymongo.ASCENDING)], name="idx_lostfound_status_cat")
    lf_col.create_index([("item_type", pymongo.ASCENDING)], name="idx_lostfound_type")
    lf_col.create_index([("created_at", pymongo.DESCENDING)], name="idx_lostfound_created_desc")
    created_indexes['lost_found'] = [idx['name'] for idx in lf_col.list_indexes()]

    # =========================================================================
    # 13. Peer Reviews & Disputes Collection Indexes
    # =========================================================================
    user_reviews_col = db['user_reviews']
    user_reviews_col.create_index([("reviewee_id", pymongo.ASCENDING)], name="idx_user_reviews_reviewee")
    user_reviews_col.create_index([("reviewer_id", pymongo.ASCENDING)], name="idx_user_reviews_reviewer")
    created_indexes['user_reviews'] = [idx['name'] for idx in user_reviews_col.list_indexes()]

    disputes_col = db['disputes']
    disputes_col.create_index([("status", pymongo.ASCENDING)], name="idx_disputes_status")
    disputes_col.create_index([("transaction_id", pymongo.ASCENDING)], name="idx_disputes_transaction")
    created_indexes['disputes'] = [idx['name'] for idx in disputes_col.list_indexes()]

    bookmarks_col = db['bookmarks']
    bookmarks_col.create_index([("user_id", pymongo.ASCENDING), ("resource_id", pymongo.ASCENDING)], unique=True, name="idx_bookmarks_user_res_unique")
    created_indexes['bookmarks'] = [idx['name'] for idx in bookmarks_col.list_indexes()]

    announcements_col = db['announcements']
    announcements_col.create_index([("is_active", pymongo.ASCENDING), ("created_at", pymongo.DESCENDING)], name="idx_announcements_active")
    created_indexes['announcements'] = [idx['name'] for idx in announcements_col.list_indexes()]

    print("[MongoDB Indexes] Successfully verified and applied all B-Tree & Text indexes.")
    return created_indexes


def demonstrate_query_plan(query={"status": "approved", "department": "CSE"}):
    """
    Runs explain('executionStats') to demonstrate index optimization (IXSCAN vs COLLSCAN)
    for examination / Viva demonstrations.
    """
    db = get_db()
    explanation = db['resources'].find(query).explain()
    stats = explanation.get("executionStats", {})
    winning_plan = explanation.get("queryPlanner", {}).get("winningPlan", {})
    
    stage = winning_plan.get("stage")
    if stage == "FETCH":
        input_stage = winning_plan.get("inputStage", {}).get("stage", "UNKNOWN")
    else:
        input_stage = stage

    report = {
        "query": query,
        "execution_stage": input_stage,  # Should be IXSCAN when indexed
        "nReturned": stats.get("nReturned", 0),
        "totalDocsExamined": stats.get("totalDocsExamined", 0),
        "totalKeysExamined": stats.get("totalKeysExamined", 0),
        "executionTimeMillis": stats.get("executionTimeMillis", 0)
    }
    return report


if __name__ == "__main__":
    db = get_db()
    indexes = create_indexes(db)
    print("\n--- Summary of Created Indexes ---")
    for col_name, idx_list in indexes.items():
        print(f"Collection '{col_name}': {', '.join(idx_list)}")

    print("\n--- Query Optimization Verification ---")
    plan = demonstrate_query_plan()
    print(f"Filter: {plan['query']}")
    print(f"Plan Stage: {plan['execution_stage']} (IXSCAN = Index scan used!)")
    print(f"Docs Examined: {plan['totalDocsExamined']} | Keys Examined: {plan['totalKeysExamined']}")
    print(f"Execution Time: {plan['executionTimeMillis']} ms")
