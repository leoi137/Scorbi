#!/usr/bin/env python3
"""Copy folders to Google Drive and verify every file.

    python training/tools/drive_sync.py push [--record files.json] <local folder> <Drive path> [<local> <Drive path> ...]

The Drive path is below the root folder named by SCORBI_DRIVE_ROOT (default "Autonomous-Robotics").
Reads GDRIVE_CLIENT_ID, GDRIVE_CLIENT_SECRET and GDRIVE_TOKEN from the environment and prints none
of them. Run it where those are set, not on a rented GPU.

A file already in Drive with the same MD5 is left alone, so a rerun only sends what changed. After
each upload the size and MD5 Drive reports are compared with the local file. The record file lists
every file with its Drive id, size and SHA-256. Exits 1 if any file does not match.
"""
import hashlib
import json
import os
import pathlib
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

API = "https://www.googleapis.com/drive/v3"
UPLOAD = "https://www.googleapis.com/upload/drive/v3"
FOLDER = "application/vnd.google-apps.folder"
AUTH: dict[str, str] = {}


def call(method: str, url: str, data: bytes | None = None, headers: dict | None = None):
    """Returns (parsed JSON body, response headers). Retries what Drive says to retry."""
    for attempt in range(6):
        req = urllib.request.Request(url, data=data, method=method, headers={**AUTH, **(headers or {})})
        try:
            with urllib.request.urlopen(req, timeout=600) as r:
                body = r.read()
                return (json.loads(body) if body else {}), r.headers
        except urllib.error.HTTPError as e:
            if e.code in (403, 429, 500, 502, 503, 504) and attempt < 5:
                time.sleep(2**attempt)
                continue
            raise SystemExit(f"Drive {method} {url.split('?')[0]}: HTTP {e.code} {e.read()[:300].decode('utf8', 'replace')}")
        except urllib.error.URLError:
            if attempt == 5:
                raise
            time.sleep(2**attempt)


def sign_in() -> None:
    saved = json.loads(os.environ["GDRIVE_TOKEN"])
    body = urllib.parse.urlencode({
        "client_id": os.environ["GDRIVE_CLIENT_ID"],
        "client_secret": os.environ["GDRIVE_CLIENT_SECRET"],
        "refresh_token": saved["refresh_token"],
        "grant_type": "refresh_token",
    }).encode()
    AUTH["Authorization"] = "Bearer " + call("POST", "https://oauth2.googleapis.com/token", data=body)[0]["access_token"]


def children(parent: str) -> dict[str, dict]:
    found, page = {}, ""
    while True:
        q = urllib.parse.quote(f"'{parent}' in parents and trashed = false")
        r, _ = call("GET", f"{API}/files?q={q}&fields=nextPageToken,files(id,name,mimeType,md5Checksum,size)&pageSize=1000{page}")
        for f in r.get("files", []):
            found.setdefault(f["name"], f)
        if not r.get("nextPageToken"):
            return found
        page = "&pageToken=" + urllib.parse.quote(r["nextPageToken"])


_listing: dict[str, dict[str, dict]] = {}


def listing(parent: str) -> dict[str, dict]:
    if parent not in _listing:
        _listing[parent] = children(parent)
    return _listing[parent]


def folder(parent: str, name: str) -> str:
    here = listing(parent)
    if name in here:
        if here[name]["mimeType"] != FOLDER:
            raise SystemExit(f"{name} exists in Drive and is not a folder")
        return here[name]["id"]
    made, _ = call("POST", f"{API}/files?fields=id,name,mimeType", json.dumps({"name": name, "mimeType": FOLDER, "parents": [parent]}).encode(), {"Content-Type": "application/json"})
    here[name] = made
    _listing[made["id"]] = {}
    return made["id"]


def digests(path: pathlib.Path) -> tuple[str, str]:
    md5, sha = hashlib.md5(), hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            md5.update(block)
            sha.update(block)
    return md5.hexdigest(), sha.hexdigest()


def send(path: pathlib.Path, parent: str) -> tuple[dict, str]:
    """Returns (the file as Drive reports it, 'sent' or 'kept')."""
    md5, _ = digests(path)
    there = listing(parent).get(path.name)
    if there and there.get("md5Checksum") == md5:
        return there, "kept"
    size = path.stat().st_size
    head = {"Content-Type": "application/json", "X-Upload-Content-Length": str(size)}
    if there:
        _, h = call("PATCH", f"{UPLOAD}/files/{there['id']}?uploadType=resumable", b"{}", head)
    else:
        _, h = call("POST", f"{UPLOAD}/files?uploadType=resumable", json.dumps({"name": path.name, "parents": [parent]}).encode(), head)
    made, _ = call("PUT", h["Location"], path.read_bytes(), {"Content-Length": str(size)})
    now, _ = call("GET", f"{API}/files/{made['id']}?fields=id,name,mimeType,md5Checksum,size")
    listing(parent)[path.name] = now
    return now, "sent"


def push(pairs: list[tuple[pathlib.Path, str]], record: pathlib.Path) -> int:
    sign_in()
    root_name = os.environ.get("SCORBI_DRIVE_ROOT", "Autonomous-Robotics")
    root = listing("root").get(root_name)
    if not root or root["mimeType"] != FOLDER:
        raise SystemExit(f"no folder named {root_name} at the top of the Drive")
    rows, bad, sent = [], 0, 0
    for local, remote in pairs:
        files = sorted(p for p in local.rglob("*") if p.is_file())
        for path in files:
            parts = [p for p in remote.strip("/").split("/") if p] + list(path.relative_to(local).parts[:-1])
            parent = root["id"]
            for part in parts:
                parent = folder(parent, part)
            there, how = send(path, parent)
            md5, sha = digests(path)
            ok = there.get("md5Checksum") == md5 and int(there.get("size", -1)) == path.stat().st_size
            bad += not ok
            sent += how == "sent"
            rows.append({"path": "/".join(parts + [path.name]), "drive_file_id": there["id"], "bytes": path.stat().st_size, "sha256": sha, "verified": ok})
            if not ok:
                print("MISMATCH", rows[-1]["path"])
    record.write_text(json.dumps({"drive_root": root_name, "checked_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "files": rows}, indent=1))
    total = sum(r["bytes"] for r in rows)
    print(f"{len(rows)} files, {total / 1e6:.1f} MB: {sent} sent, {len(rows) - sent} already there, {bad} mismatched. Record: {record}")
    return 1 if bad else 0


if __name__ == "__main__":
    argv = sys.argv[1:]
    if not argv or argv[0] != "push":
        raise SystemExit(__doc__)
    argv = argv[1:]
    record = pathlib.Path("drive_files.json")
    if argv[:1] == ["--record"]:
        record, argv = pathlib.Path(argv[1]), argv[2:]
    if not argv or len(argv) % 2:
        raise SystemExit(__doc__)
    raise SystemExit(push([(pathlib.Path(argv[i]), argv[i + 1]) for i in range(0, len(argv), 2)], record))
