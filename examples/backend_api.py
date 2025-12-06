# Example FastAPI backend for WideChat media uploads

from fastapi import FastAPI, File, UploadFile, HTTPException, Header
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
import firebase_admin
from firebase_admin import auth, credentials
import io
import os
from typing import Optional

app = FastAPI(title="WideChat Media API")

# Initialize Firebase Admin SDK
cred = credentials.Certificate("path/to/serviceAccountKey.json")
firebase_admin.initialize_app(cred)

# Google Drive setup
SCOPES = ['https://www.googleapis.com/auth/drive']
SERVICE_ACCOUNT_FILE = 'path/to/drive-service-account.json'

credentials_drive = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE, scopes=SCOPES)
drive_service = build('drive', 'v3', credentials=credentials_drive)

@app.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    authorization: str = Header(...)
):
    try:
        # Verify Firebase ID token
        token = authorization.replace("Bearer ", "")
        decoded_token = auth.verify_id_token(token)
        user_id = decoded_token['uid']
        
        # Read file content
        file_content = await file.read()
        file_stream = io.BytesIO(file_content)
        
        # Upload to Google Drive
        file_metadata = {
            'name': file.filename,
            'parents': ['YOUR_DRIVE_FOLDER_ID']  # Optional: specify folder
        }
        
        media = MediaIoBaseUpload(
            file_stream,
            mimetype=file.content_type,
            resumable=True
        )
        
        drive_file = drive_service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id'
        ).execute()
        
        file_id = drive_file.get('id')
        
        # Make file publicly accessible
        drive_service.permissions().create(
            fileId=file_id,
            body={'role': 'reader', 'type': 'anyone'}
        ).execute()
        
        # Generate download URL
        download_url = f"https://drive.google.com/uc?id={file_id}"
        
        return {
            "file_id": file_id,
            "download_url": download_url,
            "filename": file.filename,
            "mime_type": file.content_type,
            "size": len(file_content)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)