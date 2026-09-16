"""Multi-Agent Orchestration module using LangGraph for NL2SQL AI.

Coordinates a multi-agent StateGraph comprising:
1. Router Node: Distinguishes between database queries and conversational chit-chat.
2. Conversational Node: Direct LLM responses for greetings and general inquiries.
3. Coder Node: Generates schema-aware SQL queries using Gemini.
4. Validator Node: Static schema inspection (EXPLAIN QUERY PLAN) and safety AST checks,
   with automated self-correction loops if errors are detected.
"""

from __future__ import annotations

import logging
import re
import sys
from pathlib import Path
from typing import Any, Dict, Optional, TypedDict

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from langgraph.graph import END, START, StateGraph

from ai.gemini import GeminiClient, GeminiError, get_gemini_client
from ai.parser import extract_sql
from ai.prompts import (
    SQL_GENERATION_SYSTEM_INSTRUCTION,
    build_sql_prompt,
)
from database.database import get_schema_prompt_context
from sql.validator import validate_query

logger = logging.getLogger(__name__)

# Fast heuristic keywords for conversational intent
CONVERSATIONAL_PATTERNS = [
    r"^\s*(hi|hello|hey|hola|namaste|namaskar)\b",
    r"^\s*how\s+are\s+you\b",
    r"^\s*who\s+are\s+you\b",
    r"^\s*what\s+can\s+you\s+do\b",
    r"^\s*(help|good\s+morning|good\s+evening|good\s+afternoon)\b",
    r"^\s*(thank\s+you|thanks|thx)\b",
    r"^\s*(bye|goodbye|see\s+you)\b",
    r"^\s*(kaise\s+ho|kya\s+hal\s+hai|aap\s+kaun\s+ho)\b",
]

# Database entity indicator keywords (override conversational triggers)
DB_ENTITY_KEYWORDS = {
    "student", "students", "marks", "grade", "grades", "attendance", "department",
    "course", "subject", "subjects", "faculty", "score", "scores", "percentage",
    "select", "table", "average", "avg", "highest", "lowest", "count", "total",
    "kitne", "bachhe", "bacche", "dikhao", "top", "list",
}


# ----------------------------------------------------------------------
# State Definition
# ----------------------------------------------------------------------

class AgentState(TypedDict, total=False):
    """Represents the shared context across the LangGraph multi-agent pipeline."""
    question: str
    db_path: Optional[str]
    db_uri: Optional[str]
    intent: str  # "query" | "conversational"
    sql: Optional[str]
    is_valid: bool
    error: Optional[str]
    response: Optional[str]
    validation_attempts: int


# ----------------------------------------------------------------------
# Node 1: Router Node
# ----------------------------------------------------------------------

def classify_intent(question: str, client: Optional[GeminiClient] = None) -> str:
    """Classify user input into 'query' or 'conversational'.

    Uses hybrid heuristic pattern matching with LLM classification fallback.
    """
    if not question or not question.strip():
        return "conversational"

    cleaned = question.strip().lower()
    words = set(re.findall(r"\b\w+\b", cleaned))

    # If any database-specific entity keyword is present, treat as query
    if words.intersection(DB_ENTITY_KEYWORDS):
        return "query"

    # Check fast conversational regex patterns
    for pattern in CONVERSATIONAL_PATTERNS:
        if re.search(pattern, cleaned):
            return "conversational"

    # For ambiguous inputs, consult LLM
    try:
        active_client = client or get_gemini_client()
        prompt = (
            "Determine if the user's message is asking for data/records from a college database "
            "or is a general conversational greeting/chit-chat.\n\n"
            f"User message: \"{question}\"\n\n"
            "Respond with strictly one word: either 'QUERY' or 'CONVERSATIONAL'."
        )
        resp = active_client.generate_text(prompt=prompt, temperature=0.0).strip().upper()
        if "CONVERSATIONAL" in resp:
            return "conversational"
        return "query"
    except Exception as exc:
        logger.warning("Router LLM classification failed, defaulting to query: %s", exc)
        return "query"


def router_node(state: AgentState) -> AgentState:
    """Analyze the user's natural language question and route appropriately."""
    question = state.get("question", "")
    intent = classify_intent(question)
    return {**state, "intent": intent}


# ----------------------------------------------------------------------
# Node 2: Conversational Node
# ----------------------------------------------------------------------

def conversational_node(state: AgentState) -> AgentState:
    """Generate a friendly natural language response for general conversational inputs."""
    question = state.get("question", "")
    fallback_response = (
        "👋 Hello! I am **NL2SQL AI**, your intelligent database assistant for the college system.\n\n"
        "You can ask me questions about students, departments, marks, and attendance in "
        "English, Hindi, or Hinglish! For example:\n"
        "- *'Show top 5 students in Computer Science'*  \n"
        "- *'Wo students dikhao jinke marks 80 se zyada hain'*  \n"
        "- *'What is the average attendance per department?'*"
    )

    try:
        active_client = get_gemini_client()
        prompt = (
            "You are NL2SQL AI, a helpful and polite database assistant for a college system. "
            "Respond naturally to the following greeting or conversational remark. "
            "Keep it brief (1-3 sentences) and invite them to ask a question about students, marks, or attendance.\n\n"
            f"User: {question}"
        )
        response_text = active_client.generate_text(
            prompt=prompt,
            temperature=0.3,
            max_output_tokens=250,
        )
        reply = response_text.strip() if response_text else fallback_response
    except Exception as exc:
        logger.warning("Conversational LLM node failed: %s", exc)
        reply = fallback_response

    return {
        **state,
        "response": reply,
        "sql": None,
        "is_valid": True,
        "error": None,
    }


# ----------------------------------------------------------------------
# Node 3: Coder Node
# ----------------------------------------------------------------------

def coder_node(state: AgentState) -> AgentState:
    """Generate or refine a SQLite query based on schema and previous validation feedback."""
    question = state.get("question", "")
    db_path = state.get("db_path")
    previous_error = state.get("error")
    attempts = state.get("validation_attempts", 0)

    # 1. Retrieve dynamic schema context
    schema_context = get_schema_prompt_context(db_path=db_path)

    # 2. Build SQL prompt with retry feedback if repairing
    base_prompt = build_sql_prompt(question=question, schema_context=schema_context)
    if previous_error and attempts > 0:
        repair_instruction = (
            f"\n\n[SELF-CORRECTION NOTICE]\n"
            f"Your previous query was: {state.get('sql', '')}\n"
            f"It failed schema/syntax validation with the following error: {previous_error}\n"
            f"Please correct the query to ensure all referenced tables and columns exist in the schema."
        )
        full_prompt = base_prompt + repair_instruction
    else:
        full_prompt = base_prompt

    # 3. Invoke Gemini
    active_client = get_gemini_client()
    raw_response = active_client.generate_text(
        prompt=full_prompt,
        system_instruction=SQL_GENERATION_SYSTEM_INSTRUCTION,
        temperature=0.0,
    )

    cleaned_sql = extract_sql(raw_response)
    return {
        **state,
        "sql": cleaned_sql,
        "validation_attempts": attempts + 1,
    }


# ----------------------------------------------------------------------
# Node 4: Validator Node
# ----------------------------------------------------------------------

def validator_node(state: AgentState) -> AgentState:
    """Review generated SQL against schema and syntax guardrails using EXPLAIN QUERY PLAN."""
    sql = state.get("sql", "")
    db_path = state.get("db_path")
    db_uri = state.get("db_uri")

    if not sql or not sql.strip():
        return {
            **state,
            "is_valid": False,
            "error": "No SQL query was generated.",
        }

    is_valid, err_msg = validate_query(sql_query=sql, db_path=db_path, db_uri=db_uri)
    return {
        **state,
        "is_valid": is_valid,
        "error": None if is_valid else err_msg,
    }


# ----------------------------------------------------------------------
# Conditional Edge Functions
# ----------------------------------------------------------------------

def route_decision(state: AgentState) -> str:
    """Conditional routing: query -> coder, conversational -> conversational."""
    return "conversational" if state.get("intent") == "conversational" else "coder"


def validate_decision(state: AgentState) -> str:
    """Conditional validation: retry coder if invalid (max 2 attempts), else end."""
    if state.get("is_valid", False):
        return "end"
    if state.get("validation_attempts", 0) < 2:
        return "coder"
    return "end"


# ----------------------------------------------------------------------
# Graph Compilation
# ----------------------------------------------------------------------

def create_agent_graph() -> Any:
    """Construct and compile the multi-agent StateGraph workflow."""
    workflow = StateGraph(AgentState)

    # Register Nodes
    workflow.add_node("router", router_node)
    workflow.add_node("conversational", conversational_node)
    workflow.add_node("coder", coder_node)
    workflow.add_node("validator", validator_node)

    # Register Edges
    workflow.add_edge(START, "router")
    workflow.add_conditional_edges(
        "router",
        route_decision,
        {
            "conversational": "conversational",
            "coder": "coder",
        },
    )
    workflow.add_edge("conversational", END)
    workflow.add_edge("coder", "validator")
    workflow.add_conditional_edges(
        "validator",
        validate_decision,
        {
            "coder": "coder",
            "end": END,
        },
    )

    return workflow.compile()


# Singleton compiled graph
_AGENT_GRAPH = None


def get_agent_graph():
    """Return cached compiled StateGraph instance."""
    global _AGENT_GRAPH
    if _AGENT_GRAPH is None:
        _AGENT_GRAPH = create_agent_graph()
    return _AGENT_GRAPH


def run_agent(
    question: str,
    db_path: Optional[str] = None,
    db_uri: Optional[str] = None,
) -> AgentState:
    """Execute the multi-agent orchestration workflow on a user prompt.

    Args:
        question: User prompt in English, Hindi, or Hinglish.
        db_path: Optional SQLite database file path.
        db_uri: Optional database connection URI.

    Returns:
        Final AgentState dictionary with intent, sql, is_valid, error, or response.
    """
    if not question or not question.strip():
        return {
            "question": question,
            "db_path": db_path,
            "db_uri": db_uri,
            "intent": "conversational",
            "sql": None,
            "is_valid": True,
            "error": None,
            "response": "Please ask a question or enter a database query.",
            "validation_attempts": 0,
        }

    graph = get_agent_graph()
    initial_state: AgentState = {
        "question": question,
        "db_path": db_path,
        "db_uri": db_uri,
        "intent": "query",
        "sql": None,
        "is_valid": False,
        "error": None,
        "response": None,
        "validation_attempts": 0,
    }

    try:
        final_state = graph.invoke(initial_state)
        return final_state
    except Exception as exc:
        logger.error("LangGraph agent invocation error: %s", exc)
        # Fallback to direct conversational or error state
        return {
            "question": question,
            "db_path": db_path,
            "db_uri": db_uri,
            "intent": "query",
            "sql": None,
            "is_valid": False,
            "error": f"Agent workflow error: {exc}",
            "response": None,
            "validation_attempts": 1,
        }


__all__ = [
    "AgentState",
    "classify_intent",
    "create_agent_graph",
    "get_agent_graph",
    "run_agent",
]
