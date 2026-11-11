"""Pilota: Jev giudica se le coppie di pubblicazioni che motivano un arco `sem` trattano lo stesso tema.

Perche': `evaluate` misura solo la predizione di coautorie future; qui si prova una seconda misura, indipendente dagli
embedding. NON e' una verita': prima di fidarsi va confrontata con giudizi umani (`export-labels`, poi `analyze`).

Cosa parte verso l'API: solo titoli e abstract (troncati) delle DUE pubblicazioni. Mai nomi, id di persona, dipartimenti.
Per ogni coppia due chiamate con A/B scambiati (bias di posizione). Coppie di controllo (temi diversi, stessa lingua)
servono a vedere se il punteggio le separa dagli archi.

Uso (dalla radice del progetto; l'SDK e' nell'extra `jev`):
  uv run --extra jev python scripts/jev_judge_edges.py plan                        # nessuna chiamata: campione + costo stimato
  uv run --extra jev --env-file .env python scripts/jev_judge_edges.py send --yes  # chiama l'API (serve TYPESAFE_API_KEY)
  uv run --extra jev python scripts/jev_judge_edges.py export-labels --n 100       # csv cieco per un giudizio umano
  uv run --extra jev python scripts/jev_judge_edges.py analyze                     # reports/05_jev_edges.md

`send` non parte senza --yes; si ferma se il costo stimato supera --max-usd (per esecuzione) o se speso + stimato supera
--budget-usd (cumulativo, dai token realmente riportati dall'API). Riprende dai mancanti.
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import random
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
from unitn_net import config  # noqa: E402

OUT_DIR = config.PROCESSED / "jev"           # ignorato da git (data/processed/)
PAIRS = OUT_DIR / "pairs.parquet"
RUN = OUT_DIR / "edges_run.jsonl"
LABELS = OUT_DIR / "human_labels.csv"
PRICE_PER_M_TOKENS = 0.042                   # $ input, docs.typesafe.ai/models (letto il 29/09/2026)
ABSTRACT_CHARS = 1200

# ---------------------------------------------------------------- domande

INSTR = {
    "en": ("Two publications, `PUB_A` and `PUB_B`, are given with their title and (when available) abstract. "
           "Rate how closely related their research topics are. Judge the subject matter, not the language, style, "
           "publication type or length of the text. Publications in different languages are not to be compared: "
           "both are written in the same language."),
    "it": ("Sono date due pubblicazioni, `PUB_A` e `PUB_B`, con titolo e (se disponibile) abstract. "
           "Valuta quanto siano vicini i loro temi di ricerca. Giudica l'argomento, non la lingua, lo stile, il tipo di "
           "pubblicazione o la lunghezza del testo. Le due pubblicazioni sono scritte nella stessa lingua."),
}
LEVELS = {
    "en": ["Unrelated: different fields or subjects.",
           "Same broad discipline, but different subjects.",
           "Same subfield or shared theme, but different specific research questions.",
           "Closely related: same specific topic; a researcher on one would want to read the other.",
           "Near-identical: essentially the same research problem."],
    "it": ["Non correlate: campi o argomenti diversi.",
           "Stessa disciplina in senso ampio, ma argomenti diversi.",
           "Stesso sottocampo o tema comune, ma domande di ricerca specifiche diverse.",
           "Strettamente correlate: stesso tema specifico; chi lavora su una vorrebbe leggere l'altra.",
           "Quasi identiche: sostanzialmente lo stesso problema di ricerca."],
}
NARROW = {
    "en": "Do `PUB_A` and `PUB_B` address the same specific research question or topic (not merely the same broad field)?",
    "it": "`PUB_A` e `PUB_B` trattano lo stesso specifico tema o domanda di ricerca (non solo lo stesso campo in senso ampio)?",
}


def questions(instr_lang: str) -> dict:
    from typesafe_sdk import Noul, Score
    return {
        "topic": Score(instructions=INSTR[instr_lang], criteria=LEVELS[instr_lang]),
        "narrow": Noul(instructions=NARROW[instr_lang], criteria={"true": "Yes." if instr_lang == "en" else "Sì.",
                                                                  "false": "No."}),
    }


def _pub(title, abstract) -> dict:
    return {"title": title, **({"abstract": abstract[:ABSTRACT_CHARS]} if isinstance(abstract, str) and abstract.strip() else {})}


def build_state(row, order: str) -> dict:
    a, b = _pub(row["title_a"], row["abstract_a"]), _pub(row["title_b"], row["abstract_b"])
    return {"PUB_A": a, "PUB_B": b} if order == "ab" else {"PUB_A": b, "PUB_B": a}


# ---------------------------------------------------------------- campione

def _pid(*parts) -> str:
    return hashlib.sha1("|".join(map(str, parts)).encode()).hexdigest()[:16]


def build_pairs(n_edges: int, n_controls: int, seed: int, lang: str) -> pd.DataFrame:
    rng = random.Random(seed)
    pubs = pd.read_parquet(config.PROCESSED / "publications.parquet")
    edges = pd.read_parquet(config.PROCESSED / "edges.parquet")
    abstract_of = {}
    for t, a in zip(pubs.title, pubs.abstract):
        if isinstance(t, str) and isinstance(a, str) and a.strip():
            abstract_of.setdefault(t, a)

    cands = []  # archi: la coppia con coseno piu' alto dell'evidenza `sem`
    for ev, sem in zip(edges["evidence"], edges["sem"]):
        if pd.isna(sem):
            continue
        top = (json.loads(ev).get("sem") or [None])[0]
        if top and top.get("lang") in ("it", "en"):
            cands.append({"kind": "edge", "lang": top["lang"], "cos": top["cos"], "title_a": top["a"], "title_b": top["b"]})
    rows = []
    langs = ["it", "en"] if lang == "all" else [lang]
    for lg in langs:
        pool = [c for c in cands if c["lang"] == lg]
        rng.shuffle(pool)
        rows += pool[: n_edges // len(langs)]

    # controlli: due pubblicazioni della stessa lingua, di macro-aree SSD diverse (temi diversi per costruzione)
    people = pd.read_parquet(config.INTERIM / "people.parquet")[["person_id", "ssd"]].dropna()
    auth = pd.read_parquet(config.PROCESSED / "authorship.parquet").merge(people, on="person_id")
    macro = auth.assign(m=auth.ssd.str[:4]).groupby("pub_id").m.agg(lambda s: s.iloc[0])
    p = pubs[pubs.pub_id.isin(macro.index) & pubs.text_lang.isin(langs)].copy()
    p["macro"] = p.pub_id.map(macro)
    for lg in langs:
        q = p[p.text_lang == lg].reset_index(drop=True)
        made, tries = 0, 0
        while made < n_controls // len(langs) and tries < 100000 and len(q) > 1:
            tries += 1
            i, j = rng.randrange(len(q)), rng.randrange(len(q))
            if q.macro[i] == q.macro[j]:
                continue
            rows.append({"kind": "control", "lang": lg, "cos": None, "title_a": q.title[i], "title_b": q.title[j]})
            made += 1
    df = pd.DataFrame(rows)
    df["abstract_a"] = df.title_a.map(abstract_of).where(lambda s: s.notna(), None)
    df["abstract_b"] = df.title_b.map(abstract_of).where(lambda s: s.notna(), None)
    df["pair_id"] = [_pid(a, b) for a, b in zip(df.title_a, df.title_b)]
    return df.drop_duplicates("pair_id").reset_index(drop=True)


def jobs(pairs: pd.DataFrame, orders=("ab", "ba")):
    for r in pairs.to_dict("records"):
        for o in orders:
            yield {"key": f"{r['pair_id']}|{o}", "row": r, "order": o}


def estimate(todo, instr_lang: str) -> tuple[int, float]:
    q = json.dumps({k: v.model_dump() for k, v in questions(instr_lang).items()}, ensure_ascii=False)
    chars = sum(len(json.dumps(build_state(j["row"], j["order"]), ensure_ascii=False)) + len(q) for j in todo)
    tokens = int(chars / 3.5)  # stima grossolana, come nel pilota ASR: la misura vera e' in `usage` dopo l'invio
    return tokens, tokens / 1e6 * PRICE_PER_M_TOKENS


def spent_usd() -> float:
    """Dollars already spent on this project's runs, from the token counts the API reported (input only: output is free)."""
    if not RUN.exists():
        return 0.0
    tok = sum(r.get("usage", {}).get("input_tokens", 0) for r in map(json.loads, RUN.read_text(encoding="utf-8").splitlines()) if "error" not in r)
    return tok / 1e6 * PRICE_PER_M_TOKENS


def done_keys() -> set[str]:
    if not RUN.exists():
        return set()
    return {r["key"] for r in map(json.loads, RUN.read_text(encoding="utf-8").splitlines()) if "error" not in r}


# ---------------------------------------------------------------- comandi

def cmd_plan(a) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    pairs = build_pairs(a.edges, a.controls, a.seed, a.lang)
    pairs.to_parquet(PAIRS, index=False)
    todo = [j for j in jobs(pairs) if j["key"] not in done_keys()]
    tokens, usd = estimate(todo, a.instr_lang)
    print(pairs.groupby(["kind", "lang"]).size().rename("coppie").to_string())
    print(f"\ncoppie con abstract: A {pairs.abstract_a.notna().mean():.0%}, B {pairs.abstract_b.notna().mean():.0%}")
    print(f"chiamate da fare: {len(todo)}   token stimati: ~{tokens:,}   costo stimato: ~${usd:.4f}   (tetto --max-usd {a.max_usd})")
    if len(pairs):
        r = pairs.iloc[0].to_dict()
        print("\n=== esempio di stato inviato (nessun nome, nessun id):")
        print(json.dumps(build_state(r, "ab"), ensure_ascii=False, indent=1)[:900])
    print(f"\ncampione salvato in {PAIRS} (locale, ignorato da git)")


async def _send(a, todo) -> None:
    from typesafe_sdk import AsyncTypeSafeClient, TypeSafeError
    qs = questions(a.instr_lang)
    sem, lock = asyncio.Semaphore(a.concurrency), asyncio.Lock()

    async def one(client, j) -> bool:
        rec = {"key": j["key"], "pair_id": j["row"]["pair_id"], "order": j["order"], "instr_lang": a.instr_lang}
        async with sem:
            try:
                resp = await client.system_one(state=build_state(j["row"], j["order"]), questions=qs)
                rec["model"], rec["usage"] = resp.model, resp.usage.model_dump(mode="json")
                rec["answers"] = {k: v.model_dump(mode="json") for k, v in resp.answers.items()}
            except TypeSafeError as exc:  # si registra e si rilancia: riprende dai mancanti
                rec["error"] = f"{type(exc).__name__}: {exc}"
        async with lock:
            with open(RUN, "a", encoding="utf-8") as f:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        return "error" not in rec

    async with AsyncTypeSafeClient() as client:
        ok = sum(await asyncio.gather(*(one(client, j) for j in todo)))
    print(f"fatte {ok}/{len(todo)} chiamate -> {RUN}")
    if ok < len(todo):
        print("alcune sono fallite (campo 'error'): rilancia lo stesso comando")


def cmd_send(a) -> None:
    if not PAIRS.exists():
        sys.exit("Nessun campione: lancia prima `plan`.")
    if not a.yes:
        sys.exit("Serve --yes: questo comando manda titoli e abstract a un servizio esterno (TypeSafe).")
    if not os.environ.get("TYPESAFE_API_KEY"):
        sys.exit("TYPESAFE_API_KEY non trovata: lancia con `uv run --env-file .env ...`.")
    pairs = pd.read_parquet(PAIRS)
    done = done_keys()
    todo = [j for j in jobs(pairs) if j["key"] not in done]
    tokens, usd = estimate(todo, a.instr_lang)
    spent = spent_usd()
    print(f"{len(todo)} chiamate, ~{tokens:,} token, costo stimato ~${usd:.4f}; gia' speso ${spent:.4f}; budget totale ${a.budget_usd}")
    if usd > a.max_usd:
        sys.exit(f"Costo stimato sopra --max-usd {a.max_usd}: non parto.")
    if spent + usd > a.budget_usd:
        sys.exit(f"Speso + stimato (${spent + usd:.4f}) supera il budget totale --budget-usd {a.budget_usd}: non parto.")
    if todo:
        asyncio.run(_send(a, todo))


def cmd_export_labels(a) -> None:
    """CSV cieco per un giudizio umano: niente tipo (arco/controllo), niente coseno, niente punteggio di Jev; ordine casuale."""
    pairs = pd.read_parquet(PAIRS).sample(frac=1, random_state=a.seed).head(a.n)
    out = pairs[["pair_id", "lang", "title_a", "abstract_a", "title_b", "abstract_b"]].copy()
    out["label"] = ""   # 0-4, stessa scala di Jev (vedi LEVELS)
    out.to_csv(LABELS, index=False)
    print(f"{len(out)} coppie in {LABELS}. Scala: " + " | ".join(f"{i}={t}" for i, t in enumerate(LEVELS['it'])))


def _auc(pos: list[float], neg: list[float]) -> float | None:
    if not pos or not neg:
        return None
    from sklearn.metrics import roc_auc_score
    return float(roc_auc_score([1] * len(pos) + [0] * len(neg), pos + neg))


def cmd_analyze(a) -> None:
    pairs = pd.read_parquet(PAIRS).set_index("pair_id")
    recs = [r for r in map(json.loads, RUN.read_text(encoding="utf-8").splitlines()) if "error" not in r]
    if not recs:
        sys.exit("Nessun risultato in " + str(RUN))
    rows = [{"pair_id": r["pair_id"], "order": r["order"], "score": r["answers"]["topic"]["score"],
             "narrow": r["answers"]["narrow"]["noul"], "conf": r["answers"]["topic"].get("confidence"),
             "tokens": r["usage"]["input_tokens"]} for r in recs]
    d = pd.DataFrame(rows)
    wide = d.pivot_table(index="pair_id", columns="order", values=["score", "narrow"])
    wide.columns = [f"{x}_{y}" for x, y in wide.columns]
    wide = wide.join(pairs[["kind", "lang"]]).dropna()
    wide["score"] = wide[["score_ab", "score_ba"]].mean(axis=1)
    wide["narrow"] = wide[["narrow_ab", "narrow_ba"]].mean(axis=1)
    wide["bias"] = (wide.score_ab - wide.score_ba).abs()
    wide["flip"] = (wide.score_ab >= 2) != (wide.score_ba >= 2)
    md = ["# 05 Jev come giudice degli archi `sem` (pilota)\n",
          f"Coppie con entrambi gli ordini: {len(wide)}. Token in ingresso: {int(d.tokens.sum()):,} "
          f"(~${d.tokens.sum() / 1e6 * PRICE_PER_M_TOKENS:.4f}). Punteggio 0-4, media dei due ordini.\n",
          "| lingua | tipo | n | punteggio medio | % narrow>0,5 | scarto medio fra ordini | % verdetto (>=2) che cambia |",
          "|---|---|---|---|---|---|---|"]
    for (lg, kind), g in wide.groupby(["lang", "kind"]):
        md.append(f"| {lg} | {kind} | {len(g)} | {g.score.mean():.2f} | {(g.narrow > .5).mean():.0%} | {g.bias.mean():.2f} | {g.flip.mean():.0%} |")
    md += ["\n## Separazione archi / controlli (AUC; 0,5 = nessuna)\n", "| lingua | AUC |", "|---|---|"]
    for lg, g in wide.groupby("lang"):
        auc = _auc(g[g.kind == "edge"].score.tolist(), g[g.kind == "control"].score.tolist())
        md.append(f"| {lg} | {'n.d.' if auc is None else f'{auc:.2f}'} |")
    if LABELS.exists():
        lab = pd.read_csv(LABELS).dropna(subset=["label"])
        if len(lab):
            from scipy.stats import spearmanr
            j = lab.merge(wide.reset_index()[["pair_id", "score"]], on="pair_id")
            md += ["\n## Accordo con il giudizio umano (Spearman)\n", "| lingua | n | rho |", "|---|---|---|"]
            for lg, g in j.groupby("lang"):
                rho = spearmanr(g.label, g.score)[0] if len(g) > 2 else float("nan")
                md.append(f"| {lg} | {len(g)} | {rho:.2f} |")
    md.append("\nLimiti: campione piccolo; Jev ha l'inglese come lingua principale; senza giudizi umani il punteggio "
              "non e' una verita'. Le coppie di controllo sono facili (macro-aree diverse): separarle e' condizione "
              "necessaria, non sufficiente.")
    (config.REPORTS / "05_jev_edges.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print("\n".join(md))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["plan", "send", "export-labels", "analyze"])
    ap.add_argument("--edges", type=int, default=200, help="coppie-arco totali (meta' it, meta' en)")
    ap.add_argument("--controls", type=int, default=100)
    ap.add_argument("--lang", choices=["all", "it", "en"], default="all")
    ap.add_argument("--instr-lang", choices=["en", "it"], default="en", help="lingua di istruzioni e livelli")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--n", type=int, default=100, help="export-labels: numero di coppie")
    ap.add_argument("--max-usd", type=float, default=0.5, help="tetto per UNA esecuzione di send")
    ap.add_argument("--budget-usd", type=float, default=1.0, help="tetto TOTALE cumulativo (speso + stimato) su questo progetto")
    ap.add_argument("--concurrency", type=int, default=8)
    ap.add_argument("--yes", action="store_true")
    a = ap.parse_args()
    {"plan": cmd_plan, "send": cmd_send, "export-labels": cmd_export_labels, "analyze": cmd_analyze}[a.cmd](a)


if __name__ == "__main__":
    main()
