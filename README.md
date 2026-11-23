# Verwaltungs-RAG: Fragen an öffentliche Rechtstexte aus Baden-Württemberg

Ein kleiner, vollständig lokal laufender Prototyp für Retrieval-Augmented Generation (RAG)
auf öffentlichen Verwaltungstexten. Sprachmodell, Embedding-Modell und Vektordatenbank
laufen auf dem eigenen Rechner. Keine Anfrage und kein Dokument verlässt das Gerät.

Ziel war nicht ein fertiges Produkt. Ich wollte die Bausteine einer RAG-Architektur für
die Verwaltung einmal selbst zusammensetzen und messbar bewerten: Datenaufnahme,
Aktualisierung, Herkunftsnachweis, Abruf, Antwort mit Quellen und Evaluation.

## Aufbau

```
Dokumente (PDF/HTML)  ->  ingest.py  ->  Abschnitte + Metadaten  ->  Qdrant (lokal)
                                               |
Frage  ->  ask.py  ->  Embedding  ->  Top-k-Abruf  ->  Sprachmodell (Ollama)  ->  Antwort mit [Quellen]
                                                                        |
                                                              logs/anfragen.jsonl
```

| Baustein | Umsetzung | Warum |
|---|---|---|
| Sprachmodell | Qwen 2.5 7B über Ollama | Offene Gewichte, läuft lokal, gutes Deutsch |
| Embeddings | BGE-M3 über Ollama | Mehrsprachig, stark auf deutschen Texten |
| Vektordatenbank | Qdrant im lokalen Modus | Open Source, kein Server, kein Cloud-Dienst |
| Aufnahme | pypdf, BeautifulSoup | Einfache, nachvollziehbare Textextraktion |

## Was der Prototyp zeigt

**Aktualisierungskonzept.** `ingest.py` speichert für jede Datei einen SHA-256-Hash im
Manifest. Beim nächsten Lauf werden nur neue oder geänderte Dateien verarbeitet. Bei einer
Änderung werden die alten Abschnitte erst gelöscht und dann ersetzt, gelöschte Dateien
verschwinden auch aus dem Index. So bleibt der Index bei Gesetzesänderungen aktuell, ohne
dass alles neu eingebettet werden muss.

**Data Lineage.** Jeder Abschnitt trägt Quelldatei, Seite, Hash der Quelldatei und den
Zeitpunkt der Aufnahme. Jede Antwort lässt sich damit auf eine bestimmte Fassung eines
Dokuments zurückführen.

**Antworten mit Belegen.** Das Modell darf nur aus den abgerufenen Auszügen antworten und
muss jede Aussage mit [n] belegen. Findet der Abruf nichts Passendes (Ähnlichkeit unter
`min_score`) oder enthalten die Auszüge keine Antwort, sagt das System das ausdrücklich.

**Observability.** Jede Anfrage wird in `logs/anfragen.jsonl` protokolliert: Modell,
Treffer mit Ähnlichkeitswerten, Laufzeit von Abruf und Generierung und ob das System sich
enthalten hat.

**Evaluation.** `evaluate.py` misst mit einem kleinen Fragenkatalog:

- Hit@k und MRR für die Qualität des Abrufs
- Belegquote: Haben die Antworten Quellenangaben?
- Enthaltungsquote: Sagt das System bei Fragen ohne Antwort in den Dokumenten
  „keine Information“, statt etwas zu erfinden?

Die Ergebnisse werden mit Modell und Parametern gespeichert, sodass sich Einstellungen
(z. B. `chunk_size`, `top_k`, anderes Modell) vergleichen lassen.

## Installation

Voraussetzungen: Python 3.10 oder neuer, etwa 16 GB RAM, [Ollama](https://ollama.com).

```bash
ollama pull qwen2.5:7b
ollama pull bge-m3

python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Daten

Öffentliche Rechtstexte als PDF oder HTML in `data/raw/` ablegen. Für die Beispielfragen
in `eval/fragen.jsonl` werden erwartet (Dateiname sollte das Kürzel enthalten):

- Landesdatenschutzgesetz Baden-Württemberg, z. B. `LDSG_BW.pdf`
- E-Government-Gesetz Baden-Württemberg, z. B. `EGovG_BW.pdf`
- Landesverwaltungsverfahrensgesetz, z. B. `LVwVfG_BW.pdf`

Die Texte sind z. B. über das Landesrecht-Portal Baden-Württemberg abrufbar.
Die Dokumente selbst werden nicht ins Repository übernommen.

## Benutzung

```bash
python ingest.py                 # einlesen (inkrementell)
python ask.py "Welche Aufgaben hat die oder der Landesbeauftragte für den Datenschutz?"
python evaluate.py               # Evaluation ausführen
```

## Ergebnisse

<!-- Nach dem ersten Lauf von evaluate.py hier eintragen -->

| Modell | chunk_size | top_k | Hit@k | MRR | Belegquote | Enthaltungsquote |
|---|---|---|---|---|---|---|
| qwen2.5:7b / bge-m3 | 1200 | 5 | | | | |

## Datenschutz, Sicherheit und EU AI Act

- **Digitale Souveränität:** Alle Komponenten sind Open Source und laufen lokal. Es gibt
  keine Abhängigkeit von einem Cloud-Anbieter außerhalb der eigenen Infrastruktur.
- **Personenbezogene Daten:** Der Prototyp verarbeitet nur öffentliche Rechtstexte. Bei
  internen Verwaltungsdokumenten wären vor dem Einsatz eine Datenschutz-Folgenabschätzung,
  ein Rollen- und Rechtekonzept für den Abruf und eine Prüfung der Protokolldaten nötig,
  denn auch die Fragen selbst können personenbezogen sein.
- **EU AI Act:** Ein Auskunftssystem für Beschäftigte dürfte in der Regel kein
  Hochrisiko-System sein, unterliegt aber Transparenzpflichten (erkennbar als KI). Die
  Quellenangaben, die Enthaltung bei fehlender Grundlage und das Protokoll unterstützen
  Nachvollziehbarkeit und menschliche Kontrolle.

## Grenzen und nächste Schritte

- Gescannte PDFs ohne Textebene werden nicht erkannt (OCR fehlt).
- Abschnitte werden nach Zeichenzahl gebildet. Bei Gesetzen wäre eine Teilung nach
  Paragraphen genauer.
- Hybrider Abruf (Vektor + Stichwortsuche, z. B. BM25) und ein Re-Ranker würden bei
  Paragraphennummern und Fachbegriffen helfen.
- Der Fragenkatalog ist klein. Für belastbare Aussagen braucht es einen größeren,
  fachlich geprüften Testsatz.

## Lizenz

MIT
