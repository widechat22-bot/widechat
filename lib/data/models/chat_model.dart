import 'package:cloud_firestore/cloud_firestore.dart';

class ChatModel {
  final String id;
  final bool isGroup;
  final List<String> members;
  final DateTime createdAt;
  final String? lastMessage;
  final String? lastMessageType;
  final String? lastMessageSenderId;
  final DateTime? lastMessageTime;
  final String? groupName;
  final String? groupPhotoUrl;
  final List<String>? adminIds;

  const ChatModel({
    required this.id,
    required this.isGroup,
    required this.members,
    required this.createdAt,
    this.lastMessage,
    this.lastMessageType,
    this.lastMessageSenderId,
    this.lastMessageTime,
    this.groupName,
    this.groupPhotoUrl,
    this.adminIds,
  });

  factory ChatModel.fromJson(String id, Map<String, dynamic> json) {
    return ChatModel(
      id: id,
      isGroup: json['isGroup'] ?? false,
      members: List<String>.from(json['members'] ?? []),
      createdAt: json['createdAt'].toDate(),
      lastMessage: json['lastMessage'],
      lastMessageType: json['lastMessageType'],
      lastMessageSenderId: json['lastMessageSenderId'],
      lastMessageTime: json['lastMessageTime']?.toDate(),
      groupName: json['groupName'],
      groupPhotoUrl: json['groupPhotoUrl'],
      adminIds: json['adminIds'] != null ? List<String>.from(json['adminIds']) : null,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'isGroup': isGroup,
      'members': members,
      'createdAt': Timestamp.fromDate(createdAt),
      'lastMessage': lastMessage,
      'lastMessageType': lastMessageType,
      'lastMessageSenderId': lastMessageSenderId,
      'lastMessageTime': lastMessageTime != null ? Timestamp.fromDate(lastMessageTime!) : null,
      'groupName': groupName,
      'groupPhotoUrl': groupPhotoUrl,
      'adminIds': adminIds,
    };
  }
}