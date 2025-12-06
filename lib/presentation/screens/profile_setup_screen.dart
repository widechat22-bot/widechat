import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:firebase_auth/firebase_auth.dart';
import '../providers/auth_provider.dart';
import '../../data/models/user_model.dart';

class ProfileSetupScreen extends ConsumerStatefulWidget {
  const ProfileSetupScreen({super.key});

  @override
  ConsumerState<ProfileSetupScreen> createState() => _ProfileSetupScreenState();
}

class _ProfileSetupScreenState extends ConsumerState<ProfileSetupScreen> {
  final _formKey = GlobalKey<FormState>();
  final _displayNameController = TextEditingController();
  final _usernameController = TextEditingController();
  final _aboutController = TextEditingController();
  bool _isCheckingUsername = false;
  bool _isUsernameAvailable = false;

  @override
  Widget build(BuildContext context) {
    final authState = ref.watch(authNotifierProvider);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Setup Profile'),
        automaticallyImplyLeading: false,
      ),
      body: Padding(
        padding: const EdgeInsets.all(24.0),
        child: Form(
          key: _formKey,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              const CircleAvatar(
                radius: 50,
                child: Icon(Icons.person, size: 50),
              ),
              const SizedBox(height: 24),
              TextFormField(
                controller: _displayNameController,
                decoration: const InputDecoration(
                  labelText: 'Display Name',
                  prefixIcon: Icon(Icons.person),
                ),
                validator: (value) {
                  if (value?.isEmpty ?? true) return 'Display name is required';
                  return null;
                },
              ),
              const SizedBox(height: 16),
              TextFormField(
                controller: _usernameController,
                decoration: InputDecoration(
                  labelText: 'Username',
                  prefixIcon: const Icon(Icons.alternate_email),
                  suffixIcon: _isCheckingUsername
                      ? const SizedBox(
                          width: 20,
                          height: 20,
                          child: CircularProgressIndicator(strokeWidth: 2),
                        )
                      : _isUsernameAvailable
                          ? const Icon(Icons.check, color: Colors.green)
                          : null,
                ),
                onChanged: _checkUsername,
                validator: (value) {
                  if (value?.isEmpty ?? true) return 'Username is required';
                  if (!RegExp(r'^[a-zA-Z0-9_]+$').hasMatch(value!)) {
                    return 'Username can only contain letters, numbers, and underscores';
                  }
                  if (!_isUsernameAvailable) return 'Username is not available';
                  return null;
                },
              ),
              const SizedBox(height: 16),
              TextFormField(
                controller: _aboutController,
                decoration: const InputDecoration(
                  labelText: 'About (Optional)',
                  prefixIcon: Icon(Icons.info),
                ),
                maxLines: 2,
              ),
              const SizedBox(height: 32),
              ElevatedButton(
                onPressed: authState.isLoading || !_isUsernameAvailable ? null : _createProfile,
                child: authState.isLoading
                    ? const CircularProgressIndicator()
                    : const Text('Complete Setup'),
              ),
            ],
          ),
        ),
      ),
    );
  }

  void _checkUsername(String value) async {
    if (value.isEmpty) {
      setState(() => _isUsernameAvailable = false);
      return;
    }

    setState(() => _isCheckingUsername = true);
    
    final isAvailable = await ref.read(authNotifierProvider.notifier).isUsernameAvailable(value);
    
    setState(() {
      _isCheckingUsername = false;
      _isUsernameAvailable = isAvailable;
    });
  }

  void _createProfile() async {
    if (_formKey.currentState!.validate()) {
      final user = FirebaseAuth.instance.currentUser!;
      
      final userModel = UserModel(
        uid: user.uid,
        email: user.email!,
        displayName: _displayNameController.text.trim(),
        username: _usernameController.text.toLowerCase().trim(),
        about: _aboutController.text.trim().isEmpty ? null : _aboutController.text.trim(),
        photoUrl: user.photoURL,
        isOnline: true,
        createdAt: DateTime.now(),
      );

      await ref.read(authNotifierProvider.notifier).createUserProfile(userModel);
      if (mounted) context.go('/home');
    }
  }

  @override
  void dispose() {
    _displayNameController.dispose();
    _usernameController.dispose();
    _aboutController.dispose();
    super.dispose();
  }
}