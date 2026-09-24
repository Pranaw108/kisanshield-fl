import 'dart:io';

import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';

import '../services/api_service.dart';
import 'result_screen.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  final _picker = ImagePicker();
  final _api = ApiService();
  File? _image;
  bool _busy = false;
  String? _error;

  Future<void> _pick(ImageSource source) async {
    final picked = await _picker.pickImage(source: source, maxWidth: 1600, imageQuality: 90);
    if (picked == null) return;
    setState(() {
      _image = File(picked.path);
      _error = null;
    });
  }

  Future<void> _analyze() async {
    if (_image == null) return;
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      final result = await _api.predict(_image!);
      if (!mounted) return;
      await Navigator.push(
        context,
        MaterialPageRoute(builder: (_) => ResultScreen(image: _image!, result: result)),
      );
    } on ApiException catch (e) {
      setState(() => _error = e.message);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('KisanShield-FL')),
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            children: [
              Expanded(child: _PhotoArea(image: _image, onTap: () => _pick(ImageSource.camera))),
              const SizedBox(height: 16),
              if (_error != null) _ErrorBanner(message: _error!),
              const SizedBox(height: 12),
              Row(
                children: [
                  Expanded(
                    child: OutlinedButton.icon(
                      onPressed: _busy ? null : () => _pick(ImageSource.gallery),
                      icon: const Icon(Icons.photo_library_outlined),
                      label: const Text('Gallery'),
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: OutlinedButton.icon(
                      onPressed: _busy ? null : () => _pick(ImageSource.camera),
                      icon: const Icon(Icons.camera_alt_outlined),
                      label: const Text('Camera'),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 12),
              SizedBox(
                width: double.infinity,
                child: FilledButton(
                  onPressed: (_image == null || _busy) ? null : _analyze,
                  style: FilledButton.styleFrom(padding: const EdgeInsets.symmetric(vertical: 16)),
                  child: _busy
                      ? const SizedBox(
                          height: 20, width: 20,
                          child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                      : const Text('Analyze photo'),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _PhotoArea extends StatelessWidget {
  final File? image;
  final VoidCallback onTap;
  const _PhotoArea({required this.image, required this.onTap});

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: image == null ? onTap : null,
      child: Container(
        width: double.infinity,
        decoration: BoxDecoration(
          color: Colors.green.shade50,
          borderRadius: BorderRadius.circular(20),
          border: Border.all(color: Colors.green.shade100, width: 2),
        ),
        clipBehavior: Clip.antiAlias,
        child: image != null
            ? Image.file(image!, fit: BoxFit.cover)
            : Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Icon(Icons.camera_alt_outlined, size: 48, color: Colors.green.shade700),
                  const SizedBox(height: 12),
                  Text('Tap to photograph a leaf', style: Theme.of(context).textTheme.titleMedium),
                  const SizedBox(height: 4),
                  Text('or choose one from your gallery below',
                      style: Theme.of(context).textTheme.bodySmall?.copyWith(color: Colors.black54)),
                ],
              ),
      ),
    );
  }
}

class _ErrorBanner extends StatelessWidget {
  final String message;
  const _ErrorBanner({required this.message});

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(color: Colors.red.shade50, borderRadius: BorderRadius.circular(12)),
      child: Row(
        children: [
          Icon(Icons.error_outline, color: Colors.red.shade700, size: 20),
          const SizedBox(width: 8),
          Expanded(child: Text(message, style: TextStyle(color: Colors.red.shade900))),
        ],
      ),
    );
  }
}
