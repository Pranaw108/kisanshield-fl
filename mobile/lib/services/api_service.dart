import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:http/http.dart' as http;

import '../config.dart';
import '../models/prediction.dart';

/// Thrown for any failure the UI should show a specific message for — keeps
/// network/parsing details out of the screen code.
class ApiException implements Exception {
  final String message;
  ApiException(this.message);
  @override
  String toString() => message;
}

class ApiService {
  final String baseUrl;
  ApiService({this.baseUrl = Config.apiBaseUrl});

  Future<PredictResponse> predict(File imageFile) async {
    final uri = Uri.parse('$baseUrl/v1/predict');
    final request = http.MultipartRequest('POST', uri)
      ..files.add(await http.MultipartFile.fromPath('file', imageFile.path));

    http.StreamedResponse streamed;
    try {
      streamed = await request.send().timeout(const Duration(seconds: 30));
    } on SocketException {
      throw ApiException('Could not reach the server. Check your connection and try again.');
    } on TimeoutException {
      throw ApiException('The request timed out. Please try again.');
    }

    final response = await http.Response.fromStream(streamed);
    if (response.statusCode != 200) {
      throw ApiException(_readDetail(response.body) ?? 'Server error (${response.statusCode}).');
    }
    return PredictResponse.fromJson(jsonDecode(response.body) as Map<String, dynamic>);
  }

  String? _readDetail(String body) {
    try {
      return (jsonDecode(body) as Map<String, dynamic>)['detail'] as String?;
    } catch (_) {
      return null;
    }
  }
}
