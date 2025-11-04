#!/usr/bin/env python3
"""
Transform AAP 2.4 export JSON into AAP 2.5 Config-as-Code YAML.

This script reads JSON files produced by the export playbook (under ./_export_24),
normalizes object fields, and writes YAML files that match the variable schemas
expected by the `infra.aap_configuration` collection (AAP 2.5+).

Input directory:
  ./_export_24/
    organizations.json
    credentials.json
    projects.json
    inventories.json
    job_templates.json
    workflow_job_templates.json
    execution_environments.json
    (others may be present but are not required)

Output directory:
  ./_cac_25/
    controller_organizations.yml
    controller_credentials.yml
    controller_projects.yml
    controller_inventories.yml
    controller_templates.yml
    controller_workflows.yml
    controller_execution_environments.yml

Notes
-----
* IDs are dropped; relationships are preserved by *name* to avoid brittle mappings.
* Sensitive credential inputs (passwords, tokens, private keys) are stripped;
  rehydrate them during import from a secrets source (Ansible Vault, AWS SM).
* Extend the normalizers if you need additional objects (notifications, schedules, RBAC).
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional

import yaml

EXPORT_DIR = Path("./_export_24")
OUTPUT_DIR = Path("./_cac_25")

# Map 2.4 credential type 'name' to the 2.5 display names used by infra.aap_configuration
CREDTYPE_MAP: Dict[str, str] = {
    "Machine": "Machine",
    "Source Control": "Source Control",
    "Vault": "Vault",
    "Amazon Web Services": "Amazon Web Services",
    "OpenShift or Kubernetes API Bearer Token": "OpenShift or Kubernetes API Bearer Token",
    "OpenShift or Kubernetes API Certificate": "OpenShift or Kubernetes API Certificate",
}


def _load_json(resource: str) -> List[Dict[str, Any]]:
    """
    Load a JSON export file from EXPORT_DIR.

    Parameters
    ----------
    resource : str
        Base filename (without extension), e.g. "organizations" or "projects".

    Returns
    -------
    list[dict]
        Parsed JSON array; empty list if file does not exist.
    """
    p = EXPORT_DIR / f"{resource}.json"
    if not p.exists():
        return []
    with p.open("r", encoding="utf-8") as f:
        return json.load(f)


def _stripped(s: Any) -> Any:
    """
    Strip surrounding whitespace from strings; return value unchanged for non-strings.
    """
    return s.strip() if isinstance(s, str) else s


def _name(obj_or_name: Any) -> Optional[str]:
    """
    Resolve an object's name, supporting either a string or a dict with 'name'.
    Returns None if not available.
    """
    if isinstance(obj_or_name, dict):
        return obj_or_name.get("name")
    if isinstance(obj_or_name, str):
        return obj_or_name
    return None


def normalize_org(o: Mapping[str, Any]) -> Dict[str, Any]:
    """
    Normalize an Organization object.

    Keeps only the fields relevant to infra.aap_configuration's controller_organizations.
    """
    return {
        "name": _stripped(o.get("name")),
        "state": "present",
    }


def normalize_credential(c: Mapping[str, Any]) -> Dict[str, Any]:
    """
    Normalize a Credential object for controller_credentials.

    - Converts credential type names/kinds to expected display names.
    - Removes sensitive fields from inputs (to be rehydrated from a secret source).
    """
    ct = c.get("credential_type") or {}
    ct_name = ct.get("name") or c.get("kind")
    ct_name = CREDTYPE_MAP.get(ct_name, ct_name)

    org = _name(c.get("organization")) or _name(c.get("organization_id"))
    inputs = dict(c.get("inputs") or {})

    for key in ("password", "secret", "ssh_key_data", "ssh_key_unlock", "token", "client_secret", "become_password"):
        inputs.pop(key, None)

    payload = {
        "name": _stripped(c.get("name")),
        "description": c.get("description") or "",
        "organization": _stripped(org) if org else None,
        "credential_type": ct_name,
        "inputs": inputs or {},
        "state": "present",
    }
    return {k: v for k, v in payload.items() if v not in (None, {}, [])}


def normalize_project(p: Mapping[str, Any]) -> Dict[str, Any]:
    """
    Normalize a Project object for controller_projects.
    """
    scm_type = p.get("scm_type") or ("git" if p.get("scm_url") else "manual")
    org = _name(p.get("organization"))
    payload = {
        "name": _stripped(p.get("name")),
        "description": p.get("description") or "",
        "organization": _stripped(org) if org else None,
        "scm_type": scm_type,
        "scm_url": p.get("scm_url"),
        "scm_branch": p.get("scm_branch") or "main",
        "scm_update_on_launch": bool(p.get("scm_update_on_launch", True)),
        "allow_override": bool(p.get("allow_override", True)),
        "state": "present",
    }
    return {k: v for k, v in payload.items() if v not in (None, {}, [])}


def normalize_inventory(inv: Mapping[str, Any]) -> Dict[str, Any]:
    """
    Normalize an Inventory object for controller_inventories.

    Notes
    -----
    * If any sources used Smart Inventories, consider converting to Constructed
      Inventories in a future enhancement --> emit constructed vars here.
    """
    org = _name(inv.get("organization"))
    kind = inv.get("kind") or "normal"
    payload = {
        "name": _stripped(inv.get("name")),
        "description": inv.get("description") or "",
        "organization": _stripped(org) if org else None,
        "variables": inv.get("variables") or {},
        "kind": kind,
        "state": "present",
    }
    return {k: v for k, v in payload.items() if v not in (None, {}, [])}


def normalize_job_template(t: Mapping[str, Any]) -> Dict[str, Any]:
    """
    Normalize a Job Template object for controller_templates.
    """
    org = _name(t.get("organization"))
    proj = _name(t.get("project"))
    inv = _name(t.get("inventory"))
    ee = _name(t.get("execution_environment"))

    creds = [_stripped(_name(c)) for c in (t.get("credentials") or []) if _name(c)]

    payload = {
        "name": _stripped(t.get("name")),
        "description": t.get("description") or "",
        "organization": _stripped(org) if org else None,
        "project": _stripped(proj) if proj else None,
        "inventory": _stripped(inv) if inv else None,
        "execution_environment": _stripped(ee) if ee else None,
        "job_type": t.get("job_type") or "run",
        "playbook": t.get("playbook"),
        "credentials": creds,
        "survey_enabled": bool(t.get("survey_enabled")),
        "limit": t.get("limit") or "",
        "verbosity": t.get("verbosity") or 0,
        "state": "present",
    }
    return {k: v for k, v in payload.items() if v not in (None, [], {})}


def normalize_workflow_template(w: Mapping[str, Any]) -> Dict[str, Any]:
    """
    Normalize a Workflow Job Template for controller_workflows.

    The detailed node graph is typically handled by the CaC role; this keeps
    the object itself present and ready for subsequent node linking.
    """
    org = _name(w.get("organization"))
    payload = {
        "name": _stripped(w.get("name")),
        "description": w.get("description") or "",
        "organization": _stripped(org) if org else None,
        "state": "present",
    }
    return {k: v for k, v in payload.items() if v not in (None, [], {})}


def normalize_execution_environment(ee: Mapping[str, Any]) -> Dict[str, Any]:
    """
    Normalize an Execution Environment for controller_execution_environments.
    """
    org = _name(ee.get("organization"))
    payload = {
        "name": _stripped(ee.get("name")),
        "image": _stripped(ee.get("image")),
        "organization": _stripped(org) if org else None,
        "pull": ee.get("pull", "missing"),
        "state": "present",
    }
    return {k: v for k, v in payload.items() if v not in (None, [], {})}


def _write_yaml(path: Path, data: Dict[str, Any]) -> None:
    """
    Write a YAML file to path, creating parent directories as needed.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, sort_keys=False)


def main() -> int:
    """
    Main entrypoint:
      * Load JSON exports.
      * Normalize objects.
      * Write YAML files for AAP 2.5 CaC.
    """
    if not EXPORT_DIR.exists():
        print("ERROR: Missing _export_24 directory with JSON exports. Run the 2.4 export first.", file=sys.stderr)
        return 2

    orgs = [normalize_org(o) for o in _load_json("organizations")]
    creds = [normalize_credential(c) for c in _load_json("credentials")]
    projs = [normalize_project(p) for p in _load_json("projects")]
    invs = [normalize_inventory(i) for i in _load_json("inventories")]
    tmps = [normalize_job_template(t) for t in _load_json("job_templates")]
    wfts = [normalize_workflow_template(w) for w in _load_json("workflow_job_templates")]
    ees  = [normalize_execution_environment(e) for e in _load_json("execution_environments")]

    _write_yaml(OUTPUT_DIR / "controller_organizations.yml", {"controller_organizations": orgs})
    _write_yaml(OUTPUT_DIR / "controller_credentials.yml", {"controller_credentials": creds})
    _write_yaml(OUTPUT_DIR / "controller_projects.yml", {"controller_projects": projs})
    _write_yaml(OUTPUT_DIR / "controller_inventories.yml", {"controller_inventories": invs})
    _write_yaml(OUTPUT_DIR / "controller_templates.yml", {"controller_templates": tmps})
    _write_yaml(OUTPUT_DIR / "controller_workflows.yml", {"controller_workflows": wfts})
    _write_yaml(OUTPUT_DIR / "controller_execution_environments.yml", {"controller_execution_environments": ees})

    print(f"Wrote YAML to {OUTPUT_DIR}/")
    return 0


if __name__ == "__main__":
    sys.exit(main())