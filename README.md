# WideChat - Modern WhatsApp-Style Chat Application

A complete chat application built with Python FastAPI backend and Flutter frontend, featuring real-time messaging, file sharing, groups, and status updates.

## 🚀 Features

### Authentication
- ✅ Email signup/login
- ✅ Google Sign-In
- ✅ Username setup
- ✅ User search by username
- ✅ Online/offline status

### Chat System
- ✅ 1-on-1 Chat
- ✅ Real-time messages (Firestore Streams)
- ✅ Typing indicators
- ✅ Last seen status
- ✅ Message read receipts (✓ and ✓✓)
- ✅ Send text, images, videos, documents, audio
- ✅ Voice recording
- ✅ Delete message (for me/everyone)
- ✅ Edit messages
- ✅ Push notifications

### Groups
- ✅ Create groups
- ✅ Add/remove members
- ✅ Group name & icon
- ✅ Group messages
- ✅ Group typing indicators
- ✅ Group read receipts

### Status Feature
- ✅ Upload image/video/text status
- ✅ View others' status
- ✅ 24-hour expiry

### Settings & Profile
- ✅ Profile picture
- ✅ Username & bio
- ✅ Privacy settings
- ✅ Notifications
- ✅ Logout

## 🛠 Tech Stack

### Backend
- **Python** with **FastAPI**
- **Uvicorn** server
- **Firebase Admin SDK** (Firestore)
- **Google Drive API** for file storage
- **Pydantic** for data validation

### Frontend
- **Flutter** with **Riverpod** state management
- **Firebase Auth** & **Firestore**
- **Firebase Messaging** for push notifications
- **Clean Architecture** (domain → data → presentation)
- **Modern gradient UI** with glassmorphism

## 📁 Project Structure

```
WideChat/
├── backend/
│   ├── main.py              # FastAPI app entry point
│   ├── models.py            # Pydantic models
│   ├── config.py            # Configuration settings
│   ├── requirements.txt     # Python dependencies
│   ├── render.yaml          # Render deployment config
│   └── .env.example         # Environment variables template
└── flutter_app/
    ├── lib/
    │   ├── core/            # Core utilities, theme, router
    │   ├── data/            # Data layer
    │   ├── domain/          # Domain layer
    │   ├── presentation/    # UI screens
    │   ├── services/        # Business logic services
    │   └── widgets/         # Reusable UI components
    └── pubspec.yaml         # Flutter dependencies
```

## 🔧 Setup Instructions

### Backend Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd WideChat/backend
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables**
   ```bash
   cp .env.example .env
   ```
   
   Fill in your credentials:
   - `FIREBASE_CREDENTIALS`: Firebase Admin SDK JSON (as string)
   - `GOOGLE_DRIVE_CREDENTIALS`: Google Drive API credentials JSON


4. **Run locally**
   ```bash
   uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```

### Frontend Setup

1. **Navigate to Flutter app**
   ```bash
   cd ../flutter_app
   ```

2. **Install dependencies**
   ```bash
   flutter pub get
   ```

3. **Configure Firebase**
   - Add your `google-services.json` (Android) and `GoogleService-Info.plist` (iOS)
   - Update `ApiConstants.baseUrl` in `lib/core/constants/api_constants.dart`

4. **Run the app**
   ```bash
   flutter run
   ```

## 🚀 Deployment

### Backend Deployment on Render

1. **Create a new Web Service on Render**
2. **Connect your GitHub repository**
3. **Set environment variables:**
   - `FIREBASE_CREDENTIALS`
   - `GOOGLE_DRIVE_CREDENTIALS`
   - `GOOGLE_DRIVE_FOLDER_ID`
4. **Deploy automatically** (Render will use `render.yaml`)

### Frontend Deployment

1. **Build for production:**
   ```bash
   flutter build apk --release  # Android
   flutter build ios --release  # iOS
   ```

2. **Update API endpoint** in `ApiConstants.baseUrl` to your Render URL

## 🔐 Firebase Setup

### Firestore Database Structure

```
users/
  {uid}/
    username: string
    email: string
    profilePic: string
    about: string
    lastSeen: timestamp
    isOnline: boolean
    createdAt: timestamp

chats/
  {chatId}/
    participants: array
    lastMessage: string
    lastMessageTime: timestamp
    createdAt: timestamp
    
    messages/
      {messageId}/
        messageId: string
        senderId: string
        content: string
        messageType: string
        timestamp: timestamp
        readBy: array
        isEdited: boolean
        isDeleted: boolean
        fileUrl?: string
        fileName?: string

groups/
  {groupId}/
    groupId: string
    name: string
    description: string
    groupIcon: string
    adminId: string
    members: array
    createdAt: timestamp
    lastMessage: string
    lastMessageTime: timestamp

status/
  {uid}/
    statuses/
      {statusId}/
        statusId: string
        content: string
        mediaUrl: string
        mediaType: string
        timestamp: timestamp
        expiresAt: timestamp
```

### Security Rules

```javascript
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    // Users can read/write their own data
    match /users/{userId} {
      allow read, write: if request.auth != null && request.auth.uid == userId;
    }
    
    // Chat participants can read/write messages
    match /chats/{chatId} {
      allow read, write: if request.auth != null && 
        request.auth.uid in resource.data.participants;
      
      match /messages/{messageId} {
        allow read, write: if request.auth != null && 
          request.auth.uid in get(/databases/$(database)/documents/chats/$(chatId)).data.participants;
      }
    }
    
    // Group members can read/write
    match /groups/{groupId} {
      allow read, write: if request.auth != null && 
        request.auth.uid in resource.data.members;
    }
    
    // Status visibility
    match /status/{userId} {
      allow read: if request.auth != null;
      allow write: if request.auth != null && request.auth.uid == userId;
    }
  }
}
```

## 🔧 Troubleshooting

### Common Issues

1. **Firebase connection issues**
   - Verify `google-services.json` and `GoogleService-Info.plist` are correctly placed
   - Check Firebase project configuration

2. **Backend API errors**
   - Ensure environment variables are set correctly
   - Verify Firebase Admin SDK credentials
   - Check Google Drive API permissions

3. **File upload failures**
   - Verify Google Drive folder permissions
   - Check file size limits
   - Ensure proper API credentials

4. **Push notifications not working**
   - Verify Firebase Cloud Messaging setup
   - Check device permissions
   - Ensure FCM server key is configured

### Development Tips

1. **Hot reload** works for Flutter UI changes
2. **Backend changes** require server restart
3. **Use Firebase Emulator** for local development
4. **Test on real devices** for push notifications
5. **Monitor Firestore usage** to avoid quota limits

## 📱 App Screenshots

The app features a modern gradient UI with:
- Glassmorphism cards
- Smooth animations
- Chat bubbles with gradients
- Real-time status indicators
- Clean navigation

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License.

## 🆘 Support

For support and questions:
- Create an issue on GitHub
- Check the troubleshooting section
- Review Firebase and Flutter documentation

---

**WideChat** - Connect with friends worldwide! 🌍💬