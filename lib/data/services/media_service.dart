import 'dart:io';
import 'package:http/http.dart' as http;
import 'dart:convert';
import 'package:firebase_auth/firebase_auth.dart';

class MediaUploadResponse {
  final String fileId;
  final String downloadUrl;
  final String filename;
  final String mimeType;
  final int size;

  MediaUploadResponse({
    required this.fileId,
    required this.downloadUrl,
    required this.filename,
    required this.mimeType,
    required this.size,
  });

  factory MediaUploadResponse.fromJson(Map<String, dynamic> json) {
    return MediaUploadResponse(
      fileId: json['file_id'],
      downloadUrl: json['download_url'],
      filename: json['filename'],
      mimeType: json['mime_type'],
      size: json['size'],
    );
  }
}

class MediaService {
  static const String baseUrl = 'YOUR_BACKEND_URL'; // Replace with actual backend URL

  Future<MediaUploadResponse> uploadFile(File file) async {
    final user = FirebaseAuth.instance.currentUser;
    if (user == null) throw Exception('User not authenticated');

    final token = await user.getIdToken();
    
    final request = http.MultipartRequest(
      'POST',
      Uri.parse('$baseUrl/upload'),
    );

    request.headers['Authorization'] = 'Bearer $token';
    request.files.add(await http.MultipartFile.fromPath('file', file.path));

    final streamedResponse = await request.send();
    final response = await http.Response.fromStream(streamedResponse);

    if (response.statusCode == 200) {
      final jsonData = json.decode(response.body);
      return MediaUploadResponse.fromJson(jsonData);
    } else {
      throw Exception('Failed to upload file: ${response.body}');
    }
  }
}