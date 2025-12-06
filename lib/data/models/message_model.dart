import 'package:cloud_firestore/cloud_firestore.dart';

enum MessageType { text, image, video, file, audio }
enum MessageStatus { sent, delivered, seen }

class MessageModel {
  final String id;
  final String from;
  final String? to;
  final String? text;
  final MessageType type;
  final String? fileId;
  final String? fileUrl;
  final String? fileName;
  final String? mimeType;
  final DateTime sentAt;
  final MessageStatus status;
  final String? replyToMessageId;
  final bool isEdited;
  final bool deletedForEveryone;

  const MessageModel({
    required this.id,
    required this.from,
    this.to,
    this.text,
    required this.type,
    this.fileId,
    this.fileUrl,
    this.fileName,
    this.mimeType,
    required this.sentAt,
    required this.status,
    this.replyToMessageId,
    required this.isEdited,
    required this.deletedForEveryone,
  });

  factory MessageModel.fromJson(String id, Map<String, dynamic> json) {
    return MessageModel(
      id: id,
      from: json['from'],
      to: json['to'],
      text: json['text'],
      type: MessageType.values.firstWhere(
        (e) => e.name == json['type'],
        orElse: () => MessageType.text,
      ),
      fileId: json['fileId'],
      fileUrl: json['fileUrl'],
      fileName: json['fileName'],
      mimeType: json['mimeType'],
      sentAt: json['sentAt'].toDate(),
      status: MessageStatus.values.firstWhere(
        (e) => e.name == json['status'],
        orElse: () => MessageStatus.sent,
      ),
      replyToMessageId: json['replyToMessageId'],
      isEdited: json['isEdited'] ?? false,
      deletedForEveryone: json['deletedForEveryone'] ?? false,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'from': from,
      'to': to,
      'text': text,
      'type': type.name,
      'fileId': fileId,
      'fileUrl': fileUrl,
      'fileName': fileName,
      'mimeType': mimeType,
      'sentAt': Timestamp.fromDate(sentAt),
      'status': status.name,
      'replyToMessageId': replyToMessageId,
      'isEdited': isEdited,
      'deletedForEveryone': deletedForEveryone,
    };
  }
}