from fastapi import FastAPI, HTTPException, Depends, status, UploadFile, File, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import socketio
from datetime import datetime, timedelta
import secrets
import qrcode
from io import BytesIO
import base64
import os
from typing import Optional, List
import aiofiles
import pytz
import asyncio
from contextlib import asynccontextmanager
import pyotp
from PIL import Image
from cryptography.fernet import Fernet

# Firebase imports
import firebase_admin
from firebase_admin import credentials, firestore, auth

# Google Drive imports
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from google.oauth2 import service_account
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request as GoogleRequest
import pickle
import io

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# ==================== UTILITY CLASSES ====================
class SecurityUtils:
    @staticmethod
    def generate_secret_key():
        return Fernet.generate_key()
    
    @staticmethod
    def encrypt_message(message: str, key: bytes) -> str:
        f = Fernet(key)
        encrypted = f.encrypt(message.encode())
        return base64.b64encode(encrypted).decode()
    
    @staticmethod
    def decrypt_message(encrypted_message: str, key: bytes) -> str:
        f = Fernet(key)
        decoded = base64.b64decode(encrypted_message.encode())
        decrypted = f.decrypt(decoded)
        return decrypted.decode()

class QRUtils:
    @staticmethod
    def generate_qr_code(data: str, filename: str) -> str:
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(data)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        filepath = f"uploads/qr_{filename}.png"
        img.save(filepath)
        return filepath

class OTPUtils:
    @staticmethod
    def generate_secret():
        return pyotp.random_base32()
    
    @staticmethod
    def generate_otp(secret: str) -> str:
        totp = pyotp.TOTP(secret)
        return totp.now()
    
    @staticmethod
    def verify_otp(secret: str, token: str) -> bool:
        totp = pyotp.TOTP(secret)
        return totp.verify(token)

class FileUtils:
    @staticmethod
    def compress_image(file_path: str, quality: int = 85) -> str:
        with Image.open(file_path) as img:
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")
            
            max_size = (1920, 1080)
            img.thumbnail(max_size, Image.Resampling.LANCZOS)
            
            compressed_path = file_path.replace(".", "_compressed.")
            img.save(compressed_path, "JPEG", quality=quality, optimize=True)
            return compressed_path
    
    @staticmethod
    def get_file_type(filename: str) -> str:
        ext = filename.lower().split('.')[-1]
        if ext in ['jpg', 'jpeg', 'png', 'gif', 'webp']:
            return 'image'
        elif ext in ['mp4', 'avi', 'mov', 'wmv', 'flv']:
            return 'video'
        elif ext in ['mp3', 'wav', 'ogg', 'm4a']:
            return 'audio'
        elif ext in ['pdf', 'doc', 'docx', 'txt', 'rtf']:
            return 'document'
        else:
            return 'file'

# Initialize Firebase
import json
try:
    # Try to load from environment variable (JSON string)
    firebase_config = os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON") or os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    print(f"Firebase config found: {bool(firebase_config)}")
    
    if firebase_config and firebase_config.startswith('{'):
        print("Loading Firebase from JSON string")
        cred = credentials.Certificate(json.loads(firebase_config))
    else:
        print("Loading Firebase from file path")
        # Fallback to file path
        cred = credentials.Certificate(firebase_config or "./firebase-service-account.json")
except Exception as e:
    print(f"Firebase initialization error: {e}")
    # Fallback to file
    try:
        print("Trying fallback file path")
        cred = credentials.Certificate("./firebase-service-account.json")
    except Exception as e2:
        print(f"Fallback also failed: {e2}")
        raise e2

print("Initializing Firebase app...")
firebase_admin.initialize_app(cred)
db = firestore.client()
print("Firebase initialized successfully")

# ==================== GOOGLE DRIVE SERVICE ====================
class GoogleDriveService:
    def __init__(self):
        self.service = None
        self.SCOPES = ['https://www.googleapis.com/auth/drive']
        self._initialize_service()
    
    def _initialize_service(self):
        try:
            creds = None
            # Check if token.pickle exists
            if os.path.exists('token.pickle'):
                with open('token.pickle', 'rb') as token:
                    creds = pickle.load(token)
            
            # If no valid credentials, run OAuth flow
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(GoogleRequest())
                else:
                    # Check if credentials.json exists
                    if os.path.exists('credentials.json'):
                        flow = InstalledAppFlow.from_client_secrets_file(
                            'credentials.json', self.SCOPES)
                        flow.redirect_uri = 'http://localhost:8000/oauth2callback'
                        # Get authorization URL
                        auth_url, _ = flow.authorization_url(prompt='consent')
                        print(f"Please visit this URL to authorize: {auth_url}")
                        print("After authorization, you'll be redirected. Copy the 'code' parameter from the URL.")
                        auth_code = input("Enter the authorization code: ")
                        flow.fetch_token(code=auth_code)
                        creds = flow.credentials
                    else:
                        print("credentials.json not found. Please create OAuth2 credentials.")
                        return
                
                # Save credentials for next run
                with open('token.pickle', 'wb') as token:
                    pickle.dump(creds, token)
            
            self.service = build('drive', 'v3', credentials=creds)
            print("Google Drive OAuth2 service initialized successfully")
            
        except Exception as e:
            print(f"Google Drive OAuth2 initialization failed: {e}")
            import traceback
            traceback.print_exc()
            self.service = None
    
    def create_user_folder(self, user_email: str) -> str:
        """Create a folder for the user in Google Drive root"""
        try:
            folder_metadata = {
                "name": user_email,
                "mimeType": "application/vnd.google-apps.folder"
            }
            folder = self.service.files().create(
                body=folder_metadata,
                fields="id"
            ).execute()
            print(f"Created folder for user {user_email}: {folder['id']}")
            return folder["id"]
        except Exception as e:
            print(f"Error creating user folder: {e}")
            raise e
    
    def delete_user_folder(self, folder_id: str):
        """Delete user folder and all files in it"""
        try:
            self.service.files().delete(fileId=folder_id).execute()
            print(f"Deleted user folder: {folder_id}")
        except Exception as e:
            print(f"Error deleting user folder: {e}")
            raise e
    
    async def upload_file(self, file_content: bytes, filename: str, mime_type: str, folder_id: str = None) -> str:
        if not self.service:
            raise Exception("Google Drive service not initialized")
        
        try:
            print(f"Uploading file to Google Drive: {filename} ({len(file_content)} bytes)")
            
            file_metadata = {
                'name': filename
            }
            
            # If folder_id provided, upload to that folder
            if folder_id:
                file_metadata['parents'] = [folder_id]
            
            media = MediaIoBaseUpload(
                io.BytesIO(file_content),
                mimetype=mime_type,
                resumable=False
            )
            
            file = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id,webViewLink,webContentLink'
            ).execute()
            
            file_id = file['id']
            print(f"File uploaded to Google Drive with ID: {file_id}")
            
            # Make file publicly accessible
            try:
                self.service.permissions().create(
                    fileId=file_id,
                    body={'role': 'reader', 'type': 'anyone'}
                ).execute()
                print(f"File permissions set to public for ID: {file_id}")
            except Exception as perm_error:
                print(f"Permission setting failed: {perm_error}")
            
            return f"https://drive.google.com/uc?id={file_id}"
        except Exception as e:
            print(f"Google Drive upload error: {str(e)}")
            import traceback
            traceback.print_exc()
            raise e

# Initialize Google Drive service
google_drive_service = GoogleDriveService()

# ==================== FIREBASE SERVICE CLASS ====================
class FirebaseService:
    def __init__(self):
        self.db = db

    async def create_user(self, user_data: dict) -> dict:
        user_ref = self.db.collection('users').document()
        user_data['id'] = user_ref.id
        user_data['created_at'] = datetime.utcnow()
        user_data['updated_at'] = datetime.utcnow()
        user_ref.set(user_data)
        return user_data

    async def get_user_by_email(self, email: str) -> Optional[dict]:
        users_ref = self.db.collection('users')
        query = users_ref.where('email', '==', email).limit(1)
        docs = query.stream()
        for doc in docs:
            return {'id': doc.id, **doc.to_dict()}
        return None

    async def get_user_by_id(self, user_id: str) -> Optional[dict]:
        doc_ref = self.db.collection('users').document(user_id)
        doc = doc_ref.get()
        if doc.exists:
            return {'id': doc.id, **doc.to_dict()}
        return None

    async def update_user(self, user_id: str, update_data: dict) -> bool:
        update_data['updated_at'] = datetime.utcnow()
        doc_ref = self.db.collection('users').document(user_id)
        doc_ref.update(update_data)
        return True

    async def get_user_connections(self, user_id: str) -> List[dict]:
        user = await self.get_user_by_id(user_id)
        if not user or 'connections' not in user:
            return []
        
        connections = []
        for conn_id in user['connections']:
            conn_user = await self.get_user_by_id(conn_id)
            if conn_user:
                connections.append(conn_user)
        return connections

    async def send_message(self, message_data: dict) -> dict:
        message_ref = self.db.collection('messages').document()
        message_data['id'] = message_ref.id
        message_data['timestamp'] = datetime.utcnow()
        message_data['status'] = 'sent'
        message_ref.set(message_data)
        return message_data

    async def get_messages(self, user_id: str, other_user_id: str) -> List[dict]:
        messages_ref = self.db.collection('messages')
        # Use simple query without ordering to avoid index requirement
        query = messages_ref.where('participants', 'array_contains', user_id)
        docs = query.stream()
        
        messages = []
        for doc in docs:
            msg_data = doc.to_dict()
            if (msg_data.get('sender_id') == user_id and msg_data.get('receiver_id') == other_user_id) or \
               (msg_data.get('sender_id') == other_user_id and msg_data.get('receiver_id') == user_id):
                messages.append({'id': doc.id, **msg_data})
        
        # Sort by timestamp in Python
        messages.sort(key=lambda x: x.get('timestamp', datetime.min))
        return messages

    async def search_messages(self, user_id: str, query: str) -> List[dict]:
        messages_ref = self.db.collection('messages')
        docs = messages_ref.where('participants', 'array_contains', user_id).stream()
        
        results = []
        for doc in docs:
            msg_data = doc.to_dict()
            if query.lower() in msg_data.get('message_text', '').lower():
                results.append({'id': doc.id, **msg_data})
        
        return results

# Create global instance
def format_last_seen(last_seen_timestamp):
    """Format last seen timestamp like WhatsApp"""
    if not last_seen_timestamp:
        return 'last seen a long time ago'
    
    try:
        if hasattr(last_seen_timestamp, 'timestamp'):
            last_seen = datetime.fromtimestamp(last_seen_timestamp.timestamp())
        else:
            last_seen = datetime.fromisoformat(str(last_seen_timestamp).replace('Z', '+00:00'))
            if last_seen.tzinfo:
                last_seen = last_seen.replace(tzinfo=None)
        
        now = datetime.now()
        diff = now - last_seen
        
        if diff.total_seconds() < 60:
            return 'last seen just now'
        elif diff.total_seconds() < 3600:
            minutes = int(diff.total_seconds() / 60)
            return f'last seen {minutes} minute{"s" if minutes > 1 else ""} ago'
        elif diff.days == 0:
            return f'last seen today at {last_seen.strftime("%I:%M %p").lower()}'
        elif diff.days == 1:
            return f'last seen yesterday at {last_seen.strftime("%I:%M %p").lower()}'
        elif diff.days < 7:
            day_name = last_seen.strftime('%A')
            return f'last seen {day_name} at {last_seen.strftime("%I:%M %p").lower()}'
        else:
            return f'last seen {last_seen.strftime("%d/%m/%Y at %I:%M %p").lower()}'
    except Exception as e:
        print(f"Error formatting last seen: {e}")
        return 'last seen a long time ago'

firebase_service = FirebaseService()

async def update_user_status(user_id: str, is_online: bool):
    """Update user online status in Firestore"""
    try:
        user_ref = db.collection('users').document(user_id)
        update_data = {'is_online': is_online}
        
        if not is_online:
            update_data['last_seen'] = firestore.SERVER_TIMESTAMP
        
        user_ref.update(update_data)
    except Exception as e:
        print(f"Error updating user status: {e}")

# Pydantic models
class UserCreate(BaseModel):
    email: str
    password: str
    name: str

class UserLogin(BaseModel):
    email: str
    password: str

class MessageSend(BaseModel):
    receiver_id: str
    message_text: str
    message_type: str = "text"
    reply_to_id: Optional[str] = None
    caption: Optional[str] = None
    file_url: Optional[str] = None
    group_id: Optional[str] = None
    location_lat: Optional[float] = None
    location_lng: Optional[float] = None
    contact_data: Optional[dict] = None

class ChatRequest(BaseModel):
    receiver_id: str
    message: str

class BroadcastCreate(BaseModel):
    name: str
    recipient_ids: List[str]

class BroadcastMessage(BaseModel):
    message_text: str
    message_type: str = "text"
    file_url: Optional[str] = None

class NotificationCreate(BaseModel):
    user_id: str
    title: str
    message: str
    type: str = "message"
    data: Optional[dict] = None

class MessageReaction(BaseModel):
    message_id: str
    emoji: str

class StatusUpdate(BaseModel):
    content: str
    media_url: Optional[str] = None
    status_type: str = "text"

class GroupCreate(BaseModel):
    name: str
    member_ids: List[str]

# Background task to clean up inactive users
async def cleanup_inactive_users():
    """Background task to mark users offline if no heartbeat received"""
    while True:
        try:
            current_time = get_indian_time()
            inactive_users = []
            
            for user_id, session_data in online_users.items():
                last_heartbeat = session_data.get('last_heartbeat')
                if last_heartbeat:
                    last_heartbeat_dt = datetime.fromisoformat(last_heartbeat.replace('Z', '+00:00'))
                    if last_heartbeat_dt.tzinfo is None:
                        last_heartbeat_dt = pytz.timezone('Asia/Kolkata').localize(last_heartbeat_dt)
                    
                    # Convert both to naive datetime for comparison
                    current_naive = current_time.replace(tzinfo=None)
                    last_heartbeat_naive = last_heartbeat_dt.replace(tzinfo=None)
                    
                    if (current_naive - last_heartbeat_naive).total_seconds() > 30:
                        inactive_users.append(user_id)
            
            for user_id in inactive_users:
                online_users.pop(user_id, None)
                user_sessions.pop(user_id, None)
                await update_user_status(user_id, False)
                
                # Emit user offline status
                await sio.emit('user_offline', {
                    'user_id': user_id,
                    'last_seen': get_indian_time().isoformat() + 'Z'
                })
                
        except Exception as e:
            print(f"Error in cleanup task: {e}")
        
        await asyncio.sleep(15)  # Check every 15 seconds

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    asyncio.create_task(cleanup_inactive_users())
    yield
    # Shutdown (if needed)

# FastAPI app
app = FastAPI(title="WideChat API", lifespan=lifespan)

# Auth setup
security = HTTPBearer()
security_optional = HTTPBearer(auto_error=False)

def get_indian_time():
    return datetime.utcnow()

async def get_current_user_optional(credentials: HTTPAuthorizationCredentials = Depends(security_optional)):
    """Optional authentication - returns None if no valid token"""
    try:
        if not credentials or not credentials.credentials:
            return None
            
        token = credentials.credentials
        decoded_token = auth.verify_id_token(token, check_revoked=True)
        user_id = decoded_token['uid']
        
        user_doc = db.collection('users').document(user_id).get()
        if not user_doc.exists:
            return None
        
        user_data = user_doc.to_dict()
        user_data['id'] = user_doc.id
        return user_data
    except Exception as e:
        print(f"Optional auth error: {str(e)}")
        return None

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        if not credentials or not credentials.credentials:
            print("No credentials provided")
            raise HTTPException(status_code=401, detail="Authorization token required")
            
        token = credentials.credentials
        print(f"Verifying token: {token[:20]}...")
        
        try:
            decoded_token = auth.verify_id_token(token, check_revoked=True)
            user_id = decoded_token['uid']
            print(f"Token verified for user: {user_id}")
        except auth.InvalidIdTokenError as e:
            print(f"Invalid token error: {str(e)}")
            raise HTTPException(status_code=401, detail="Invalid authentication token")
        except auth.ExpiredIdTokenError as e:
            print(f"Expired token error: {str(e)}")
            raise HTTPException(status_code=401, detail="Authentication token expired")
        except auth.RevokedIdTokenError as e:
            print(f"Revoked token error: {str(e)}")
            raise HTTPException(status_code=401, detail="Authentication token revoked")
        except Exception as e:
            print(f"Token verification error: {str(e)}")
            raise HTTPException(status_code=401, detail="Token verification failed")
        
        user_doc = db.collection('users').document(user_id).get()
        if not user_doc.exists:
            print(f"User document not found for: {user_id}")
            raise HTTPException(status_code=404, detail="User not found")
        
        user_data = user_doc.to_dict()
        user_data['id'] = user_doc.id
        print(f"User data retrieved successfully for: {user_id}")
        return user_data
            
    except HTTPException:
        raise
    except Exception as e:
        print(f"Unexpected auth error: {str(e)}")
        raise HTTPException(status_code=500, detail="Authentication system error")

@app.get("/")
async def root():
    return {"message": "WideChat API is running", "status": "healthy", "timestamp": get_indian_time().isoformat()}

@app.get("/test")
async def test_endpoint():
    """Simple test endpoint without authentication"""
    return {
        "message": "Test endpoint working",
        "firebase_configured": bool(os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON")),
        "google_drive_service": google_drive_service.service is not None,
        "timestamp": get_indian_time().isoformat()
    }

@app.get("/health")
async def health_check():
    try:
        # Test Firebase connection
        test_doc = db.collection('test').document('health').get()
        firebase_status = "connected"
    except Exception as e:
        firebase_status = f"error: {str(e)}"
    
    return {
        "status": "ok", 
        "service": "WideChat Backend",
        "firebase": firebase_status,
        "env_vars": {
            "FIREBASE_SERVICE_ACCOUNT_JSON": bool(os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON")),
            "GOOGLE_APPLICATION_CREDENTIALS": bool(os.getenv("GOOGLE_APPLICATION_CREDENTIALS"))
        },
        "auth_test": "Firebase auth initialized"
    }

@app.get("/debug/auth")
async def debug_auth():
    """Debug endpoint to test authentication"""
    try:
        # Test creating a test user
        test_user = auth.create_user(
            email="test@example.com",
            password="testpass123"
        )
        auth.delete_user(test_user.uid)  # Clean up
        return {"auth_status": "working", "message": "Firebase Auth is functional"}
    except Exception as e:
        return {"auth_status": "error", "error": str(e)}

@app.get("/debug/token")
async def debug_token(current_user = Depends(get_current_user)):
    """Debug endpoint to test token validation"""
    return {
        "message": "Token is valid",
        "user_id": current_user['id'],
        "user_name": current_user['name']
    }

@app.get("/debug/headers")
async def debug_headers(request: Request):
    """Debug endpoint to check request headers"""
    return {
        "headers": dict(request.headers),
        "authorization": request.headers.get("authorization", "Not found")
    }

@app.get("/debug/drive")
async def debug_drive():
    """Debug endpoint to test Google Drive service"""
    try:
        if not google_drive_service.service:
            return {"status": "error", "message": "Google Drive service not initialized"}
        
        # Try to list files to test the service
        results = google_drive_service.service.files().list(pageSize=1).execute()
        return {
            "status": "success", 
            "message": "Google Drive service is working",
            "files_count": len(results.get('files', []))
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://widechatapp.web.app", "https://widechatmessage.web.app", "https://widechat.onrender.com", "https://widechat-q4g3.onrender.com", "http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:5173", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Socket.IO
sio = socketio.AsyncServer(
    cors_allowed_origins="*",
    async_mode='asgi'
)
socket_app = socketio.ASGIApp(sio, app)

# Online users tracking
online_users = {}
user_sessions = {}

# Auth routes
@app.post("/auth/register")
async def register(user_data: UserCreate):
    try:
        # Create Firebase Auth user
        firebase_user = auth.create_user(
            email=user_data.email,
            password=user_data.password,
            display_name=user_data.name
        )
        
        # Create user folder in Google Drive
        try:
            folder_id = google_drive_service.create_user_folder(user_data.email)
        except Exception as drive_error:
            print(f"Failed to create Drive folder: {drive_error}")
            folder_id = None
        
        # Create user in Firestore
        user_doc = {
            "email": user_data.email,
            "name": user_data.name,
            "profile_image_url": None,
            "status_message": "Available",
            "is_online": True,
            "invite_code": secrets.token_urlsafe(12),
            "connections": [],
            "drive_folder_id": folder_id
        }
        
        db.collection('users').document(firebase_user.uid).set(user_doc)
        
        # Generate custom token
        custom_token = auth.create_custom_token(firebase_user.uid)
        
        return {
            "custom_token": custom_token.decode('utf-8'),
            "user": {"id": firebase_user.uid, "name": user_data.name, "email": user_data.email}
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/auth/login")
async def login(user_data: UserLogin):
    try:
        # Get user by email from Firestore
        users_query = db.collection('users').where('email', '==', user_data.email).limit(1)
        users = users_query.stream()
        
        user_doc = None
        for user in users:
            user_doc = user
            break
        
        if not user_doc:
            raise HTTPException(status_code=401, detail="Invalid credentials")
        
        user_data_dict = user_doc.to_dict()
        user_data_dict['id'] = user_doc.id
        
        # Create custom token for the user
        custom_token = auth.create_custom_token(user_doc.id)
        
        return {
            "custom_token": custom_token.decode('utf-8'),
            "user": {
                "id": user_data_dict['id'],
                "name": user_data_dict['name'],
                "email": user_data_dict['email']
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"Login error: {str(e)}")
        raise HTTPException(status_code=500, detail="Login failed")

@app.get("/users/me")
async def get_me(current_user = Depends(get_current_user)):
    return {
        "id": current_user['id'], 
        "name": current_user['name'], 
        "email": current_user['email'], 
        "status_message": current_user['status_message'],
        "profile_image_url": current_user['profile_image_url'],
        "invite_code": current_user.get('invite_code', ''),
        "connections_count": len(current_user.get('connections', []))
    }

@app.get("/users/qr")
async def get_qr_code(current_user = Depends(get_current_user)):
    """Generate QR code for user's invite code"""
    invite_code = current_user.get('invite_code')
    if not invite_code:
        raise HTTPException(status_code=404, detail="Invite code not found")
    
    # Create QR code with web link
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(f"https://widechatapp.web.app/?invite={invite_code}")
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    buffer = BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)
    
    img_str = base64.b64encode(buffer.getvalue()).decode()
    return {"qr_code": f"data:image/png;base64,{img_str}"}

@app.put("/users/invite-code")
async def update_invite_code(invite_data: dict, current_user = Depends(get_current_user)):
    """Update user's custom invite code"""
    new_invite_code = invite_data.get('invite_code', '').strip()
    
    if not new_invite_code:
        raise HTTPException(status_code=400, detail="Invite code cannot be empty")
    
    if len(new_invite_code) < 3 or len(new_invite_code) > 20:
        raise HTTPException(status_code=400, detail="Invite code must be between 3-20 characters")
    
    # Check if invite code already exists (excluding current user)
    users_query = db.collection('users').where('invite_code', '==', new_invite_code).limit(1)
    existing_users = list(users_query.stream())
    
    if existing_users and existing_users[0].id != current_user['id']:
        raise HTTPException(status_code=409, detail="Invite code already taken")
    
    # Update user's invite code (keep existing connections intact)
    user_ref = db.collection('users').document(current_user['id'])
    user_ref.update({'invite_code': new_invite_code})
    
    return {"message": "Invite code updated successfully", "invite_code": new_invite_code}

@app.get("/users/connections")
async def get_connections(current_user = Depends(get_current_user)):
    """Get user connections"""
    try:
        print(f"Getting connections for user: {current_user['id']}")
        
        if not current_user:
            raise HTTPException(status_code=401, detail="Authentication required")
            
        connections = current_user.get('connections', [])
        print(f"User has {len(connections)} connections")
        
        connected_users = []
        for conn_id in connections:
            try:
                user_doc = db.collection('users').document(conn_id).get()
                if user_doc.exists:
                    user_data = user_doc.to_dict()
                    user_data['id'] = user_doc.id
                    
                    # Format last seen
                    if user_data.get('is_online'):
                        last_seen_formatted = 'online'
                    else:
                        last_seen_formatted = format_last_seen(user_data.get('last_seen'))
                    
                    # Get last message - simplified query without ordering to avoid index requirement
                    messages_query = db.collection('messages').where('participants', 'array_contains', current_user['id'])
                    messages = messages_query.stream()
                    
                    last_message = None
                    latest_timestamp = None
                    
                    for msg in messages:
                        msg_data = msg.to_dict()
                        # Check if this message is between current user and connection
                        if ((msg_data.get('sender_id') == current_user['id'] and msg_data.get('receiver_id') == conn_id) or \
                           (msg_data.get('sender_id') == conn_id and msg_data.get('receiver_id') == current_user['id'])):
                            
                            msg_timestamp = msg_data.get('timestamp')
                            if msg_timestamp and (latest_timestamp is None or msg_timestamp > latest_timestamp):
                                latest_timestamp = msg_timestamp
                                last_message = {
                                    "text": msg_data['message_text'],
                                    "timestamp": msg_data['timestamp'],
                                    "type": msg_data['message_type'],
                                    "sender_id": msg_data['sender_id']
                                }
                    
                    connected_users.append({
                        "id": user_data['id'],
                        "name": user_data['name'],
                        "email": user_data['email'],
                        "is_online": user_data.get('is_online', False),
                        "last_seen": user_data.get('last_seen'),
                        "last_seen_formatted": last_seen_formatted,
                        "last_message": last_message
                    })
                else:
                    print(f"Connection user {conn_id} not found - removing from connections")
                    # Remove invalid connection from user's connections list
                    current_user_ref = db.collection('users').document(current_user['id'])
                    current_connections = current_user.get('connections', [])
                    if conn_id in current_connections:
                        current_connections.remove(conn_id)
                        current_user_ref.update({'connections': current_connections})
            except Exception as conn_error:
                print(f"Error processing connection {conn_id}: {str(conn_error)}")
                continue
        
        print(f"Returning {len(connected_users)} connected users")
        return connected_users
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in get_connections: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch connections")

@app.put("/users/me")
async def update_profile(profile_data: dict, current_user = Depends(get_current_user)):
    """Update user profile"""
    user_ref = db.collection('users').document(current_user['id'])
    
    update_data = {}
    if 'name' in profile_data:
        update_data['name'] = profile_data['name']
    if 'status_message' in profile_data:
        update_data['status_message'] = profile_data['status_message']
    if 'profile_image_url' in profile_data:
        update_data['profile_image_url'] = profile_data['profile_image_url']
    
    if update_data:
        user_ref.update(update_data)
    
    return {"message": "Profile updated successfully"}

@app.get("/users")
async def get_users(current_user = Depends(get_current_user)):
    """This endpoint is now deprecated - use /users/connections instead"""
    return await get_connections(current_user)

# Chat request system
@app.post("/chat-requests/send")
async def send_chat_request(request_data: dict, current_user = Depends(get_current_user)):
    """Send a chat request using invite code"""
    invite_code = request_data.get('invite_code')
    message = request_data.get('message', "Hi! I'd like to connect with you.")
    
    # Find user by invite code
    users_query = db.collection('users').where('invite_code', '==', invite_code).limit(1)
    users = users_query.stream()
    
    target_user = None
    for user_doc in users:
        target_user = user_doc.to_dict()
        target_user['id'] = user_doc.id
        break
    
    if not target_user:
        raise HTTPException(status_code=404, detail="Invalid invite code")
    
    if target_user['id'] == current_user['id']:
        raise HTTPException(status_code=400, detail="Cannot send request to yourself")
    
    # Check if already connected
    if current_user['id'] in target_user.get('connections', []):
        raise HTTPException(status_code=400, detail="Already connected")
    
    # Create chat request
    request_doc = {
        "sender_id": current_user['id'],
        "receiver_id": target_user['id'],
        "message": message,
        "status": "pending",
        "created_at": firestore.SERVER_TIMESTAMP
    }
    
    doc_ref = db.collection('chat_requests').add(request_doc)
    request_id = doc_ref[1].id
    
    # Emit to target user
    await sio.emit("chat_request", {
        "id": request_id,
        "sender": {"id": current_user['id'], "name": current_user['name']},
        "message": message
    }, room=f"user_{target_user['id']}")
    
    return {"message": "Chat request sent"}



# Chat routes
@app.get("/chats/{user_id}")
async def get_chats(user_id: str, current_user = Depends(get_current_user)):
    # Use simple query without ordering to avoid index requirement
    messages_query = db.collection('messages').where('participants', 'array_contains', current_user['id'])
    messages = messages_query.stream()
    
    user_chats = []
    for msg in messages:
        msg_data = msg.to_dict()
        if (msg_data.get('sender_id') == current_user['id'] and msg_data.get('receiver_id') == user_id) or \
           (msg_data.get('sender_id') == user_id and msg_data.get('receiver_id') == current_user['id']):
            msg_data['id'] = msg.id
            user_chats.append(msg_data)
    
    # Sort by timestamp in Python
    user_chats.sort(key=lambda x: x.get('timestamp', datetime.min))
    return user_chats

@app.post("/chats/send")
async def send_message(message_data: MessageSend, current_user = Depends(get_current_user)):
    # Check if users are connected
    receiver_doc = db.collection('users').document(message_data.receiver_id).get()
    if not receiver_doc.exists:
        raise HTTPException(status_code=404, detail="User not found")
    
    receiver_data = receiver_doc.to_dict()
    if current_user['id'] not in receiver_data.get('connections', []):
        raise HTTPException(status_code=403, detail="Not authorized to message this user")
    
    # Create message with UTC timestamp
    message_doc = {
        "sender_id": current_user['id'],
        "receiver_id": message_data.receiver_id,
        "message_text": message_data.message_text,
        "timestamp": firestore.SERVER_TIMESTAMP,
        "status": "sent",
        "message_type": message_data.message_type,
        "file_url": message_data.file_url,
        "participants": [current_user['id'], message_data.receiver_id],
        "starred_by": [],
        "forwarded": False,
        "reply_to_id": message_data.reply_to_id,
        "caption": message_data.caption,
        "edited": False
    }
    
    doc_ref = db.collection('messages').add(message_doc)
    message_id = doc_ref[1].id
    
    # Emit to socket with UTC timestamp
    current_timestamp = datetime.utcnow()
    message_payload = {
        "id": message_id,
        "sender_id": current_user['id'],
        "receiver_id": message_data.receiver_id,
        "message_text": message_data.message_text,
        "timestamp": current_timestamp.isoformat() + 'Z',
        "message_type": message_data.message_type,
        "file_url": message_data.file_url,
        "caption": message_data.caption,
        "sender_name": current_user['name']
    }
    
    # Emit to receiver only
    await sio.emit("new_message", message_payload, room=f"user_{message_data.receiver_id}")
    
    return {"id": message_id, "message": "Message sent"}

# Message reactions
@app.post("/messages/{message_id}/react")
async def react_to_message(message_id: str, reaction: MessageReaction, current_user = Depends(get_current_user)):
    # Remove existing reaction from this user
    reactions_query = db.collection('reactions').where('message_id', '==', message_id).where('user_id', '==', current_user['id'])
    existing_reactions = reactions_query.stream()
    for doc in existing_reactions:
        doc.reference.delete()
    
    # Add new reaction
    new_reaction = {
        "message_id": message_id,
        "user_id": current_user['id'],
        "emoji": reaction.emoji,
        "timestamp": firestore.SERVER_TIMESTAMP
    }
    db.collection('reactions').add(new_reaction)
    
    return {"message": "Reaction added"}

# Message editing
@app.put("/messages/{message_id}")
async def edit_message(message_id: str, new_text: str, current_user = Depends(get_current_user)):
    message_ref = db.collection('messages').document(message_id)
    message_doc = message_ref.get()
    
    if message_doc.exists and message_doc.to_dict().get('sender_id') == current_user['id']:
        message_ref.update({
            'message_text': new_text,
            'edited': True,
            'edited_at': firestore.SERVER_TIMESTAMP
        })
        return {"message": "Message edited"}
    
    raise HTTPException(status_code=404, detail="Message not found or unauthorized")

# Message deletion
@app.delete("/messages/{message_id}")
async def delete_message(message_id: str, current_user = Depends(get_current_user)):
    message_ref = db.collection('messages').document(message_id)
    message_doc = message_ref.get()
    
    if message_doc.exists and message_doc.to_dict().get('sender_id') == current_user['id']:
        message_ref.delete()
        return {"message": "Message deleted"}
    
    raise HTTPException(status_code=404, detail="Message not found or unauthorized")

# Status updates
@app.post("/status")
async def create_status(status: StatusUpdate, current_user = Depends(get_current_user)):
    new_status = {
        "user_id": current_user['id'],
        "content": status.content,
        "media_url": status.media_url,
        "status_type": status.status_type,
        "timestamp": firestore.SERVER_TIMESTAMP,
        "expires_at": datetime.utcnow() + timedelta(hours=24),
        "views": []
    }
    doc_ref = db.collection('statuses').add(new_status)
    
    return {"id": doc_ref[1].id, "message": "Status created"}

@app.get("/status")
async def get_statuses(current_user = Depends(get_current_user)):
    # Get active statuses (not expired)
    now = datetime.utcnow()
    statuses_query = db.collection('statuses').where('expires_at', '>', now)
    statuses = statuses_query.stream()
    
    # Group by user
    user_statuses = {}
    for status_doc in statuses:
        status_data = status_doc.to_dict()
        status_data['id'] = status_doc.id
        
        user_doc = db.collection('users').document(status_data['user_id']).get()
        if user_doc.exists:
            user_data = user_doc.to_dict()
            user_id = status_data['user_id']
            
            if user_id not in user_statuses:
                user_statuses[user_id] = {
                    "user": {"id": user_id, "name": user_data['name']},
                    "statuses": []
                }
            user_statuses[user_id]['statuses'].append(status_data)
    
    return list(user_statuses.values())

# File upload
@app.post("/upload")
async def upload_file(file: UploadFile = File(...), current_user = Depends(get_current_user)):
    try:
        print(f"Upload request from user: {current_user['id']}")
        print(f"File: {file.filename}, Content-Type: {file.content_type}, Size: {file.size if hasattr(file, 'size') else 'unknown'}")
        
        # Validate file
        if not file.filename:
            raise HTTPException(status_code=400, detail="No file provided")
        
        # Read file content
        content = await file.read()
        print(f"File content read: {len(content)} bytes")
        
        if len(content) == 0:
            raise HTTPException(status_code=400, detail="Empty file")
        
        # Generate unique filename
        timestamp = datetime.utcnow().timestamp()
        filename = f"{timestamp}_{file.filename}"
        
        # Upload to user's Google Drive folder
        print("Uploading to Google Drive...")
        if not google_drive_service.service:
            raise HTTPException(status_code=503, detail="Google Drive service not available")
        
        # Get user's drive folder ID
        folder_id = current_user.get('drive_folder_id')
        
        file_url = await google_drive_service.upload_file(
            content, filename, file.content_type or 'application/octet-stream', folder_id
        )
        print(f"Google Drive upload successful: {file_url}")
        
        # Determine file type
        file_extension = file.filename.split('.')[-1].lower() if '.' in file.filename else ''
        if file_extension in ['jpg', 'jpeg', 'png', 'gif', 'webp', 'svg']:
            file_type = 'image'
        elif file_extension in ['mp4', 'avi', 'mov', 'wmv', 'flv', 'webm']:
            file_type = 'video'
        elif file_extension in ['mp3', 'wav', 'ogg', 'm4a', 'aac']:
            file_type = 'audio'
        else:
            file_type = 'file'
        
        return {
            "file_url": file_url,
            "filename": file.filename,
            "file_type": file_type
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"Upload error: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

# Call routes
@app.post("/calls/initiate")
async def initiate_call(call_data: dict, current_user = Depends(get_current_user)):
    receiver_id = call_data.get('receiver_id')
    
    # Get receiver details
    receiver_doc = db.collection('users').document(receiver_id).get()
    if not receiver_doc.exists:
        raise HTTPException(status_code=404, detail="User not found")
    
    receiver_data = receiver_doc.to_dict()
    
    # Use datetime for socket emission, SERVER_TIMESTAMP for database
    current_time = datetime.utcnow()
    
    call_db = {
        "caller_id": current_user['id'],
        "receiver_id": receiver_id,
        "call_type": call_data.get('call_type', 'voice'),
        "caller_name": current_user['name'],
        "receiver_name": receiver_data['name'],
        "status": "ringing",
        "started_at": firestore.SERVER_TIMESTAMP,
        "participants": [current_user['id'], receiver_id]
    }
    doc_ref = db.collection('calls').add(call_db)
    call_id = doc_ref[1].id
    
    # Create serializable call object for socket emission
    call_socket = {
        "id": call_id,
        "caller_id": current_user['id'],
        "receiver_id": receiver_id,
        "call_type": call_data.get('call_type', 'voice'),
        "caller_name": current_user['name'],
        "receiver_name": receiver_data['name'],
        "status": "ringing",
        "started_at": current_time.isoformat(),
        "participants": [current_user['id'], receiver_id]
    }
    
    print(f"Emitting incoming_call to user_{receiver_id}: {call_socket}")
    await sio.emit("incoming_call", call_socket, room=f"user_{receiver_id}")
    
    return {"call_id": call_id, "status": "initiated", "call": call_socket}

@app.post("/calls/respond")
async def respond_to_call(response_data: dict, current_user = Depends(get_current_user)):
    call_id = response_data.get('call_id')
    action = response_data.get('action')
    
    call_ref = db.collection('calls').document(call_id)
    call_doc = call_ref.get()
    
    if call_doc.exists:
        call_data = call_doc.to_dict()
        update_data = {'status': action}
        
        if action == 'accept':
            update_data['accepted_at'] = firestore.SERVER_TIMESTAMP
        elif action == 'end':
            update_data['ended_at'] = firestore.SERVER_TIMESTAMP
        
        call_ref.update(update_data)
        
        # Emit response to caller
        target_user = call_data['caller_id'] if call_data['receiver_id'] == current_user['id'] else call_data['receiver_id']
        await sio.emit('call_response', {
            'call_id': call_id,
            'action': action
        }, room=f"user_{target_user}")
    
    return {"message": f"Call {action}"}

@app.get("/calls/history")
async def get_call_history(current_user = Depends(get_current_user)):
    # Use simple query without ordering to avoid index requirement
    calls_query = db.collection('calls').where('participants', 'array_contains', current_user['id'])
    calls = calls_query.stream()
    
    user_calls = []
    for call_doc in calls:
        call_data = call_doc.to_dict()
        call_data['id'] = call_doc.id
        user_calls.append(call_data)
    
    # Sort by started_at in Python
    user_calls.sort(key=lambda x: x.get('started_at', datetime.min), reverse=True)
    return user_calls

# ==================== CHAT MANAGEMENT ====================
@app.post("/chats/{chat_id}/pin")
async def pin_chat(chat_id: str, current_user = Depends(get_current_user)):
    # Check if already pinned
    pinned_query = db.collection('pinned_chats').where('user_id', '==', current_user['id']).where('chat_id', '==', chat_id)
    existing = list(pinned_query.stream())
    
    if not existing:
        pinned_chat = {
            "user_id": current_user['id'],
            "chat_id": chat_id,
            "pinned_at": firestore.SERVER_TIMESTAMP
        }
        db.collection('pinned_chats').add(pinned_chat)
    
    return {"message": "Chat pinned"}

@app.delete("/chats/{chat_id}/pin")
async def unpin_chat(chat_id: str, current_user = Depends(get_current_user)):
    pinned_query = db.collection('pinned_chats').where('user_id', '==', current_user['id']).where('chat_id', '==', chat_id)
    docs = pinned_query.stream()
    for doc in docs:
        doc.reference.delete()
    return {"message": "Chat unpinned"}

@app.post("/chats/{chat_id}/archive")
async def archive_chat(chat_id: str, current_user = Depends(get_current_user)):
    # Check if already archived
    archived_query = db.collection('archived_chats').where('user_id', '==', current_user['id']).where('chat_id', '==', chat_id)
    existing = list(archived_query.stream())
    
    if not existing:
        archived_chat = {
            "user_id": current_user['id'],
            "chat_id": chat_id,
            "archived_at": firestore.SERVER_TIMESTAMP
        }
        db.collection('archived_chats').add(archived_chat)
    
    return {"message": "Chat archived"}

@app.delete("/chats/{chat_id}/archive")
async def unarchive_chat(chat_id: str, current_user = Depends(get_current_user)):
    archived_query = db.collection('archived_chats').where('user_id', '==', current_user['id']).where('chat_id', '==', chat_id)
    docs = archived_query.stream()
    for doc in docs:
        doc.reference.delete()
    return {"message": "Chat unarchived"}

@app.delete("/chats/{chat_id}/clear")
async def clear_chat_history(chat_id: str, current_user = Depends(get_current_user)):
    # Delete messages between current user and chat_id - use simple query
    messages_query = db.collection('messages').where('participants', 'array_contains', current_user['id'])
    messages = messages_query.stream()
    
    for msg_doc in messages:
        msg_data = msg_doc.to_dict()
        if (msg_data.get('sender_id') == current_user['id'] and msg_data.get('receiver_id') == chat_id) or \
           (msg_data.get('sender_id') == chat_id and msg_data.get('receiver_id') == current_user['id']):
            msg_doc.reference.delete()
    
    return {"message": "Chat history cleared"}

# ==================== MESSAGE FEATURES ====================
@app.post("/messages/{message_id}/star")
async def star_message(message_id: str, current_user = Depends(get_current_user)):
    message_ref = db.collection('messages').document(message_id)
    message_doc = message_ref.get()
    
    if message_doc.exists:
        message_data = message_doc.to_dict()
        starred_by = message_data.get('starred_by', [])
        
        if current_user['id'] not in starred_by:
            starred_by.append(current_user['id'])
            message_ref.update({'starred_by': starred_by})
    
    return {"message": "Message starred"}

@app.delete("/messages/{message_id}/star")
async def unstar_message(message_id: str, current_user = Depends(get_current_user)):
    message_ref = db.collection('messages').document(message_id)
    message_doc = message_ref.get()
    
    if message_doc.exists:
        message_data = message_doc.to_dict()
        starred_by = message_data.get('starred_by', [])
        
        if current_user['id'] in starred_by:
            starred_by.remove(current_user['id'])
            message_ref.update({'starred_by': starred_by})
    
    return {"message": "Message unstarred"}

@app.get("/messages/starred")
async def get_starred_messages(current_user = Depends(get_current_user)):
    messages_query = db.collection('messages').where('starred_by', 'array_contains', current_user['id'])
    messages = messages_query.stream()
    
    starred_messages = []
    for msg_doc in messages:
        msg_data = msg_doc.to_dict()
        msg_data['id'] = msg_doc.id
        starred_messages.append(msg_data)
    
    return starred_messages

@app.post("/messages/{message_id}/forward")
async def forward_message(message_id: str, recipient_ids: List[str], current_user = Depends(get_current_user)):
    # Get original message
    original_msg_ref = db.collection('messages').document(message_id)
    original_msg_doc = original_msg_ref.get()
    
    if not original_msg_doc.exists:
        raise HTTPException(status_code=404, detail="Message not found")
    
    original_message = original_msg_doc.to_dict()
    forwarded_count = 0
    
    for recipient_id in recipient_ids:
        forwarded_message = {
            "sender_id": current_user['id'],
            "receiver_id": recipient_id,
            "message_text": original_message['message_text'],
            "timestamp": firestore.SERVER_TIMESTAMP,
            "status": "sent",
            "message_type": original_message['message_type'],
            "file_url": original_message.get('file_url'),
            "forwarded": True,
            "original_sender_id": original_message['sender_id'],
            "starred_by": [],
            "edited": False,
            "participants": [current_user['id'], recipient_id]
        }
        
        doc_ref = db.collection('messages').add(forwarded_message)
        forwarded_count += 1
        
        # Emit to socket
        await sio.emit("new_message", {
            "id": doc_ref[1].id,
            "sender_id": forwarded_message['sender_id'],
            "receiver_id": recipient_id,
            "message_text": forwarded_message['message_text'],
            "timestamp": get_indian_time().isoformat(),
            "message_type": forwarded_message['message_type'],
            "forwarded": True,
            "sender_name": current_user['name']
        }, room=f"user_{recipient_id}")
    
    return {"message": f"Message forwarded to {forwarded_count} recipients"}

# ==================== BROADCAST FEATURES ====================
@app.post("/broadcasts/create")
async def create_broadcast(broadcast_data: BroadcastCreate, current_user = Depends(get_current_user)):
    broadcast = {
        "name": broadcast_data.name,
        "owner_id": current_user['id'],
        "recipient_ids": broadcast_data.recipient_ids,
        "created_at": firestore.SERVER_TIMESTAMP
    }
    doc_ref = db.collection('broadcasts').add(broadcast)
    
    return {"id": doc_ref[1].id, "message": "Broadcast list created"}

@app.get("/broadcasts")
async def get_broadcasts(current_user = Depends(get_current_user)):
    broadcasts_query = db.collection('broadcasts').where('owner_id', '==', current_user['id'])
    broadcasts = broadcasts_query.stream()
    
    user_broadcasts = []
    for broadcast_doc in broadcasts:
        broadcast_data = broadcast_doc.to_dict()
        broadcast_data['id'] = broadcast_doc.id
        user_broadcasts.append(broadcast_data)
    
    return user_broadcasts

@app.post("/broadcasts/{broadcast_id}/send")
async def send_broadcast_message(broadcast_id: str, message_data: BroadcastMessage, current_user = Depends(get_current_user)):
    # Get broadcast
    broadcast_ref = db.collection('broadcasts').document(broadcast_id)
    broadcast_doc = broadcast_ref.get()
    
    if not broadcast_doc.exists or broadcast_doc.to_dict().get('owner_id') != current_user['id']:
        raise HTTPException(status_code=404, detail="Broadcast not found")
    
    broadcast = broadcast_doc.to_dict()
    sent_count = 0
    
    for recipient_id in broadcast['recipient_ids']:
        message = {
            "sender_id": current_user['id'],
            "receiver_id": recipient_id,
            "message_text": message_data.message_text,
            "timestamp": firestore.SERVER_TIMESTAMP,
            "status": "sent",
            "message_type": message_data.message_type,
            "file_url": message_data.file_url,
            "broadcast_id": broadcast_id,
            "starred_by": [],
            "edited": False,
            "participants": [current_user['id'], recipient_id]
        }
        
        doc_ref = db.collection('messages').add(message)
        sent_count += 1
        
        # Emit to socket
        await sio.emit("new_message", {
            "id": doc_ref[1].id,
            "sender_id": message['sender_id'],
            "receiver_id": recipient_id,
            "message_text": message['message_text'],
            "timestamp": get_indian_time().isoformat(),
            "message_type": message['message_type'],
            "broadcast_id": broadcast_id,
            "sender_name": current_user['name']
        }, room=f"user_{recipient_id}")
    
    return {"message": f"Broadcast sent to {sent_count} recipients"}

# ==================== USER BLOCKING ====================
@app.post("/users/block")
async def block_user(user_data: dict, current_user = Depends(get_current_user)):
    user_id = user_data.get('user_id')
    
    # Check if already blocked
    blocked_query = db.collection('blocked_users').where('blocker_id', '==', current_user['id']).where('blocked_id', '==', user_id)
    existing = list(blocked_query.stream())
    
    if not existing:
        blocked_user = {
            "blocker_id": current_user['id'],
            "blocked_id": user_id,
            "blocked_at": firestore.SERVER_TIMESTAMP
        }
        db.collection('blocked_users').add(blocked_user)
    
    return {"message": "User blocked"}

@app.delete("/users/block/{user_id}")
async def unblock_user(user_id: str, current_user = Depends(get_current_user)):
    blocked_query = db.collection('blocked_users').where('blocker_id', '==', current_user['id']).where('blocked_id', '==', user_id)
    docs = blocked_query.stream()
    for doc in docs:
        doc.reference.delete()
    return {"message": "User unblocked"}

@app.get("/users/blocked")
async def get_blocked_users(current_user = Depends(get_current_user)):
    blocked_query = db.collection('blocked_users').where('blocker_id', '==', current_user['id'])
    blocked_docs = blocked_query.stream()
    
    user_blocked = []
    for blocked_doc in blocked_docs:
        blocked_data = blocked_doc.to_dict()
        
        # Get user details
        user_doc = db.collection('users').document(blocked_data['blocked_id']).get()
        if user_doc.exists:
            user_data = user_doc.to_dict()
            user_blocked.append({
                "id": user_data['id'] if 'id' in user_data else blocked_data['blocked_id'],
                "name": user_data['name'],
                "email": user_data['email'],
                "blocked_at": blocked_data['blocked_at']
            })
    
    return user_blocked

# ==================== NOTIFICATIONS ====================
@app.get("/notifications")
async def get_notifications(current_user = Depends(get_current_user)):
    # Use simple query without ordering to avoid index requirement
    notifications_query = db.collection('notifications').where('user_id', '==', current_user['id'])
    notifications = notifications_query.stream()
    
    user_notifications = []
    for notification_doc in notifications:
        notification_data = notification_doc.to_dict()
        notification_data['id'] = notification_doc.id
        user_notifications.append(notification_data)
    
    # Sort by created_at in Python
    user_notifications.sort(key=lambda x: x.get('created_at', datetime.min), reverse=True)
    return user_notifications

@app.put("/notifications/{notification_id}/read")
async def mark_notification_read(notification_id: str, current_user = Depends(get_current_user)):
    notification_ref = db.collection('notifications').document(notification_id)
    notification_doc = notification_ref.get()
    
    if notification_doc.exists and notification_doc.to_dict().get('user_id') == current_user['id']:
        notification_ref.update({
            'read': True,
            'read_at': firestore.SERVER_TIMESTAMP
        })
        return {"message": "Notification marked as read"}
    
    raise HTTPException(status_code=404, detail="Notification not found")

@app.delete("/notifications/{notification_id}")
async def delete_notification(notification_id: str, current_user = Depends(get_current_user)):
    notification_ref = db.collection('notifications').document(notification_id)
    notification_doc = notification_ref.get()
    
    if notification_doc.exists and notification_doc.to_dict().get('user_id') == current_user['id']:
        notification_ref.delete()
        return {"message": "Notification deleted"}
    
    raise HTTPException(status_code=404, detail="Notification not found")



# ==================== CHAT REQUESTS ====================
@app.get("/chat-requests")
async def get_chat_requests(current_user = Depends(get_current_user)):
    try:
        print(f"Getting chat requests for user: {current_user['id']}")
        
        if not current_user:
            raise HTTPException(status_code=401, detail="Authentication required")
            
        chat_requests_query = db.collection('chat_requests').where('receiver_id', '==', current_user['id']).where('status', '==', 'pending')
        chat_requests = chat_requests_query.stream()
        
        received_requests = []
        for request_doc in chat_requests:
            try:
                request_data = request_doc.to_dict()
                request_data['id'] = request_doc.id
                
                # Get sender details
                sender_doc = db.collection('users').document(request_data['sender_id']).get()
                if sender_doc.exists:
                    sender_data = sender_doc.to_dict()
                    request_data['sender_name'] = sender_data['name']
                    request_data['sender_email'] = sender_data['email']
                    received_requests.append(request_data)
                else:
                    print(f"Sender {request_data['sender_id']} not found")
            except Exception as req_error:
                print(f"Error processing chat request {request_doc.id}: {str(req_error)}")
                continue
        
        print(f"Returning {len(received_requests)} chat requests")
        return received_requests
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in get_chat_requests: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch chat requests")

@app.post("/chat-requests/{request_id}/respond")
async def respond_to_chat_request(request_id: str, response_data: dict, current_user = Depends(get_current_user)):
    action = response_data.get('action')  # 'accept' or 'decline'
    
    request_ref = db.collection('chat_requests').document(request_id)
    request_doc = request_ref.get()
    
    if not request_doc.exists or request_doc.to_dict().get('receiver_id') != current_user['id']:
        raise HTTPException(status_code=404, detail="Request not found")
    
    request_data = request_doc.to_dict()
    
    # Update request status
    request_ref.update({
        'status': 'accepted' if action == 'accept' else 'declined',
        'responded_at': firestore.SERVER_TIMESTAMP
    })
    
    if action == 'accept':
        # Add each user to other's connections
        current_user_ref = db.collection('users').document(current_user['id'])
        sender_ref = db.collection('users').document(request_data['sender_id'])
        
        # Update current user's connections
        current_user_doc = current_user_ref.get()
        if current_user_doc.exists:
            connections = current_user_doc.to_dict().get('connections', [])
            if request_data['sender_id'] not in connections:
                connections.append(request_data['sender_id'])
                current_user_ref.update({'connections': connections})
        
        # Update sender's connections
        sender_doc = sender_ref.get()
        if sender_doc.exists:
            connections = sender_doc.to_dict().get('connections', [])
            if current_user['id'] not in connections:
                connections.append(current_user['id'])
                sender_ref.update({'connections': connections})
    
    # Emit response to sender
    await sio.emit('chat_request_response', {
        'request_id': request_id,
        'action': action,
        'responder_name': current_user['name']
    }, room=f"user_{request_data['sender_id']}")
    
    return {"message": f"Chat request {action}ed"}
@app.delete("/users/me")
async def delete_account(current_user = Depends(get_current_user)):
    """Delete user account"""
    try:
        # Delete user's Google Drive folder
        folder_id = current_user.get('drive_folder_id')
        if folder_id:
            try:
                google_drive_service.delete_user_folder(folder_id)
            except Exception as drive_error:
                print(f"Failed to delete Drive folder: {drive_error}")
        
        # Delete user from Firebase Auth
        auth.delete_user(current_user['id'])
        
        # Delete user document from Firestore
        db.collection('users').document(current_user['id']).delete()
        
        # Delete user's messages
        messages_query = db.collection('messages').where('participants', 'array_contains', current_user['id'])
        messages = messages_query.stream()
        for msg in messages:
            msg.reference.delete()
        
        return {"message": "Account deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting account: {str(e)}")

@app.get("/search")
async def search_messages(q: str, current_user = Depends(get_current_user)):
    # Search in messages - Note: Firestore doesn't support full-text search natively
    # This is a basic implementation - consider using Algolia or Elasticsearch for production
    messages_query = db.collection('messages').where('participants', 'array_contains', current_user['id'])
    messages = messages_query.stream()
    
    message_results = []
    for msg_doc in messages:
        msg_data = msg_doc.to_dict()
        if q.lower() in msg_data.get('message_text', '').lower():
            msg_data['id'] = msg_doc.id
            
            # Get other user details
            other_user_id = msg_data['receiver_id'] if msg_data['sender_id'] == current_user['id'] else msg_data['sender_id']
            other_user_doc = db.collection('users').document(other_user_id).get()
            
            if other_user_doc.exists:
                other_user_data = other_user_doc.to_dict()
                message_results.append({
                    "message": msg_data,
                    "other_user": other_user_data
                })
    
    # Search in users
    users_query = db.collection('users')
    users = users_query.stream()
    
    user_results = []
    for user_doc in users:
        user_data = user_doc.to_dict()
        if user_doc.id != current_user['id'] and \
           (q.lower() in user_data.get('name', '').lower() or q.lower() in user_data.get('email', '').lower()):
            user_data['id'] = user_doc.id
            user_results.append(user_data)
    
    return {"messages": message_results, "users": user_results}

# Group routes
@app.post("/groups/create")
async def create_group(group_data: GroupCreate, current_user = Depends(get_current_user)):
    # Validate group name
    if not group_data.name.strip():
        raise HTTPException(status_code=400, detail="Group name is required")
    
    if len(group_data.name) > 50:
        raise HTTPException(status_code=400, detail="Group name must be 50 characters or less")
    
    if group_data.description and len(group_data.description) > 200:
        raise HTTPException(status_code=400, detail="Description must be 200 characters or less")
    
    # Validate privacy setting
    if group_data.privacy not in ["open", "closed", "secret"]:
        raise HTTPException(status_code=400, detail="Invalid privacy setting")
    
    # Generate invite code for the group
    invite_code = secrets.token_urlsafe(12)
    
    group = {
        "name": group_data.name.strip(),
        "description": group_data.description.strip() if group_data.description else None,
        "privacy": group_data.privacy,
        "invite_code": invite_code,
        "group_image": None,
        "admin_ids": [current_user['id']],
        "member_ids": [current_user['id']] + group_data.member_ids,
        "created_at": firestore.SERVER_TIMESTAMP,
        "created_by": current_user['id']
    }
    
    doc_ref = db.collection('groups').add(group)
    group_id = doc_ref[1].id
    
    # Emit group creation to all members
    for member_id in group['member_ids']:
        await sio.emit('group_created', {
            'group_id': group_id,
            'name': group_data.name,
            'created_by': current_user['name']
        }, room=f"user_{member_id}")
    
    return {
        "id": group_id, 
        "name": group_data.name,
        "privacy": group_data.privacy,
        "invite_code": invite_code,
        "message": "Group created successfully"
    }

@app.get("/groups")
async def get_groups(current_user = Depends(get_current_user)):
    groups_query = db.collection('groups').where('member_ids', 'array_contains', current_user['id'])
    groups = groups_query.stream()
    
    user_groups = []
    for group_doc in groups:
        group_data = group_doc.to_dict()
        group_data['id'] = group_doc.id
        user_groups.append({
            "id": group_data['id'], 
            "name": group_data['name'], 
            "group_image": group_data.get('group_image')
        })
    
    return user_groups

# Socket.IO events
@sio.event
async def connect(sid, environ, auth=None):
    print(f"Client {sid} connected")
    return True

@sio.event
async def disconnect(sid):
    print(f"Client {sid} disconnected")
    user_id = None
    for uid, session_data in user_sessions.items():
        if session_data.get('sid') == sid:
            user_id = uid
            break
    
    if user_id:
        online_users.pop(user_id, None)
        user_sessions.pop(user_id, None)
        await update_user_status(user_id, False)
        
        # Emit user offline status to all connected users
        await sio.emit('user_offline', {
            'user_id': user_id,
            'last_seen': get_indian_time().isoformat() + 'Z'
        }, skip_sid=sid)

@sio.event
async def join_room(sid, data):
    user_id = data.get("user_id")
    if user_id:
        sio.enter_room(sid, f"user_{user_id}")
        # Track online user
        online_users[user_id] = {
            'sid': sid,
            'connected_at': get_indian_time().isoformat() + 'Z'
        }
        user_sessions[user_id] = {'sid': sid}
        await update_user_status(user_id, True)
        
        # Emit user online status to all connected users immediately
        await sio.emit('user_online', {
            'user_id': user_id,
            'timestamp': get_indian_time().isoformat() + 'Z'
        })

@sio.event
async def typing(sid, data):
    receiver_id = data.get('receiver_id')
    if receiver_id:
        await sio.emit("user_typing", data, room=f"user_{receiver_id}")

@sio.event
async def webrtc_signal(sid, data):
    target_user = data.get('target_user')
    signal = data.get('signal')
    call_id = data.get('call_id')
    from_user = data.get('from_user')
    
    if target_user and signal:
        print(f"Relaying WebRTC signal from {from_user} to {target_user} for call {call_id}")
        print(f"Signal type: {signal.get('type', 'unknown')}")
        
        # Relay the signal to the target user
        await sio.emit('webrtc_signal', {
            'signal': signal,
            'call_id': call_id,
            'from_user': from_user,
            'target_user': target_user
        }, room=f"user_{target_user}")
        
        print(f"Signal relayed successfully to user_{target_user}")
    else:
        print(f"Invalid WebRTC signal data: {data}")

@sio.event
async def screen_share_status(sid, data):
    target_user = data.get('target_user')
    is_sharing = data.get('is_sharing')
    call_id = data.get('call_id')
    from_user = data.get('from_user')
    
    if target_user is not None:
        print(f"Relaying screen share status from {from_user} to {target_user} for call {call_id}: {is_sharing}")
        
        # Relay the screen share status to the target user
        await sio.emit('screen_share_status', {
            'is_sharing': is_sharing,
            'call_id': call_id,
            'from_user': from_user,
            'target_user': target_user
        }, room=f"user_{target_user}")
        
        print(f"Screen share status relayed successfully to user_{target_user}")
    else:
        print(f"Invalid screen share status data: {data}")

@sio.event
async def heartbeat(sid, data):
    user_id = data.get('user_id')
    if user_id and user_id in online_users:
        online_users[user_id]['last_heartbeat'] = get_indian_time().isoformat() + 'Z'
        await update_user_status(user_id, True)



if __name__ == "__main__":
    import uvicorn
    uvicorn.run(socket_app, host="0.0.0.0", port=8000, reload=True)

# For Render deployment
app = socket_app
