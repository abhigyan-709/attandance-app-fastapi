from fastapi import FastAPI, Depends
# from routes.item import route as item_router  # Correct import
from database.db import db
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.middleware.cors import CORSMiddleware
from routes.user import route2
from routes.message import route3
from routes.visitors import router4 as visitor_router
from routes.meet import router6 as meet_router  # Import the dependency
from routes.attendance import router7 as attendance_router
from routes.notes import router10 as notes_router
from routes.quiz import router17
from routes.feedback import router18
from routes.forgot_username import router
from routes.blogs import blog_router
from routes.subscription import route21
from routes.testimonial import route5
from routes import product
from routes import customer_details
from routes.google_auth import router31
from fastapi.middleware.cors import CORSMiddleware
from routes.google_refresh import router as google_refresh_router



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
app.add_middleware(TrustedHostMiddleware, allowed_hosts=["*"])
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(route21)
app.include_router(blog_router)
app.include_router(route2)
app.include_router(route3)
app.include_router(route5)
app.include_router(visitor_router, prefix="/api", tags=["Visitors"])
app.include_router(meet_router, prefix="/api", tags=["Google Meet"])
app.include_router(attendance_router, prefix="/api", tags=["Attendance"])
app.include_router(notes_router, prefix="/api", tags=["Notes"])
app.include_router(router17)
app.include_router(router18)
app.include_router(router)
app.include_router(product.router)
app.include_router(customer_details.route)
app.include_router(router31)
app.include_router(google_refresh_router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)