import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../providers/auth_provider.dart';
import '../providers/chat_provider.dart';
import '../../data/models/user_model.dart';

class SearchUsersScreen extends ConsumerStatefulWidget {
  const SearchUsersScreen({super.key});

  @override
  ConsumerState<SearchUsersScreen> createState() => _SearchUsersScreenState();
}

class _SearchUsersScreenState extends ConsumerState<SearchUsersScreen> {
  final _searchController = TextEditingController();
  List<UserModel> _searchResults = [];
  bool _isSearching = false;

  @override
  Widget build(BuildContext context) {
    final currentUser = ref.watch(currentUserProvider);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Search Users'),
      ),
      body: Column(
        children: [
          Padding(
            padding: const EdgeInsets.all(16.0),
            child: TextField(
              controller: _searchController,
              decoration: InputDecoration(
                hintText: 'Enter username (e.g., @john)',
                prefixIcon: const Icon(Icons.search),
                suffixIcon: _isSearching
                    ? const SizedBox(
                        width: 20,
                        height: 20,
                        child: CircularProgressIndicator(strokeWidth: 2),
                      )
                    : IconButton(
                        icon: const Icon(Icons.clear),
                        onPressed: () {
                          _searchController.clear();
                          setState(() => _searchResults.clear());
                        },
                      ),
              ),
              onChanged: _searchUsers,
            ),
          ),
          Expanded(
            child: _searchResults.isEmpty
                ? const Center(
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        Icon(Icons.person_search, size: 64, color: Colors.grey),
                        SizedBox(height: 16),
                        Text(
                          'Search for users by username',
                          style: TextStyle(color: Colors.grey),
                        ),
                      ],
                    ),
                  )
                : ListView.builder(
                    itemCount: _searchResults.length,
                    itemBuilder: (context, index) {
                      final user = _searchResults[index];
                      return currentUser.when(
                        data: (currentUserData) => ListTile(
                          leading: CircleAvatar(
                            backgroundImage: user.photoUrl != null
                                ? NetworkImage(user.photoUrl!)
                                : null,
                            child: user.photoUrl == null
                                ? Text(user.displayName[0].toUpperCase())
                                : null,
                          ),
                          title: Text(user.displayName),
                          subtitle: Text('@${user.username}'),
                          trailing: user.uid == currentUserData?.uid
                              ? const Chip(label: Text('You'))
                              : ElevatedButton(
                                  onPressed: () => _startChat(user, currentUserData!),
                                  child: const Text('Chat'),
                                ),
                        ),
                        loading: () => const ListTile(
                          title: Text('Loading...'),
                        ),
                        error: (_, __) => const ListTile(
                          title: Text('Error'),
                        ),
                      );
                    },
                  ),
          ),
        ],
      ),
    );
  }

  void _searchUsers(String query) async {
    if (query.isEmpty) {
      setState(() => _searchResults.clear());
      return;
    }

    setState(() => _isSearching = true);

    // Remove @ if present
    final username = query.startsWith('@') ? query.substring(1) : query;
    
    try {
      final users = await ref.read(chatServiceProvider).searchUsers(username);
      setState(() {
        _searchResults = users;
        _isSearching = false;
      });
    } catch (e) {
      setState(() => _isSearching = false);
    }
  }

  void _startChat(UserModel otherUser, UserModel currentUser) async {
    final chatId = await ref.read(chatNotifierProvider.notifier).createOrGetChat([
      currentUser.uid,
      otherUser.uid,
    ]);
    
    if (mounted) {
      context.go('/chat/$chatId');
    }
  }

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }
}