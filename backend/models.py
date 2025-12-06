from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime

# Auth Models
class CreateUserRequest(BaseModel):
    email: EmailStr
    password: str
    username: str

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

# User Models
class UpdateProfileRequest(BaseModel):
    username: Optional[str] = None
    about: Optional[str] = None
    profilePic: Optional[str] = None

class UserStatusRequest(BaseModel):
    isOnline: bool

# Message Models
class FileData(BaseModel):
    file_id: str
    download_url: str
    file_name: str
    mime_type: str
    file_size: int
    thumbnail_url: Optional[str] = None

class SendMessageRequest(BaseModel):
    chatId: Optional[str] = None
    receiverId: Optional[str] = None
    content: str
    messageType: str = "text"  # text, image, video, audio, document
    fileData: Optional[FileData] = None

class DeleteMessageRequest(BaseModel):
    chatId: str
    messageId: str
    deleteForEveryone: bool = False

class EditMessageRequest(BaseModel):
    chatId: str
    messageId: str
    newContent: str

class MarkReadRequest(BaseModel):
    chatId: str
    messageId: str

# Group Models
class CreateGroupRequest(BaseModel):
    name: str
    description: Optional[str] = ""
    memberIds: List[str]
    groupIcon: Optional[str] = None

class AddGroupMemberRequest(BaseModel):
    groupId: str
    userId: str

# Status Models
class UploadStatusRequest(BaseModel):
    content: Optional[str] = ""
    mediaUrl: Optional[str] = None
    mediaType: str = "text"  # text, image, video

# Response Models
class UserResponse(BaseModel):
    uid: str
    username: str
    email: str
    profilePic: str
    about: str
    isOnline: bool
    lastSeen: datetime

class MessageResponse(BaseModel):
    messageId: str
    senderId: str
    content: str
    messageType: str
    timestamp: datetime
    readBy: List[str]
    isEdited: bool
    isDeleted: bool
    fileUrl: Optional[str] = None
    fileName: Optional[str] = None

class ChatResponse(BaseModel):
    chatId: str
    participants: List[str]
    lastMessage: str
    lastMessageTime: datetime
    messages: List[MessageResponse]

class GroupResponse(BaseModel):
    groupId: str
    name: str
    description: str
    groupIcon: str
    adminId: str
    members: List[str]
    createdAt: datetime
    lastMessage: str
    lastMessageTime: datetime

class StatusResponse(BaseModel):
    statusId: str
    content: str
    mediaUrl: str
    mediaType: str
    timestamp: datetime
    expiresAt: datetime