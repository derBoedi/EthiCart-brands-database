import os
import sys
import json
import requests
from datetime import datetime

issue_title = os.environ.get("ISSUE_TITLE", "")
api_key = os.environ.get("GEMINI_API_KEY")

if not issue_title.startswith("Add:"):
    print("Format ungültig.")
    sys.exit(0)

brand_query = issue_title.replace("Add:", "").strip()

with open("brands.json", "r", encoding="utf-8") as f:
    db = json.load(f)

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

response = requests.post(url, json=payload)
response.raise_for_status()
result_json = response.json()

text_output = result_json['candidates'][0]['content']['parts'][0]['text']

# --- VALIDIERUNGS-BLOCK ---
try:
    new_entry = json.loads(text_output)
    
    required_keys = {"keywords", "brand", "parent", "status", "reason", "alternatives"}
    if not required_keys.issubset(new_entry.keys()):
        raise ValueError("LLM hat das Schema ignoriert (fehlende Keys).")
        
    if new_entry["status"] not in ["RED", "YELLOW", "GREEN"]:
        raise ValueError(f"Ungültiger Status: {new_entry['status']}")
        
except Exception as e:
    print(f"Validierungsfehler: {e}")
    sys.exit(1) # Killt den Workflow mit Error-Code

# --- SPEICHERN ---
db["entries"].append(new_entry)
db["last_updated"] = datetime.now().strftime("%Y-%m-%d")

with open("brands.json", "w", encoding="utf-8") as f:
    json.dump(db, f, ensure_ascii=False, indent=2)

print(f"Erfolgreich hinzugefügt: {brand_query}")
