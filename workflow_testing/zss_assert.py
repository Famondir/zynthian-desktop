"""Structural assertions on saved .zss snapshot files.

See openspec/changes/add-workflow-smoke-testing/design.md's "Structural
assertion on saved snapshot content" decision. .zss is plain JSON
(confirmed by reading a real snapshot: top-level schema_version/chains/
zs3/... keys, chains[<id>]['slots'] is a list of {<slot_index>: <engine_code>}
dicts, e.g. {"3": "FS"} for a FluidSynth engine) - no schema-validation
dependency needed, just parse and assert.

If a future zynthian-ui schema_version bump changes this shape, an
assertion written against the old shape SHALL fail loudly (KeyError or a
clear assertion message naming the workflow) rather than silently
accepting a differently-shaped file - itself a useful regression signal
per design.md, not just a maintenance cost.
"""

from __future__ import annotations

import json
from pathlib import Path


class ZssAssertionError(Exception):
    """Raised when a saved snapshot doesn't contain the expected structure."""


def load_zss(path: str | Path) -> dict:
    path = Path(path)
    try:
        with path.open() as f:
            return json.load(f)
    except FileNotFoundError as e:
        raise ZssAssertionError(f"Snapshot not found: {path}") from e
    except json.JSONDecodeError as e:
        raise ZssAssertionError(f"Snapshot at {path} is not valid JSON: {e}") from e


def assert_chain_has_engine(snapshot: dict, engine_code: str, *, chain_id: str | None = None) -> None:
    """Assert some chain (or a specific `chain_id`) has `engine_code` in a slot.

    engine_code matches the short codes zyngine uses in a chain's `slots`
    list (e.g. "FS" for FluidSynth) - confirmed against a real snapshot on
    this machine (chains["1"]["slots"] == [{"3": "FS"}, {"2": "MI"}]).
    """
    chains = snapshot.get("chains")
    if chains is None:
        raise ZssAssertionError("Snapshot has no 'chains' key - unexpected schema (see module docstring)")

    candidates = [chains[chain_id]] if chain_id is not None else chains.values()
    if chain_id is not None and chain_id not in chains:
        raise ZssAssertionError(f"Snapshot has no chain '{chain_id}' (chains present: {sorted(chains)})")

    for chain in candidates:
        for slot in chain.get("slots", []):
            if engine_code in slot.values():
                return

    where = f"chain '{chain_id}'" if chain_id is not None else "any chain"
    raise ZssAssertionError(f"Engine code '{engine_code}' not found in {where}'s slots")


def assert_chain_count(snapshot: dict, expected_count: int) -> None:
    chains = snapshot.get("chains")
    if chains is None:
        raise ZssAssertionError("Snapshot has no 'chains' key - unexpected schema (see module docstring)")
    actual = len(chains)
    if actual != expected_count:
        raise ZssAssertionError(f"Expected {expected_count} chain(s), snapshot has {actual} (ids: {sorted(chains)})")
