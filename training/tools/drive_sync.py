#!/usr/bin/env python3
"""Copy folders to Google Drive and verify every file.

    python training/tools/drive_sync.py push [--record files.json] <local folder> <Drive path> [<local> <Drive path> ...]
    python training/tools/drive_sync.py stream [--record files.json] [--only scorbi,params] <ssh host> <remote folder> <local folder> <Drive path>

`stream` is for a machine with a small disk between a rented GPU and Drive. Every file under the remote
folder that is not in the local folder at its full size goes from the GPU straight into Drive, through this
machine's memory and never onto its disk. Files in the local folder are sent as `push` sends them. Copy the
small files a later step reads (JSON, logs) to the local folder first; the big ones need not be there.

The Drive path is below the root folder named by SCORBI_DRIVE_ROOT (default "Autonomous-Robotics").
Reads GDRIVE_CLIENT_ID, GDRIVE_CLIENT_SECRET and GDRIVE_TOKEN from the environment and prints none
of them. Run it where those are set, not on a rented GPU.

A file already in Drive with the same MD5 is left alone, so a rerun only sends what changed. After
each upload the size and MD5 Drive reports are compared with the local file. The record file lists
every file with its Drive id, size and SHA-256. Exits 1 if any file does not match.
"""
import concurrent.futures
import hashlib
import json
import os
import pathlib
import shlex
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

API = "https://www.googleapis.com/drive/v3"
UPLOAD = "https://www.googleapis.com/upload/drive/v3"
FOLDER = "application/vnd.google-apps.folder"
AUTH: dict[str, str] = {}
# Files sent at once. One upload from the orb runs at about 1 MB/s whatever the line could carry.
WORKERS = int(os.environ.get("DRIVE_WORKERS", 8))
# Files streamed at once from another machine. The line from the GPU carries about 4.5 MB/s in all, and Drive
# resets an upload that trickles, so few streams at a time.
STREAMS = threading.Semaphore(int(os.environ.get("DRIVE_STREAMS", 3)))


def call(method: str, url: str, data: bytes | None = None, headers: dict | None = None):
    """Returns (parsed JSON body, response headers). Retries what Drive says to retry."""
    for attempt in range(6):
        req = urllib.request.Request(url, data=data, method=method, headers={**AUTH, **(headers or {})})
        try:
            with urllib.request.urlopen(req, timeout=600) as r:
                body = r.read()
                return (json.loads(body) if body else {}), r.headers
        except urllib.error.HTTPError as e:
            if e.code == 401 and attempt < 5 and "oauth2.googleapis.com" not in url:  # the access token lasts an hour; a long push outlives it
                sign_in()
                continue
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


class _Hashed:
    """A file-like reader that hashes what passes through it."""

    def __init__(self, raw):
        self.raw, self.md5, self.sha, self.count = raw, hashlib.md5(), hashlib.sha256(), 0

    def read(self, n: int = -1) -> bytes:
        block = self.raw.read(1 << 20 if n is None or n < 0 else n)
        self.md5.update(block)
        self.sha.update(block)
        self.count += len(block)
        return block


def send_stream(host: str, remote: str, name: str, size: int, parent: str, before: dict | None = None) -> tuple[dict, str, str]:
    """One remote file into Drive without touching this disk. Returns (the file as Drive reports it, 'sent' or 'kept', SHA-256).

    `before` is the file's row in the last record. A file Drive still has with that row's id, size and MD5 is taken
    as kept without asking the remote machine again: a run's files are written once.
    """
    quoted = shlex.quote(remote)
    there = listing(parent).get(name)
    if there and before and before.get("verified") and before.get("md5") == there.get("md5Checksum") and before.get("bytes") == size == int(there.get("size", -1)):
        return there, "kept", before["sha256"]
    if there and int(there.get("size", -1)) == size:  # perhaps sent before: compare with the remote file's own hashes
        out = subprocess.run(["ssh", host, f"md5sum {quoted} && sha256sum {quoted}"], capture_output=True, text=True, check=True).stdout.split()
        if out[0] == there.get("md5Checksum"):
            return there, "kept", out[2]
    head = {"Content-Type": "application/json", "X-Upload-Content-Length": str(size)}
    for attempt in range(6):
        if there:
            _, h = call("PATCH", f"{UPLOAD}/files/{there['id']}?uploadType=resumable", b"{}", head)
        else:
            _, h = call("POST", f"{UPLOAD}/files?uploadType=resumable", json.dumps({"name": name, "parents": [parent]}).encode(), head)
        source = subprocess.Popen(["ssh", host, f"cat {quoted}"], stdout=subprocess.PIPE)
        body = _Hashed(source.stdout)
        try:
            req = urllib.request.Request(h["Location"], data=body if size else b"", method="PUT", headers={**AUTH, "Content-Length": str(size)})
            with urllib.request.urlopen(req, timeout=180) as r:
                made = json.loads(r.read())
            if source.wait() != 0 or body.count != size:
                raise OSError(f"read {body.count} of {size} bytes of {remote}")
            now, _ = call("GET", f"{API}/files/{made['id']}?fields=id,name,mimeType,md5Checksum,size")
            if size and now.get("md5Checksum") != body.md5.hexdigest():
                raise OSError(f"Drive's MD5 of {name} is not the MD5 of what was sent")
            listing(parent)[name] = now
            return now, "sent", body.sha.hexdigest() if size else hashlib.sha256(b"").hexdigest()
        except (urllib.error.URLError, OSError) as e:  # an upload that broke off cannot be resumed from a pipe: start it again
            source.kill()
            source.wait()
            if isinstance(e, urllib.error.HTTPError) and e.code == 401:
                sign_in()
            if attempt == 5:
                raise OSError(f"could not stream {remote}: {e}") from None
            time.sleep(5 * 2**attempt)
            there = listing(parent).get(name) or children(parent).get(name)


def stream(host: str, remote: str, local: pathlib.Path, drive_path: str, record: pathlib.Path, only: tuple[str, ...] = ()) -> int:
    sign_in()
    root_name = os.environ.get("SCORBI_DRIVE_ROOT", "Autonomous-Robotics")
    root = listing("root").get(root_name)
    if not root or root["mimeType"] != FOLDER:
        raise SystemExit(f"no folder named {root_name} at the top of the Drive")
    found = subprocess.run(["ssh", host, f"cd {shlex.quote(remote)} && find . -type f -printf '%s\\t%P\\n'"], capture_output=True, text=True, check=True).stdout
    sizes = {rel: int(size) for size, rel in (line.split("\t", 1) for line in found.splitlines())}
    if only:  # the remote folder's other files (a library's own checkpoints, event files) are left where they are
        sizes = {rel: size for rel, size in sizes.items() if rel.split("/")[0] in only}
    on_disk = {str(p.relative_to(local)): p for p in local.rglob("*") if p.is_file() and not p.name.startswith(".")}
    base = [p for p in drive_path.strip("/").split("/") if p]
    earlier = {f["path"]: f for f in json.loads(record.read_text())["files"]} if record.exists() else {}
    jobs = []  # (relative path, parent folder id, local file or None)
    for rel in sorted(set(sizes) | set(on_disk)):
        here = on_disk.get(rel)
        if here is not None and rel in sizes and here.stat().st_size != sizes[rel]:
            here = None  # a copy that broke off: the remote file is the whole one
        parent = root["id"]
        for part in base + rel.split("/")[:-1]:
            parent = folder(parent, part)
        listing(parent)
        jobs.append((rel, parent, here))

    def one(job):
        rel, parent, here = job
        if here is not None:
            there, how = send(here, parent)
            md5, sha = digests(here)
            size = here.stat().st_size
            ok = there.get("md5Checksum") == md5 and int(there.get("size", -1)) == size
        else:
            size = sizes[rel]
            try:
                with STREAMS:
                    there, how, sha = send_stream(host, f"{remote.rstrip('/')}/{rel}", rel.split("/")[-1], size, parent, earlier.get("/".join(base + [rel])))
            except (OSError, subprocess.CalledProcessError) as e:  # one file that will not go does not stop the others; the next run sends it
                print(e, file=sys.stderr)
                there, how, sha = {"id": None}, "failed", None
            ok = int(there.get("size", -1)) == size  # its MD5 was compared when it was sent or kept
        return {"path": "/".join(base + [rel]), "drive_file_id": there["id"], "bytes": size, "sha256": sha, "md5": there.get("md5Checksum"), "verified": ok, "on_this_disk": here is not None}, how

    with concurrent.futures.ThreadPoolExecutor(max_workers=WORKERS) as pool:
        done = list(pool.map(one, jobs))
    rows = [row for row, _ in done]
    bad = [row["path"] for row in rows if not row["verified"]]
    for path in bad:
        print("MISMATCH", path)
    record.write_text(json.dumps({"drive_root": root_name, "checked_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "files": rows}, indent=1))
    streamed = sum(not row["on_this_disk"] for row in rows)
    print(f"{len(rows)} files, {sum(r['bytes'] for r in rows) / 1e6:.1f} MB: {sum(how == 'sent' for _, how in done)} sent, {sum(how == 'kept' for _, how in done)} already there, "
          f"{len(bad)} mismatched; {streamed} of them only on {host} and in Drive. Record: {record}")
    return 1 if bad else 0


def push(pairs: list[tuple[pathlib.Path, str]], record: pathlib.Path) -> int:
    sign_in()
    root_name = os.environ.get("SCORBI_DRIVE_ROOT", "Autonomous-Robotics")
    root = listing("root").get(root_name)
    if not root or root["mimeType"] != FOLDER:
        raise SystemExit(f"no folder named {root_name} at the top of the Drive")
    # Folders are made and listed one at a time, before anything is sent: two uploads making the same folder would make it twice.
    jobs = []
    for local, remote in pairs:
        files = sorted(p for p in local.rglob("*") if p.is_file())
        for path in files:
            parts = [p for p in remote.strip("/").split("/") if p] + list(path.relative_to(local).parts[:-1])
            parent = root["id"]
            for part in parts:
                parent = folder(parent, part)
            listing(parent)
            jobs.append((path, parent, parts))

    def one(job):
        path, parent, parts = job
        there, how = send(path, parent)
        md5, sha = digests(path)
        ok = there.get("md5Checksum") == md5 and int(there.get("size", -1)) == path.stat().st_size
        return {"path": "/".join(parts + [path.name]), "drive_file_id": there["id"], "bytes": path.stat().st_size, "sha256": sha, "verified": ok}, how

    # The files go several at once; the record keeps their sorted order.
    with concurrent.futures.ThreadPoolExecutor(max_workers=WORKERS) as pool:
        done = list(pool.map(one, jobs))
    rows = [row for row, _ in done]
    sent = sum(how == "sent" for _, how in done)
    bad = sum(not row["verified"] for row in rows)
    for row in rows:
        if not row["verified"]:
            print("MISMATCH", row["path"])
    record.write_text(json.dumps({"drive_root": root_name, "checked_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "files": rows}, indent=1))
    total = sum(r["bytes"] for r in rows)
    print(f"{len(rows)} files, {total / 1e6:.1f} MB: {sent} sent, {len(rows) - sent} already there, {bad} mismatched. Record: {record}")
    return 1 if bad else 0


if __name__ == "__main__":
    argv = sys.argv[1:]
    if not argv or argv[0] not in ("push", "stream"):
        raise SystemExit(__doc__)
    command, argv = argv[0], argv[1:]
    record = pathlib.Path("drive_files.json")
    if argv[:1] == ["--record"]:
        record, argv = pathlib.Path(argv[1]), argv[2:]
    if command == "stream":
        only: tuple[str, ...] = ()
        if argv[:1] == ["--only"]:
            only, argv = tuple(argv[1].split(",")), argv[2:]
        if len(argv) != 4:
            raise SystemExit(__doc__)
        raise SystemExit(stream(argv[0], argv[1], pathlib.Path(argv[2]), argv[3], record, only))
    if not argv or len(argv) % 2:
        raise SystemExit(__doc__)
    raise SystemExit(push([(pathlib.Path(argv[i]), argv[i + 1]) for i in range(0, len(argv), 2)], record))
