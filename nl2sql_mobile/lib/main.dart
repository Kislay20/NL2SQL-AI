import 'dart:convert';
import 'dart:io' show Platform;
import 'package:firebase_auth/firebase_auth.dart';
import 'package:firebase_core/firebase_core.dart';
import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';

import 'screens/login_screen.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  try {
    await Firebase.initializeApp();
  } catch (e) {
    debugPrint("Firebase initialization note: $e");
  }
  runApp(const NL2SQLApp());
}

/// Root Application Widget configured with a modern Material 3 theme.
class NL2SQLApp extends StatelessWidget {
  const NL2SQLApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'NL2SQL Mobile AI',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        useMaterial3: true,
        colorScheme: ColorScheme.fromSeed(
          seedColor: const Color(0xFF4F46E5), // Indigo primary
          brightness: Brightness.light,
        ),
        scaffoldBackgroundColor: const Color(0xFFF8FAFC), // Slate 50
        appBarTheme: const AppBarTheme(
          elevation: 0,
          backgroundColor: Colors.white,
          foregroundColor: Color(0xFF1E293B),
          surfaceTintColor: Colors.transparent,
        ),
      ),
      home: const AuthGate(),
    );
  }
}

/// Gate widget directing between LoginScreen and ChatScreen based on auth state.
class AuthGate extends StatelessWidget {
  const AuthGate({super.key});

  @override
  Widget build(BuildContext context) {
    return StreamBuilder<User?>(
      stream: FirebaseAuth.instance.authStateChanges(),
      builder: (context, snapshot) {
        if (snapshot.connectionState == ConnectionState.waiting) {
          return const Scaffold(
            body: Center(
              child: CircularProgressIndicator(
                valueColor: AlwaysStoppedAnimation<Color>(Color(0xFF4F46E5)),
              ),
            ),
          );
        }
        if (snapshot.hasData && snapshot.data != null) {
          return const ChatScreen();
        }
        return const LoginScreen();
      },
    );
  }
}

/// Represents an individual chat message in the conversation.
class ChatMessage {
  final bool isUser;
  final String text;
  final String? intent;
  final String? sql;
  final List<Map<String, dynamic>>? data;
  final bool isError;
  final DateTime timestamp;

  ChatMessage({
    required this.isUser,
    required this.text,
    this.intent,
    this.sql,
    this.data,
    this.isError = false,
    DateTime? timestamp,
  }) : timestamp = timestamp ?? DateTime.now();
}

/// Main conversational screen for querying the college database.
class ChatScreen extends StatefulWidget {
  const ChatScreen({super.key});

  /// Helper to compile SQLAlchemy connection URI from fields.
  static String constructDbUri({
    required String type,
    required String host,
    required String port,
    required String user,
    required String pass,
    required String name,
  }) {
    if (type == "SQLite") {
      final clean = name.trim().isEmpty ? "college.db" : name.trim();
      if (clean.startsWith("sqlite:///")) return clean;
      return "sqlite:///$clean";
    } else if (type == "MySQL") {
      final u = user.trim().isEmpty ? "root" : user.trim();
      final p = pass.trim().isNotEmpty ? ":${Uri.encodeComponent(pass.trim())}" : "";
      final h = host.trim().isEmpty ? "localhost" : host.trim();
      final prt = port.trim().isEmpty ? "3306" : port.trim();
      final db = name.trim().isEmpty ? "college" : name.trim();
      return "mysql+pymysql://$u$p@$h:$prt/$db";
    } else if (type == "PostgreSQL") {
      final u = user.trim().isEmpty ? "postgres" : user.trim();
      final p = pass.trim().isNotEmpty ? ":${Uri.encodeComponent(pass.trim())}" : "";
      final h = host.trim().isEmpty ? "localhost" : host.trim();
      final prt = port.trim().isEmpty ? "5432" : port.trim();
      final db = name.trim().isEmpty ? "college" : name.trim();
      return "postgresql+psycopg2://$u$p@$h:$prt/$db";
    }
    return "sqlite:///college.db";
  }

  @override
  State<ChatScreen> createState() => _ChatScreenState();
}

class _ChatScreenState extends State<ChatScreen> {
  final TextEditingController _textController = TextEditingController();
  final ScrollController _scrollController = ScrollController();
  final List<ChatMessage> _messages = [];
  bool _isLoading = false;

  /// Backend REST API URL
  late String _apiBaseUrl;

  /// Active Enterprise Database Connection Settings
  String _activeDbType = "SQLite";
  String _activeDbUri = "sqlite:///college.db";
  String _dbHost = "localhost";
  String _dbPort = "3306";
  String _dbUser = "root";
  String _dbPass = "";
  String _dbName = "college.db";

  @override
  void initState() {
    super.initState();
    _apiBaseUrl = _resolveDefaultApiUrl();
    _loadSettings();

    // Welcome greeting message
    _messages.add(
      ChatMessage(
        isUser: false,
        text:
            "👋 Welcome to **NL2SQL AI Mobile**!\nAsk me questions about students, marks, departments, or attendance in English, Hindi, or Hinglish.",
        intent: "conversational",
      ),
    );
  }

  static String _resolveDefaultApiUrl() {
    if (!kIsWeb && Platform.isAndroid) {
      return "http://10.0.2.2:5000";
    }
    return "http://127.0.0.1:5000";
  }

  /// Load persisted backend and database settings from SharedPreferences.
  Future<void> _loadSettings() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      setState(() {
        _apiBaseUrl = prefs.getString('api_base_url') ?? _resolveDefaultApiUrl();
        _activeDbType = prefs.getString('db_type') ?? "SQLite";
        _activeDbUri = prefs.getString('db_uri') ?? "sqlite:///college.db";
        _dbHost = prefs.getString('db_host') ?? "localhost";
        _dbPort = prefs.getString('db_port') ?? (_activeDbType == "PostgreSQL" ? "5432" : "3306");
        _dbUser = prefs.getString('db_user') ?? (_activeDbType == "PostgreSQL" ? "postgres" : "root");
        _dbPass = prefs.getString('db_pass') ?? "";
        _dbName = prefs.getString('db_name') ?? (_activeDbType == "SQLite" ? "college.db" : "college");
      });
    } catch (_) {
      // Fallback defaults on platform error
    }
  }

  @override
  void dispose() {
    _textController.dispose();
    _scrollController.dispose();
    super.dispose();
  }

  void _scrollToBottom() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_scrollController.hasClients) {
        _scrollController.animateTo(
          _scrollController.position.maxScrollExtent,
          duration: const Duration(milliseconds: 300),
          curve: Curves.easeOut,
        );
      }
    });
  }


  /// Sends a natural language query to the Flask backend REST API with dynamic db_uri.
  Future<void> _sendMessage([String? presetQuery]) async {
    final queryText = presetQuery ?? _textController.text.trim();
    if (queryText.isEmpty || _isLoading) return;

    _textController.clear();

    // 1. Append User Message
    setState(() {
      _messages.add(ChatMessage(isUser: true, text: queryText));
      _isLoading = true;
    });
    _scrollToBottom();

    try {
      final uri = Uri.parse("$_apiBaseUrl/api/query");
      final idToken = await FirebaseAuth.instance.currentUser?.getIdToken();
      final headers = <String, String>{"Content-Type": "application/json"};
      if (idToken != null && idToken.isNotEmpty) {
        headers["Authorization"] = "Bearer $idToken";
      }

      final response = await http
          .post(
            uri,
            headers: headers,
            body: jsonEncode({
              "query": queryText,
              "db_uri": _activeDbUri,
            }),
          )
          .timeout(const Duration(seconds: 45));

      final Map<String, dynamic> jsonResponse = jsonDecode(response.body);

      if (response.statusCode == 200) {
        final intent = jsonResponse['intent'] as String?;
        final responseText = jsonResponse['response'] as String? ?? 'No response received.';
        final sql = jsonResponse['sql'] as String?;
        final rawData = jsonResponse['data'];

        List<Map<String, dynamic>>? parsedData;
        if (rawData is List && rawData.isNotEmpty) {
          parsedData = rawData.map((item) => Map<String, dynamic>.from(item as Map)).toList();
        }

        setState(() {
          _messages.add(
            ChatMessage(
              isUser: false,
              text: responseText,
              intent: intent,
              sql: sql,
              data: parsedData,
              isError: false,
            ),
          );
        });
      } else {
        // HTTP 400 / 500 error from backend
        final errText = jsonResponse['error'] ??
            jsonResponse['response'] ??
            "Server error (${response.statusCode})";
        setState(() {
          _messages.add(
            ChatMessage(
              isUser: false,
              text: "❌ $errText",
              sql: jsonResponse['sql'] as String?,
              isError: true,
            ),
          );
        });
      }
    } catch (exc) {
      setState(() {
        _messages.add(
          ChatMessage(
            isUser: false,
            text:
                "⚠️ Network error connecting to $_apiBaseUrl:\n$exc\n\nMake sure the Flask API server is running (`python -m api.server`).",
            isError: true,
          ),
        );
      });
    } finally {
      setState(() {
        _isLoading = false;
      });
      _scrollToBottom();
    }
  }

  /// Displays Database Connection Manager modal dialog.
  void _showDatabaseConnectionManager() {
    String selectedType = _activeDbType;
    final hostController = TextEditingController(text: _dbHost);
    final portController = TextEditingController(text: _dbPort);
    final userController = TextEditingController(text: _dbUser);
    final passController = TextEditingController(text: _dbPass);
    final nameController = TextEditingController(text: _dbName);

    bool isTesting = false;
    String? testResultMsg;
    bool? testResultSuccess;

    showDialog(
      context: context,
      builder: (ctx) {
        return StatefulBuilder(
          builder: (dialogContext, setDialogState) {
            final isSqlite = selectedType == "SQLite";

            // Live generated URI preview
            final currentUri = ChatScreen.constructDbUri(
              type: selectedType,
              host: hostController.text,
              port: portController.text,
              user: userController.text,
              pass: passController.text,
              name: nameController.text,
            );

            Future<void> runTestConnection() async {
              setDialogState(() {
                isTesting = true;
                testResultMsg = null;
                testResultSuccess = null;
              });

              try {
                final testUrl = Uri.parse("$_apiBaseUrl/api/test-connection");
                final idToken = await FirebaseAuth.instance.currentUser?.getIdToken();
                final headers = <String, String>{"Content-Type": "application/json"};
                if (idToken != null && idToken.isNotEmpty) {
                  headers["Authorization"] = "Bearer $idToken";
                }

                final resp = await http
                    .post(
                      testUrl,
                      headers: headers,
                      body: jsonEncode({"db_uri": currentUri}),
                    )
                    .timeout(const Duration(seconds: 15));

                final Map<String, dynamic> body = jsonDecode(resp.body);
                if (resp.statusCode == 200 && body['status'] == "success") {
                  setDialogState(() {
                    testResultSuccess = true;
                    testResultMsg = body['message'] ?? "Connection verified successfully!";
                  });
                } else {
                  setDialogState(() {
                    testResultSuccess = false;
                    testResultMsg = body['error'] ?? "Connection test failed (${resp.statusCode})";
                  });
                }
              } catch (e) {
                setDialogState(() {
                  testResultSuccess = false;
                  testResultMsg = "Test failed: $e";
                });
              } finally {
                setDialogState(() {
                  isTesting = false;
                });
              }
            }

            return AlertDialog(
              title: const Row(
                children: [
                  Icon(Icons.storage_rounded, color: Color(0xFF4F46E5)),
                  SizedBox(width: 8),
                  Text(
                    "Database Manager",
                    style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
                  ),
                ],
              ),
              content: SingleChildScrollView(
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text(
                      "Configure client target database:",
                      style: TextStyle(fontSize: 12.5, color: Colors.black54),
                    ),
                    const SizedBox(height: 12),

                    // Database Type Dropdown
                    DropdownButtonFormField<String>(
                      initialValue: selectedType,
                      decoration: const InputDecoration(
                        labelText: "Database Type",
                        border: OutlineInputBorder(),
                        isDense: true,
                      ),
                      items: const [
                        DropdownMenuItem(value: "SQLite", child: Text("SQLite (Local File)")),
                        DropdownMenuItem(value: "MySQL", child: Text("MySQL (PyMySQL)")),
                        DropdownMenuItem(value: "PostgreSQL", child: Text("PostgreSQL (psycopg2)")),
                      ],
                      onChanged: (val) {
                        if (val == null) return;
                        setDialogState(() {
                          selectedType = val;
                          if (val == "MySQL") {
                            portController.text = "3306";
                            userController.text = "root";
                            nameController.text = "college";
                          } else if (val == "PostgreSQL") {
                            portController.text = "5432";
                            userController.text = "postgres";
                            nameController.text = "college";
                          } else {
                            nameController.text = "college.db";
                          }
                        });
                      },
                    ),
                    const SizedBox(height: 10),

                    if (!isSqlite) ...[
                      // Host & Port Row
                      Row(
                        children: [
                          Expanded(
                            flex: 3,
                            child: TextField(
                              controller: hostController,
                              decoration: const InputDecoration(
                                labelText: "Host",
                                border: OutlineInputBorder(),
                                isDense: true,
                              ),
                              onChanged: (_) => setDialogState(() {}),
                            ),
                          ),
                          const SizedBox(width: 8),
                          Expanded(
                            flex: 2,
                            child: TextField(
                              controller: portController,
                              keyboardType: TextInputType.number,
                              decoration: const InputDecoration(
                                labelText: "Port",
                                border: OutlineInputBorder(),
                                isDense: true,
                              ),
                              onChanged: (_) => setDialogState(() {}),
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 10),

                      // Username & Password Row
                      Row(
                        children: [
                          Expanded(
                            child: TextField(
                              controller: userController,
                              decoration: const InputDecoration(
                                labelText: "Username",
                                border: OutlineInputBorder(),
                                isDense: true,
                              ),
                              onChanged: (_) => setDialogState(() {}),
                            ),
                          ),
                          const SizedBox(width: 8),
                          Expanded(
                            child: TextField(
                              controller: passController,
                              obscureText: true,
                              decoration: const InputDecoration(
                                labelText: "Password",
                                border: OutlineInputBorder(),
                                isDense: true,
                              ),
                              onChanged: (_) => setDialogState(() {}),
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 10),
                    ],

                    // Database Name / File Path
                    TextField(
                      controller: nameController,
                      decoration: InputDecoration(
                        labelText: isSqlite ? "SQLite DB File / Path" : "Database Name",
                        hintText: isSqlite ? "college.db" : "college",
                        border: const OutlineInputBorder(),
                        isDense: true,
                      ),
                      onChanged: (_) => setDialogState(() {}),
                    ),
                    const SizedBox(height: 10),

                    // URI Preview box
                    Container(
                      width: double.infinity,
                      padding: const EdgeInsets.all(8),
                      decoration: BoxDecoration(
                        color: const Color(0xFFF1F5F9),
                        borderRadius: BorderRadius.circular(6),
                        border: Border.all(color: const Color(0xFFE2E8F0)),
                      ),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          const Text(
                            "SQLAlchemy URI Preview:",
                            style: TextStyle(fontSize: 10.5, fontWeight: FontWeight.bold, color: Colors.grey),
                          ),
                          const SizedBox(height: 2),
                          SelectableText(
                            currentUri,
                            style: const TextStyle(
                              fontSize: 11,
                              fontFamily: 'monospace',
                              color: Color(0xFF1E293B),
                            ),
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(height: 10),

                    // Test Connection Result feedback
                    if (testResultMsg != null)
                      Container(
                        padding: const EdgeInsets.all(8),
                        margin: const EdgeInsets.only(bottom: 8),
                        decoration: BoxDecoration(
                          color: testResultSuccess == true ? Colors.green.shade50 : Colors.red.shade50,
                          borderRadius: BorderRadius.circular(6),
                          border: Border.all(
                            color: testResultSuccess == true ? Colors.green.shade200 : Colors.red.shade200,
                          ),
                        ),
                        child: Row(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Icon(
                              testResultSuccess == true ? Icons.check_circle_outline : Icons.error_outline,
                              size: 16,
                              color: testResultSuccess == true ? Colors.green.shade700 : Colors.red.shade700,
                            ),
                            const SizedBox(width: 6),
                            Expanded(
                              child: Text(
                                testResultMsg!,
                                style: TextStyle(
                                  fontSize: 11.5,
                                  color: testResultSuccess == true ? Colors.green.shade800 : Colors.red.shade800,
                                ),
                              ),
                            ),
                          ],
                        ),
                      ),

                    // Test Connection Action Button
                    SizedBox(
                      width: double.infinity,
                      child: OutlinedButton.icon(
                        style: OutlinedButton.styleFrom(
                          foregroundColor: const Color(0xFF4F46E5),
                          side: const BorderSide(color: Color(0xFF4F46E5)),
                        ),
                        onPressed: isTesting ? null : runTestConnection,
                        icon: isTesting
                            ? const SizedBox(
                                width: 14,
                                height: 14,
                                child: CircularProgressIndicator(strokeWidth: 2),
                              )
                            : const Icon(Icons.bolt, size: 18),
                        label: Text(isTesting ? "Testing Connection..." : "Test Connection (SELECT 1)"),
                      ),
                    ),
                  ],
                ),
              ),
              actions: [
                TextButton(
                  onPressed: () => Navigator.pop(ctx),
                  child: const Text("Cancel"),
                ),
                FilledButton(
                  onPressed: () async {
                    final newUri = currentUri;
                    setState(() {
                      _activeDbType = selectedType;
                      _dbHost = hostController.text.trim();
                      _dbPort = portController.text.trim();
                      _dbUser = userController.text.trim();
                      _dbPass = passController.text.trim();
                      _dbName = nameController.text.trim();
                      _activeDbUri = newUri;
                    });

                    // Persist to SharedPreferences
                    try {
                      final prefs = await SharedPreferences.getInstance();
                      await prefs.setString('db_type', selectedType);
                      await prefs.setString('db_host', _dbHost);
                      await prefs.setString('db_port', _dbPort);
                      await prefs.setString('db_user', _dbUser);
                      await prefs.setString('db_pass', _dbPass);
                      await prefs.setString('db_name', _dbName);
                      await prefs.setString('db_uri', newUri);
                    } catch (_) {}

                    if (ctx.mounted) {
                      Navigator.pop(ctx);
                    }
                    if (mounted) {
                      ScaffoldMessenger.of(context).showSnackBar(
                        SnackBar(
                          content: Text("✅ Connected to $selectedType database"),
                          backgroundColor: const Color(0xFF4F46E5),
                          duration: const Duration(seconds: 2),
                        ),
                      );
                    }
                  },
                  child: const Text("Save & Connect"),
                ),
              ],
            );
          },
        );
      },
    );
  }

  /// Displays settings dialog to customize API Base URL.
  void _showSettingsDialog() {
    final controller = TextEditingController(text: _apiBaseUrl);
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Row(
          children: [
            Icon(Icons.settings, color: Color(0xFF4F46E5)),
            SizedBox(width: 8),
            Text("API Server Settings"),
          ],
        ),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              "Configure backend URL:",
              style: TextStyle(fontSize: 13, color: Colors.black54),
            ),
            const SizedBox(height: 8),
            TextField(
              controller: controller,
              decoration: const InputDecoration(
                border: OutlineInputBorder(),
                hintText: "http://10.0.2.2:5000",
                isDense: true,
              ),
            ),
            const SizedBox(height: 10),
            const Text(
              "• Android Emulator: http://10.0.2.2:5000\n• Desktop / Web: http://127.0.0.1:5000\n• Physical Phone: http://<YOUR_LAN_IP>:5000",
              style: TextStyle(fontSize: 11, color: Colors.grey),
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx),
            child: const Text("Cancel"),
          ),
          FilledButton(
            onPressed: () async {
              final newUrl = controller.text.trim();
              setState(() {
                _apiBaseUrl = newUrl;
              });
              try {
                final prefs = await SharedPreferences.getInstance();
                await prefs.setString('api_base_url', newUrl);
              } catch (_) {}
              if (ctx.mounted) Navigator.pop(ctx);
            },
            child: const Text("Save"),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Row(
          children: [
            Container(
              padding: const EdgeInsets.all(6),
              decoration: BoxDecoration(
                color: const Color(0xFF4F46E5).withValues(alpha: 0.1),
                borderRadius: BorderRadius.circular(8),
              ),
              child: const Icon(Icons.school, color: Color(0xFF4F46E5), size: 22),
            ),
            const SizedBox(width: 10),
            Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text(
                  "NL2SQL AI",
                  style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
                ),
                Row(
                  children: [
                    Container(
                      width: 6,
                      height: 6,
                      decoration: const BoxDecoration(
                        color: Colors.green,
                        shape: BoxShape.circle,
                      ),
                    ),
                    const SizedBox(width: 4),
                    Text(
                      _activeDbType,
                      style: const TextStyle(fontSize: 11, color: Colors.grey, fontWeight: FontWeight.w500),
                    ),
                  ],
                ),
              ],
            ),
          ],
        ),
        actions: [
          // Database Manager Action Button
          IconButton(
            icon: const Icon(Icons.storage_rounded),
            tooltip: "Database Connection",
            onPressed: _showDatabaseConnectionManager,
          ),
          // Server Settings Action Button
          IconButton(
            icon: const Icon(Icons.settings_outlined),
            tooltip: "API Settings",
            onPressed: _showSettingsDialog,
          ),
          // Sign Out Action Button
          IconButton(
            icon: const Icon(Icons.logout_rounded),
            tooltip: "Sign Out",
            onPressed: () async {
              final confirm = await showDialog<bool>(
                context: context,
                builder: (dCtx) => AlertDialog(
                  title: const Text("Sign Out"),
                  content: const Text("Are you sure you want to sign out?"),
                  actions: [
                    TextButton(
                      onPressed: () => Navigator.pop(dCtx, false),
                      child: const Text("Cancel"),
                    ),
                    FilledButton(
                      onPressed: () => Navigator.pop(dCtx, true),
                      child: const Text("Sign Out"),
                    ),
                  ],
                ),
              );
              if (confirm == true) {
                await FirebaseAuth.instance.signOut();
              }
            },
          ),
        ],
      ),
      body: SafeArea(
        child: Column(
          children: [
            // Sample prompt chips
            _buildSampleChips(),

            // Chat Messages ListView
            Expanded(
              child: ListView.builder(
                controller: _scrollController,
                padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
                itemCount: _messages.length,
                itemBuilder: (context, index) {
                  return _buildMessageItem(_messages[index]);
                },
              ),
            ),

            // Loading indicator bar
            if (_isLoading)
              Container(
                padding: const EdgeInsets.symmetric(vertical: 8, horizontal: 16),
                child: Row(
                  children: [
                    const SizedBox(
                      width: 16,
                      height: 16,
                      child: CircularProgressIndicator(
                        strokeWidth: 2,
                        valueColor: AlwaysStoppedAnimation<Color>(Color(0xFF4F46E5)),
                      ),
                    ),
                    const SizedBox(width: 10),
                    Text(
                      "Querying $_activeDbType database...",
                      style: TextStyle(fontSize: 12, color: Colors.grey.shade600, fontStyle: FontStyle.italic),
                    ),
                  ],
                ),
              ),

            // Bottom Input Field
            _buildInputArea(),
          ],
        ),
      ),
    );
  }

  /// Sample suggestion chips for fast testing during demos.
  Widget _buildSampleChips() {
    final samples = [
      "Top students in CS",
      "Marks > 80",
      "Average attendance by dept",
      "Kitne bacche hain CS mein?",
    ];

    return Container(
      height: 42,
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: ListView.separated(
        scrollDirection: Axis.horizontal,
        padding: const EdgeInsets.symmetric(horizontal: 14),
        itemCount: samples.length,
        separatorBuilder: (context, index) => const SizedBox(width: 8),
        itemBuilder: (context, index) {
          final sample = samples[index];
          return ActionChip(
            label: Text(sample, style: const TextStyle(fontSize: 12)),
            backgroundColor: Colors.white,
            side: BorderSide(color: Colors.grey.shade300),
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
            onPressed: () => _sendMessage(sample),
          );
        },
      ),
    );
  }

  /// Builds a single chat message bubble.
  Widget _buildMessageItem(ChatMessage msg) {
    if (msg.isUser) {
      return Align(
        alignment: Alignment.centerRight,
        child: Container(
          margin: const EdgeInsets.symmetric(vertical: 6),
          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
          constraints: BoxConstraints(maxWidth: MediaQuery.of(context).size.width * 0.78),
          decoration: BoxDecoration(
            color: const Color(0xFF4F46E5),
            borderRadius: const BorderRadius.only(
              topLeft: Radius.circular(16),
              topRight: Radius.circular(16),
              bottomLeft: Radius.circular(16),
              bottomRight: Radius.circular(4),
            ),
            boxShadow: [
              BoxShadow(
                color: const Color(0xFF4F46E5).withValues(alpha: 0.2),
                blurRadius: 4,
                offset: const Offset(0, 2),
              ),
            ],
          ),
          child: Text(
            msg.text,
            style: const TextStyle(color: Colors.white, fontSize: 14, height: 1.3),
          ),
        ),
      );
    }

    // Assistant response bubble
    return Align(
      alignment: Alignment.centerLeft,
      child: Container(
        margin: const EdgeInsets.symmetric(vertical: 6),
        padding: const EdgeInsets.all(12),
        constraints: BoxConstraints(maxWidth: MediaQuery.of(context).size.width * 0.92),
        decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: const BorderRadius.only(
            topLeft: Radius.circular(16),
            topRight: Radius.circular(16),
            bottomLeft: Radius.circular(4),
            bottomRight: Radius.circular(16),
          ),
          border: Border.all(
            color: msg.isError ? Colors.red.shade200 : const Color(0xFFE2E8F0),
          ),
          boxShadow: [
            BoxShadow(
              color: Colors.black.withValues(alpha: 0.04),
              blurRadius: 6,
              offset: const Offset(0, 2),
            ),
          ],
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Header tag
            Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Icon(
                  msg.isError ? Icons.error_outline : Icons.auto_awesome,
                  size: 14,
                  color: msg.isError ? Colors.red : const Color(0xFF4F46E5),
                ),
                const SizedBox(width: 4),
                Text(
                  msg.isError ? "Error" : (msg.intent == "query" ? "Query Result" : "AI Assistant"),
                  style: TextStyle(
                    fontSize: 11,
                    fontWeight: FontWeight.bold,
                    color: msg.isError ? Colors.red : const Color(0xFF4F46E5),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 6),

            // AI Explanation / Response Text
            Text(
              msg.text,
              style: TextStyle(
                fontSize: 13.5,
                color: msg.isError ? Colors.red.shade900 : const Color(0xFF1E293B),
                height: 1.35,
              ),
            ),

            // Generated SQL Query Box
            if (msg.sql != null && msg.sql!.isNotEmpty) ...[
              const SizedBox(height: 8),
              Container(
                width: double.infinity,
                padding: const EdgeInsets.all(8),
                decoration: BoxDecoration(
                  color: const Color(0xFF1E293B), // Dark slate
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text(
                      "⚡ SQL",
                      style: TextStyle(color: Color(0xFF94A3B8), fontSize: 10, fontWeight: FontWeight.bold),
                    ),
                    const SizedBox(height: 4),
                    SelectableText(
                      msg.sql!,
                      style: const TextStyle(
                        color: Color(0xFF38BDF8), // Cyan code highlight
                        fontSize: 11.5,
                        fontFamily: 'monospace',
                      ),
                    ),
                  ],
                ),
              ),
            ],

            // Tabular Data Result
            if (msg.data != null && msg.data!.isNotEmpty) ...[
              const SizedBox(height: 10),
              _buildDataTable(msg.data!),
            ],
          ],
        ),
      ),
    );
  }

  /// Builds a scrollable Material DataTable from JSON database records.
  Widget _buildDataTable(List<Map<String, dynamic>> records) {
    if (records.isEmpty) return const SizedBox.shrink();

    final columns = records.first.keys.toList();

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          "📋 Results (${records.length} records):",
          style: const TextStyle(fontSize: 11.5, fontWeight: FontWeight.bold, color: Color(0xFF475569)),
        ),
        const SizedBox(height: 6),
        Container(
          decoration: BoxDecoration(
            border: Border.all(color: const Color(0xFFE2E8F0)),
            borderRadius: BorderRadius.circular(8),
          ),
          child: ClipRRect(
            borderRadius: BorderRadius.circular(8),
            child: SingleChildScrollView(
              scrollDirection: Axis.horizontal,
              child: DataTable(
                headingRowHeight: 34,
                dataRowMinHeight: 30,
                dataRowMaxHeight: 36,
                headingRowColor: WidgetStateProperty.all(const Color(0xFFF1F5F9)),
                columnSpacing: 18,
                horizontalMargin: 12,
                columns: columns.map((col) {
                  final cleanCol = col.replaceAll('_', ' ').toUpperCase();
                  return DataColumn(
                    label: Text(
                      cleanCol,
                      style: const TextStyle(fontSize: 11, fontWeight: FontWeight.bold, color: Color(0xFF334155)),
                    ),
                  );
                }).toList(),
                rows: records.map((row) {
                  return DataRow(
                    cells: columns.map((col) {
                      final val = row[col];
                      return DataCell(
                        Text(
                          val?.toString() ?? "-",
                          style: const TextStyle(fontSize: 11.5, color: Color(0xFF1E293B)),
                        ),
                      );
                    }).toList(),
                  );
                }).toList(),
              ),
            ),
          ),
        ),
      ],
    );
  }

  /// Bottom text input bar with send button.
  Widget _buildInputArea() {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
      decoration: const BoxDecoration(
        color: Colors.white,
        border: Border(top: BorderSide(color: Color(0xFFE2E8F0))),
      ),
      child: Row(
        children: [
          Expanded(
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 14),
              decoration: BoxDecoration(
                color: const Color(0xFFF1F5F9),
                borderRadius: BorderRadius.circular(24),
              ),
              child: TextField(
                controller: _textController,
                textInputAction: TextInputAction.send,
                onSubmitted: (_) => _sendMessage(),
                decoration: const InputDecoration(
                  hintText: "Ask in English, Hindi, or Hinglish...",
                  hintStyle: TextStyle(fontSize: 13, color: Colors.grey),
                  border: InputBorder.none,
                  isDense: true,
                  contentPadding: EdgeInsets.symmetric(vertical: 10),
                ),
              ),
            ),
          ),
          const SizedBox(width: 8),
          IconButton.filled(
            style: IconButton.styleFrom(
              backgroundColor: const Color(0xFF4F46E5),
              foregroundColor: Colors.white,
            ),
            icon: const Icon(Icons.send_rounded, size: 20),
            onPressed: _isLoading ? null : () => _sendMessage(),
          ),
        ],
      ),
    );
  }
}
