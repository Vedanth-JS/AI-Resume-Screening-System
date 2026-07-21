"""
ABAC — Attribute-Based Access Control Engine.

Evaluates policies of the form:
  (subject_attributes, resource_attributes, action, environment) → allow | deny

Policies are stored as JSON objects in the settings or database.
"""
import json
from typing import Dict, List, Any, Optional
from ..core.logger import log


class ABACEngine:
    """
    Simple ABAC engine that evaluates JSON policy rules.
    Policies are loaded from settings or database.

    Example policy:
    {
        "name": "recruiters_can_read_candidates_in_own_org",
        "effect": "allow",
        "subject": {"roles": ["RECRUITER", "ADMIN"]},
        "resource": {"type": "candidate"},
        "action": ["read", "list"],
        "condition": {"subject.org_id": "resource.org_id"}
    }
    """

    def __init__(self, policies: List[Dict] = None):
        self.policies = policies or []

    def evaluate(
        self,
        subject: Dict[str, Any],
        resource: Dict[str, Any],
        action: str,
        environment: Dict[str, Any] = None,
    ) -> bool:
        """
        Evaluate all policies. Default is deny unless explicitly allowed.
        Returns True if any matching policy allows the action.
        """
        env = environment or {}
        for policy in self.policies:
            if policy.get("effect") != "allow":
                continue

            if not self._match_subject(policy.get("subject", {}), subject):
                continue
            if not self._match_resource(policy.get("resource", {}), resource):
                continue
            if not self._match_action(policy.get("action", []), action):
                continue
            if not self._match_condition(policy.get("condition", {}), subject, resource, env):
                continue

            return True

        return False  # Default deny

    def _match_subject(self, policy_subject: dict, subject: dict) -> bool:
        if not policy_subject:
            return True
        for key, values in policy_subject.items():
            subject_val = subject.get(key)
            if isinstance(values, list):
                if subject_val not in values:
                    return False
            else:
                if subject_val != values:
                    return False
        return True

    def _match_resource(self, policy_resource: dict, resource: dict) -> bool:
        if not policy_resource:
            return True
        for key, values in policy_resource.items():
            resource_val = resource.get(key)
            if isinstance(values, list):
                if resource_val not in values:
                    return False
            elif values == "*":
                continue
            else:
                if resource_val != values:
                    return False
        return True

    def _match_action(self, policy_actions: list, action: str) -> bool:
        if not policy_actions:
            return True
        return action in policy_actions or "*" in policy_actions

    def _match_condition(
        self,
        conditions: dict,
        subject: dict,
        resource: dict,
        env: dict,
    ) -> bool:
        """
        Evaluate conditions. Supports equality checks between subject/resource/env attributes.
        Format: {"subject.org_id": "resource.org_id"}
        """
        if not conditions:
            return True
        for key, expected in conditions.items():
            actual = self._resolve_condition_key(key, subject, resource, env)
            # If expected starts with "resource." or "env.", resolve that too
            expected_val = self._resolve_condition_key(str(expected), subject, resource, env) if isinstance(expected, str) and expected.startswith(("resource.", "subject.", "env.")) else expected
            if actual != expected_val:
                return False
        return True

    def _resolve_condition_key(self, key: str, subject: dict, resource: dict, env: dict) -> Any:
        """Resolve dotted paths like 'subject.org_id' or 'resource.owner_id'."""
        parts = key.split(".")
        if parts[0] == "subject":
            return self._nested_get(subject, parts[1:])
        if parts[0] == "resource":
            return self._nested_get(resource, parts[1:])
        if parts[0] == "env":
            return self._nested_get(env, parts[1:])
        return key

    @staticmethod
    def _nested_get(data: dict, keys: list) -> Any:
        val = data
        for k in keys:
            if isinstance(val, dict):
                val = val.get(k)
            else:
                return None
        return val


# ─── Default ATS Policies ──────────────────────────────────────────────────────

DEFAULT_POLICIES: List[Dict[str, Any]] = [
    {
        "name": "admin_all_access",
        "effect": "allow",
        "subject": {"roles": ["ADMIN"]},
        "resource": {"type": "*"},
        "action": ["*"],
    },
    {
        "name": "recruiter_read_write_candidates",
        "effect": "allow",
        "subject": {"roles": ["RECRUITER"]},
        "resource": {"type": "candidate"},
        "action": ["read", "list", "create", "update"],
        "condition": {"subject.org_id": "resource.org_id"},
    },
    {
        "name": "recruiter_manage_interviews",
        "effect": "allow",
        "subject": {"roles": ["RECRUITER"]},
        "resource": {"type": "interview"},
        "action": ["read", "list", "create", "update", "schedule"],
        "condition": {"subject.org_id": "resource.org_id"},
    },
    {
        "name": "recruiter_manage_offers",
        "effect": "allow",
        "subject": {"roles": ["RECRUITER"]},
        "resource": {"type": "offer"},
        "action": ["read", "list", "create", "send"],
        "condition": {"subject.org_id": "resource.org_id"},
    },
    {
        "name": "viewer_read_all_in_org",
        "effect": "allow",
        "subject": {"roles": ["VIEWER", "RECRUITER", "ADMIN"]},
        "resource": {"type": "job"},
        "action": ["read", "list"],
        "condition": {"subject.org_id": "resource.org_id"},
    },
    {
        "name": "viewer_read_analytics",
        "effect": "allow",
        "subject": {"roles": ["VIEWER", "RECRUITER", "ADMIN"]},
        "resource": {"type": "analytics"},
        "action": ["read", "list"],
        "condition": {"subject.org_id": "resource.org_id"},
    },
]

# Module-level engine instance with default policies
engine = ABACEngine(DEFAULT_POLICIES)
