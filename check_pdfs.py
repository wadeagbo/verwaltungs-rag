"""Zeigt für jede PDF in data/raw: Seitenzahl, Zeichen und den Anfang des Textes."""
from pathlib import Path
from pypdf import PdfReader

for pdf in sorted(Path(__file__).parent.joinpath("data/raw").glob("*.pdf")):
    pages = PdfReader(str(pdf)).pages
    texts = [p.extract_text() or "" for p in pages]
    print(f"{pdf.name}: {len(pages)} Seiten, {sum(map(len, texts))} Zeichen")
    print("   Anfang:", " ".join(texts[0].split())[:150] if texts else "-")
