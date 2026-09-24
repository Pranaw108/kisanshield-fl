import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:kisanshield_mobile/main.dart';
import 'package:kisanshield_mobile/widgets/confidence_bar.dart';

void main() {
  testWidgets('home screen shows the capture prompt and disabled analyze button', (tester) async {
    await tester.pumpWidget(const KisanShieldApp());

    expect(find.text('Tap to photograph a leaf'), findsOneWidget);
    final button = tester.widget<FilledButton>(find.byType(FilledButton));
    expect(button.onPressed, isNull); // no photo yet, so Analyze must be disabled
  });

  testWidgets('gallery and camera buttons are present and enabled', (tester) async {
    await tester.pumpWidget(const KisanShieldApp());

    expect(find.text('Gallery'), findsOneWidget);
    expect(find.text('Camera'), findsOneWidget);
    final buttons = tester.widgetList<OutlinedButton>(find.byType(OutlinedButton));
    expect(buttons.every((b) => b.onPressed != null), isTrue);
  });

  testWidgets('ConfidenceBar animates to the given value and shows a percentage', (tester) async {
    await tester.pumpWidget(const MaterialApp(home: Scaffold(body: ConfidenceBar(confidence: 0.82))));
    await tester.pumpAndSettle();

    expect(find.text('82% confidence'), findsOneWidget);
    final bar = tester.widget<LinearProgressIndicator>(find.byType(LinearProgressIndicator));
    expect(bar.value, closeTo(0.82, 0.001));
  });

  testWidgets('ConfidenceBar uses amber when marked low confidence', (tester) async {
    await tester.pumpWidget(
      const MaterialApp(home: Scaffold(body: ConfidenceBar(confidence: 0.3, lowConfidence: true))),
    );
    await tester.pumpAndSettle();

    final bar = tester.widget<LinearProgressIndicator>(find.byType(LinearProgressIndicator));
    expect(bar.valueColor?.value, Colors.amber.shade800);
  });
}
