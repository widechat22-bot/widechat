// Example Firestore queries for WideChat

import 'package:cloud_firestore/cloud_firestore.dart';

class FirestoreQueries {
  final FirebaseFirestore _firestore = FirebaseFirestore.instance;

  // Get user's chat list ordered by last message time
  Stream<QuerySnapshot> getUserChats(String userId) {
    return _firestore
        .collection('chats')
        .where('members', arrayContains: userId)
        .orderBy('lastMessageTime', descending: true)
        .snapshots();
  }

  // Get messages in a chat ordered by timestamp
  Stream<QuerySnapshot> getChatMessages(String chatId) {
    return _firestore
        .collection('chats')
        .doc(chatId)
        .collection('messages')
        .orderBy('sentAt', descending: true)
        .limit(50)
        .snapshots();
  }

  // Search users by username
  Future<QuerySnapshot> searchUsersByUsername(String username) {
    return _firestore
        .collection('users')
        .where('username', isEqualTo: username.toLowerCase())
        .get();
  }

  // Send a message
  Future<void> sendMessage(String chatId, Map<String, dynamic> messageData) {
    final batch = _firestore.batch();
    
    final messageRef = _firestore
        .collection('chats')
        .doc(chatId)
        .collection('messages')
        .doc();
    
    batch.set(messageRef, {
      ...messageData,
      'sentAt': FieldValue.serverTimestamp(),
    });

    final chatRef = _firestore.collection('chats').doc(chatId);
    batch.update(chatRef, {
      'lastMessage': messageData['text'] ?? messageData['fileName'] ?? 'Media',
      'lastMessageType': messageData['type'],
      'lastMessageSenderId': messageData['from'],
      'lastMessageTime': FieldValue.serverTimestamp(),
    });

    return batch.commit();
  }

  // Mark messages as seen
  Future<void> markMessagesAsSeen(String chatId, String userId) {
    return _firestore
        .collection('chats')
        .doc(chatId)
        .collection('messages')
        .where('from', isNotEqualTo: userId)
        .where('status', isNotEqualTo: 'seen')
        .get()
        .then((snapshot) {
      final batch = _firestore.batch();
      for (final doc in snapshot.docs) {
        batch.update(doc.reference, {'status': 'seen'});
      }
      return batch.commit();
    });
  }
}