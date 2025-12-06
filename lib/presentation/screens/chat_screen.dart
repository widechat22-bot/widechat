import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:image_picker/image_picker.dart';
import 'package:file_picker/file_picker.dart';
import '../providers/auth_provider.dart';
import '../providers/chat_provider.dart';
import '../widgets/message_bubble.dart';
import '../widgets/message_input.dart';
import '../../data/models/message_model.dart';
import '../../data/services/media_service.dart';

class ChatScreen extends ConsumerStatefulWidget {
  final String chatId;

  const ChatScreen({super.key, required this.chatId});

  @override
  ConsumerState<ChatScreen> createState() => _ChatScreenState();
}

class _ChatScreenState extends ConsumerState<ChatScreen> {
  final _messageController = TextEditingController();
  final _scrollController = ScrollController();
  final _mediaService = MediaService();

  @override
  Widget build(BuildContext context) {
    final currentUser = ref.watch(currentUserProvider);
    final messages = ref.watch(chatMessagesProvider(widget.chatId));

    return currentUser.when(
      data: (user) {
        if (user == null) return const SizedBox();

        return Scaffold(
          appBar: AppBar(
            title: const Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('Chat'),
                Text(
                  'Online',
                  style: TextStyle(fontSize: 12, color: Colors.grey),
                ),
              ],
            ),
            leading: IconButton(
              icon: const Icon(Icons.arrow_back),
              onPressed: () => Navigator.of(context).pop(),
            ),
          ),
          body: Column(
            children: [
              Expanded(
                child: messages.when(
                  data: (messageList) {
                    if (messageList.isEmpty) {
                      return const Center(
                        child: Text('No messages yet. Start the conversation!'),
                      );
                    }

                    return ListView.builder(
                      controller: _scrollController,
                      reverse: true,
                      itemCount: messageList.length,
                      itemBuilder: (context, index) {
                        final message = messageList[index];
                        final isMe = message.from == user.uid;
                        
                        return MessageBubble(
                          message: message,
                          isMe: isMe,
                        );
                      },
                    );
                  },
                  loading: () => const Center(child: CircularProgressIndicator()),
                  error: (error, stack) => Center(
                    child: Text('Error: $error'),
                  ),
                ),
              ),
              MessageInput(
                controller: _messageController,
                onSendMessage: (text) => _sendMessage(text, user.uid),
                onAttachImage: () => _pickImage(user.uid),
                onAttachFile: () => _pickFile(user.uid),
              ),
            ],
          ),
        );
      },
      loading: () => const Scaffold(
        body: Center(child: CircularProgressIndicator()),
      ),
      error: (error, stack) => Scaffold(
        body: Center(child: Text('Error: $error')),
      ),
    );
  }

  void _sendMessage(String text, String userId) async {
    if (text.trim().isEmpty) return;

    await ref.read(chatNotifierProvider.notifier).sendMessage(
      chatId: widget.chatId,
      from: userId,
      text: text.trim(),
      type: MessageType.text,
    );

    _messageController.clear();
    _scrollToBottom();
  }

  void _pickImage(String userId) async {
    final picker = ImagePicker();
    final image = await picker.pickImage(source: ImageSource.gallery);
    
    if (image != null) {
      try {
        final uploadResponse = await _mediaService.uploadFile(File(image.path));
        
        await ref.read(chatNotifierProvider.notifier).sendMessage(
          chatId: widget.chatId,
          from: userId,
          type: MessageType.image,
          fileId: uploadResponse.fileId,
          fileUrl: uploadResponse.downloadUrl,
          fileName: uploadResponse.filename,
          mimeType: uploadResponse.mimeType,
        );
        
        _scrollToBottom();
      } catch (e) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Failed to upload image: $e')),
        );
      }
    }
  }

  void _pickFile(String userId) async {
    final result = await FilePicker.platform.pickFiles();
    
    if (result != null && result.files.single.path != null) {
      try {
        final uploadResponse = await _mediaService.uploadFile(File(result.files.single.path!));
        
        await ref.read(chatNotifierProvider.notifier).sendMessage(
          chatId: widget.chatId,
          from: userId,
          type: MessageType.file,
          fileId: uploadResponse.fileId,
          fileUrl: uploadResponse.downloadUrl,
          fileName: uploadResponse.filename,
          mimeType: uploadResponse.mimeType,
        );
        
        _scrollToBottom();
      } catch (e) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Failed to upload file: $e')),
        );
      }
    }
  }

  void _scrollToBottom() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_scrollController.hasClients) {
        _scrollController.animateTo(
          0,
          duration: const Duration(milliseconds: 300),
          curve: Curves.easeOut,
        );
      }
    });
  }

  @override
  void dispose() {
    _messageController.dispose();
    _scrollController.dispose();
    super.dispose();
  }
}