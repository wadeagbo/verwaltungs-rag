"""Evaluation: Retrieval-Qualität und Antwortverhalten messen.

Kennzahlen
- Hit@k:  Anteil der Fragen, bei denen die erwartete Quelle unter den Top-k-Treffern ist
- MRR:    Mean Reciprocal Rank der ersten richtigen Quelle
- Belegquote:  Anteil der beantworteten Fragen mit mindestens einer Quellenangabe [n]
- Enthaltungsquote: Anteil der Fragen ohne Antwort in den Dokumenten, bei denen das
  System korrekt "keine Information" sagt (prüft, ob das Modell halluziniert)

Testfragen stehen in eval/fragen.jsonl, eine Frage pro Zeile:
  {"frage": "...", "erwartete_quelle": "Teil des Dateinamens"}
  {"frage": "...", "erwartete_quelle": null}     <- Frage ohne Antwort in den Dokumenten

Aufruf:  python evaluate.py            (Retrieval + Antworten)
         python evaluate.py --nur-retrieval
"""

import argparse
import json
import re
from pathlib import Path

from ask import NO_ANSWER, answer
from common import ROOT, get_client, load_config, now_iso, retrieve


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--nur-retrieval", action="store_true")
    args = ap.parse_args()

    cfg = load_config()
    client = get_client(cfg)
    k = cfg["top_k"]
    questions = [
        json.loads(line)
        for line in (ROOT / "eval" / "fragen.jsonl").read_text("utf-8").splitlines()
        if line.strip()
    ]

    rows, rr, hits_at_k = [], [], []
    cited, answered, abstained, out_of_scope = 0, 0, 0, 0

    for q in questions:
        expected = q.get("erwartete_quelle")
        row = {"frage": q["frage"], "erwartete_quelle": expected}

        if expected:
            sources = [h["source"] for h in retrieve(q["frage"], cfg, client, k)]
            rank = next((i for i, s in enumerate(sources, 1) if expected.lower() in s.lower()), None)
            rr.append(1 / rank if rank else 0.0)
            hits_at_k.append(1 if rank else 0)
            row.update({"rang": rank, "quellen": sources})

        if not args.nur_retrieval:
            res = answer(q["frage"], cfg, client)
            said_no = res["antwort"].startswith(NO_ANSWER[:30])
            row["antwort"] = res["antwort"]
            if expected:
                if not said_no:
                    answered += 1
                    cited += bool(re.search(r"\[\d+\]", res["antwort"]))
            else:
                out_of_scope += 1
                abstained += said_no

        rows.append(row)
        print(f"- {q['frage'][:70]:<70}  Rang: {row.get('rang', '–')}")

    summary = {
        "zeit": now_iso(),
        "llm_modell": cfg["llm_model"],
        "embedding_modell": cfg["embedding_model"],
        "chunk_size": cfg["chunk_size"],
        "top_k": k,
        f"hit@{k}": round(sum(hits_at_k) / len(hits_at_k), 3) if hits_at_k else None,
        "mrr": round(sum(rr) / len(rr), 3) if rr else None,
    }
    if not args.nur_retrieval:
        summary["belegquote"] = round(cited / answered, 3) if answered else None
        summary["enthaltungsquote"] = round(abstained / out_of_scope, 3) if out_of_scope else None

    print("\nErgebnis:")
    for key, value in summary.items():
        print(f"  {key}: {value}")

    out = ROOT / "eval" / f"ergebnis_{summary['zeit'][:19].replace(':', '-')}.json"
    out.write_text(json.dumps({"zusammenfassung": summary, "fragen": rows}, ensure_ascii=False, indent=2), "utf-8")
    print(f"\nGespeichert: {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
