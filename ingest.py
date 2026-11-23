"""Dokumente einlesen, in Abschnitte teilen, einbetten und in Qdrant speichern.

Aktualisierungskonzept: Für jede Datei wird ein SHA-256-Hash im Manifest gespeichert.
Unveränderte Dateien werden übersprungen, geänderte neu eingelesen (alte Abschnitte
werden vorher gelöscht), entfernte Dateien werden aus dem Index entfernt.
Jeder Abschnitt trägt Quelle, Seite, Hash und Zeitpunkt der Aufnahme (Data Lineage).

Aufruf:  python ingest.py            (inkrementell)
         python ingest.py --neu      (Index komplett neu aufbauen)
"""

import argparse
import hashlib
import json
import uuid
from pathlib import Path

from bs4 import BeautifulSoup
from pypdf import PdfReader
from qdrant_client.models import (
    Distance, FieldCondition, Filter, FilterSelector, MatchValue, PointStruct, VectorParams,
)

from common import embed, get_client, load_config, now_iso

SUPPORTED = {".pdf", ".html", ".htm", ".txt", ".md"}


def extract_pages(path: Path) -> list[tuple[int, str]]:
    """Gibt (Seitennummer, Text) zurück. HTML/TXT zählen als eine Seite."""
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        reader = PdfReader(str(path))
        return [(i + 1, p.extract_text() or "") for i, p in enumerate(reader.pages)]
    raw = path.read_text(encoding="utf-8", errors="ignore")
    if suffix in {".html", ".htm"}:
        soup = BeautifulSoup(raw, "html.parser")
        for tag in soup(["script", "style", "nav", "header", "footer"]):
            tag.decompose()
        raw = soup.get_text("\n")
    return [(1, raw)]


def chunk_text(text: str, size: int, overlap: int) -> list[str]:
    """Teilt an Absatzgrenzen, bis ca. `size` Zeichen; Überlappung für Kontext."""
    paragraphs = [" ".join(p.split()) for p in text.split("\n\n")]
    paragraphs = [p for p in paragraphs if p]
    chunks, current = [], ""
    for p in paragraphs:
        if len(current) + len(p) + 1 <= size:
            current = f"{current} {p}".strip()
            continue
        if current:
            chunks.append(current)
            current = current[-overlap:] if overlap else ""
        # sehr lange Absätze hart teilen
        while len(p) > size:
            chunks.append(f"{current} {p[:size]}".strip())
            current = p[size - overlap:size] if overlap else ""
            p = p[size:]
        current = f"{current} {p}".strip()
    if current:
        chunks.append(current)
    return chunks


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def delete_source(client, cfg, source: str) -> None:
    client.delete(
        collection_name=cfg["collection"],
        points_selector=FilterSelector(
            filter=Filter(must=[FieldCondition(key="source", match=MatchValue(value=source))])
        ),
    )


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--neu", action="store_true", help="Index komplett neu aufbauen")
    args = ap.parse_args()

    cfg = load_config()
    data_dir = Path(cfg["data_dir"])
    manifest_path = Path(cfg["manifest_path"])
    client = get_client(cfg)

    if args.neu and client.collection_exists(cfg["collection"]):
        client.delete_collection(cfg["collection"])
    manifest = {} if args.neu or not manifest_path.exists() else json.loads(manifest_path.read_text("utf-8"))

    files = sorted(p for p in data_dir.rglob("*") if p.suffix.lower() in SUPPORTED)
    current_sources = {str(p.relative_to(data_dir)) for p in files}
    stats = {"neu": 0, "aktualisiert": 0, "unveraendert": 0, "entfernt": 0}

    # entfernte Dateien aus dem Index löschen
    for source in set(manifest) - current_sources:
        if client.collection_exists(cfg["collection"]):
            delete_source(client, cfg, source)
        del manifest[source]
        stats["entfernt"] += 1

    for path in files:
        source = str(path.relative_to(data_dir))
        sha = file_hash(path)
        if manifest.get(source, {}).get("sha256") == sha:
            stats["unveraendert"] += 1
            continue

        records = []
        for page, text in extract_pages(path):
            for i, chunk in enumerate(chunk_text(text, cfg["chunk_size"], cfg["chunk_overlap"])):
                records.append({"source": source, "page": page, "chunk": i, "text": chunk})
        if not records:
            print(f"  ! kein Text gefunden: {source} (gescanntes PDF?)")
            continue

        vectors = []
        batch = cfg.get("embed_batch", 32)
        for start in range(0, len(records), batch):
            vectors += embed([r["text"] for r in records[start:start + batch]], cfg)

        if not client.collection_exists(cfg["collection"]):
            client.create_collection(
                cfg["collection"],
                vectors_config=VectorParams(size=len(vectors[0]), distance=Distance.COSINE),
            )

        if source in manifest:
            delete_source(client, cfg, source)
            stats["aktualisiert"] += 1
        else:
            stats["neu"] += 1

        ingested_at = now_iso()
        points = [
            PointStruct(
                id=str(uuid.uuid5(uuid.NAMESPACE_URL, f"{source}|{r['page']}|{r['chunk']}")),
                vector=v,
                payload={**r, "sha256": sha, "ingested_at": ingested_at},
            )
            for r, v in zip(records, vectors)
        ]
        client.upsert(collection_name=cfg["collection"], points=points)
        manifest[source] = {"sha256": sha, "ingested_at": ingested_at, "chunks": len(points)}
        print(f"  + {source}: {len(points)} Abschnitte")

    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), "utf-8")
    print("Fertig:", ", ".join(f"{k}={v}" for k, v in stats.items()))


if __name__ == "__main__":
    main()
