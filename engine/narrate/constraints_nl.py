"""L1 -- natural language -> optimizer constraints (COOLBLOCK-BUILD-PLAN.md
§7.1 L1): *"Keep it to public land, prioritize blocks near Garfield
Elementary, cap maintenance at $8k/yr" -> validated JSON config -> the
solver.* "Structured output against a strict Pydantic schema, with tool
calls to resolve place names against the actual OSM feature table.
Round-trips into real compute."

**Scope, matching `apps/api`'s `ConstraintsIn` 1:1** (`apps/api/src/coolblock_api/schemas.py`),
plus one honesty-rail field this module adds (`unsupported_requests`).
Budget is deliberately excluded here -- `ConstraintsIn`'s own docstring is
explicit that budget "lives on the plan itself, not nested inside its
constraints" -- so a sentence's budget mention, if any, is left for the
existing budget field in the UI, not silently absorbed here.

**Real tool calls, not a wrapper.** The model is given two tools that run
against this project's own real cached data, not simulated or invented:

- `resolve_place(name)` -- looks up a named location (school, playground,
  transit stop, ...) against `engine/ingest/d04_osm.py`'s cached
  "amenities" OSM export, returning its real coordinates if a match is
  found, and disclosing "not found" rather than guessing if not.
- `nearby_candidate_ids(lat, lon, radius_m)` -- queries the exact same
  cached, scored candidate universe the solver itself runs against
  (`engine.optimize.plan_service.load_candidate_universe`) for real
  candidate ids within a real metric radius of a resolved point.

The model's final answer is captured, not free-parsed: it must call a
third tool, `submit_constraints`, whose arguments are validated against
`ParsedConstraints` (a strict Pydantic schema) before anything is handed
back to the caller. A model that names a constraint type this schema
doesn't have (species diversity, a water budget -- both explicitly
disclosed as unmodeled in `engine.optimize.constraints`'s own docstring)
is instructed to say so via `unsupported_requests`, not invent a field.

Same two-provider switch as L3 (`engine/narrate/memo.py`,
`docs/adr/0019-*.md`): `MEMO_LLM_PROVIDER` env var, or an explicit
`provider=` override. `claude-sonnet-5` here, not `claude-opus-5` -- this
is the interactive, latency-sensitive path (§7.1's own model-routing
rule), not the "quality, run once" memo.
"""

from __future__ import annotations

import difflib
import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import geopandas as gpd
from dotenv import load_dotenv
from pydantic import BaseModel, Field, ValidationError
from shapely.geometry import Point

from engine.config import load_neighborhood_config
from engine.narrate.memo import GROQ_MODEL, LLM_PROVIDER_ENV_VAR
from engine.optimize.plan_service import load_candidate_universe

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
AMENITIES_PATH = REPO_ROOT / "data" / "cache" / "osm" / "2026-09-04" / "amenities.parquet"

DEFAULT_PROVIDER = "anthropic"
ANTHROPIC_MODEL = "claude-sonnet-5"  # interactive/latency path (§7.1 model routing), not opus
MAX_OUTPUT_TOKENS = 1500
MAX_TOOL_TURNS = 6
DEFAULT_RADIUS_M = 300.0
DEFAULT_CANDIDATE_LIMIT = 10

SYSTEM_PROMPT = """You turn a planner's plain-English request into structured constraints for a \
real heat-mitigation siting optimizer. You have three tools:

1. resolve_place(name) -- looks up a real named place (a school, playground, transit stop, or \
   similar) in this project's actual cached OpenStreetMap data. ALWAYS call this before using a \
   place the user names -- never invent or guess coordinates yourself.
2. nearby_candidate_ids(lat, lon, radius_m) -- returns the real candidate_id strings of scored \
   intervention sites within radius_m meters of a point, from the actual candidate universe the \
   solver runs against. Use the coordinates resolve_place gave you, never coordinates you made up.
3. submit_constraints -- call this exactly once, last, with your final answer.

Rules:
- Only set fields that correspond to something the schema actually supports: public land only, a \
  max sites per zone, a minimum spend per zone, an annual maintenance cap, and mandatory \
  include/exclude candidate ids. Leave everything else at its default (false/null/empty).
- If the user names a place ("near Garfield Elementary", "around the library"), call resolve_place. \
  If it is found, call nearby_candidate_ids with its real coordinates and put the returned \
  candidate ids into mandatory_include_ids. If resolve_place reports the place was not found, do \
  NOT invent an id or coordinate -- instead add a plain-English note to unsupported_requests saying \
  the place could not be located in the local map data.
- If the user asks for something this schema has no field for (a species/genus diversity cap, a \
  water/irrigation budget, or anything similarly specific), do not invent a field for it -- add a \
  short plain-English note describing the request to unsupported_requests instead.
- Dollar amounts: parse "$8k" as 8000, "8,000" as 8000, etc.
- Do not set mandatory_include_ids or mandatory_exclude_ids to anything except real candidate ids \
  returned by nearby_candidate_ids or explicitly given to you by the user.
"""

_PARAMETERS_SCHEMA = {
    "resolve_place": {
        "type": "object",
        "properties": {"name": {"type": "string", "description": "the place name as the user wrote it"}},
        "required": ["name"],
    },
    "nearby_candidate_ids": {
        "type": "object",
        "properties": {
            "lat": {"type": "number"},
            "lon": {"type": "number"},
            "radius_m": {"type": "number", "description": f"search radius in meters, default {DEFAULT_RADIUS_M:.0f}"},
            "limit": {"type": "integer", "description": f"max candidate ids to return, default {DEFAULT_CANDIDATE_LIMIT}"},
        },
        "required": ["lat", "lon"],
    },
}

_TOOL_DESCRIPTIONS = {
    "resolve_place": "Look up a named place in this project's real cached OpenStreetMap data, returning its real coordinates if found.",
    "nearby_candidate_ids": "Return the real candidate_id strings of scored intervention sites within a radius (meters) of a point, from the actual candidate universe the solver runs against.",
}


class ParsedConstraints(BaseModel):
    """Mirrors `apps.api.coolblock_api.schemas.ConstraintsIn` field-for-field
    (see module docstring for why budget is excluded), plus
    `unsupported_requests` for anything the model was asked for that this
    schema has no real field for."""

    public_land_only: bool = False
    max_sites_per_zone: int | None = None
    min_spend_per_zone_usd: float | None = None
    annual_maintenance_cap_usd: float | None = None
    mandatory_include_ids: list[str] = Field(default_factory=list)
    mandatory_exclude_ids: list[str] = Field(default_factory=list)
    unsupported_requests: list[str] = Field(default_factory=list)


_LIST_FIELDS = ("mandatory_include_ids", "mandatory_exclude_ids", "unsupported_requests")


def _make_submit_constraints_schema() -> dict[str, Any]:
    """Pydantic's own schema declares the three list fields as plain
    `"type": "array"` (they have a default, not `| None`) -- but a model
    with nothing to put in one still sometimes emits `null` for it rather
    than `[]`. Groq's own tool-call validator checks the model's output
    against this exact schema *before* it ever reaches us, and rejected
    that null with a 400 (a real failure hit in live testing, not
    hypothetical) since the schema as generated didn't allow it. Widening
    these three to accept null keeps the provider-side validator happy;
    `_normalize_submit_args` below then turns a null back into `[]` before
    Pydantic ever sees it, so `ParsedConstraints` itself still guarantees
    "always a list.\""""
    schema = ParsedConstraints.model_json_schema()
    for key in _LIST_FIELDS:
        original = schema["properties"][key]
        schema["properties"][key] = {"anyOf": [original, {"type": "null"}], "default": []}
    return schema


_SUBMIT_CONSTRAINTS_SCHEMA = _make_submit_constraints_schema()


def _normalize_submit_args(raw_args: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(raw_args)
    for key in _LIST_FIELDS:
        if normalized.get(key) is None:
            normalized[key] = []
    return normalized


@dataclass(frozen=True)
class PlaceResolution:
    """One `resolve_place` lookup and (if it was found) the real
    candidate ids `nearby_candidate_ids` returned for it -- surfaced to
    the caller so the UI can show *why* a site was included, not just
    that it was."""

    query: str
    found: bool
    matched_name: str | None = None
    lat: float | None = None
    lon: float | None = None
    candidate_ids: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class ParsedConstraintsResult:
    constraints: ParsedConstraints
    place_resolutions: list[PlaceResolution]


class ConstraintParseError(RuntimeError):
    """The model never called `submit_constraints` within `MAX_TOOL_TURNS`,
    or its arguments failed schema validation. A real, actionable failure
    -- surfaced to the caller, not silently papered over with a default
    empty constraint set."""


def resolve_place(name: str) -> dict[str, Any]:
    """Real lookup against the cached OSM amenities export -- substring
    and fuzzy matching only (no geocoding API call; this project's whole
    universe is the one cached bbox), disclosing "not found" rather than
    guessing when nothing matches. A high fuzzy-match cutoff (0.75) is
    deliberate: at 0.5, "Nonexistent Imaginary School" matched "Bioscience
    High School" (both real, both unrelated) purely because both are
    multi-word strings ending in "School" -- silently returning the wrong
    real place is worse than correctly reporting "not found," so this
    errs toward the latter."""
    if not AMENITIES_PATH.exists():
        return {"found": False, "query": name, "reason": "amenities data not cached"}
    gdf = gpd.read_parquet(AMENITIES_PATH)
    if gdf.crs is None:
        raise ConstraintParseError(f"{AMENITIES_PATH} has no CRS -- cannot resolve real coordinates from it")
    names = [n for n in gdf["name"].dropna().unique().tolist() if isinstance(n, str)]

    lowered = name.strip().lower()
    substring_matches = [n for n in names if lowered in n.lower() or n.lower() in lowered]
    fuzzy_matches = difflib.get_close_matches(name, names, n=1, cutoff=0.75)
    matched_name = substring_matches[0] if substring_matches else (fuzzy_matches[0] if fuzzy_matches else None)

    if matched_name is None:
        return {"found": False, "query": name}

    row = gdf[gdf["name"] == matched_name].iloc[0]
    centroid_wgs84 = gpd.GeoSeries([row.geometry.centroid], crs=gdf.crs).to_crs(epsg=4326).iloc[0]
    return {"found": True, "query": name, "matched_name": matched_name, "lat": float(centroid_wgs84.y), "lon": float(centroid_wgs84.x)}


def nearby_candidate_ids(
    lat: float, lon: float, radius_m: float = DEFAULT_RADIUS_M, limit: int = DEFAULT_CANDIDATE_LIMIT
) -> dict[str, Any]:
    """Real distance query against the same cached, scored candidate
    universe the solver itself reads (`engine.optimize.plan_service.load_candidate_universe`),
    reprojected to the neighborhood's own metric CRS -- not a synthetic
    or pre-baked list."""
    universe = load_candidate_universe()
    cfg = load_neighborhood_config()
    point = gpd.GeoSeries([Point(lon, lat)], crs=4326).to_crs(epsg=cfg.target_epsg).iloc[0]
    distances = universe.geometry.distance(point)
    within = universe.loc[distances <= radius_m].assign(_dist=distances[distances <= radius_m])
    within = within.sort_values("_dist")
    ids = [str(cid) for cid in within["candidate_id"].head(limit).tolist()]
    return {"candidate_ids": ids, "count": len(ids), "radius_m": radius_m}


def _execute_tool(name: str, tool_input: dict[str, Any]) -> dict[str, Any]:
    if name == "resolve_place":
        return resolve_place(tool_input["name"])
    if name == "nearby_candidate_ids":
        return nearby_candidate_ids(
            lat=tool_input["lat"],
            lon=tool_input["lon"],
            radius_m=tool_input.get("radius_m", DEFAULT_RADIUS_M),
            limit=tool_input.get("limit", DEFAULT_CANDIDATE_LIMIT),
        )
    raise ConstraintParseError(f"model tried to call an unknown tool: {name!r}")


def _build_place_resolutions(tool_log: list[dict[str, Any]]) -> list[PlaceResolution]:
    """Pairs each `resolve_place` call with the `nearby_candidate_ids`
    call (if any) that used its exact resolved coordinates, so the UI can
    show which real candidates a named place actually pulled in."""
    resolutions: list[PlaceResolution] = []
    for entry in tool_log:
        if entry["tool"] != "resolve_place":
            continue
        result = entry["result"]
        if not result.get("found"):
            resolutions.append(PlaceResolution(query=result["query"], found=False))
            continue
        candidate_ids: list[str] = []
        for other in tool_log:
            if other["tool"] != "nearby_candidate_ids":
                continue
            args = other["input"]
            if abs(args.get("lat", 0.0) - result["lat"]) < 1e-6 and abs(args.get("lon", 0.0) - result["lon"]) < 1e-6:
                candidate_ids = other["result"]["candidate_ids"]
        resolutions.append(
            PlaceResolution(
                query=result["query"],
                found=True,
                matched_name=result["matched_name"],
                lat=result["lat"],
                lon=result["lon"],
                candidate_ids=candidate_ids,
            )
        )
    return resolutions


def _run_anthropic_loop(client: Any, user_text: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    tools = [
        {"name": "resolve_place", "description": _TOOL_DESCRIPTIONS["resolve_place"], "input_schema": _PARAMETERS_SCHEMA["resolve_place"]},
        {
            "name": "nearby_candidate_ids",
            "description": _TOOL_DESCRIPTIONS["nearby_candidate_ids"],
            "input_schema": _PARAMETERS_SCHEMA["nearby_candidate_ids"],
        },
        {"name": "submit_constraints", "description": "Submit the final parsed constraints. Call exactly once, last.", "input_schema": _SUBMIT_CONSTRAINTS_SCHEMA},
    ]
    messages: list[dict[str, Any]] = [{"role": "user", "content": user_text}]
    tool_log: list[dict[str, Any]] = []

    for _ in range(MAX_TOOL_TURNS):
        response = client.messages.create(
            model=ANTHROPIC_MODEL,
            max_tokens=MAX_OUTPUT_TOKENS,
            system=SYSTEM_PROMPT,
            tools=tools,
            messages=messages,
        )
        messages.append({"role": "assistant", "content": response.content})
        tool_uses = [b for b in response.content if b.type == "tool_use"]
        if not tool_uses:
            raise ConstraintParseError("model responded with no tool call at all")

        submit = next((b for b in tool_uses if b.name == "submit_constraints"), None)
        if submit is not None:
            return submit.input, tool_log

        tool_results = []
        for block in tool_uses:
            result = _execute_tool(block.name, block.input)
            tool_log.append({"tool": block.name, "input": block.input, "result": result})
            tool_results.append({"type": "tool_result", "tool_use_id": block.id, "content": json.dumps(result)})
        messages.append({"role": "user", "content": tool_results})

    raise ConstraintParseError(f"model did not call submit_constraints within {MAX_TOOL_TURNS} turns")


def _run_groq_loop(client: Any, user_text: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    tools = [
        {"type": "function", "function": {"name": "resolve_place", "description": _TOOL_DESCRIPTIONS["resolve_place"], "parameters": _PARAMETERS_SCHEMA["resolve_place"]}},
        {"type": "function", "function": {"name": "nearby_candidate_ids", "description": _TOOL_DESCRIPTIONS["nearby_candidate_ids"], "parameters": _PARAMETERS_SCHEMA["nearby_candidate_ids"]}},
        {"type": "function", "function": {"name": "submit_constraints", "description": "Submit the final parsed constraints. Call exactly once, last.", "parameters": _SUBMIT_CONSTRAINTS_SCHEMA}},
    ]
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_text},
    ]
    tool_log: list[dict[str, Any]] = []

    for _ in range(MAX_TOOL_TURNS):
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            max_completion_tokens=MAX_OUTPUT_TOKENS,
            tools=tools,
            messages=messages,
        )
        message = response.choices[0].message
        tool_calls = message.tool_calls or []
        if not tool_calls:
            raise ConstraintParseError("model responded with no tool call at all")
        messages.append({"role": "assistant", "content": message.content, "tool_calls": [tc.model_dump() for tc in tool_calls]})

        submit = next((tc for tc in tool_calls if tc.function.name == "submit_constraints"), None)
        if submit is not None:
            return json.loads(submit.function.arguments), tool_log

        for tc in tool_calls:
            tool_input = json.loads(tc.function.arguments)
            result = _execute_tool(tc.function.name, tool_input)
            tool_log.append({"tool": tc.function.name, "input": tool_input, "result": result})
            messages.append({"role": "tool", "tool_call_id": tc.id, "content": json.dumps(result)})

    raise ConstraintParseError(f"model did not call submit_constraints within {MAX_TOOL_TURNS} turns")


def parse_constraints(
    user_text: str,
    *,
    provider: str | None = None,
    client: Any | None = None,
) -> ParsedConstraintsResult:
    """Runs the real tool-use loop against whichever provider is selected
    (same `MEMO_LLM_PROVIDER` switch as L3), validates the model's final
    `submit_constraints` call against `ParsedConstraints`, and returns it
    alongside a record of every place actually resolved. Raises
    `ConstraintParseError` on a malformed or missing final answer --
    surfaced to the caller, never silently defaulted."""
    load_dotenv()
    resolved_provider = (provider or os.environ.get(LLM_PROVIDER_ENV_VAR, DEFAULT_PROVIDER)).lower()

    if resolved_provider == "anthropic":
        import anthropic

        anthropic_client = client or anthropic.Anthropic()
        raw_args, tool_log = _run_anthropic_loop(anthropic_client, user_text)
    elif resolved_provider == "groq":
        import groq

        groq_client = client or groq.Groq()
        raw_args, tool_log = _run_groq_loop(groq_client, user_text)
    else:
        raise ValueError(f"unknown {LLM_PROVIDER_ENV_VAR}: {resolved_provider!r} -- expected 'anthropic' or 'groq'")

    try:
        constraints = ParsedConstraints.model_validate(_normalize_submit_args(raw_args))
    except ValidationError as exc:
        raise ConstraintParseError(f"model's submit_constraints call failed schema validation: {exc}") from exc

    return ParsedConstraintsResult(constraints=constraints, place_resolutions=_build_place_resolutions(tool_log))
