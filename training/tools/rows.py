#!/usr/bin/env python3
"""Turn a recorded run into rows for the shared record (the training_* tables), and send them.

    python training/tools/rows.py build <run folder> <Drive record .json> --session 2026-11-a --out rows.json [--slim]
    python training/tools/rows.py push rows.json            # needs SUPABASE_URL and SUPABASE_SECRET_KEY

`build` reads only files and talks to nothing. A row points at other rows by name, in fields that
start with "@": "@run" is a run's folder name, "@file" a Drive path, "@checkpoint" an iteration,
"@episode" [batch, cell, seed]. `push` looks the ids up and upserts, so sending a run twice changes
nothing. Run it in the orb, never on a rented GPU. Only files that are in Drive and verified get rows.

`--slim` is for a database with little room. An episode keeps only the SLIM_NUMBERS in `numbers`, and an
episode of the fixed-seed batch that is not a picked moment keeps none: with 32 seeds of 13 commands at every
checkpoint those are nine rows in ten. The description of the ball goes once into the run's manifest
(`recorded.ball`) instead of into every ball episode. Everything left out is in that checkpoint's episodes.json
in Drive, beside its poses file, and sending the full rows later fills it in.
"""
import argparse
import json
import os
import pathlib
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

GPU_USD_PER_HOUR = 0.174
VAST_INSTANCE = 61888788
CAMERAS = {"pet": "CAM_PET", "side": "CAM_SIDE", "top": "CAM_TOP", "fixed": "CAM_FIXED"}
# What an episode row keeps in `numbers` when built with --slim: what a video's caption or a filter needs.
SLIM_NUMBERS = ("achieved", "parked_share", "largest_tilt_deg", "time_upright_seconds", "along_command_10s_m", "fall_cause",
                "torque_peak_max_n_m", "torque_mean_max_n_m", "share_of_time_at_limit_max")
EPISODE_COLUMNS = ("cell", "seed", "duration_seconds", "success", "reward", "fell_at_seconds", "fail_label", "funny_score", "motor_mark", "pushes")


def lean(value):
    """Floats to 4 significant figures, so 300,000 episode rows stay small. The full numbers are in episodes.json in Drive."""
    if isinstance(value, float):
        return float(f"{value:.4g}")
    if isinstance(value, dict):
        return {k: lean(v) for k, v in value.items()}
    if isinstance(value, list):
        return [lean(v) for v in value]
    return value


def file_kind(rel: str) -> str:
    name = rel.rsplit("/", 1)[-1]
    if name == "manifest.json":
        return "manifest"
    if rel.startswith("params/"):
        return "config"
    if name.endswith(".pt"):
        return "model"
    if "/export/" in rel and name in ("policy.onnx", "policy.json"):
        return "policy"
    if name == "poses.npz":
        return "poses"
    if name == "detail.npz":
        return "full_states"
    if name.endswith(".mp4"):
        return "video"
    if name.endswith((".log", ".jsonl")) or name in ("checkpoints.json", "finished.json", "eval_done.json"):
        return "log"
    return "other"


def build(run_dir: pathlib.Path, record_path: pathlib.Path, session: str, slim: bool = False) -> dict:
    run = run_dir.name
    scorbi = run_dir / "scorbi"
    manifest = json.loads((scorbi / "manifest.json").read_text())
    meta = manifest.get("meta", {})
    record = json.loads(record_path.read_text())
    finished = json.loads((scorbi / "finished.json").read_text()) if (scorbi / "finished.json").exists() else None
    done = json.loads((scorbi / "eval_done.json").read_text()) if (scorbi / "eval_done.json").exists() else None
    marker = f"/{run}/"
    in_drive = {f["path"].split(marker, 1)[1]: f for f in record["files"] if marker in f["path"] and f.get("verified")}
    path_of = lambda rel: in_drive[rel]["path"]  # noqa: E731

    evals = {}  # folder name -> its episodes.json
    for folder in sorted((scorbi / "eval").iterdir()) if (scorbi / "eval").exists() else []:
        rel = f"scorbi/eval/{folder.name}"
        if folder.is_dir() and (folder / "episodes.json").exists() and f"{rel}/poses.npz" in in_drive:
            evals[folder.name] = json.loads((folder / "episodes.json").read_text())
    wall = (finished or {}).get("wall_seconds", 0.0) + sum(e["meta"]["wall_seconds"] for e in evals.values())
    seeds_meta = next((e["meta"] for e in evals.values() if e["meta"]["batch"] == "seeds"), None)

    rewards = manifest["reward_config"]
    kind = "what_if" if meta.get("config_diff") and meta.get("kind") != "production" and "reward" in meta.get("config_diff", "") else "series"
    has_parent = all(meta.get(k) for k in ("parent_run", "config_diff", "change_reason"))
    all_verified = bool(in_drive) and all(f.get("verified") for f in record["files"])
    run_row = {
        "name": run, "session": session, "kind": kind, "skill_number": None, "skill": meta.get("skill", "WALK"),
        "success_test": json.dumps(seeds_meta["tests"]) if seeds_meta and seeds_meta.get("tests") else None,  # the pilot predates the tests
        "@parent_run": meta["parent_run"] if has_parent else None,
        "config_diff": meta["config_diff"] if has_parent else None,
        "change_reason": meta["change_reason"] if has_parent else None,
        "status": "done" if finished and (done or evals) else "running",  # the pilot predates eval_done.json
        "num_envs": manifest["num_envs"], "policy_observations": manifest["policy_observations"],
        "reward_config": json.dumps(rewards, indent=1),
        "reward_code": "\n\n".join(f"# {name}\n{code}" for name, code in manifest["reward_code"].items() if code),
        "manifest": {k: v for k, v in manifest.items() if k not in ("reward_config", "reward_code", "policy_observations")}
        | {"recorded": {"training": finished, "evaluation": done, "kind_in_plan": meta.get("kind"), "seconds_on_gpu": wall}},
        "gpu_hours": round(wall / 3600, 4), "cost_usd": round(wall / 3600 * GPU_USD_PER_HOUR, 4),
        "gpu_name": manifest.get("gpu"), "vast_instance_id": VAST_INSTANCE,
        "started_at": manifest.get("started_at"), "finished_at": (done or finished or {}).get("finished_at"),
        "synced_at": record.get("checked_at"), "verified_at": record.get("checked_at") if all_verified else None,
        "notes": meta.get("what"),
    }

    files = []
    for rel, f in sorted(in_drive.items()):
        kind_ = file_kind(rel)
        row = {"@run": run, "drive_file_id": f["drive_file_id"], "path": f["path"], "kind": kind_, "rate_hz": None, "channels": None, "bytes": f["bytes"], "sha256": f["sha256"]}
        if kind_ in ("poses", "full_states"):
            e = evals.get(rel.split("/")[2])
            if e is None or (kind_ == "full_states" and not e["meta"].get("detail")):
                row["kind"] = "other"
            elif kind_ == "poses":
                row |= {"rate_hz": e["meta"]["rate_hz"], "channels": [k for k in e["meta"]["channels"] if k != "length"]}
            else:
                row |= {"rate_hz": e["meta"]["detail"]["rate_hz"], "channels": list(e["meta"]["detail"]["columns"])}
        files.append(row)

    iterations = []
    for line in (scorbi / "iterations.jsonl").read_text().splitlines():
        r = json.loads(line)
        extras = dict(r.get("extras") or {}) | {"metrics": r.get("metrics", {}), "measured_terms": r.get("measured_terms", {}), "episodes_finished": r.get("episodes_finished"),
                                                 "non_finite_rewards_total": r.get("non_finite_rewards_total", 0)}
        iterations.append({"@run": run, "iteration": r["iteration"], "mean_reward": r["mean_reward"], "mean_episode_seconds": r["mean_episode_seconds"], "success_rate": None,
                           "reward_terms": r["reward_terms"], "termination_rates": r["termination_rates"], "terrain_levels": {},
                           "env_steps_total": r["env_steps_total"], "episodes_total": r["episodes_total"], "sim_seconds_total": r["sim_seconds_total"],
                           "wall_seconds_total": r["wall_seconds_total"], "falls_total": r["falls_total"], "extras": extras})

    checkpoints, episodes, moments = [], [], []
    for c in json.loads((scorbi / "checkpoints.json").read_text()):
        n = c["iteration"]
        e = evals.get(str(n))
        policy = f"scorbi/export/{n}/policy.onnx"
        checkpoints.append({"@run": run, "iteration": n, "gait": e.get("gait") if e else None, "gait_stats": e.get("gait_stats") if e else None, "swarm": f"{n}_swarm" in evals, "cheat_reason": None,
                            "@model_file": path_of(f"scorbi/{c['file']}") if f"scorbi/{c['file']}" in in_drive else None,
                            "@policy_file": path_of(policy) if policy in in_drive else None})
    saved = {c["iteration"] for c in checkpoints}
    unscored = []
    for folder, e in evals.items():
        m = e["meta"]
        # The pilot run was recorded before the pass tests existed. An episode row must say passed or failed, so its
        # episodes get no rows; the files they are in do, and the run's notes say where they are.
        if e["episodes"] and "success" not in e["episodes"][0]:
            unscored.append(folder)
            continue
        n, batch = m["iteration"], m["batch"]
        if n not in saved or batch not in ("seeds", "noise", "training_noise", "do_nothing", "swarm", "extra", "ball"):
            continue
        # A checkpoint has one 'noise' batch in the table. Where a batch with the checkpoint's own training noise
        # exists (32 seeds), it is the one stored; the older fixed-noise batch (8 seeds) stays in Drive only.
        if batch == "noise" and f"{n}_training_noise" in evals:
            continue
        # The table knows five batches. The ball episodes (skill 5) are stored as 'extra', like the shove ladder:
        # their cells are named forward_ball_400 and so on, their moments are tagged 'ball', and setup.ball has the ball.
        tag, batch = batch, "extra" if batch == "ball" else "noise" if batch == "training_noise" else batch
        poses = path_of(f"scorbi/eval/{folder}/poses.npz")
        detail_rel = f"scorbi/eval/{folder}/detail.npz"
        picked = {(mo["cell"], mo["seed"]) for mo in e["moments"]}
        if slim and m.get("ball"):
            run_row["manifest"]["recorded"]["ball"] = m["ball"]
        for ep in e["episodes"]:
            row = {k: lean(ep[k]) for k in EPISODE_COLUMNS}
            row |= {"@run": run, "@checkpoint": n, "batch": batch, "@poses_file": poses, "poses_index": ep["index"], "terrain_type": "flat", "terrain_level": None,
                    "numbers": lean({k: v for k, v in ep.items() if k not in EPISODE_COLUMNS and k not in ("index", "command", "skill", "torque_peak_n_m", "torque_mean_n_m")}
                                    | {"torque_peak_max_n_m": max(ep["torque_peak_n_m"][:12]), "torque_mean_max_n_m": max(ep["torque_mean_n_m"][:12])}),
                    "setup": {"command": ep["command"], "noise_std": m["noise_std"], "skill": ep.get("skill")} | ({"ball": m["ball"]} if m.get("ball") else {})}
            if slim:
                keep = batch != "seeds" or (ep["cell"], ep["seed"]) in picked
                row["numbers"] = ({k: v for k, v in row["numbers"].items() if k in SLIM_NUMBERS} if keep else {}) | {"slim": True}
                if "ball" in row["setup"]:
                    row["setup"]["ball"] = {k: m["ball"][k] for k in ("mass_kg", "radius_m", "hits_at_seconds")}
            episodes.append(row)
        for mo in e["moments"]:
            detail = mo.get("detail_index") is not None and detail_rel in in_drive
            label = f"{mo['fail_label']}" if mo.get("fail_label") else "clean"
            moments.append({"@run": run, "@checkpoint": n, "@episode": [batch, mo["cell"], mo["seed"]], "start_seconds": mo["start_seconds"], "end_seconds": mo["end_seconds"],
                            "kind": mo["kind"], "description": f"{mo['cell']}, seed {mo['seed']}, iteration {n}: {label}" + (f" ({mo['note']})" if mo.get("note") else ""),
                            "tags": [t for t in (mo["cell"], mo.get("fail_label"), tag) if t],
                            "@states_file": path_of(detail_rel) if detail else None, "states_index": mo["detail_index"] if detail else None})

    renders = []
    recorded = {(e["@checkpoint"], e["batch"], e["cell"], e["seed"]) for e in episodes}
    for rel in in_drive:
        found = re.fullmatch(r"scorbi/previews/iter(\d+)_([a-z0-9_]+?)_seed(\d+)_([a-z]+)\.mp4", rel)
        if found and found.group(4) in CAMERAS:
            cell = found.group(2)
            batch = "extra" if re.search(r"_(ball|shoved)_\d+$", cell) else "seeds"  # the ball and the shove ladder are stored as 'extra'
            episode = (int(found.group(1)), batch, cell, int(found.group(3)))
            if episode not in recorded:  # a clip whose name matches no recorded episode gets a file row only
                print(f"no render row for {rel}: no episode {episode}", file=sys.stderr)
                continue
            renders.append({"@run": run, "@checkpoint": episode[0], "@episode": [batch, cell, episode[3]], "camera": CAMERAS[found.group(4)], "kind": "preview", "@file": path_of(rel)})
    if unscored:
        clips = sorted(rel for rel in in_drive if rel.startswith("scorbi/previews/"))
        run_row["notes"] = ((run_row["notes"] + ". ") if run_row["notes"] else "") + (
            f"The pilot run, recorded before the pass tests existed: its episodes have no pass or fail, so they have no rows in training_episodes. "
            f"They are in episodes.json and poses.npz (50 Hz) under scorbi/eval/{{{', '.join(unscored)}}}/ of this run's Drive folder."
            + (f" Clips: {', '.join(clips)}." if clips else ""))
    return {"training_runs": [run_row], "training_files": files, "training_iterations": iterations, "training_checkpoints": checkpoints,
            "training_episodes": episodes, "training_moments": moments, "training_renders": renders}


# ── sending ──────────────────────────────────────────────────────────────


def api(method: str, table: str, query: str = "", body=None, prefer: str = ""):
    # SUPABASE_REST_PATH is "" when testing against a bare PostgREST, which serves tables at the root.
    url = os.environ["SUPABASE_URL"].rstrip("/") + os.environ.get("SUPABASE_REST_PATH", "/rest/v1") + f"/{table}" + (f"?{query}" if query else "")
    key = os.environ["SUPABASE_SECRET_KEY"]
    headers = {"apikey": key, "Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    if prefer:
        headers["Prefer"] = prefer
    request = urllib.request.Request(url, method=method, headers=headers, data=json.dumps(body).encode() if body is not None else None)
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            text = response.read().decode()
            return json.loads(text) if text else []
    except urllib.error.HTTPError as err:
        raise SystemExit(f"{method} {table}: {err.code} {err.read().decode()[:500]}") from None


def upsert(table: str, rows: list[dict], conflict: str, returning: str) -> list[dict]:
    out = []
    for i in range(0, len(rows), 500):
        out += api("POST", table, f"on_conflict={conflict}&select={returning}", rows[i : i + 500], "resolution=merge-duplicates,return=representation")
    return out


def fetch_all(table: str, query: str) -> list[dict]:
    """Every matching row. Supabase returns at most 1,000 rows a request, so this pages by id."""
    out, last = [], 0
    while True:
        page = api("GET", table, f"{query}&id=gt.{last}&order=id&limit=1000")
        out += page
        if len(page) < 1000:
            return out
        last = page[-1]["id"]


def push(rows: dict) -> None:
    plain = lambda row: {k: v for k, v in row.items() if not k.startswith("@")}  # noqa: E731
    run_row = rows["training_runs"][0]
    parent = run_row.get("@parent_run")
    body = plain(run_row)
    if parent:
        found = api("GET", "training_runs", f"select=id,name&or=(name.eq.{urllib.parse.quote(parent)},name.like.*_{urllib.parse.quote(parent)})")
        if not found:
            raise SystemExit(f"the parent run {parent} has no row yet; send it first")
        body["parent_run_id"] = found[0]["id"]
    run_id = upsert("training_runs", [body], "name", "id")[0]["id"]
    files = {f["path"]: f["id"] for f in upsert("training_files", [plain(f) | {"run_id": run_id} for f in rows["training_files"]], "path", "id,path")}
    upsert("training_iterations", [plain(r) | {"run_id": run_id} for r in rows["training_iterations"]], "run_id,iteration", "iteration")
    checkpoints = {c["iteration"]: c["id"] for c in upsert(
        "training_checkpoints",
        [plain(c) | {"run_id": run_id, "model_file_id": files.get(c["@model_file"]), "policy_file_id": files.get(c["@policy_file"])} for c in rows["training_checkpoints"]],
        "run_id,iteration", "id,iteration")}
    sent = upsert("training_episodes", [plain(e) | {"checkpoint_id": checkpoints[e["@checkpoint"]], "poses_file_id": files[e["@poses_file"]]} for e in rows["training_episodes"]],
                  "checkpoint_id,batch,cell,seed", "id,checkpoint_id,batch,cell,seed")
    episodes = {(e["checkpoint_id"], e["batch"], e["cell"], e["seed"]): e["id"] for e in sent}
    episode_of = lambda row: episodes[(checkpoints[row["@checkpoint"]], *row["@episode"])]  # noqa: E731
    # Moments have no unique key in the table. One is taken as sent already when its episode has a moment of the
    # same kind over the same seconds, so sending a run again, or after a send that broke off, adds only what is missing.
    ids = ",".join(str(i) for i in checkpoints.values())
    made = fetch_all("training_moments", f"select=id,episode_id,kind,start_seconds,end_seconds&checkpoint_id=in.({ids})")
    key = lambda m: (m["episode_id"], m["kind"], round(float(m["start_seconds"]), 3), round(float(m["end_seconds"]), 3))  # noqa: E731
    there = {key(m) for m in made}
    batch = [plain(m) | {"checkpoint_id": checkpoints[m["@checkpoint"]], "episode_id": episode_of(m), "states_file_id": files.get(m["@states_file"])} for m in rows["training_moments"]]
    batch = [m for m in batch if key(m) not in there]
    for i in range(0, len(batch), 500):
        made += api("POST", "training_moments", "select=id,episode_id", batch[i : i + 500], "return=representation")
    by_episode = {m["episode_id"]: m["id"] for m in made}
    renders = []
    for r in rows["training_renders"]:
        episode = episode_of(r)
        if episode not in by_episode:  # a render of an episode that was not a picked moment: make its moment
            by_episode[episode] = api("POST", "training_moments", "select=id", [{"checkpoint_id": checkpoints[r["@checkpoint"]], "episode_id": episode, "start_seconds": 0, "end_seconds": 20,
                                                                                "kind": "preview", "description": "rendered as a preview", "tags": [], "states_file_id": None, "states_index": None}], "return=representation")[0]["id"]
        renders.append(plain(r) | {"moment_id": by_episode[episode], "file_id": files[r["@file"]]})
    if renders:
        upsert("training_renders", renders, "file_id", "id")
    print(f"{run_row['name']}: run {run_id}, " + ", ".join(f"{len(v)} {k.removeprefix('training_')}" for k, v in rows.items() if k != "training_runs"))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    b = sub.add_parser("build")
    b.add_argument("run_dir")
    b.add_argument("record")
    b.add_argument("--session", required=True)
    b.add_argument("--out", required=True)
    b.add_argument("--slim", action="store_true", help="keep only SLIM_NUMBERS in each episode's numbers")
    p = sub.add_parser("push")
    p.add_argument("rows")
    args = parser.parse_args()
    if args.command == "build":
        rows = build(pathlib.Path(args.run_dir).resolve(), pathlib.Path(args.record), args.session, args.slim)
        pathlib.Path(args.out).write_text(json.dumps(rows))
        print(f"{args.out}: " + ", ".join(f"{len(v)} {k.removeprefix('training_')}" for k, v in rows.items()))
    else:
        push(json.loads(pathlib.Path(args.rows).read_text()))
    sys.exit(0)
