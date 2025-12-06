import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../data/services/chat_service.dart';
import '../../data/models/chat_model.dart';
import '../../data/models/message_model.dart';
import '../../data/models/user_model.dart';

final chatServiceProvider = Provider<ChatService>((ref) => ChatService());

final userChatsProvider = StreamProvider.family<List<ChatModel>, String>((ref, userId) {
  return ref.watch(chatServiceProvider).getUserChats(userId);
});

final chatMessagesProvider = StreamProvider.family<List<MessageModel>, String>((ref, chatId) {
  return ref.watch(chatServiceProvider).getChatMessages(chatId);
});

final searchUsersProvider = FutureProvider.family<List<UserModel>, String>((ref, username) {
  return ref.watch(chatServiceProvider).searchUsers(username);
});

class ChatNotifier extends StateNotifier<AsyncValue<void>> {
  ChatNotifier(this._chatService) : super(const AsyncValue.data(null));

  final ChatService _chatService;

  Future<String> createOrGetChat(List<String> memberIds) async {
    return await _chatService.createOrGetChat(memberIds);
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
    state = const AsyncValue.loading();
    try {
      await _chatService.sendMessage(
        chatId: chatId,
        from: from,
        to: to,
        text: text,
        type: type,
        fileId: fileId,
        fileUrl: fileUrl,
        fileName: fileName,
        mimeType: mimeType,
      );
      state = const AsyncValue.data(null);
    } catch (e) {
      state = AsyncValue.error(e, StackTrace.current);
    }
  }

  Future<void> markMessagesAsSeen(String chatId, String userId) async {
    await _chatService.markMessagesAsSeen(chatId, userId);
  }
}

final chatNotifierProvider = StateNotifierProvider<ChatNotifier, AsyncValue<void>>((ref) {
  return ChatNotifier(ref.watch(chatServiceProvider));
});