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
    about_visibility: str = "everyone"
    read_receipts: bool = True
    groups_visibility: str = "everyone"
    public_discovery: bool = True

# Message models
class MessageSend(BaseModel):
    receiver_id: Optional[str] = None
    group_id: Optional[str] = None
    message_text: str
    message_type: str = "text"  # text, image, video, audio, document, location, contact
    reply_to_id: Optional[str] = None
    caption: Optional[str] = None
    file_url: Optional[str] = None
    location_lat: Optional[float] = None
    location_lng: Optional[float] = None
    contact_data: Optional[dict] = None

class MessageReaction(BaseModel):
    message_id: str
    emoji: str

class MessageEdit(BaseModel):
    message_text: str

# Group models
class GroupCreate(BaseModel):
    name: str
    member_ids: List[str] = []
    description: Optional[str] = None
    privacy: str = "open"  # open, closed, secret

class GroupUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    group_image_url: Optional[str] = None

class GroupMemberAction(BaseModel):
    user_id: str
    action: str  # add, remove, promote, demote

# Status models
class StatusUpdate(BaseModel):
    content: str
    media_url: Optional[str] = None
    status_type: str = "text"  # text, image, video

# Call models
class CallInitiate(BaseModel):
    receiver_id: Optional[str] = None
    group_id: Optional[str] = None
    call_type: str  # voice, video

class CallResponse(BaseModel):
    call_id: str
    action: str  # accept, reject, end

# Broadcast models
class BroadcastCreate(BaseModel):
    name: str
    recipient_ids: List[str]

class BroadcastMessage(BaseModel):
    broadcast_id: str
    message_text: str
    message_type: str = "text"
    file_url: Optional[str] = None

# Security models
class TwoFactorSetup(BaseModel):
    password: str

class TwoFactorVerify(BaseModel):
    token: str

class BlockUser(BaseModel):
    user_id: str

# Private messaging models
class ChatRequest(BaseModel):
    invite_code: str
    message: Optional[str] = "Hi! I'd like to connect with you."

class ChatRequestResponse(BaseModel):
    request_id: str
    action: str  # accept, reject
