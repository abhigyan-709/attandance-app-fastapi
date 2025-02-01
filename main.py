from fastapi import FastAPI
from routes import user_routes, attendance_routes

app = FastAPI()

app.include_router(user_routes.router, prefix="/users", tags=["Users"])
app.include_router(attendance_routes.router, prefix="/attendance", tags=["Attendance"])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
