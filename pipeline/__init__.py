"""SentinelAI pipeline: residual -> calibrated p(leak) -> cost-based decision -> grounded rationale.

Reads the frozen knowledge graph (knowledge_graph v1.0.0) through queries.py only and writes runtime
RiskAssessment / Decision nodes into a copy of it for audit.
"""
