#!/usr/bin/env python3
"""
Create daily horoscope in MongoDB
Usage: python3 create_horoscope.py [YYYY-MM-DD]
"""

import sys
from datetime import date, datetime
from pymongo import MongoClient
from database.db import db

# Zodiac data with emojis, Hindi names, syllables based on your pattern
ZODIAC_DATA = [
    {
        "sign": "mesh",
        "emoji": "🐏",
        "hindi_name": "मेष राशि",
        "syllables": "चू, चे, चो, ला, ली, लू, ले, लो, अ"
    },
    {
        "sign": "vrishabh",
        "emoji": "🐂",
        "hindi_name": "वृष राशि",
        "syllables": "ई, उ, ए, ओ, वा, वी, वू, वे, वो"
    },
    {
        "sign": "mithun",
        "emoji": "👭",
        "hindi_name": "मिथुन राशि",
        "syllables": "का, की, कु, घ, ड, छ, के, को, हा"
    },
    {
        "sign": "kark",
        "emoji": "🦀",
        "hindi_name": "कर्क राशि",
        "syllables": "ही, हू, हे, हो, डा, डी, डू, डे, डो"
    },
    {
        "sign": "simha",
        "emoji": "🐅",
        "hindi_name": "सिंह राशि",
        "syllables": "मा, मी, मू, मे, मो, टा, टी, टू, टे"
    },
    {
        "sign": "kanya",
        "emoji": "🙎‍♀️",
        "hindi_name": "कन्या राशि",
        "syllables": "टो, पा, पी, पू, ष, ण, ठ, पे, पो"
    },
    {
        "sign": "tula",
        "emoji": "⚖️",
        "hindi_name": "तुला राशि",
        "syllables": "रा, री, रु, रे, रो, ता, ती, तू, ते"
    },
    {
        "sign": "vrishchik",
        "emoji": "🦂",
        "hindi_name": "वृश्चिक राशि",
        "syllables": "तो, ना, नी, नू, ने, नो, या, यी, यू"
    },
    {
        "sign": "dhanu",
        "emoji": "🏹",
        "hindi_name": "धनु राशि",
        "syllables": "ये, यो, भा, भी, भू, ध, फ, ढ, भे"
    },
    {
        "sign": "makar",
        "emoji": "🐊",
        "hindi_name": "मकर राशि",
        "syllables": "भो, जा, जी, खी, खू, खे, खो, गा, गी"
    },
    {
        "sign": "kumbh",
        "emoji": "⚱️",
        "hindi_name": "कुम्भ राशि",
        "syllables": "गू, गे, गो, सा, सी, सू, से, सो, दा"
    },
    {
        "sign": "meen",
        "emoji": "🐟",
        "hindi_name": "मीन राशि",
        "syllables": "दी, दू, थ, झ, ञ, दे, दो, चा, ची"
    }
]

# Sample predictions (you can customize these)
SAMPLE_PREDICTIONS = {
    "mesh": "आज अपने काम के लिए दूसरों पर दबाव न डालें। दूसरे लोगों की इच्छाओं और दिलचस्पियों पर भी ग़ौर करें।",
    "vrishabh": "आज कठिनाइयों का सामना करना पड़ सकता है। हिम्मत न हारें और इच्छित फल पाने के लिए कड़ी मेहनत करें।",
    "mithun": "आज सबकी मदद करने की आपकी इच्छा आपको आज बुरी तरह थकाएगी। किसी करीबी रिश्तेदार की मदद मिलेगी।",
    "kark": "आज दोस्तों के साथ शाम अच्छी रहेगी। पैसा अचानक आपके पास आएगा, जो आपके ख़र्चों को सम्हाल लेगा।",
    "simha": "आज यह हँसी की चमक से उजला दिन है। बोलते समय और वित्तीय लेन-देन करते समय सावधानी बरतें।",
    "kanya": "आज तनाव को नज़रअंदाज़ न करें। घर में किसी फंक्शन के होने से धन खर्च होगा।",
    "tula": "आज सोचने से पहले दो बार सोचें। अनजाने ही आपका नज़रिया किसी की भावनाओं को आहत कर सकता है।",
    "vrishchik": "आज दोस्त से मिली ख़ास तारीफ़ ख़ुशी का ज़रिया बनेगी। परिवार के साथ समय बिताएं।",
    "dhanu": "आज पिता की सलाह मददगार रहेगी। नए अवसर मिल सकते हैं। दोस्त शाम की योजना बनाएंगे।",
    "makar": "आज दोस्त आपका परिचय किसी ख़ास से कराएंगे। पैसे की अहमियत समझ आएगी।",
    "kumbh": "आज तनाव दूर करने के लिए परिवार की मदद लें। अपनी भावनाओं को दबाएँ नहीं।",
    "meen": "आज दानशीलता का व्यवहार आशीर्वाद की तरह सिद्ध होगा। निवेश के लिए अच्छा दिन है।"
}


def create_daily_horoscope(target_date: date, author_username: str = "admin"):
    """Create daily horoscope in MongoDB"""
    try:
        # Get MongoDB client
        client = db.get_client()
        coll = client[db.db_name]["daily_horoscopes"]
        
        # Check if horoscope already exists
        existing = coll.find_one({"date": target_date.isoformat()})
        if existing:
            print(f"⚠️  Horoscope for {target_date} already exists!")
            print(f"ID: {existing['_id']}")
            return
        
        # Create zodiac predictions
        zodiac_predictions = []
        for z in ZODIAC_DATA:
            prediction = {
                "sign": z["sign"],
                "emoji": z["emoji"],
                "hindi_name": z["hindi_name"],
                "syllables": z["syllables"],
                "prediction": SAMPLE_PREDICTIONS.get(z["sign"], "आज का दिन शुभ रहेगा।")
            }
            zodiac_predictions.append(prediction)
        
        # Create horoscope document
        horoscope = {
            "title": "राशि फल✡️🙏🏻",
            "date": target_date.isoformat(),
            "zodiac_predictions": zodiac_predictions,
            "closing_message": "☘️आपका दिन मंगलमय हो।☘️",
            "contact_info": "🕉️ कुण्डली विचार, भविष्य की जानकारी, प्रश्न कुण्डली विचार हेतु सम्पर्क कर सकते हैं",
            "author_username": author_username,
            "published": True,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "published_at": datetime.utcnow(),
            "views": 0,
            "viewed_ips": [],
            "likes": 0,
            "liked_ips": []
        }
        
        # Insert into database
        result = coll.insert_one(horoscope)
        
        print(f"✓ Daily horoscope created successfully!")
        print(f"Date: {target_date}")
        print(f"ID: {result.inserted_id}")
        print(f"Zodiac signs: {len(zodiac_predictions)}")
        
    except Exception as e:
        print(f"✗ Error creating horoscope: {str(e)}")
        raise


if __name__ == "__main__":
    # Parse date from command line or use today
    if len(sys.argv) > 1:
        try:
            target_date = datetime.strptime(sys.argv[1], "%Y-%m-%d").date()
        except ValueError:
            print("Invalid date format. Use YYYY-MM-DD")
            sys.exit(1)
    else:
        target_date = date.today()
    
    # Get author username
    author = sys.argv[2] if len(sys.argv) > 2 else "admin"
    
    print(f"Creating daily horoscope for {target_date}...")
    create_daily_horoscope(target_date, author)
