from fastapi import FastAPI, HTTPException, Depends, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import firebase_admin
from firebase_admin import credentials, firestore, auth
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
import os
from datetime import datetime, timedelta
import uuid
import io
from typing import Optional, List
import json

from models import *
from config import settings

app = FastAPI(title="WideChat API", version="1.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Firebase Admin
firebase_creds = json.loads(settings.FIREBASE_CREDENTIALS)
cred = credentials.Certificate(firebase_creds)
firebase_admin.initialize_app(cred)
db = firestore.client()

# Google Drive
drive_creds_dict = json.loads(settings.GOOGLE_DRIVE_CREDENTIALS)
drive_creds = service_account.Credentials.from_service_account_info(
    drive_creds_dict,
    scopes=['https://www.googleapis.com/auth/drive.file']
)
drive_service = build('drive', 'v3', credentials=drive_creds)

security = HTTPBearer()

async def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        decoded_token = auth.verify_id_token(credentials.credentials)
        return decoded_token['uid']
    except:
        raise HTTPException(status_code=401, detail="Invalid token")

# AUTH ROUTES
@app.post("/auth/createUser")
async def create_user(user_data: CreateUserRequest):
    try:
        user = auth.create_user(
            email=user_data.email,
            password=user_data.password,
            display_name=user_data.username
        )
        
        # Create user document
        db.collection('users').document(user.uid).set({
            'username': user_data.username,
            'email': user_data.email,
            'profilePic': '',
            'about': 'Hey there! I am using WideChat.',
            'lastSeen': datetime.now(),
            'isOnline': True,
            'createdAt': datetime.now()
        })
        
        return {"success": True, "uid": user.uid}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/auth/login")
async def login(login_data: LoginRequest):
    try:
        return {"success": True, "message": "Login handled by Firebase client"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# USER ROUTES
@app.put("/users/updateProfile")
async def update_profile(profile_data: UpdateProfileRequest, uid: str = Depends(verify_token)):
    try:
        update_data = {}
        if profile_data.username:
            update_data['username'] = profile_data.username
        if profile_data.about:
            update_data['about'] = profile_data.about
        if profile_data.profilePic:
            update_data['profilePic'] = profile_data.profilePic
        
        db.collection('users').document(uid).update(update_data)
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/users/search")
async def search_users(username: str, uid: str = Depends(verify_token)):
    try:
        users_ref = db.collection('users')
        query = users_ref.where('username', '>=', username).where('username', '<=', username + '\uf8ff').limit(10)
        users = query.stream()
        
        result = []
        for user in users:
            user_data = user.to_dict()
            if user.id != uid:
                result.append({
                    'uid': user.id,
                    'username': user_data.get('username'),
                    'profilePic': user_data.get('profilePic', ''),
                    'about': user_data.get('about', '')
                })
        
        return {"users": result}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.put("/users/status")
async def update_user_status(status_data: UserStatusRequest, uid: str = Depends(verify_token)):
    try:
        db.collection('users').document(uid).update({
            'isOnline': status_data.isOnline,
            'lastSeen': datetime.now()
        })
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# FILE UPLOAD
def get_or_create_user_folder(user_email: str):
    try:
        # Search for existing folder
        query = f"name='{user_email}' and mimeType='application/vnd.google-apps.folder'"
        results = drive_service.files().list(q=query, fields='files(id, name)').execute()
        folders = results.get('files', [])
        
        if folders:
            return folders[0]['id']
        
        # Create new folder
        folder_metadata = {
            'name': user_email,
            'mimeType': 'application/vnd.google-apps.folder'
        }
        folder = drive_service.files().create(body=folder_metadata, fields='id').execute()
        return folder.get('id')
    except Exception as e:
        raise Exception(f"Failed to create user folder: {e}")

@app.post("/upload/file")
async def upload_file(file: UploadFile = File(...), uid: str = Depends(verify_token)):
    try:
        # Get user email
        user = auth.get_user(uid)
        user_email = user.email
        
        # Get or create user folder
        folder_id = get_or_create_user_folder(user_email)
        
        file_content = await file.read()
        file_size = len(file_content)
        file_extension = file.filename.split('.')[-1] if '.' in file.filename else ''
        unique_filename = f"{uuid.uuid4()}.{file_extension}"
        
        file_metadata = {
            'name': unique_filename,
            'parents': [folder_id]
        }
        
        media = MediaIoBaseUpload(
            io.BytesIO(file_content),
            mimetype=file.content_type,
            resumable=True
        )
        
        uploaded_file = drive_service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id'
        ).execute()
        
        drive_service.permissions().create(
            fileId=uploaded_file['id'],
            body={'role': 'reader', 'type': 'anyone'}
        ).execute()
        
        file_id = uploaded_file['id']
        download_url = f"https://drive.google.com/uc?export=download&id={file_id}"
        thumbnail_url = f"https://drive.google.com/thumbnail?id={file_id}" if file.content_type.startswith('image/') else None
        
        return {
            "success": True,
            "file_id": file_id,
            "download_url": download_url,
            "file_name": file.filename,
            "mime_type": file.content_type,
            "file_size": file_size,
            "thumbnail_url": thumbnail_url
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# MESSAGE ROUTES
@app.post("/messages/send")
async def send_message(message_data: SendMessageRequest, uid: str = Depends(verify_token)):
    try:
        chat_id = message_data.chatId
        if not chat_id:
            participants = sorted([uid, message_data.receiverId])
            chat_id = f"{participants[0]}_{participants[1]}"
            
            db.collection('chats').document(chat_id).set({
                'participants': participants,
                'lastMessage': message_data.content,
                'lastMessageTime': datetime.now(),
                'createdAt': datetime.now()
            })
        
        message_id = str(uuid.uuid4())
        message_doc = {
            'messageId': message_id,
            'senderId': uid,
            'content': message_data.content,
            'messageType': message_data.messageType,
            'timestamp': datetime.now(),
            'readBy': [uid],
            'isEdited': False,
            'isDeleted': False
        }
        
        if message_data.fileData:
            message_doc['file'] = message_data.fileData
        
        db.collection('chats').document(chat_id).collection('messages').document(message_id).set(message_doc)
        
        db.collection('chats').document(chat_id).update({
            'lastMessage': message_data.content,
            'lastMessageTime': datetime.now()
        })
        
        return {"success": True, "chatId": chat_id, "messageId": message_id}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.delete("/messages/delete")
async def delete_message(delete_data: DeleteMessageRequest, uid: str = Depends(verify_token)):
    try:
        message_ref = db.collection('chats').document(delete_data.chatId).collection('messages').document(delete_data.messageId)
        message = message_ref.get()
        
        if not message.exists:
            raise HTTPException(status_code=404, detail="Message not found")
        
        message_data = message.to_dict()
        if message_data['senderId'] != uid:
            raise HTTPException(status_code=403, detail="Not authorized")
        
        if delete_data.deleteForEveryone:
            message_ref.update({'isDeleted': True, 'content': 'This message was deleted'})
        else:
            message_ref.update({f'deletedFor.{uid}': True})
        
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.put("/messages/edit")
async def edit_message(edit_data: EditMessageRequest, uid: str = Depends(verify_token)):
    try:
        message_ref = db.collection('chats').document(edit_data.chatId).collection('messages').document(edit_data.messageId)
        message = message_ref.get()
        
        if not message.exists:
            raise HTTPException(status_code=404, detail="Message not found")
        
        message_data = message.to_dict()
        if message_data['senderId'] != uid:
            raise HTTPException(status_code=403, detail="Not authorized")
        
        message_ref.update({
            'content': edit_data.newContent,
            'isEdited': True,
            'editedAt': datetime.now()
        })
        
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.put("/messages/markRead")
async def mark_message_read(read_data: MarkReadRequest, uid: str = Depends(verify_token)):
    try:
        message_ref = db.collection('chats').document(read_data.chatId).collection('messages').document(read_data.messageId)
        message_ref.update({
            'readBy': firestore.ArrayUnion([uid])
        })
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# GROUP ROUTES
@app.post("/groups/create")
async def create_group(group_data: CreateGroupRequest, uid: str = Depends(verify_token)):
    try:
        group_id = str(uuid.uuid4())
        
        db.collection('groups').document(group_id).set({
            'groupId': group_id,
            'name': group_data.name,
            'description': group_data.description,
            'groupIcon': group_data.groupIcon or '',
            'adminId': uid,
            'members': [uid] + group_data.memberIds,
            'createdAt': datetime.now(),
            'lastMessage': '',
            'lastMessageTime': datetime.now()
        })
        
        return {"success": True, "groupId": group_id}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/groups/addMember")
async def add_group_member(member_data: AddGroupMemberRequest, uid: str = Depends(verify_token)):
    try:
        group_ref = db.collection('groups').document(member_data.groupId)
        group = group_ref.get()
        
        if not group.exists:
            raise HTTPException(status_code=404, detail="Group not found")
        
        group_data = group.to_dict()
        if group_data['adminId'] != uid:
            raise HTTPException(status_code=403, detail="Not authorized")
        
        group_ref.update({
            'members': firestore.ArrayUnion([member_data.userId])
        })
        
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# STATUS ROUTES
@app.post("/status/upload")
async def upload_status(status_data: UploadStatusRequest, uid: str = Depends(verify_token)):
    try:
        status_id = str(uuid.uuid4())
        
        db.collection('status').document(uid).collection('statuses').document(status_id).set({
            'statusId': status_id,
            'content': status_data.content,
            'mediaUrl': status_data.mediaUrl,
            'mediaType': status_data.mediaType,
            'timestamp': datetime.now(),
            'expiresAt': datetime.now() + timedelta(hours=24)
        })
        
        return {"success": True, "statusId": status_id}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/status/view/{user_id}")
async def view_user_status(user_id: str, uid: str = Depends(verify_token)):
    try:
        statuses_ref = db.collection('status').document(user_id).collection('statuses')
        query = statuses_ref.where('expiresAt', '>', datetime.now()).order_by('timestamp', direction=firestore.Query.DESCENDING)
        statuses = query.stream()
        
        result = []
        for status in statuses:
            status_data = status.to_dict()
            result.append({
                'statusId': status.id,
                'content': status_data.get('content', ''),
                'mediaUrl': status_data.get('mediaUrl', ''),
                'mediaType': status_data.get('mediaType', ''),
                'timestamp': status_data.get('timestamp')
            })
        
        return {"statuses": result}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
