import 'package:flutter/material.dart';

import 'screens/home_screen.dart';

void main() => runApp(const KisanShieldApp());

class KisanShieldApp extends StatelessWidget {
  const KisanShieldApp({super.key});

  @override
  Widget build(BuildContext context) {
    final seed = Colors.green.shade700;
    return MaterialApp(
      title: 'KisanShield-FL',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(colorScheme: ColorScheme.fromSeed(seedColor: seed), useMaterial3: true),
      home: const HomeScreen(),
    );
  }
}
