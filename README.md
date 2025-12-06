# WideChat

A modern WhatsApp-like chat application built with Flutter and Firebase.

## Features

- **Authentication**: Email/password and Google Sign-In
- **Real-time Chat**: 1-on-1 and group messaging
- **Media Sharing**: Images, files, and documents via custom backend
- **User Search**: Find users by username
- **Modern UI**: Clean design with purple/blue theme
- **Cross-platform**: Android (iOS ready)

## Tech Stack

- **Frontend**: Flutter 3.x with Riverpod state management
- **Backend**: Firebase (Auth, Firestore) + Custom FastAPI for media
- **Storage**: Google Drive via service account
- **Navigation**: go_router

## Project Structure

```
lib/
├── core/
│   ├── router/          # App routing configuration
│   └── theme/           # App theme and styling
├── data/
│   ├── models/          # Data models (User, Chat, Message)
│   ├── repositories/    # Data repositories
│   └── services/        # Firebase and API services
└── presentation/
    ├── providers/       # Riverpod providers
    ├── screens/         # App screens
    └── widgets/         # Reusable widgets
```

## Setup Instructions

### 1. Firebase Setup

1. Create a new Firebase project
2. Enable Authentication (Email/Password and Google)
3. Create Firestore database
4. Add Android app to Firebase project
5. Download `google-services.json` to `android/app/`
6. Deploy Firestore security rules from `firestore.rules`

### 2. Backend API Setup

Create a FastAPI backend with the following endpoint:

```python
@app.post("/upload")
async def upload_file(
    file: UploadFile,
    authorization: str = Header(...)
):
    # Verify Firebase ID token
    # Upload to Google Drive
    # Return file metadata
    return {
        "file_id": "drive_file_id",
        "download_url": "public_url",
        "filename": "original_name",
        "mime_type": "file_type",
        "size": file_size
    }
```

### 3. Flutter Setup

1. Install Flutter dependencies:
   ```bash
   flutter pub get
   ```

2. Update `lib/data/services/media_service.dart` with your backend URL

3. Run the app:
   ```bash
   flutter run
   ```

## Key Features Implementation

### Authentication Flow
- Splash screen checks auth state
- Login/signup with validation
- Profile setup with unique username
- Auto-navigation based on auth state

### Real-time Chat
- Firestore streams for live updates
- Message status indicators (sent/delivered/seen)
- Typing indicators
- Online/offline status

### Media Handling
- Custom backend integration for file uploads
- Google Drive storage via service account
- Support for images, documents, and files
- Progress indicators and error handling

### User Discovery
- Username-based search
- Profile display with chat initiation
- Duplicate chat prevention

## Firestore Data Structure

### Users Collection
```javascript
users/{uid} {
  uid: string,
  email: string,
  displayName: string,
  username: string,
  about?: string,
  photoUrl?: string,
  isOnline: boolean,
  lastSeen: timestamp,
  fcmToken?: string,
  createdAt: timestamp
}
```

### Chats Collection
```javascript
chats/{chatId} {
  isGroup: boolean,
  members: string[],
  createdAt: timestamp,
  lastMessage?: string,
  lastMessageType?: string,
  lastMessageSenderId?: string,
  lastMessageTime?: timestamp,
  // Group-specific fields
  groupName?: string,
  groupPhotoUrl?: string,
  adminIds?: string[]
}
```

### Messages Subcollection
```javascript
chats/{chatId}/messages/{messageId} {
  from: string,
  to?: string,
  text?: string,
  type: "text" | "image" | "video" | "file" | "audio",
  fileId?: string,
  fileUrl?: string,
  fileName?: string,
  mimeType?: string,
  sentAt: timestamp,
  status: "sent" | "delivered" | "seen",
  replyToMessageId?: string,
  isEdited: boolean,
  deletedForEveryone: boolean
}
```

## Security Rules

The app uses comprehensive Firestore security rules that:
- Allow users to read/write only their own data
- Restrict chat access to members only
- Validate message creation permissions
- Enable user search functionality

## Building for Production

1. Configure Firebase for production
2. Set up proper signing for Android
3. Update backend URL in MediaService
4. Test all authentication flows
5. Deploy Firestore rules

## Future Enhancements

- Voice messages
- Video calls
- Message reactions
- Push notifications
- Message encryption
- Status/Stories feature
- Dark mode toggle
- Message search within chats