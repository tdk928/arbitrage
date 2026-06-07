from __future__ import annotations

import hashlib
import re
import unicodedata
from datetime import datetime

# Common aliases for national teams (BG / EN)
ALIASES: dict[str, str] = {
    "мексико": "mexico",
    "южна африка": "south africa",
    "юар": "south africa",
    "сащ": "usa",
    "англия": "england",
    "германия": "germany",
    "франция": "france",
    "испания": "spain",
    "италия": "italy",
    "бразилия": "brazil",
    "аржентина": "argentina",
    "португалия": "portugal",
    "хърватия": "croatia",
    "белгия": "belgium",
    "холандия": "netherlands",
    "нидерландия": "netherlands",
    "швейцария": "switzerland",
    "чехия": "czechia",
    "южна корея": "south korea",
    "канада": "canada",
    "чили": "chile",
    "еквадор": "ecuador",
    "япония": "japan",
    "австралия": "australia",
    "ман utd": "manchester united",
    "man united": "manchester united",
}


def normalize_team(name: str) -> str:
    text = name.strip().lower()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = re.sub(r"\s*\(ж\)\s*", "", text)
    text = re.sub(r"[^\w\s]", " ", text, flags=re.UNICODE)
    text = re.sub(r"\s+", " ", text).strip()
    for suffix in (" fc", " cf", " sc"):
        if text.endswith(suffix):
            text = text[: -len(suffix)].strip()
    return ALIASES.get(text, text)


def canonical_key(home: str, away: str, kickoff_utc: datetime) -> str:
    h = normalize_team(home)
    a = normalize_team(away)
    date_part = kickoff_utc.strftime("%Y-%m-%d")
    raw = f"{h}|{a}|{date_part}"
    return hashlib.sha256(raw.encode()).hexdigest()[:32]


def split_fixture_name(name: str) -> tuple[str, str] | None:
    for sep in (" vs ", " vs. ", " - ", " – ", " v "):
        if sep in name:
            parts = name.split(sep, 1)
            if len(parts) == 2:
                return parts[0].strip(), parts[1].strip()
    return None
