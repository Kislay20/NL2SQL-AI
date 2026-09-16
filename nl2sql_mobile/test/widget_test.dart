import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:nl2sql_mobile/main.dart';

void main() {
  testWidgets('NL2SQL Mobile ChatScreen renders correctly', (WidgetTester tester) async {
    // Build our app and trigger a frame.
    await tester.pumpWidget(const NL2SQLApp());

    // Verify app title and active DB badge in AppBar
    expect(find.text('NL2SQL AI'), findsOneWidget);
    expect(find.text('SQLite'), findsOneWidget);
    expect(find.byIcon(Icons.storage_rounded), findsOneWidget);

    // Verify sample question chips
    expect(find.text('Top students in CS'), findsOneWidget);
    expect(find.text('Marks > 80'), findsOneWidget);

    // Verify bottom input field and send icon
    expect(find.byType(TextField), findsOneWidget);
    expect(find.byIcon(Icons.send_rounded), findsOneWidget);
  });

  testWidgets('Database Connection URI constructor test', (WidgetTester tester) async {
    final sqliteUri = ChatScreen.constructDbUri(
      type: "SQLite",
      host: "",
      port: "",
      user: "",
      pass: "",
      name: "college.db",
    );
    expect(sqliteUri, equals("sqlite:///college.db"));

    final mysqlUri = ChatScreen.constructDbUri(
      type: "MySQL",
      host: "127.0.0.1",
      port: "3306",
      user: "admin",
      pass: "secret",
      name: "university",
    );
    expect(mysqlUri, equals("mysql+pymysql://admin:secret@127.0.0.1:3306/university"));

    final pgUri = ChatScreen.constructDbUri(
      type: "PostgreSQL",
      host: "db.host.internal",
      port: "5432",
      user: "postgres",
      pass: "p@ss",
      name: "campus",
    );
    expect(pgUri, equals("postgresql+psycopg2://postgres:p%40ss@db.host.internal:5432/campus"));
  });
}
