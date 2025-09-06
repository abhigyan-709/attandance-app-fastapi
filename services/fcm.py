import os, json, time, hashlib
from firebase_admin import credentials, initialize_app, messaging
from pymongo.database import Database as MongoDB

_firebase_app = None

def _ensure_firebase():
    global _firebase_app
    if _firebase_app:
        return _firebase_app
    cred_json = os.getenv("FIREBASE_CREDENTIALS_JSON")
    cred_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    if cred_json:
        cred = credentials.Certificate(json.loads(cred_json))
    elif cred_path:
        cred = credentials.Certificate(cred_path)
    else:
        raise RuntimeError("Set FIREBASE_CREDENTIALS_JSON or GOOGLE_APPLICATION_CREDENTIALS")
    _firebase_app = initialize_app(cred)
    return _firebase_app

def vendor_topic(email: str) -> str:
    # topic-safe deterministic id from email
    digest = hashlib.sha256(email.strip().lower().encode()).hexdigest()[:24]
    return f"vendor_{digest}"

def _ensure_indexes(db: MongoDB):
    db.push_tokens.create_index("token", unique=True)
    db.push_tokens.create_index("email")
    db.push_tokens.create_index("last_seen")

def register_token(
    db: MongoDB, *,
    email: str,
    token: str,
    platform: str,     # 'web' | 'android' | 'ios'
    user_type: str,    # 'vendor' | 'customer' | 'admin'
    user_agent: str | None = None,
) -> str | None:
    _ensure_firebase()
    _ensure_indexes(db)

    db.push_tokens.update_one(
        {"token": token},
        {"$set": {
            "email": email.strip().lower(),
            "platform": platform,
            "user_type": user_type,
            "user_agent": user_agent,
            "last_seen": int(time.time()),
        }},
        upsert=True,
    )

    topic = None
    if user_type == "vendor":
        topic = vendor_topic(email)
        messaging.subscribe_to_topic([token], topic)  # idempotent
    return topic

def unregister_token(db: MongoDB, token: str):
    db.push_tokens.delete_one({"token": token})

def send_vendor_order_created(
    vendor_email: str, *,
    order_id: str,
    amount: float,
    customer_name: str = "",
):
    _ensure_firebase()
    topic = vendor_topic(vendor_email)

    message = messaging.Message(
        topic=topic,
        notification=messaging.Notification(
            title="New Order Received",
            body=f"#{order_id} • ₹{amount:.0f}" + (f" from {customer_name}" if customer_name else ""),
        ),
        data={
            "type": "order_created",
            "orderId": str(order_id),
            "amount": str(amount),
            "customerName": customer_name or "",
            "link": f"/orders/{order_id}",
        },
        webpush=messaging.WebpushConfig(
            headers={"TTL": "60"},
            fcm_options=messaging.WebpushFCMOptions(link=f"/orders/{order_id}"),
        ),
        android=messaging.AndroidConfig(priority="high"),
    )
    return messaging.send(message)
