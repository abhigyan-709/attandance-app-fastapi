from fastapi import FastAPI, Depends
# from routes.item import route as item_router  # Correct import
from database.db import db
from routes.user import route2
from routes.message import route3
from routes.visitors import router4 as visitor_router
from routes.meet import router6 as meet_router  # Import the dependency
from routes.attendance import router7 as attendance_router
from routes.notes import router10 as notes_router

from fastapi.middleware.cors import CORSMiddleware

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


app.include_router(route2)
app.include_router(route3)
app.include_router(visitor_router, prefix="/api", tags=["Visitors"])
app.include_router(meet_router, prefix="/api", tags=["Google Meet"])
app.include_router(attendance_router, prefix="/api", tags=["Attendance"])
app.include_router(notes_router, prefix="/api", tags=["Notes"])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)