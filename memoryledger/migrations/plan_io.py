"""Deterministic plan serialization for Memoryledger migrations.

Provides strict plan file reading/writing with schema validation.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any


PLAN_SCHEMA_V2 = "memoryledger.migration-plan.v2"


class PlanSerializationError(Exception):
    """Raised when plan serialization/deserialization fails."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.details = details or {}


def serialize_plan(
    migration: str,
    migration_id: str,
    project_uuid: str,
    project_root: Path,
    source: Mapping[str, Any],
    target: Mapping[str, Any],
    domain: Mapping[str, Any],
    ledgercore_plan: Mapping[str, Any] | None = None,
    warnings: list[str] | None = None,
) -> str:
    """Serialize a migration plan to deterministic JSON.

    Args:
        migration: Migration name (e.g., "storage-layout")
        migration_id: Unique migration identifier
        project_uuid: Project UUID
        project_root: Absolute project root path
        source: Source state description
        target: Target state description
        domain: Domain-specific plan data
        ledgercore_plan: Optional Ledgercore plan data
        warnings: Optional list of warnings

    Returns:
        Deterministic JSON string
    """
    plan: dict[str, Any] = {
        "schema": PLAN_SCHEMA_V2,
        "migration": migration,
        "migration_id": migration_id,
        "project_uuid": project_uuid,
        "project_root": str(project_root),
        "source": source,
        "target": target,
        "domain": domain,
    }
    if ledgercore_plan is not None:
        plan["ledgercore_plan"] = ledgercore_plan
    if warnings:
        plan["warnings"] = warnings
    else:
        plan["warnings"] = []

    return json.dumps(plan, indent=2, sort_keys=True)


def deserialize_plan(text: str, *, expected_migration: str | None = None) -> dict[str, Any]:
    """Deserialize and validate a migration plan.

    Args:
        text: JSON string
        expected_migration: If set, validate migration name matches

    Returns:
        Validated plan dictionary

    Raises:
        PlanSerializationError: If validation fails
    """
    try:
        plan = json.loads(text)
    except json.JSONDecodeError as e:
        raise PlanSerializationError(f"Invalid JSON: {e}") from e

    if not isinstance(plan, dict):
        raise PlanSerializationError("Plan must be a JSON object")

    # Validate schema
    schema = plan.get("schema")
    if schema != PLAN_SCHEMA_V2:
        raise PlanSerializationError(
            f"Unsupported plan schema: {schema}",
            details={"expected": PLAN_SCHEMA_V2, "actual": schema},
        )

    # Validate required fields
    required = ["migration", "migration_id", "project_uuid", "project_root", "source", "target", "domain"]
    missing = [f for f in required if f not in plan]
    if missing:
        raise PlanSerializationError(
            f"Missing required fields: {', '.join(missing)}",
            details={"missing": missing},
        )

    # Validate migration name if expected
    if expected_migration and plan["migration"] != expected_migration:
        raise PlanSerializationError(
            f"Migration mismatch: expected '{expected_migration}', got '{plan['migration']}'",
            details={"expected": expected_migration, "actual": plan["migration"]},
        )

    # Validate no unknown fields
    known = {"schema", "migration", "migration_id", "project_uuid", "project_root",
             "source", "target", "domain", "ledgercore_plan", "warnings"}
    unknown = set(plan.keys()) - known
    if unknown:
        raise PlanSerializationError(
            f"Unknown fields in plan: {', '.join(sorted(unknown))}",
            details={"unknown": sorted(unknown)},
        )

    return plan


def write_plan_file(plan_text: str, output: Path) -> Path:
    """Write a plan file deterministically.

    Args:
        plan_text: Serialized plan JSON
        output: Output path

    Returns:
        Path to written file
    """
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(plan_text)
    return output


def read_plan_file(path: Path, *, expected_migration: str | None = None) -> dict[str, Any]:
    """Read and validate a plan file.

    Args:
        path: Path to plan file
        expected_migration: If set, validate migration name matches

    Returns:
        Validated plan dictionary
    """
    if not path.exists():
        raise PlanSerializationError(f"Plan file not found: {path}")
    text = path.read_text()
    return deserialize_plan(text, expected_migration=expected_migration)
