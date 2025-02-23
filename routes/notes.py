import uuid
import boto3
from fastapi import APIRouter, Depends, HTTPException, File, UploadFile
from database.db import db
from routes.config import AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_BUCKET_NAME, AWS_REGION
from models.notes import NoteModel
from routes.user import get_current_user
from models.user import User

router10 = APIRouter()

# Initialize S3 Client
s3_client = boto3.client(
    "s3",
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    region_name=AWS_REGION,
)

# Connect to MongoDB
def get_db():
    return db.get_client()[db.db_name]

# 1️⃣ Upload PDF to S3 and Save Metadata in MongoDB
@router10.post("/upload-note/")
async def upload_pdf(file: UploadFile = File(...), db_client=Depends(get_db), current_user: User = Depends(get_current_user)):
    """Uploads a PDF to S3 and saves metadata in MongoDB"""

    if current_user.role != "admin":
        raise HTTPException(
            status_code=403,
            detail="You do not have permission to add a Notes"
        )

    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Only PDF files are allowed.")

    # Generate unique filename
    unique_filename = f"{uuid.uuid4()}.pdf"

    try:
        # Upload file to S3
        s3_client.upload_fileobj(file.file, AWS_BUCKET_NAME, unique_filename, ExtraArgs={"ContentType": "application/pdf"})

        # Get file URL
        file_url = f"https://{AWS_BUCKET_NAME}.s3.{AWS_REGION}.amazonaws.com/{unique_filename}"

        # Save metadata in MongoDB
        note_data = {"title": file.filename, "file_url": file_url}
        inserted_note = db_client.notes.insert_one(note_data)

        return {
            "message": "File uploaded successfully",
            "file_url": file_url,
            "note_id": str(inserted_note.inserted_id)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"File upload failed: {str(e)}")

# 2️⃣ Fetch List of Notes
@router10.get("/list-notes/")
async def list_notes(db_client=Depends(get_db), current_user: dict = Depends(get_current_user)):
    """Returns a list of uploaded notes (Accessible to all authenticated users)"""

    # ✅ Allow access if the user is either "admin" or "user"
    if current_user.role not in ["admin", "user"]:
        raise HTTPException(
            status_code=403,
            detail="You do not have permission to access this resource"
        )

    # Fetch all notes from MongoDB
    notes = list(db_client.notes.find({}, {"_id": 0}))  # Exclude MongoDB ObjectId
    return notes