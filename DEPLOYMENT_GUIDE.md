# WideChat Deployment Guide

## 🚀 Backend Deployment on Render

### Step 1: Prepare Your Repository
1. Push your code to GitHub
2. Ensure `render.yaml` is in the backend directory
3. Verify `requirements.txt` contains all dependencies

### Step 2: Create Render Account
1. Go to [render.com](https://render.com)
2. Sign up with GitHub
3. Connect your repository

### Step 3: Deploy Backend
1. **Create New Web Service**
   - Click "New +" → "Web Service"
   - Connect your GitHub repository
   - Select the repository containing WideChat

2. **Configure Service**
   ```
   Name: widechat-backend
   Environment: Python 3
   Build Command: pip install -r requirements.txt
   Start Command: uvicorn main:app --host 0.0.0.0 --port $PORT
   ```

3. **Set Environment Variables**
   ```
   FIREBASE_CREDENTIALS={"type":"service_account",...}
   GOOGLE_DRIVE_CREDENTIALS={"type":"service_account",...}
   ```

4. **Deploy**
   - Click "Create Web Service"
   - Wait for deployment (5-10 minutes)
   - Note your app URL: `https://your-app-name.onrender.com`

### Step 4: Verify Deployment
Test your API endpoints:
```bash
curl https://your-app-name.onrender.com/auth/login
```

## 📱 Flutter App Configuration

### Step 1: Update API Endpoint
In `lib/core/constants/api_constants.dart`:
```dart
class ApiConstants {
  static const String baseUrl = 'https://your-app-name.onrender.com';
  // ... rest of the constants
}
```

### Step 2: Firebase Setup
1. **Create Firebase Project**
   - Go to [Firebase Console](https://console.firebase.google.com)
   - Create new project
   - Enable Authentication, Firestore, Cloud Messaging

2. **Add Android App**
   - Package name: `com.widechat`
   - Download `google-services.json`
   - Place in `android/app/`
   - Ensure Google services plugin is configured in build.gradle files

3. **Add iOS App**
   - Bundle ID: `com.widechat`
   - Download `GoogleService-Info.plist`
   - Place in `ios/Runner/`

### Step 3: Build Release APK
```bash
cd flutter_app
flutter clean
flutter pub get
flutter build apk --release
```

The APK will be in `build/app/outputs/flutter-apk/app-release.apk`

## 🔐 Firebase Configuration

### Firestore Security Rules
```javascript
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    match /users/{userId} {
      allow read, write: if request.auth != null && request.auth.uid == userId;
    }
    
    match /chats/{chatId} {
      allow read, write: if request.auth != null && 
        request.auth.uid in resource.data.participants;
      
      match /messages/{messageId} {
        allow read, write: if request.auth != null && 
          request.auth.uid in get(/databases/$(database)/documents/chats/$(chatId)).data.participants;
      }
    }
    
    match /groups/{groupId} {
      allow read, write: if request.auth != null && 
        request.auth.uid in resource.data.members;
    }
    
    match /status/{userId} {
      allow read: if request.auth != null;
      allow write: if request.auth != null && request.auth.uid == userId;
    }
  }
}
```

### Authentication Setup
1. **Enable Email/Password**
   - Go to Authentication → Sign-in method
   - Enable Email/Password

2. **Enable Google Sign-In**
   - Enable Google provider
   - Add your app's SHA-1 fingerprint (Android)

### Cloud Messaging Setup
1. **Generate Server Key**
   - Go to Project Settings → Cloud Messaging
   - Copy Server Key for backend notifications

## 🗄️ Google Drive Setup

### Step 1: Create Service Account
1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create new project or select existing
3. Enable Google Drive API
4. Create Service Account
5. Download JSON credentials

### Step 2: Set Environment Variables
```bash
GOOGLE_DRIVE_CREDENTIALS='{"type":"service_account",...}'
```

Files will be uploaded to Google Drive root directory.

## 🔧 Environment Variables Setup

### Backend (.env file)
```bash
# Firebase Admin SDK
FIREBASE_CREDENTIALS='{"type":"service_account","project_id":"your-project",...}'

# Google Drive API
GOOGLE_DRIVE_CREDENTIALS='{"type":"service_account","project_id":"your-project",...}'

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
```

### Render Environment Variables
Set these in Render dashboard:
- `FIREBASE_CREDENTIALS`
- `GOOGLE_DRIVE_CREDENTIALS`

## 🧪 Testing Deployment

### Backend API Tests
```bash
# Health check
curl https://your-app.onrender.com/

# Test auth endpoint
curl -X POST https://your-app.onrender.com/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"password"}'
```

### Flutter App Tests
1. **Authentication Flow**
   - Test email signup/login
   - Test Google Sign-In
   - Verify user creation in Firestore

2. **Messaging**
   - Send text messages
   - Upload and send images
   - Test real-time updates

3. **File Upload**
   - Test image upload to Google Drive
   - Verify file accessibility

## 🚨 Troubleshooting

### Common Deployment Issues

1. **Render Build Fails**
   ```bash
   # Check requirements.txt
   # Verify Python version compatibility
   # Check for missing dependencies
   ```

2. **Firebase Connection Error**
   ```bash
   # Verify FIREBASE_CREDENTIALS format
   # Check service account permissions
   # Ensure Firestore is enabled
   ```

3. **Google Drive Upload Fails**
   ```bash
   # Verify service account has Drive access
   # Check folder permissions
   # Validate credentials JSON
   ```

4. **Flutter Build Issues**
   ```bash
   flutter clean
   flutter pub get
   flutter doctor  # Check for issues
   ```

### Performance Optimization

1. **Backend**
   - Use connection pooling for Firestore
   - Implement caching for frequent queries
   - Optimize file upload size limits

2. **Frontend**
   - Implement image caching
   - Use pagination for chat history
   - Optimize build size with `--split-per-abi`

### Monitoring & Logs

1. **Render Logs**
   - View real-time logs in Render dashboard
   - Set up log alerts for errors

2. **Firebase Analytics**
   - Monitor user engagement
   - Track feature usage
   - Set up crash reporting

## 📊 Scaling Considerations

### Backend Scaling
- Render auto-scales based on traffic
- Consider upgrading to paid plan for better performance
- Implement database indexing for large datasets

### Frontend Distribution
- Use Firebase App Distribution for beta testing
- Consider Play Store/App Store deployment
- Implement over-the-air updates

## 🔒 Security Best Practices

1. **API Security**
   - Validate all inputs
   - Implement rate limiting
   - Use HTTPS only

2. **Firebase Security**
   - Review security rules regularly
   - Monitor authentication logs
   - Implement proper data validation

3. **File Upload Security**
   - Validate file types and sizes
   - Scan for malicious content
   - Implement access controls

---

Your WideChat app is now ready for production! 🎉