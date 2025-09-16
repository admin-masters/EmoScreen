# content/state_districts.py
import json
import re
from pathlib import Path

# We allow loading from the JS static file to avoid duplicating the huge mapping.
# The file sets `window.statesAndDistricts = {...}`; we strip the prefix/suffix and parse.
_JS_PATH = Path(__file__).resolve().parent / "static" / "content" / "states_districts.js"

def _load_mapping_from_js() -> dict:
    text = _JS_PATH.read_text(encoding="utf-8")
    # Extract {...} from "window.statesAndDistricts = {...};"
    m = re.search(r"statesAndDistricts\s*=\s*({.*})\s*;", text, flags=re.S)
    if not m:
        # also accept without trailing ;
        m = re.search(r"statesAndDistricts\s*=\s*({.*})\s*", text, flags=re.S)
    raw = m.group(1) if m else "{}"
    # JSON requires double-quotes; the JS snippet already uses them.
    return json.loads(raw)

# Load once
_STATES_TO_DISTRICTS = _load_mapping_from_js()

def list_states():
    states = list(_STATES_TO_DISTRICTS.keys())
    # Keep "NULL" but sort others; show placeholder at top in the form.
    if "NULL" in states:
        states.remove("NULL")
        states = sorted(states) + ["NULL"]
    else:
        states = sorted(states)
    return states

def districts_for_state(state: str):
    if state == "NULL":
        return ["NULL"]
    arr = _STATES_TO_DISTRICTS.get(state) or []
    # Many lists start with "Select district" placeholder in the PDF — drop it
    return [d for d in arr if d and d != "Select district"]

def state_choices():
    return [("", "Select a State")] + [(s, s) for s in list_states()]

def district_choices(state: str):
    if state == "NULL":
        return [("NULL", "NULL")]
    items = districts_for_state(state)
    return [("", "Select a District")] + [(d, d) for d in items]

def is_valid_pair(state: str, district: str) -> bool:
    if not state or not district:
        return False
    if state == "NULL":
        return district == "NULL"
    return district in set(districts_for_state(state))
