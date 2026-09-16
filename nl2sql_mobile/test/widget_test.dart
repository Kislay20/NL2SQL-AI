import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:nl2sql_mobile/main.dart';

void main() {
  testWidgets('NL2SQL Mobile ChatScreen renders correctly', (WidgetTester tester) async {
    // Build our app and trigger a frame.
    await tester.pumpWidget(const NL2SQLApp());

    // Verify app title in AppBar
    expect(find.text('NL2SQL AI'), findsOneWidget);
    expect(find.text('College Assistant'), findsOneWidget);

    // Verify sample question chips
    expect(find.text('Top students in CS'), findsOneWidget);
    expect(find.text('Marks > 80'), findsOneWidget);

    // Verify bottom input field and send icon
    expect(find.byType(TextField), findsOneWidget);
    expect(find.byIcon(Icons.send_rounded), findsOneWidget);
  });
}
