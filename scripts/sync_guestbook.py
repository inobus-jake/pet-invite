import json
import urllib.request

TOPIC = "inobus-pet-2026-gb-7Kq2xW9mR4tZ"
PATH = "guestbook.json"

with open(PATH, encoding="utf-8") as f:
    data = json.load(f)

entries = data.get("entries", [])
seen = {e["id"] for e in entries}

req = urllib.request.Request(
    f"https://ntfy.sh/{TOPIC}/json?poll=1&since=all",
    headers={"User-Agent": "pet-invite-guestbook-sync"},
)
with urllib.request.urlopen(req, timeout=30) as resp:
    lines = resp.read().decode("utf-8").splitlines()

added = 0
for line in lines:
    line = line.strip()
    if not line:
        continue
    m = json.loads(line)
    if m.get("event") != "message" or m.get("id") in seen:
        continue
    try:
        payload = json.loads(m.get("message") or "")
    except ValueError:
        continue
    if not isinstance(payload, dict):
        continue
    name = str(payload.get("name") or "").strip()[:20]
    try:
        party = int(payload.get("party"))
    except (TypeError, ValueError):
        continue
    if not name or not 1 <= party <= 11:
        continue
    msg = str(payload.get("msg") or "").strip()[:60]
    entries.append({"id": m["id"], "time": m["time"], "name": name, "party": party, "msg": msg})
    seen.add(m["id"])
    added += 1

if added:
    entries.sort(key=lambda e: e["time"])
    data["entries"] = entries
    with open(PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
        f.write("\n")

print(f"added {added}")
