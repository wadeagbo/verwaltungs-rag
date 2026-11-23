"""Gemeinsame Funktionen: Konfiguration, Ollama-Aufrufe, Qdrant, Retrieval, Logging."""

import json
import time
from datetime import datetime, timezone
from pathlib import Path

import requests
import yaml
from qdrant_client import QdrantClient

ROOT = Path(__file__).resolve().parent


def load_config(path: Path = ROOT / "config.yaml") -> dict:
    with open(path, encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    # relative Pfade auf das Projektverzeichnis beziehen
    for key in ("data_dir", "qdrant_path", "manifest_path", "log_path"):
        cfg[key] = str((ROOT / cfg[key]).resolve())
    return cfg


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# ---------- Ollama (läuft lokal, keine Daten verlassen den Rechner) ----------

def embed(texts: list[str], cfg: dict) -> list[list[float]]:
    r = requests.post(
        f"{cfg['ollama_host']}/api/embed",
        json={"model": cfg["embedding_model"], "input": texts},
        timeout=1800,
    )
    r.raise_for_status()
    return r.json()["embeddings"]


def generate(system: str, user: str, cfg: dict) -> str:
    r = requests.post(
        f"{cfg['ollama_host']}/api/chat",
        json={
            "model": cfg["llm_model"],
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "stream": False,
            "options": {"temperature": cfg.get("temperature", 0.0), "num_ctx": 4096},
        },
        timeout=1800,
    )
    r.raise_for_status()
    return r.json()["message"]["content"].strip()


# ---------- Vektordatenbank ----------

def get_client(cfg: dict) -> QdrantClient:
    # Qdrant im lokalen Modus: eine Datei auf der Festplatte, kein Server nötig
    return QdrantClient(path=cfg["qdrant_path"])


def retrieve(question: str, cfg: dict, client: QdrantClient, k: int | None = None) -> list[dict]:
    k = k or cfg["top_k"]
    vector = embed([question], cfg)[0]
    hits = client.query_points(
        collection_name=cfg["collection"],
        query=vector,
        limit=k,
        with_payload=True,
    ).points
    return [{"score": h.score, **h.payload} for h in hits]


# ---------- Observability: jede Anfrage als JSON-Zeile protokollieren ----------

def log_event(cfg: dict, record: dict) -> None:
    Path(cfg["log_path"]).parent.mkdir(parents=True, exist_ok=True)
    record = {"zeit": now_iso(), **record}
    with open(cfg["log_path"], "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


class Timer:
    def __enter__(self):
        self.t0 = time.perf_counter()
        return self

    def __exit__(self, *exc):
        self.ms = round((time.perf_counter() - self.t0) * 1000)
