import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../presentation/providers/auth_provider.dart';
import '../../presentation/screens/splash_screen.dart';
import '../../presentation/screens/login_screen.dart';
import '../../presentation/screens/signup_screen.dart';
import '../../presentation/screens/profile_setup_screen.dart';
import '../../presentation/screens/home_screen.dart';
import '../../presentation/screens/chat_screen.dart';
import '../../presentation/screens/search_users_screen.dart';
import '../../presentation/screens/settings_screen.dart';

final routerProvider = Provider<GoRouter>((ref) {
  final authState = ref.watch(authStateProvider);
  
  return GoRouter(
    initialLocation: '/splash',
    redirect: (context, state) {
      return authState.when(
        data: (user) {
          if (user == null) {
            if (state.matchedLocation == '/login' || 
                state.matchedLocation == '/signup' ||
                state.matchedLocation == '/splash') {
              return null;
            }
            return '/login';
          } else {
            if (state.matchedLocation == '/login' || 
                state.matchedLocation == '/signup' ||
                state.matchedLocation == '/splash') {
              return '/home';
            }
            return null;
          }
        },
        loading: () => '/splash',
        error: (_, __) => '/login',
      );
    },
    routes: [
      GoRoute(
        path: '/splash',
        builder: (context, state) => const SplashScreen(),
      ),
      GoRoute(
        path: '/login',
        builder: (context, state) => const LoginScreen(),
      ),
      GoRoute(
        path: '/signup',
        builder: (context, state) => const SignUpScreen(),
      ),
      GoRoute(
        path: '/profile-setup',
        builder: (context, state) => const ProfileSetupScreen(),
      ),
      GoRoute(
        path: '/home',
        builder: (context, state) => const HomeScreen(),
      ),
      GoRoute(
        path: '/chat/:chatId',
        builder: (context, state) => ChatScreen(
          chatId: state.pathParameters['chatId']!,
        ),
      ),
      GoRoute(
        path: '/search-users',
        builder: (context, state) => const SearchUsersScreen(),
      ),
      GoRoute(
        path: '/settings',
        builder: (context, state) => const SettingsScreen(),
      ),
    ],
  );
});