import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:timeago/timeago.dart' as timeago;
import '../providers/auth_provider.dart';
import '../providers/chat_provider.dart';
import '../widgets/chat_tile.dart';

class HomeScreen extends ConsumerWidget {
  const HomeScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final currentUser = ref.watch(currentUserProvider);
    
    return currentUser.when(
      data: (user) {
        if (user == null) return const SizedBox();
        
        final chats = ref.watch(userChatsProvider(user.uid));
        
        return Scaffold(
          appBar: AppBar(
            title: const Text('WideChat'),
            actions: [
              IconButton(
                icon: const Icon(Icons.search),
                onPressed: () => context.go('/search-users'),
              ),
              PopupMenuButton(
                itemBuilder: (context) => [
                  PopupMenuItem(
                    child: const Text('Settings'),
                    onTap: () => context.go('/settings'),
                  ),
                ],
              ),
            ],
          ),
          body: chats.when(
            data: (chatList) {
              if (chatList.isEmpty) {
                return const Center(
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Icon(Icons.chat_bubble_outline, size: 64, color: Colors.grey),
                      SizedBox(height: 16),
                      Text(
                        'No chats yet',
                        style: TextStyle(fontSize: 18, color: Colors.grey),
                      ),
                      SizedBox(height: 8),
                      Text(
                        'Start a conversation by searching for users',
                        style: TextStyle(color: Colors.grey),
                      ),
                    ],
                  ),
                );
              }
              
              return ListView.builder(
                itemCount: chatList.length,
                itemBuilder: (context, index) {
                  final chat = chatList[index];
                  return ChatTile(
                    chat: chat,
                    currentUserId: user.uid,
                    onTap: () => context.go('/chat/${chat.id}'),
                  );
                },
              );
            },
            loading: () => const Center(child: CircularProgressIndicator()),
            error: (error, stack) => Center(
              child: Text('Error: $error'),
            ),
          ),
          floatingActionButton: FloatingActionButton(
            onPressed: () => context.go('/search-users'),
            child: const Icon(Icons.add_comment),
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
}