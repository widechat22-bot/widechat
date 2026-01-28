from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

# User models
class UserCreate(BaseModel):
    email: str
    password: str
    name: str
    phone: Optional[str] = None

class UserLogin(BaseModel):
    email: str
    password: str

class PhoneLogin(BaseModel):
    phone: str
    otp: str

class ProfileUpdate(BaseModel):
    name: Optional[str] = None
    status_message: Optional[str] = None
    profile_image_url: Optional[str] = None

class PrivacySettings(BaseModel):
    profile_photo_visibility: str = "everyone"  # everyone, contacts, nobody
    last_seen_visibility: str = "everyone"
    status_visibility: str = "everyone"

# Message models
class MessageSend(BaseModel):
    receiver_id: Optional[int] = None
    group_id: Optional[int] = None
    message_text: str
    message_type: str = "text"  # text, image, video, audio, document, location, contact
    reply_to_id: Optional[int] = None
    caption: Optional[str] = None
    file_url: Optional[str] = None
    location_lat: Optional[float] = None
    location_lng: Optional[float] = None
    contact_data: Optional[dict] = None

class MessageReaction(BaseModel):
    message_id: int
    emoji: str

class MessageEdit(BaseModel):
    message_text: str

# Group models
class GroupCreate(BaseModel):
    name: str
    member_ids: List[int]
    description: Optional[str] = None

class GroupUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    group_image_url: Optional[str] = None

class GroupMemberAction(BaseModel):
    user_id: int
    action: str  # add, remove, promote, demote

# Status models
class StatusUpdate(BaseModel):
    content: str
    media_url: Optional[str] = None
    status_type: str = "text"  # text, image, video

# Call models
class CallInitiate(BaseModel):
    receiver_id: Optional[int] = None
    group_id: Optional[int] = None
    call_type: str  # voice, video

class CallResponse(BaseModel):
    call_id: int
    action: str  # accept, reject, end

# Broadcast models
class BroadcastCreate(BaseModel):
    name: str
    recipient_ids: List[int]

class BroadcastMessage(BaseModel):
    broadcast_id: int
    message_text: str
    message_type: str = "text"
    file_url: Optional[str] = None

# Security models
class TwoFactorSetup(BaseModel):
    password: str

class TwoFactorVerify(BaseModel):
    token: str

class BlockUser(BaseModel):
    user_id: int

# Private messaging models
class ChatRequest(BaseModel):
    invite_code: str
    message: Optional[str] = "Hi! I'd like to connect with you."

class ChatRequestResponse(BaseModel):
    request_id: int
    action: str  # accept, reject
