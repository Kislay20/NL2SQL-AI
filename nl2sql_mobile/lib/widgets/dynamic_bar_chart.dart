import 'dart:math';
import 'package:fl_chart/fl_chart.dart';
import 'package:flutter/material.dart';

/// A dynamic BarChart widget that analyzes JSON records returned by SQL queries,
/// identifies numeric metrics and categorical labels, and displays an interactive,
/// modern BarChart matching the NL2SQL AI theme.
class DynamicBarChart extends StatefulWidget {
  final List<Map<String, dynamic>> records;

  const DynamicBarChart({
    super.key,
    required this.records,
  });

  /// Static helper to check whether a dataset has enough structure for a bar chart.
  static bool canVisualize(List<Map<String, dynamic>>? records) {
    if (records == null || records.isEmpty) return false;
    final numericCols = _detectNumericColumns(records);
    return numericCols.isNotEmpty;
  }

  static List<String> _detectNumericColumns(List<Map<String, dynamic>> records) {
    if (records.isEmpty) return [];
    final allKeys = records.first.keys.toList();
    final numericKeys = <String>[];

    for (final key in allKeys) {
      int numericCount = 0;
      int nonNullCount = 0;

      for (final row in records) {
        final val = row[key];
        if (val != null) {
          nonNullCount++;
          if (val is num) {
            numericCount++;
          } else if (val is String && double.tryParse(val) != null) {
            numericCount++;
          }
        }
      }

      if (nonNullCount > 0 && numericCount == nonNullCount) {
        numericKeys.add(key);
      }
    }

    return numericKeys;
  }

  @override
  State<DynamicBarChart> createState() => _DynamicBarChartState();
}

class _DynamicBarChartState extends State<DynamicBarChart> {
  late List<String> _numericColumns;
  late String _selectedMetric;
  late String _labelColumn;

  @override
  void initState() {
    super.initState();
    _initColumns();
  }

  @override
  void didUpdateWidget(covariant DynamicBarChart oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.records != widget.records) {
      _initColumns();
    }
  }

  void _initColumns() {
    _numericColumns = DynamicBarChart._detectNumericColumns(widget.records);
    if (_numericColumns.isEmpty) return;

    // Pick best metric column: prioritize marks, attendance, score, avg, count, percentage
    _selectedMetric = _pickBestMetricColumn(_numericColumns);
    _labelColumn = _pickBestLabelColumn(widget.records, _numericColumns);
  }

  String _pickBestMetricColumn(List<String> numericCols) {
    final priorityKeywords = [
      'mark',
      'score',
      'attendance',
      'pct',
      'percent',
      'avg',
      'count',
      'total',
      'sum',
      'age',
    ];

    // Check priority keywords on non-ID columns first
    for (final keyword in priorityKeywords) {
      for (final col in numericCols) {
        final lower = col.toLowerCase();
        if (!lower.endsWith('_id') && lower != 'id' && lower.contains(keyword)) {
          return col;
        }
      }
    }

    // Fallback: first non-ID column
    for (final col in numericCols) {
      final lower = col.toLowerCase();
      if (!lower.endsWith('_id') && lower != 'id') {
        return col;
      }
    }

    // Last resort: first numeric column
    return numericCols.first;
  }

  String _pickBestLabelColumn(
    List<Map<String, dynamic>> records,
    List<String> numericCols,
  ) {
    if (records.isEmpty) return '';
    final allKeys = records.first.keys.toList();
    final nonNumericKeys = allKeys.where((k) => !numericCols.contains(k)).toList();

    final labelKeywords = [
      'name',
      'student_name',
      'subject_name',
      'department',
      'dept',
      'subject',
      'title',
      'label',
      'student',
    ];

    for (final keyword in labelKeywords) {
      for (final col in nonNumericKeys) {
        if (col.toLowerCase().contains(keyword)) {
          return col;
        }
      }
    }

    if (nonNumericKeys.isNotEmpty) {
      return nonNumericKeys.first;
    }

    // If all columns are numeric, pick an ID column as label, or the first column
    for (final col in allKeys) {
      if (col.toLowerCase().endsWith('_id') || col.toLowerCase() == 'id') {
        return col;
      }
    }

    return allKeys.first;
  }

  double _parseNumber(dynamic val) {
    if (val == null) return 0.0;
    if (val is num) return val.toDouble();
    if (val is String) {
      return double.tryParse(val) ?? 0.0;
    }
    return 0.0;
  }

  String _cleanHeader(String col) {
    return col.replaceAll('_', ' ').toUpperCase();
  }

  @override
  Widget build(BuildContext context) {
    if (widget.records.isEmpty || _numericColumns.isEmpty) {
      return const SizedBox.shrink();
    }

    final records = widget.records;
    final metricValues = records.map((r) => _parseNumber(r[_selectedMetric])).toList();

    double maxVal = metricValues.isEmpty ? 0.0 : metricValues.reduce(max);
    double minVal = metricValues.isEmpty ? 0.0 : metricValues.reduce(min);
    double avgVal = metricValues.isEmpty
        ? 0.0
        : metricValues.reduce((a, b) => a + b) / metricValues.length;

    // Sane upper bound with breathing room
    double maxY = maxVal <= 0 ? 10.0 : (maxVal * 1.2);
    if (maxVal <= 100 && maxVal > 70 && maxY < 100) {
      maxY = 100.0;
    }

    // Build bar groups
    final barGroups = <BarChartGroupData>[];
    for (int i = 0; i < records.length; i++) {
      final val = metricValues[i];
      barGroups.add(
        BarChartGroupData(
          x: i,
          barRods: [
            BarChartRodData(
              toY: val,
              width: records.length > 8 ? 14 : (records.length > 4 ? 18 : 24),
              gradient: const LinearGradient(
                colors: [Color(0xFF4F46E5), Color(0xFF818CF8)],
                begin: Alignment.bottomCenter,
                end: Alignment.topCenter,
              ),
              borderRadius: const BorderRadius.vertical(top: Radius.circular(6)),
              backDrawRodData: BackgroundBarChartRodData(
                show: true,
                toY: maxY,
                color: const Color(0xFFF1F5F9),
              ),
            ),
          ],
        ),
      );
    }

    final interval = (maxY / 4) > 0 ? (maxY / 4) : 1.0;
    final bool needsHorizontalScroll = records.length > 5;
    final double dynamicWidth = max(260.0, records.length * 48.0);

    return Container(
      margin: const EdgeInsets.only(top: 12),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: const Color(0xFFFAFAFE),
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: const Color(0xFFE2E8F0)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Header: Title + Metric Selector
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Row(
                children: [
                  const Icon(Icons.bar_chart_rounded, size: 18, color: Color(0xFF4F46E5)),
                  const SizedBox(width: 6),
                  Text(
                    "Chart: ${_cleanHeader(_selectedMetric)}",
                    style: const TextStyle(
                      fontSize: 12,
                      fontWeight: FontWeight.bold,
                      color: Color(0xFF1E293B),
                    ),
                  ),
                ],
              ),

              // Metric Switcher if multiple numeric columns exist
              if (_numericColumns.length > 1)
                DropdownButtonHideUnderline(
                  child: DropdownButton<String>(
                    value: _selectedMetric,
                    isDense: true,
                    icon: const Icon(Icons.tune_rounded, size: 15, color: Color(0xFF4F46E5)),
                    items: _numericColumns.map((col) {
                      return DropdownMenuItem<String>(
                        value: col,
                        child: Text(
                          _cleanHeader(col),
                          style: const TextStyle(fontSize: 11, fontWeight: FontWeight.w600),
                        ),
                      );
                    }).toList(),
                    onChanged: (newMetric) {
                      if (newMetric != null) {
                        setState(() {
                          _selectedMetric = newMetric;
                        });
                      }
                    },
                  ),
                ),
            ],
          ),

          const SizedBox(height: 4),

          // Mini statistics summary chips
          Row(
            children: [
              _buildStatChip("Avg", avgVal.toStringAsFixed(1)),
              const SizedBox(width: 6),
              _buildStatChip("Max", maxVal.toStringAsFixed(1)),
              const SizedBox(width: 6),
              _buildStatChip("Min", minVal.toStringAsFixed(1)),
            ],
          ),

          const SizedBox(height: 14),

          // Chart Display (Scrollable if records > 5)
          SizedBox(
            height: 180,
            child: LayoutBuilder(
              builder: (context, constraints) {
                final chartWidget = SizedBox(
                  width: needsHorizontalScroll ? dynamicWidth : constraints.maxWidth,
                  child: BarChart(
                    BarChartData(
                      maxY: maxY,
                      minY: 0,
                      barTouchData: BarTouchData(
                        enabled: true,
                        touchTooltipData: BarTouchTooltipData(
                          getTooltipColor: (group) => const Color(0xFF1E293B),
                          tooltipBorderRadius: BorderRadius.circular(8),
                          tooltipPadding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                          getTooltipItem: (group, groupIndex, rod, rodIndex) {
                            final row = records[group.x];
                            final label = row[_labelColumn]?.toString() ?? '#${group.x + 1}';
                            final valStr = rod.toY % 1 == 0
                                ? rod.toY.toInt().toString()
                                : rod.toY.toStringAsFixed(1);
                            return BarTooltipItem(
                              '$label\n',
                              const TextStyle(
                                color: Colors.white,
                                fontWeight: FontWeight.bold,
                                fontSize: 11.5,
                              ),
                              children: [
                                TextSpan(
                                  text: '${_cleanHeader(_selectedMetric)}: $valStr',
                                  style: const TextStyle(
                                    color: Color(0xFF38BDF8),
                                    fontWeight: FontWeight.w500,
                                    fontSize: 10.5,
                                  ),
                                ),
                              ],
                            );
                          },
                        ),
                      ),
                      titlesData: FlTitlesData(
                        show: true,
                        topTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
                        rightTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
                        leftTitles: AxisTitles(
                          sideTitles: SideTitles(
                            showTitles: true,
                            reservedSize: 34,
                            interval: interval,
                            getTitlesWidget: (val, meta) {
                              if (val == 0 || val > maxY) return const SizedBox.shrink();
                              final display = val % 1 == 0
                                  ? val.toInt().toString()
                                  : val.toStringAsFixed(1);
                              return SideTitleWidget(
                                meta: meta,
                                space: 4,
                                child: Text(
                                  display,
                                  style: const TextStyle(
                                    fontSize: 9,
                                    color: Color(0xFF94A3B8),
                                    fontWeight: FontWeight.w500,
                                  ),
                                ),
                              );
                            },
                          ),
                        ),
                        bottomTitles: AxisTitles(
                          sideTitles: SideTitles(
                            showTitles: true,
                            reservedSize: 32,
                            getTitlesWidget: (val, meta) {
                              final idx = val.toInt();
                              if (idx < 0 || idx >= records.length) {
                                return const SizedBox.shrink();
                              }
                              final rawLabel = records[idx][_labelColumn]?.toString() ?? '#${idx + 1}';
                              final shortLabel = rawLabel.length > 8
                                  ? '${rawLabel.substring(0, 7)}…'
                                  : rawLabel;
                              return SideTitleWidget(
                                meta: meta,
                                space: 4,
                                child: Text(
                                  shortLabel,
                                  style: const TextStyle(
                                    fontSize: 9.5,
                                    fontWeight: FontWeight.w600,
                                    color: Color(0xFF64748B),
                                  ),
                                ),
                              );
                            },
                          ),
                        ),
                      ),
                      gridData: FlGridData(
                        show: true,
                        drawVerticalLine: false,
                        horizontalInterval: interval,
                        getDrawingHorizontalLine: (value) => const FlLine(
                          color: Color(0xFFE2E8F0),
                          strokeWidth: 0.8,
                        ),
                      ),
                      borderData: FlBorderData(show: false),
                      barGroups: barGroups,
                    ),
                  ),
                );

                if (needsHorizontalScroll) {
                  return SingleChildScrollView(
                    scrollDirection: Axis.horizontal,
                    child: chartWidget,
                  );
                }
                return chartWidget;
              },
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildStatChip(String label, String value) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
      decoration: BoxDecoration(
        color: const Color(0xFFEEF2FF),
        borderRadius: BorderRadius.circular(4),
      ),
      child: Text(
        "$label: $value",
        style: const TextStyle(
          fontSize: 9.5,
          fontWeight: FontWeight.w600,
          color: Color(0xFF4F46E5),
        ),
      ),
    );
  }
}
