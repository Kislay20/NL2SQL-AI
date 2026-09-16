"""Backend REST API Server for NL2SQL AI using Flask and Flask-CORS.

Provides a decoupled HTTP API endpoint for mobile clients, web dashboards,
and third-party integrations to interact with the LangGraph multi-agent pipeline.
"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from flask import Flask, jsonify, request
from flask_cors import CORS
import pandas as pd

from ai.agent import run_agent
from ai.explainer import explain_sql
from database.database import validate_database_connection
from sql.executor import execute_safe_query

logger = logging.getLogger(__name__)


def create_app() -> Flask:
    """Create and configure the Flask application with CORS support."""
    app = Flask(__name__)
    CORS(app)

    @app.route("/api/health", methods=["GET"])
    def health_check():
        """Health check endpoint confirming API availability."""
        return jsonify({
            "status": "healthy",
            "service": "NL2SQL AI REST API",
            "version": "1.0.0",
        }), 200

    @app.route("/api/test-connection", methods=["POST"])
    def test_connection():
        """Test database connection via SQLAlchemy by executing 'SELECT 1;'.

        Expected JSON payload:
        {
            "db_uri": "mysql+pymysql://user:pass@host:port/dbname"
            (or postgresql+psycopg2://... or sqlite:///college.db)
        }

        Returns:
            {"status": "success", "message": "..."} or {"status": "error", "error": "..."}.
        """
        if not request.is_json:
            return jsonify({"status": "error", "error": "Request body must be valid JSON."}), 400

        payload = request.get_json(silent=True)
        if not payload or not isinstance(payload, dict):
            return jsonify({"status": "error", "error": "Invalid or missing JSON payload."}), 400

        db_uri = payload.get("db_uri")
        if not db_uri or not str(db_uri).strip():
            return jsonify({"status": "error", "error": "The 'db_uri' field is required."}), 400

        clean_uri = str(db_uri).strip()
        try:
            is_valid, err_msg = validate_database_connection(clean_uri)
            if is_valid:
                return jsonify({
                    "status": "success",
                    "message": "Database connection verified successfully!",
                    "db_uri": clean_uri,
                }), 200
            else:
                return jsonify({
                    "status": "error",
                    "error": err_msg or "Failed to connect to database.",
                }), 400
        except Exception as exc:
            return jsonify({
                "status": "error",
                "error": f"Connection test failed: {str(exc)}",
            }), 400

    @app.route("/api/query", methods=["POST"])
    def process_query():
        """Process natural language query through the LangGraph multi-agent workflow.

        Expected JSON payload:
        {
            "query": "Show top 5 students based on marks",
            "db_uri": "sqlite:///college.db"  (optional, defaults to sqlite:///college.db)
        }

        Returns:
            JSON response with intent, response, sql, is_valid, and data.
        """
        if not request.is_json:
            return jsonify({
                "error": "Request body must be valid JSON.",
                "intent": None,
                "response": None,
                "sql": None,
                "is_valid": False,
                "data": None,
            }), 400

        payload = request.get_json(silent=True)
        if not payload or not isinstance(payload, dict):
            return jsonify({
                "error": "Invalid or missing JSON payload.",
                "intent": None,
                "response": None,
                "sql": None,
                "is_valid": False,
                "data": None,
            }), 400

        user_query = payload.get("query")
        if not user_query or not str(user_query).strip():
            return jsonify({
                "error": "The 'query' field is required and cannot be empty.",
                "intent": None,
                "response": None,
                "sql": None,
                "is_valid": False,
                "data": None,
            }), 400

        db_uri = payload.get("db_uri") or "sqlite:///college.db"
        user_query_str = str(user_query).strip()

        try:
            # 1. Route prompt through LangGraph multi-agent workflow
            agent_state = run_agent(question=user_query_str, db_uri=db_uri)

            intent = agent_state.get("intent", "query")

            # 2. Handle conversational chit-chat responses
            if intent == "conversational":
                reply = agent_state.get(
                    "response",
                    "Hello! I am NL2SQL AI. You can ask me queries about the college database.",
                )
                return jsonify({
                    "intent": "conversational",
                    "response": reply,
                    "sql": None,
                    "is_valid": True,
                    "data": None,
                }), 200

            # 3. Handle database queries
            sql = agent_state.get("sql")
            is_valid = agent_state.get("is_valid", False)

            if not is_valid:
                val_error = agent_state.get("error") or "SQL validation failed."
                return jsonify({
                    "intent": "query",
                    "response": val_error,
                    "sql": sql,
                    "is_valid": False,
                    "data": None,
                    "error": val_error,
                }), 400

            # 4. Safe execution of validated query
            success, df, exec_error = execute_safe_query(sql_query=sql, db_uri=db_uri)
            if not success:
                return jsonify({
                    "intent": "query",
                    "response": f"Database execution error: {exec_error}",
                    "sql": sql,
                    "is_valid": False,
                    "data": None,
                    "error": exec_error,
                }), 400

            # 5. Format results to list of dicts
            data_rows = []
            if df is not None and not df.empty:
                # Replace NaN with None for clean JSON serialization
                clean_df = df.where(pd.notnull(df), None)
                data_rows = clean_df.to_dict(orient="records")

            # 6. Generate AI Explanation
            explanation = explain_sql(question=user_query_str, sql_query=sql)

            return jsonify({
                "intent": "query",
                "response": explanation,
                "sql": sql,
                "is_valid": True,
                "data": data_rows,
            }), 200

        except Exception as exc:
            logger.error("Unhandled API error processing query: %s", exc, exc_info=True)
            return jsonify({
                "error": f"Internal Server Error: {str(exc)}",
                "intent": None,
                "response": None,
                "sql": None,
                "is_valid": False,
                "data": None,
            }), 500

    return app


# Default application instance for WSGI runners
app = create_app()


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    host = os.getenv("HOST", "0.0.0.0")
    print(f"🚀 NL2SQL AI Flask REST API running on http://{host}:{port}")
    app.run(host=host, port=port, debug=False)
