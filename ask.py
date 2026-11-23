"""Frage an die Dokumente stellen.

Aufruf:  python ask.py "Welche Aufgaben hat die oder der Landesbeauftragte für den Datenschutz?"
"""

import re
import sys

from common import Timer, generate, get_client, load_config, log_event, retrieve

SYSTEM_PROMPT = """Du bist ein Assistent für die öffentliche Verwaltung.
Beantworte die Frage ausschließlich auf Grundlage der nummerierten Auszüge.
Belege jede Aussage mit der Nummer des Auszugs in eckigen Klammern, z. B. [2].
Wenn die Auszüge die Frage nicht beantworten, antworte genau mit:
"Dazu enthalten die vorliegenden Dokumente keine Information."
Antworte sachlich und knapp auf Deutsch."""

NO_ANSWER = "Dazu enthalten die vorliegenden Dokumente keine Information."


def build_context(hits: list[dict]) -> str:
    return "\n\n".join(
        f"[{i}] (Quelle: {h['source']}, S. {h['page']})\n{h['text']}"
        for i, h in enumerate(hits, start=1)
    )


def answer(question: str, cfg: dict, client) -> dict:
    with Timer() as t_ret:
        hits = retrieve(question, cfg, client)
    hits = [h for h in hits if h["score"] >= cfg["min_score"]]

    if not hits:
        text, t_gen_ms = NO_ANSWER, 0
    else:
        user = f"Auszüge:\n{build_context(hits)}\n\nFrage: {question}"
        with Timer() as t_gen:
            text = generate(SYSTEM_PROMPT, user, cfg)
        # Kontrollmechanismus: Antworten ohne Quellenangabe gelten als nicht belegt
        if cfg.get("require_citation", True) and not re.search(r"\[\d+\]", text):
            text = NO_ANSWER + " (Antwort des Modells ohne Quellenangabe verworfen.)"
        t_gen_ms = t_gen.ms

    result = {"frage": question, "antwort": text, "treffer": hits}
    log_event(cfg, {
        "frage": question,
        "modell": cfg["llm_model"],
        "embedding_modell": cfg["embedding_model"],
        "treffer": [{"source": h["source"], "page": h["page"], "score": round(h["score"], 3)} for h in hits],
        "retrieval_ms": t_ret.ms,
        "generierung_ms": t_gen_ms,
        "keine_antwort": text.startswith(NO_ANSWER[:30]),
    })
    return result


def main() -> None:
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    cfg = load_config()
    result = answer(" ".join(sys.argv[1:]), cfg, get_client(cfg))
    print("\n" + result["antwort"] + "\n")
    print("Quellen:")
    for i, h in enumerate(result["treffer"], start=1):
        print(f"  [{i}] {h['source']}, S. {h['page']} (Ähnlichkeit {h['score']:.2f})")


if __name__ == "__main__":
    main()
