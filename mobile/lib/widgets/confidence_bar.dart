import 'package:flutter/material.dart';

/// An animated confidence meter, coloured green when confident and amber near
/// the "not sure" threshold, so the same visual language reads consistently
/// with the web demo (see web/styles.css .confidence-fill).
class ConfidenceBar extends StatelessWidget {
  final double confidence; // 0.0 - 1.0
  final bool lowConfidence;

  const ConfidenceBar({super.key, required this.confidence, this.lowConfidence = false});

  @override
  Widget build(BuildContext context) {
    final color = lowConfidence ? Colors.amber.shade800 : Colors.green.shade700;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        ClipRRect(
          borderRadius: BorderRadius.circular(999),
          child: TweenAnimationBuilder<double>(
            tween: Tween(begin: 0, end: confidence.clamp(0, 1)),
            duration: const Duration(milliseconds: 500),
            curve: Curves.easeOutCubic,
            builder: (context, value, _) => LinearProgressIndicator(
              value: value,
              minHeight: 8,
              backgroundColor: color.withValues(alpha: 0.15),
              valueColor: AlwaysStoppedAnimation(color),
            ),
          ),
        ),
        const SizedBox(height: 6),
        Text('${(confidence * 100).round()}% confidence',
            style: Theme.of(context).textTheme.bodySmall?.copyWith(color: Colors.black54)),
      ],
    );
  }
}
