"""Step `audit`: data audit -> reports/00_data_audit.md. STOP for approval after this step.

The report compares the actual schemas with the documented ones so that the field names in
normalize.py can be fixed before Phase 1. Every field-specific statistic is guarded: a missing field is
reported as missing, never as zero.
"""

from __future__ import annotations

import json
import logging
import os
import re
from collections import Counter
from pathlib import Path

from . import config, net, opendata
from .textnorm import DOI_RE

log = logging.getLogger(__name__)

_YEAR_RE = re.compile(r"(20\d\d)\s*[/\-–]\s*(20\d\d|\d\d)|(20\d\d)")


def _role(p: dict):
    """The role field is `ruolo` in the 2026-09-17 snapshot; `descrizioneRuolo` is what the dataset documentation says."""
    return p.get("ruolo") or p.get("descrizioneRuolo")


def _fill(recs: list[dict], key: str) -> float:
    return sum(1 for r in recs if r.get(key) not in (None, "", [], {})) / max(len(recs), 1)


def key_table(recs: list[dict]) -> list[str]:
    keys = Counter(k for r in recs for k in r)
    lines = ["| field | present in | non-empty | example type |", "|---|---|---|---|"]
    for k, n in keys.most_common():
        example = next((r[k] for r in recs if r.get(k) not in (None, "")), None)
        t = type(example).__name__
        if isinstance(example, list) and example and isinstance(example[0], dict):
            t += f"[dict: {', '.join(sorted(example[0]))}]"
        elif isinstance(example, dict):
            t += f"{{{', '.join(sorted(example))}}}"
        lines.append(f"| `{k}` | {n / len(recs):.0%} | {_fill(recs, k):.0%} | {t} |")
    return lines


def _h(v):
    """Hashable form of a field value for Counter (real records use lists where the documentation has scalars)."""
    return json.dumps(v, ensure_ascii=False) if isinstance(v, (list, dict)) else v


def counter_lines(c: Counter, top: int = 40) -> list[str]:
    total = sum(c.values())
    return [f"- `{k}`: {v} ({v / total:.1%})" for k, v in c.most_common(top)] or ["- (none)"]


def _ids(recs: list[dict], key: str = "id") -> set[str]:
    return {str(r[key]) for r in recs if r.get(key) not in (None, "")}


def _nested_ids(recs: list[dict], list_key: str) -> set[str]:
    return {str(a["id"]) for r in recs for a in (r.get(list_key) or []) if isinstance(a, dict) and a.get("id") is not None}


def _openalex_estimate(cfg: dict) -> list[str]:
    oa = cfg["openalex"]
    key = os.environ.get(oa["api_key_env"])
    if not key:
        return [f"- `{oa['api_key_env']}` not set: estimate skipped (the OpenAlex step is optional)."]
    s = net.session(cfg)
    flt = f"institutions.id:{oa['institution_id']},publication_year:>{cfg['scope']['pub_year_min'] - 1}"
    # Auth by query parameter; verify at https://docs.openalex.org/ (API keys) before the first paid run.
    inst = net.get_json(s, f"{oa['base_url']}/institutions/{oa['institution_id']}", {"api_key": key})
    data = net.get_json(s, f"{oa['base_url']}/works", {"filter": flt, "per_page": 1, "select": "id", "api_key": key})
    count = data["meta"]["count"]
    calls = -(-count // oa["per_page"])
    cost = calls / 1000 * oa["list_cost_per_1000"]
    return [
        f"- institution `{oa['institution_id']}`: {inst.get('display_name')} (ROR {inst.get('ror')}), works_count={inst.get('works_count')}",
        f"- works matching `{flt}`: **{count}** -> {calls} list calls -> **~${cost:.3f}** (limit {oa['max_cost_usd']})",
        f"- meta of the count call: `{data['meta']}`",
    ]


def run(cfg: dict, args=None) -> None:
    raw = config.latest_raw("opendata")
    md: list[str] = [f"# 00 Data audit\n\nRaw snapshot: `{raw}`\n"]
    roles = [r.lower() for r in cfg["scope"]["roles"]]
    staff_ids: set[str] = set()
    author_ids: set[str] = set()
    teacher_ids: set[str] = set()

    for slug in cfg["opendata"]["datasets"]:
        resources = opendata.load_resources(raw, slug)
        recs = [r for _, rs in resources for r in rs]
        pkg = opendata.package(raw, slug)
        md += [f"\n## `{slug}`\n", f"- license: `{pkg.get('license_id')}` — metadata_modified: {pkg.get('metadata_modified')}",
               f"- JSON resources: {len(resources)}, records: {len(recs)}"]
        for res, rs in resources:
            md.append(f"  - `{res.get('name')}` ({res.get('format')}): {len(rs)} records")
        if not recs:
            md.append("- **no records**")
            continue
        md += ["\n### Fields (union over records)\n", *key_table(recs)]

        if slug == opendata.STAFF:
            staff_ids = _ids(recs)
            pos = [p for r in recs for p in (r.get("posizioni") or []) if isinstance(p, dict)]
            n_per = sum(bool(re.fullmatch(r"PER\d+", i)) for i in staff_ids)
            md += [f"\n- distinct `id`: {len(staff_ids)} / {len(recs)} records",
                   f"- ids matching the Digital University pattern `PER<digits>`: {n_per} of {len(staff_ids)}",
                   "\n### `posizioni[].ruolo` (older snapshots: `descrizioneRuolo`)\n", *counter_lines(Counter(_h(_role(p)) for p in pos))]
            in_scope = [r for r in recs if any(any(role in (_role(p) or "").lower() for role in roles)
                                                   for p in (r.get("posizioni") or []) if isinstance(p, dict))]
            md += [f"\n- people matching `scope.roles` {roles}: **{len(in_scope)}**",
                   f"- of which with `SSD`: {_fill(in_scope, 'ssd'):.0%}, with `CUN`: {_fill(in_scope, 'cun'):.0%}",
                   "\n### Structures of in-scope people (`posizioni[].nomeStruttura`)\n",
                   *counter_lines(Counter(_h(p.get("nomeStruttura")) for r in in_scope for p in (r.get("posizioni") or [])
                                          if any(role in (_role(p) or "").lower() for role in roles)))]

        elif slug == opendata.PUBS:
            author_ids = _nested_ids(recs, "autori")
            years = Counter(str(r.get("anno")) for r in recs)
            doi_field = next((k for k in recs[0] if k.lower() == "doi"), None)
            with_abs = _fill(recs, "abstract")
            doi_rx = sum(1 for r in recs if DOI_RE.search(str(r.get("citazione") or "")))
            md += [f"\n- with non-empty `abstract`: {with_abs:.1%}",
                   f"- DOI field: {'`' + doi_field + '`' if doi_field else '**none documented and none found**'}",
                   f"- DOI regex hits in `citazione`: {doi_rx} ({doi_rx / len(recs):.1%})",
                   f"- records with >= 1 `autori[].id`: {_fill(recs, 'autori'):.1%}; distinct author ids: {len(author_ids)}",
                   "\n### `anno`\n", *counter_lines(years, 60),
                   "\n### `lingua`\n", *counter_lines(Counter(_h(r.get("lingua")) for r in recs)),
                   "\n### `tipo`\n", *counter_lines(Counter(_h(r.get("tipo")) for r in recs))]

        elif slug == opendata.COURSES:
            teacher_ids = _nested_ids(recs, "docenti") | _nested_ids(recs, "assistenti")
            md += ["\n### Academic years inferred from resource names\n"]
            for res, rs in resources:
                m = _YEAR_RE.search(f"{res.get('name')} {res.get('description')}")
                md.append(f"- `{res.get('name')}` -> {m.group(0) if m else '**unknown**'} ({len(rs)} courses)")
            md += [f"\n- with `descrizione`: {_fill(recs, 'descrizione'):.1%}, with `docenti`: {_fill(recs, 'docenti'):.1%}",
                   f"- distinct teacher ids: {len(teacher_ids)}",
                   "\n### `dipartimento.nome`\n",
                   *counter_lines(Counter((r.get("dipartimento") or {}).get("nome") if isinstance(r.get("dipartimento"), dict)
                                          else _h(r.get("dipartimento")) for r in recs))]

    md += ["\n## Id consistency across datasets\n",
           f"- staff ids: {len(staff_ids)}; publication author ids: {len(author_ids)}; course teacher ids: {len(teacher_ids)}",
           f"- author ids in staff: {len(author_ids & staff_ids)} / {len(author_ids)}",
           f"- teacher ids in staff: {len(teacher_ids & staff_ids)} / {len(teacher_ids)}",
           "\n## OpenAlex cost estimate\n", *_openalex_estimate(cfg),
           "\n## Checklist before Phase 1\n",
           "- [ ] field names in `normalize.py` match the tables above",
           "- [ ] `scope.roles` in `config.toml` finalized from the `ruolo` values",
           "- [ ] academic years of the course resources understood",
           "- [ ] OpenAlex cost within budget (or step skipped)"]
    out: Path = config.REPORTS / "00_data_audit.md"
    out.write_text("\n".join(md) + "\n", encoding="utf-8")
    log.info("wrote %s — STOP: review it before running `normalize`", out)
