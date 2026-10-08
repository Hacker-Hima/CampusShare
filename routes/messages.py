from datetime import datetime, timezone
from bson import ObjectId
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from database.connection import get_db
from utils.decorators import login_required
from utils.trust import calculate_trust_score

messages_bp = Blueprint('messages', __name__, url_prefix='/messages')

@messages_bp.route('', methods=['GET'])
@messages_bp.route('/', methods=['GET'])
@login_required
def inbox():
    """
    Campus Messaging Inbox (Server-Rendered):
    Lists active conversations with other students/faculty,
    showing unread indicators, context tags, and last activity timestamps.
    """
    db = get_db()
    user_id = session.get('user_id')

    # Find conversations where current user is a participant
    conversations = list(db['conversations'].find({
        "participants": user_id
    }).sort("last_updated", -1))

    # Decorate conversation records with counterpart details
    for conv in conversations:
        other_id = next((p for p in conv.get('participants', []) if p != user_id), None)
        conv['counterpart_id'] = other_id
        if other_id:
            try:
                other_user = db['users'].find_one({"_id": ObjectId(other_id)})
                conv['counterpart_name'] = other_user.get('full_name') or other_user.get('username') if other_user else 'Campus User'
                conv['counterpart_dept'] = other_user.get('department') if other_user else ''
                conv['counterpart_role'] = other_user.get('role') if other_user else 'student'
            except Exception:
                conv['counterpart_name'] = 'Campus User'
                conv['counterpart_dept'] = ''
                conv['counterpart_role'] = 'student'
        else:
            conv['counterpart_name'] = 'Campus User'

        # Check for unread messages in this conversation for current user
        unread_count = db['messages'].count_documents({
            "conversation_id": str(conv['_id']),
            "receiver_id": user_id,
            "is_read": False
        })
        conv['has_unread'] = (unread_count > 0)
        conv['unread_in_thread'] = unread_count

    return render_template(
        'messages/inbox.html',
        active_page='messages',
        conversations=conversations
    )


@messages_bp.route('/c/<conv_id>', methods=['GET', 'POST'])
@login_required
def view_thread(conv_id):
    """
    Server-rendered conversation thread showing message history
    and pure HTML POST form for sending responses.
    """
    db = get_db()
    user_id = session.get('user_id')

    try:
        obj_conv_id = ObjectId(conv_id)
    except Exception:
        flash("Invalid conversation ID.", "danger")
        return redirect(url_for('messages.inbox'))

    conv = db['conversations'].find_one({"_id": obj_conv_id})
    if not conv or user_id not in conv.get('participants', []):
        flash("Conversation not found or access denied.", "danger")
        return redirect(url_for('messages.inbox'))

    other_id = next((p for p in conv.get('participants', []) if p != user_id), None)
    other_user = None
    other_trust = 75
    if other_id:
        try:
            other_user = db['users'].find_one({"_id": ObjectId(other_id)})
            other_trust = calculate_trust_score(other_id, db)
        except Exception:
            pass

    # Handle sending a reply message (POST)
    if request.method == 'POST':
        message_text = request.form.get('message_text', '').strip()
        if not message_text:
            flash("Message cannot be blank.", "warning")
            return redirect(url_for('messages.view_thread', conv_id=conv_id))

        new_msg = {
            "conversation_id": str(obj_conv_id),
            "sender_id": user_id,
            "sender_name": session.get('full_name') or session.get('username'),
            "sender_username": session.get('username'),
            "receiver_id": other_id,
            "message_text": message_text,
            "is_read": False,
            "created_at": datetime.now(timezone.utc)
        }
        db['messages'].insert_one(new_msg)

        # Update parent conversation last message and timestamp
        db['conversations'].update_one(
            {"_id": obj_conv_id},
            {"$set": {
                "last_message": message_text[:120],
                "last_updated": datetime.now(timezone.utc)
            }}
        )

        # Notify recipient
        if other_id:
            db['notifications'].insert_one({
                "user_id": other_id,
                "title": f"New message from {session.get('full_name')}",
                "message": message_text[:90] + ("..." if len(message_text) > 90 else ""),
                "category": "messages",
                "is_read": False,
                "created_at": datetime.now(timezone.utc)
            })

        return redirect(url_for('messages.view_thread', conv_id=conv_id))

    # Mark incoming messages as read
    db['messages'].update_many(
        {"conversation_id": str(obj_conv_id), "receiver_id": user_id, "is_read": False},
        {"$set": {"is_read": True}}
    )

    # Fetch messages in chronological order
    messages = list(db['messages'].find({"conversation_id": str(obj_conv_id)}).sort("created_at", 1))

    return render_template(
        'messages/thread.html',
        active_page='messages',
        conversation=conv,
        other_user=other_user,
        other_trust=other_trust,
        messages=messages
    )


@messages_bp.route('/start', methods=['GET', 'POST'])
@login_required
def start_conversation():
    """
    Initiates a new conversation or redirects to an existing one.
    Accepts GET/POST with to_user_id, item_title, and initial message.
    """
    db = get_db()
    current_user_id = session.get('user_id')

    to_user_id = request.values.get('to_user_id', '').strip()
    item_title = request.values.get('item_title', '').strip()
    context_type = request.values.get('context_type', 'general').strip()
    initial_text = request.values.get('message', '').strip()

    if not to_user_id:
        flash("Recipient must be specified to start a conversation.", "danger")
        return redirect(url_for('messages.inbox'))

    if to_user_id == current_user_id:
        flash("You cannot start a conversation with yourself.", "warning")
        return redirect(url_for('messages.inbox'))

    # Check for existing conversation with this user
    query = {
        "participants": {"$all": [current_user_id, to_user_id]}
    }
    if item_title:
        query["item_title"] = item_title

    existing_conv = db['conversations'].find_one(query)

    if existing_conv:
        conv_id = existing_conv['_id']
        if initial_text:
            # Post initial message
            db['messages'].insert_one({
                "conversation_id": str(conv_id),
                "sender_id": current_user_id,
                "sender_name": session.get('full_name') or session.get('username'),
                "sender_username": session.get('username'),
                "receiver_id": to_user_id,
                "message_text": initial_text,
                "is_read": False,
                "created_at": datetime.now(timezone.utc)
            })
            db['conversations'].update_one(
                {"_id": conv_id},
                {"$set": {
                    "last_message": initial_text[:120],
                    "last_updated": datetime.now(timezone.utc)
                }}
            )
        return redirect(url_for('messages.view_thread', conv_id=str(conv_id)))

    # Create new conversation
    subject = f"Regarding {item_title}" if item_title else "Direct Campus Message"
    first_msg_text = initial_text or f"Hi! I'm reaching out regarding {item_title or 'your campus listing'}."

    new_conv_id = db['conversations'].insert_one({
        "participants": [current_user_id, to_user_id],
        "subject": subject,
        "item_title": item_title,
        "context_type": context_type,
        "last_message": first_msg_text[:120],
        "last_updated": datetime.now(timezone.utc)
    }).inserted_id

    db['messages'].insert_one({
        "conversation_id": str(new_conv_id),
        "sender_id": current_user_id,
        "sender_name": session.get('full_name') or session.get('username'),
        "sender_username": session.get('username'),
        "receiver_id": to_user_id,
        "message_text": first_msg_text,
        "is_read": False,
        "created_at": datetime.now(timezone.utc)
    })

    # Notify recipient
    db['notifications'].insert_one({
        "user_id": to_user_id,
        "title": f"New message from {session.get('full_name')}",
        "message": first_msg_text[:90] + ("..." if len(first_msg_text) > 90 else ""),
        "category": "messages",
        "is_read": False,
        "created_at": datetime.now(timezone.utc)
    })

    return redirect(url_for('messages.view_thread', conv_id=str(new_conv_id)))
