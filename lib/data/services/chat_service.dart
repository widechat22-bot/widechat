import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:uuid/uuid.dart';
import '../models/chat_model.dart';
import '../models/message_model.dart';
import '../models/user_model.dart';

class ChatService {
  final FirebaseFirestore _firestore = FirebaseFirestore.instance;
  final Uuid _uuid = const Uuid();

  Stream<List<ChatModel>> getUserChats(String userId) {
    return _firestore
        .collection('chats')
        .where('members', arrayContains: userId)
        .orderBy('lastMessageTime', descending: true)
        .snapshots()
        .map((snapshot) => snapshot.docs
            .map((doc) => ChatModel.fromJson(doc.id, doc.data()))
            .toList());
  }

  Stream<List<MessageModel>> getChatMessages(String chatId) {
    return _firestore
        .collection('chats')
        .doc(chatId)
        .collection('messages')
        .orderBy('sentAt', descending: true)
        .snapshots()
        .map((snapshot) => snapshot.docs
            .map((doc) => MessageModel.fromJson(doc.id, doc.data()))
            .toList());
  }

  Future<String> createOrGetChat(List<String> memberIds) async {
    memberIds.sort();
    
    final existingChat = await _firestore
        .collection('chats')
        .where('members', isEqualTo: memberIds)
        .where('isGroup', isEqualTo: false)
        .get();

    if (existingChat.docs.isNotEmpty) {
      return existingChat.docs.first.id;
    }

    final chatId = _uuid.v4();
    final chat = ChatModel(
      id: chatId,
      isGroup: false,
      members: memberIds,
      createdAt: DateTime.now(),
    );

    await _firestore.collection('chats').doc(chatId).set(chat.toJson());
    return chatId;
  }

  Future<void> sendMessage({
    required String chatId,
    required String from,
    String? to,
    String? text,
    required MessageType type,
    String? fileId,
    String? fileUrl,
    String? fileName,
    String? mimeType,
  }) async {
    final messageId = _uuid.v4();
    final message = MessageModel(
      id: messageId,
      from: from,
      to: to,
      text: text,
      type: type,
      fileId: fileId,
      fileUrl: fileUrl,
      fileName: fileName,
      mimeType: mimeType,
      sentAt: DateTime.now(),
      status: MessageStatus.sent,
      isEdited: false,
      deletedForEveryone: false,
    );

    final batch = _firestore.batch();
    
    batch.set(
      _firestore.collection('chats').doc(chatId).collection('messages').doc(messageId),
      message.toJson(),
    );

    batch.update(_firestore.collection('chats').doc(chatId), {
      'lastMessage': text ?? fileName ?? 'Media',
      'lastMessageType': type.name,
      'lastMessageSenderId': from,
      'lastMessageTime': FieldValue.serverTimestamp(),
    });

    await batch.commit();
  }

  Future<List<UserModel>> searchUsers(String username) async {
    final query = await _firestore
        .collection('users')
        .where('username', isEqualTo: username.toLowerCase())
        .get();

    return query.docs.map((doc) => UserModel.fromJson(doc.data())).toList();
  }

  Future<void> markMessagesAsSeen(String chatId, String userId) async {
    final messages = await _firestore
        .collection('chats')
        .doc(chatId)
        .collection('messages')
        .where('from', isNotEqualTo: userId)
        .where('status', isNotEqualTo: 'seen')
        .get();

    final batch = _firestore.batch();
    for (final doc in messages.docs) {
      batch.update(doc.reference, {'status': 'seen'});
    }
    await batch.commit();
  }
}