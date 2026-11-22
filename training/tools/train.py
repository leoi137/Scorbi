#!/usr/bin/env python3
"""Train a Scorbi task with Isaac Lab's own RSL-RL entry point, recorded to the content spec.

    cd /workspace/isaaclab && SCORBI_RUN_META='{"skill": "WALK", "kind": "probe"}' \
        uv run python /workspace/Scorbi/training/tools/train.py --task Scorbi-Velocity-Flat --seed 1 \
        --max_iterations 500 --run_name baseline_s1

The training loop is Isaac Lab's, unchanged. This file adds, in the run's `scorbi/` folder:

  manifest.json      robots, seed, the policy's observation list, the full reward config and the
                     reward code as text, the versions, the GPU, and SCORBI_RUN_META
  iterations.jsonl   one row per iteration: every reward term, every termination cause, and the
                     cumulative counters (steps, episodes, simulated time, wall-clock time, falls)
  ckpt_<n>.pt        the policy after n updates, on the dense-early schedule. ckpt_0.pt is the
                     untrained policy ("try 1"); rsl_rl's own model_0.pt is after one update.

Iteration n here means "after n updates", so iteration 0 is untrained.
"""
import hashlib
import inspect
import json
import os
import subprocess
import sys
import time

import warp as wp

wp.config.enable_backward = False

import torch  # noqa: E402
from rsl_rl.runners import OnPolicyRunner  # noqa: E402

import scorbi_lab  # noqa: E402,F401  registers the tasks


def is_checkpoint(n: int) -> bool:
    """Dense early, where the learning and the fails are (Account 1 strategy, part 8.4)."""
    if n <= 20:
        return n in (0, 1, 2, 3, 5, 8, 12, 16, 20)
    if n <= 200:
        return n % 10 == 0
    if n <= 1000:
        return n % 25 == 0
    return n % 100 == 0


def sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def plain(value):
    """Config values as JSON: tensors, tuples and config objects become numbers, lists and text."""
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, torch.Tensor):
        return value.tolist()
    if isinstance(value, dict):
        return {str(k): plain(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [plain(v) for v in value]
    if hasattr(value, "to_dict"):
        return plain(value.to_dict())
    return str(value)


def git(*args: str) -> str:
    here = os.path.dirname(os.path.abspath(__file__))
    return subprocess.run(["git", "-C", here, *args], capture_output=True, text=True).stdout.strip()


def write_manifest(runner: OnPolicyRunner, out: str) -> None:
    import importlib.metadata as md

    u = runner.env.unwrapped
    rewards, code = {}, {}
    for name in u.reward_manager.active_terms:
        cfg = u.reward_manager.get_term_cfg(name)
        func = cfg.func
        rewards[name] = {"weight": cfg.weight, "func": f"{func.__module__}.{func.__qualname__}", "params": plain(cfg.params)}
        try:
            code[name] = inspect.getsource(func)
        except (OSError, TypeError):
            code[name] = None
    terminations = {
        name: {"time_out": u.termination_manager.get_term_cfg(name).time_out, "params": plain(u.termination_manager.get_term_cfg(name).params)}
        for name in u.termination_manager.active_terms
    }
    robot = u.scene["robot"]
    action = u.action_manager.get_term("joint_pos")
    names = list(robot.joint_names)
    command = u.cfg.commands.base_velocity
    manifest = {
        "task": u.spec.id if getattr(u, "spec", None) else None,
        "meta": json.loads(os.environ.get("SCORBI_RUN_META", "{}")),
        "argv": sys.argv[1:],
        "seed": runner.cfg.get("seed", u.cfg.seed),
        "num_envs": u.num_envs,
        "num_steps_per_env": runner.cfg["num_steps_per_env"],
        "physics_dt": u.physics_dt,
        "control_dt": u.step_dt,
        "episode_length_s": u.cfg.episode_length_s,
        "physics": plain(u.cfg.sim.physics),
        "policy_observations": list(u.observation_manager.active_terms["policy"]),
        "policy_observation_dims": [list(d) for d in u.observation_manager.group_obs_term_dim["policy"]],
        "critic_observations": list(u.observation_manager.active_terms["critic"]),
        "observation_joints": names,
        "action_joints": [names[i] for i in action._joint_ids],
        "action_scale": plain(u.cfg.actions.joint_pos.scale),
        "default_joint_pos": dict(zip(names, robot.data.default_joint_pos.torch[0].tolist())),
        "command_ranges": plain(command.ranges),
        "rel_standing_envs": command.rel_standing_envs,
        "reward_config": rewards,
        "reward_code": code,
        "terminations": terminations,
        "events": plain(u.cfg.events),
        "agent": plain(runner.cfg),
        "versions": {p: md.version(p) for p in ("isaaclab", "isaaclab_newton", "newton", "mujoco-warp", "rsl-rl-lib", "torch")},
        "gpu": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
        "scorbi_commit": git("rev-parse", "HEAD"),
        "scorbi_dirty": bool(git("status", "--porcelain", "--", "..")),
        "robot_model": scorbi_lab.robot.MODEL["source"],
        "robot_mass_kg": scorbi_lab.robot.MODEL["mass"],
        "started_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "iteration_meaning": "iteration n = the policy after n updates; ckpt_0.pt is untrained",
    }
    with open(os.path.join(out, "manifest.json"), "w") as f:
        json.dump(manifest, f, indent=1)


_learn = OnPolicyRunner.learn


def learn(self: OnPolicyRunner, num_learning_iterations: int, init_at_random_ep_len: bool = False) -> None:
    import scorbi_lab.robot  # noqa: F401

    out = os.path.join(self.logger.log_dir, "scorbi")
    os.makedirs(out, exist_ok=True)
    write_manifest(self, out)
    u = self.env.unwrapped
    n_envs, dt = u.num_envs, u.step_dt
    device = u.device
    totals = {"env_steps": 0, "episodes": 0, "falls": 0}
    it_sums: dict[str, float] = {}
    it_steps = 0
    ep_return = torch.zeros(n_envs, device=device)
    ep_steps = torch.zeros(n_envs, device=device)
    done_return, done_steps, done_count = 0.0, 0.0, 0
    started = time.time()
    checkpoints: list[dict] = []
    rows = open(os.path.join(out, "iterations.jsonl"), "a")

    def save(n: int) -> None:
        path = os.path.join(out, f"ckpt_{n}.pt")
        self.save(path)
        checkpoints.append({"iteration": n, "file": os.path.basename(path), "sha256": sha256(path), "bytes": os.path.getsize(path)})
        with open(os.path.join(out, "checkpoints.json"), "w") as f:
            json.dump(checkpoints, f, indent=1)

    def row(n: int, extra: dict) -> None:
        log = {k: v / max(it_steps, 1) for k, v in it_sums.items()}
        rows.write(json.dumps({
            "iteration": n,
            "mean_reward": done_return / done_count if done_count else None,
            "mean_episode_seconds": done_steps * dt / done_count if done_count else None,
            "episodes_finished": done_count,
            "reward_terms": {k.split("/", 1)[1]: v for k, v in log.items() if k.startswith("Episode_Reward/")},
            "termination_rates": {k.split("/", 1)[1]: v for k, v in log.items() if k.startswith("Episode_Termination/")},
            "metrics": {k.split("/", 1)[1]: v for k, v in log.items() if k.startswith("Metrics/")},
            "env_steps_total": totals["env_steps"],
            "episodes_total": totals["episodes"],
            "sim_seconds_total": totals["env_steps"] * dt,
            "wall_seconds_total": time.time() - started,
            "falls_total": totals["falls"],
            "extras": extra,
        }) + "\n")
        rows.flush()

    env_step = self.env.step

    def step(actions):
        nonlocal it_steps, done_return, done_steps, done_count
        obs, rewards, dones, extras = env_step(actions)
        done = dones.bool()
        ep_return.add_(rewards)
        ep_steps.add_(1)
        finished = int(done.sum())
        if finished:
            falls = done & ~extras["time_outs"].bool() if "time_outs" in extras else done
            totals["episodes"] += finished
            totals["falls"] += int(falls.sum())
            done_return += float(ep_return[done].sum())
            done_steps += float(ep_steps[done].sum())
            done_count += finished
            ep_return[done] = 0
            ep_steps[done] = 0
        totals["env_steps"] += n_envs
        it_steps += 1
        for k, v in extras.get("log", {}).items():
            it_sums[k] = it_sums.get(k, 0.0) + float(v)
        return obs, rewards, dones, extras

    logger_log = self.logger.log

    def log(**kw):
        nonlocal it_steps, done_return, done_steps, done_count
        logger_log(**kw)
        n = kw["it"] + 1
        std = kw.get("action_std")
        row(n, {
            "learning_rate": kw.get("learning_rate"),
            "action_std": float(std.mean()) if std is not None else None,
            "losses": {k: float(v) for k, v in (kw.get("loss_dict") or {}).items()},
            "collect_seconds": kw.get("collect_time"),
            "learn_seconds": kw.get("learn_time"),
        })
        it_sums.clear()
        it_steps, done_return, done_steps, done_count = 0, 0.0, 0.0, 0
        if is_checkpoint(n) or n == self._scorbi_last:
            save(n)

    self.env.step = step
    self.logger.log = log
    self._scorbi_last = self.current_learning_iteration + num_learning_iterations
    self.logger.init_logging_writer()
    if self.current_learning_iteration == 0:
        row(0, {})  # before any step: the counters are all zero
        save(0)
    try:
        _learn(self, num_learning_iterations, init_at_random_ep_len)
    finally:
        rows.close()
        self.env.step = env_step
        with open(os.path.join(out, "finished.json"), "w") as f:
            json.dump({"finished_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "wall_seconds": time.time() - started,
                       "last_iteration": checkpoints[-1]["iteration"] if checkpoints else None, **totals}, f, indent=1)


OnPolicyRunner.learn = learn

if __name__ == "__main__":
    from isaaclab_rl.entrypoints import run_train_cli

    raise SystemExit(run_train_cli(["--rl_library", "rsl_rl", *sys.argv[1:]]))
