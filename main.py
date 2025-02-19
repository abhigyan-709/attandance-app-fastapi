from fastapi import FastAPI, Depends
# from routes.item import route as item_router  # Correct import
from database.db import db
from routes.user import route2
from routes.message import route3
from routes.visitors import router4 as visitor_router
from routes.meet import router6 as meet_router  # Import the dependency
from routes.attendance import router7 as attendance_router
from routes.notes import router10 as notes_router
from routes.quiz import router17
from routes.feedback import router18
import time
import json
import threading
from fastapi.middleware.cors import CORSMiddleware
from database.db import db, cache 

app = FastAPI(title="OpenSource Enterprise API",
              description="All in ONE API for basic authentication, user registration, attendance mapping and message sending",
              version="1.1.0",
    docs_url="/docs",
    contact={
        "name": "Project DevOps",
        "url": "https://api.projectdevops.in/docs",
        "email": "connect@projectdevops.in",

    },
    swagger_ui_parameters={"syntaxHighlight.theme": "obsidian"})


app.openapi_version = "3.0.2"



# Allow all origins for CORS (update this to a specific origin in production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def sync_quiz_responses():
    while True:
        try:
            keys = cache.redis_client.scan_iter("quiz_response:*")  
            for key in keys:
                response_data = cache.get(key)
                if response_data:
                    response_data = json.loads(response_data)

                    # Save to MongoDB
                    db_client = db.get_client()
                    db_client[db.db_name]["quiz_responses"].insert_one(response_data)
                    print(f"✅ Moved response {key} to MongoDB")

                    # Delete from Redis
                    cache.delete(key)
                    print(f"🗑️ Deleted {key} from Redis")

            time.sleep(10)  
        except Exception as e:
            print(f"❌ Error syncing quiz responses: {e}")
            time.sleep(5)  # Retry after 5 seconds



# Start the background thread when the app starts
threading.Thread(target=sync_quiz_responses, daemon=True).start()


app.include_router(route2)
app.include_router(route3)
app.include_router(visitor_router, prefix="/api", tags=["Visitors"])
app.include_router(meet_router, prefix="/api", tags=["Google Meet"])
app.include_router(attendance_router, prefix="/api", tags=["Attendance"])
app.include_router(notes_router, prefix="/api", tags=["Notes"])
app.include_router(router17)
app.include_router(router18)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)