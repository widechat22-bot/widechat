import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:timeago/timeago.dart' as timeago;
import '../../data/models/chat_model.dart';
import '../../data/services/auth_service.dart';

class ChatTile extends ConsumerWidget {
  final ChatModel chat;
  final String currentUserId;
  final VoidCallback onTap;

  const ChatTile({
    super.key,
    required this.chat,
    required this.currentUserId,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return ListTile(
      leading: CircleAvatar(
        backgroundColor: Theme.of(context).colorScheme.primary,
        child: chat.isGroup
            ? const Icon(Icons.group, color: Colors.white)
            : const Icon(Icons.person, color: Colors.white),
      ),
      title: Text(
        chat.isGroup ? chat.groupName ?? 'Group Chat' : 'Chat',
        style: const TextStyle(fontWeight: FontWeight.w600),
      ),
      subtitle: Text(
        chat.lastMessage ?? 'No messages yet',
        maxLines: 1,
        overflow: TextOverflow.ellipsis,
        style: TextStyle(
          color: Colors.grey[600],
        ),
      ),
      trailing: chat.lastMessageTime != null
          ? Text(
              timeago.format(chat.lastMessageTime!),
              style: TextStyle(
                color: Colors.grey[500],
                fontSize: 12,
              ),
            )
          : null,
      onTap: onTap,
    );
  }
}