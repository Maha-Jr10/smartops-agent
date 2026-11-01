"""Registre des outils exposés au LLM sous forme de JSON Schema."""

from __future__ import annotations

TOOL_SCHEMAS: list[dict] = [  # type: ignore[type-arg]
    {
        "type": "function",
        "function": {
            "name": "search_crm",
            "description": "Recherche dans la base CRM (clients, leads, projets).",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Texte de recherche (2-100 caractères)",
                    },
                    "entity": {
                        "type": "string",
                        "enum": ["lead", "client", "project"],
                        "description": "Type d'entité à rechercher",
                    },
                },
                "required": ["query", "entity"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_invoice_status",
            "description": "Retourne le statut de paiement d'une facture ou d'un projet.",
            "parameters": {
                "type": "object",
                "properties": {
                    "invoice_id": {"type": "string", "description": "Identifiant de la facture"},
                    "project_id": {"type": "string", "description": "Identifiant du projet"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "calculate_commission",
            "description": "Calcule la commission d'un membre de l'équipe sur un projet.",
            "parameters": {
                "type": "object",
                "properties": {
                    "project_id": {"type": "string"},
                    "person_id": {"type": "string"},
                },
                "required": ["project_id", "person_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "draft_followup",
            "description": "Génère un brouillon de message de relance (non envoyé).",
            "parameters": {
                "type": "object",
                "properties": {
                    "lead_id": {"type": "string"},
                    "tone": {
                        "type": "string",
                        "enum": ["neutral", "friendly", "formal"],
                    },
                },
                "required": ["lead_id", "tone"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "request_human_action",
            "description": (
                "Soumet une action à effet réel pour validation humaine. "
                "Utiliser pour : send_email, mark_commission_paid, change_price, "
                "quote_price_to_client, delete_record."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {"type": "string"},
                    "reason": {"type": "string"},
                    "payload": {"type": "object"},
                },
                "required": ["action", "reason", "payload"],
            },
        },
    },
]
