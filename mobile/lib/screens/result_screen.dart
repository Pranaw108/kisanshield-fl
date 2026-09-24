import 'dart:io';

import 'package:flutter/material.dart';

import '../models/prediction.dart';
import '../widgets/confidence_bar.dart';

/// Shows one prediction result. No treatment advice here yet — that needs an
/// expert-approved knowledge base (roadmap S-12), same rule as the backend.
class ResultScreen extends StatelessWidget {
  final File image;
  final PredictResponse result;

  const ResultScreen({super.key, required this.image, required this.result});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Result')),
      body: SafeArea(
        child: ListView(
          padding: const EdgeInsets.all(16),
          children: [
            ClipRRect(
              borderRadius: BorderRadius.circular(16),
              child: Image.file(image, height: 240, width: double.infinity, fit: BoxFit.cover),
            ),
            const SizedBox(height: 20),
            if (result.isConfident) _ConfidentResult(result: result) else _NotSureResult(result: result),
            const SizedBox(height: 24),
            const _ResearchNotice(),
          ],
        ),
      ),
    );
  }
}

class _ConfidentResult extends StatelessWidget {
  final PredictResponse result;
  const _ConfidentResult({required this.result});

  @override
  Widget build(BuildContext context) {
    final top = result.top!;
    return Card(
      color: Colors.green.shade50,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(top.crop.toUpperCase(),
                style: Theme.of(context)
                    .textTheme
                    .labelSmall
                    ?.copyWith(letterSpacing: 1, color: Colors.black54)),
            const SizedBox(height: 4),
            Text(top.nameEn, style: Theme.of(context).textTheme.headlineSmall),
            Text(top.nameHi, style: Theme.of(context).textTheme.bodyMedium?.copyWith(color: Colors.black54)),
            const SizedBox(height: 14),
            ConfidenceBar(confidence: top.confidence),
            if (result.alternatives.isNotEmpty) ...[
              const SizedBox(height: 16),
              Text('Other possibilities', style: Theme.of(context).textTheme.labelMedium),
              const SizedBox(height: 6),
              ...result.alternatives.map((a) => Padding(
                    padding: const EdgeInsets.symmetric(vertical: 2),
                    child: Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        Text(a.nameEn, style: Theme.of(context).textTheme.bodySmall),
                        Text('${(a.confidence * 100).round()}%', style: Theme.of(context).textTheme.bodySmall),
                      ],
                    ),
                  )),
            ],
          ],
        ),
      ),
    );
  }
}

class _NotSureResult extends StatelessWidget {
  final PredictResponse result;
  const _NotSureResult({required this.result});

  @override
  Widget build(BuildContext context) {
    return Card(
      color: Colors.amber.shade50,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(children: [
              Icon(Icons.help_outline, color: Colors.amber.shade800),
              const SizedBox(width: 8),
              Text('Not sure', style: Theme.of(context).textTheme.titleMedium),
            ]),
            const SizedBox(height: 8),
            Text(result.message ?? 'The model could not confidently name a disease.'),
          ],
        ),
      ),
    );
  }
}

class _ResearchNotice extends StatelessWidget {
  const _ResearchNotice();

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: Colors.grey.shade100,
        borderRadius: BorderRadius.circular(12),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Icon(Icons.info_outline, size: 18, color: Colors.black54),
          const SizedBox(width: 8),
          Expanded(
            child: Text(
              'Research demo — a public-data baseline, not yet field-tested. '
              'No treatment advice is shown until an agronomist has approved it.',
              style: Theme.of(context).textTheme.bodySmall?.copyWith(color: Colors.black54),
            ),
          ),
        ],
      ),
    );
  }
}
