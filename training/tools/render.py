#!/usr/bin/env python3
"""Render a recorded episode by playback: the robot is placed in each saved pose. No physics runs.

    MUJOCO_GL=egl python training/tools/render.py <eval folder> --episode 3 --camera pet --out clip.mp4

Needs mujoco, numpy and ffmpeg. Works on a machine with no GPU.
"""
import argparse
import json
import pathlib
import subprocess

import mujoco
import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[2]
CAMERAS = {
    # distance m, azimuth relative to the robot's start heading, elevation, follows the robot
    "pet": (0.75, 145.0, -14.0, True),
    "side": (0.80, 90.0, -6.0, True),
    "top": (0.90, 90.0, -89.0, True),
    "fixed": (1.10, 145.0, -16.0, False),
}

parser = argparse.ArgumentParser()
parser.add_argument("eval_dir")
parser.add_argument("--episode", type=int, required=True, help="the episode's index in episodes.json")
parser.add_argument("--camera", choices=sorted(CAMERAS), default="pet")
parser.add_argument("--out", required=True)
parser.add_argument("--size", default="1080x1920")
parser.add_argument("--fps", type=int, default=30)
parser.add_argument("--start", type=float, default=0.0)
parser.add_argument("--end", type=float, default=None)
args = parser.parse_args()

folder = pathlib.Path(args.eval_dir)
meta = json.loads((folder / "episodes.json").read_text())["meta"]
poses = np.load(folder / "poses.npz")
i = args.episode
length = int(poses["length"][i])
rate = meta["rate_hz"]
pos, quat, joints = poses["root_pos"][: length + 1, i], poses["root_quat"][: length + 1, i], poses["joint_pos"][: length + 1, i]
good = ~np.isnan(pos[:, 0])
pos, quat, joints = pos[good], quat[good], joints[good]
if meta["quat_order"] == "xyzw":
    quat = quat[:, [3, 0, 1, 2]]

width, height = (int(v) for v in args.size.split("x"))
m = mujoco.MjModel.from_xml_path(str(ROOT / "scorpion" / "scene.xml"))
m.vis.global_.offwidth, m.vis.global_.offheight = width, height
names = [m.joint(j).name for j in range(1, m.njnt)]
assert names == meta["joints"], "the recording's joint order is not the model's"
d = mujoco.MjData(m)
renderer = mujoco.Renderer(m, height, width)
cam = mujoco.MjvCamera()
distance, azimuth, elevation, follows = CAMERAS[args.camera]
cam.distance, cam.azimuth, cam.elevation = distance, azimuth, elevation
look = np.array([pos[0, 0], pos[0, 1], 0.06])
cam.lookat[:] = look

first = int(args.start * rate)
last = min(int((args.end if args.end is not None else len(pos) / rate) * rate), len(pos) - 1)
frames = [min(first + int(round(k * rate / args.fps)), last) for k in range(int((last - first) / rate * args.fps) + 1)]
ffmpeg = subprocess.Popen(
    ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{width}x{height}", "-r", str(args.fps),
     "-i", "-", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20", args.out],
    stdin=subprocess.PIPE,
)
for t in frames:
    d.qpos[:3], d.qpos[3:7], d.qpos[7:] = pos[t], quat[t], joints[t]
    mujoco.mj_forward(m, d)
    if follows:  # a slight lag, so the robot moves in the frame
        look += 0.15 * (np.array([pos[t, 0], pos[t, 1], 0.06]) - look)
        cam.lookat[:] = look
    renderer.update_scene(d, cam)
    ffmpeg.stdin.write(renderer.render().tobytes())
ffmpeg.stdin.close()
ffmpeg.wait()
print(f"{args.out}: {len(frames)} frames, {len(frames) / args.fps:.1f} s, episode {i}, steps {first} to {last} of {length}")
