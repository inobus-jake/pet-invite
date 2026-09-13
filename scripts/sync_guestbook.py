import hashlib
import json
import re
import urllib.request

TOPIC = "inobus-pet-2026-gb-7Kq2xW9mR4tZ"
PATH = "guestbook.json"
HEX64 = re.compile(r"^[0-9a-f]{64}$")


def fields(p):
    name = str(p.get("name") or "").strip()[:20]
    try:
        party = int(p.get("party"))
    except (TypeError, ValueError):
        return None
    if not name or not 1 <= party <= 11:
        return None
    return {"name": name, "party": party, "msg": str(p.get("msg") or "").strip()[:60]}


def sha256(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def valid_hash(value):
    return isinstance(value, str) and bool(HEX64.match(value))


def apply_events(data, events):
    entries = {}
    for e in data.get("entries", []):
        uid = e.get("uid") or e.get("id")
        f = fields(e)
        if not uid or not f:
            continue
        entry = {"uid": uid, "eid": e.get("eid") or e.get("id") or uid, "time": e.get("time", 0), **f,
                 "kh": e.get("kh") if valid_hash(e.get("kh")) else ""}
        if "edited" in e:
            entry["edited"] = e["edited"]
        entries[uid] = entry
    deleted = set(data.get("deleted", []))
    applied = set(data.get("applied", []))

    changed = False
    for ev in events:
        eid = ev.get("id")
        if ev.get("event") != "message" or not eid or eid in applied:
            continue
        applied.add(eid)
        changed = True
        try:
            p = json.loads(ev.get("message") or "")
        except ValueError:
            continue
        if not isinstance(p, dict):
            continue

        kind = p.get("type") or "create"
        uid = str(p.get("uid") or eid)[:40]

        if kind == "create":
            f = fields(p)
            if uid in entries or uid in deleted or not f:
                continue
            entries[uid] = {"uid": uid, "eid": eid, "time": ev.get("time", 0), **f,
                            "kh": p["kh"] if valid_hash(p.get("kh")) else ""}
            continue

        cur = entries.get(uid)
        key = p.get("key")
        if not cur or not cur["kh"] or not isinstance(key, str) or sha256(key) != cur["kh"]:
            continue
        if kind == "update":
            f = fields(p)
            if not f or not valid_hash(p.get("kh")):
                continue
            cur.update(f)
            cur["kh"] = p["kh"]
            cur["edited"] = ev.get("time", 0)
        elif kind == "delete":
            del entries[uid]
            deleted.add(uid)

    data["hide"] = data.get("hide", [])
    data["entries"] = sorted(entries.values(), key=lambda e: e["time"])
    data["deleted"] = sorted(deleted)
    data["applied"] = sorted(applied)
    return changed


def main():
    with open(PATH, encoding="utf-8") as f:
        data = json.load(f)
    req = urllib.request.Request(
        f"https://ntfy.sh/{TOPIC}/json?poll=1&since=all",
        headers={"User-Agent": "pet-invite-guestbook-sync"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        events = [json.loads(line) for line in resp.read().decode("utf-8").splitlines() if line.strip()]
    if apply_events(data, events):
        with open(PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=1)
            f.write("\n")
        print("updated")
    else:
        print("no new events")


if __name__ == "__main__":
    main()
