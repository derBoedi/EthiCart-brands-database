import os
import sys
import json
import requests
import subprocess
from datetime import datetime

issue_title = os.environ.get("ISSUE_TITLE", "")
issue_number = os.environ.get("ISSUE_NUMBER", "")
api_key = os.environ.get("GEMINI_API_KEY")

if not issue_title.startswith("Add:"):
    sys.exit(0)

brand_query = issue_title.replace("Add:", "").strip()
brand_query_lower = brand_query.lower()

# Datenbank laden
with open("brands.json", "r", encoding="utf-8") as f:
    db = json.load(f)

# --- DUPLIKAT-CHECK (Scharf geschaltet) ---
for entry in db.get("entries", []):
    keywords = [k.lower() for k in entry.get("keywords", [])]
    if brand_query_lower == entry.get("brand", "").lower() or brand_query_lower in keywords:
        print(f"Abbruch: {brand_query} existiert bereits.")
        # Issue per CLI schließen und Skript sauber beenden
        subprocess.run(["gh", "issue", "close", issue_number, "--comment", f"ℹ️ **Abbruch:** Die Marke `{brand_query}` existiert bereits in der Datenbank (Treffer in Name oder Keywords)."])
        sys.exit(0)

prompt = f"""
Recherchiere den ethischen Hintergrund für die Marke oder den Konzern: "{brand_query}".
Fokus: Rechte Verstrickungen, Ausbeutung, Sexismus, Neokolonialismus.
Liefere das Ergebnis AUSSCHLIESSLICH als valides JSON-Objekt.

Schema:
{{
  "keywords": ["kleingeschriebene_suchbegriffe", "submarken"],
  "brand": "{brand_query}",
  "parent": "Name des Mutterkonzerns",
  "status": "RED" oder "YELLOW" oder "GREEN",
  "reason": "Präzise Begründung der ethischen Bewertung auf Deutsch (max. 3 Sätze).",
  "sources": [],
  "alternatives": [
    {{ "name": "Ethische Alternative", "keyword": "suchbegriff" }}
  ]
}}
"""

url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
payload = {
    "contents": [{"parts": [{"text": prompt}]}],
    "generationConfig": {"responseMimeType": "application/json"}
}

try:
    response = requests.post(url, json=payload)
    response.raise_for_status()
    result_json = response.json()
    text_output = result_json['candidates'][0]['content']['parts'][0]['text']
except Exception as e:
    print(f"API-Fehler: {e}")
    sys.exit(1)

# --- VALIDIERUNGS-BLOCK ---
try:
    new_entry = json.loads(text_output)
    
    required_keys = {"keywords", "brand", "parent", "status", "reason", "alternatives"}
    if not required_keys.issubset(new_entry.keys()):
        raise ValueError("LLM hat das Schema ignoriert (fehlende Keys).")
        
    if new_entry["status"] not in ["RED", "YELLOW", "GREEN"]:
        raise ValueError(f"Ungültiger Status: {new_entry['status']}")
    
    # Halluzinations-Schutz: Quellen immer auf leere Liste zwingen
    new_entry["sources"] = []
        
except Exception as e:
    print(f"Validierungsfehler: {e}")
    sys.exit(1)

# --- SPEICHERN ---
db["entries"].append(new_entry)
db["last_updated"] = datetime.now().strftime("%Y-%m-%d")

with open("brands.json", "w", encoding="utf-8") as f:
    json.dump(db, f, ensure_ascii=False, indent=2)

print(f"Erfolgreich hinzugefügt: {brand_query}")
