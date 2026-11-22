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
CREAM = (1.0, 0.957, 0.878)  # #FFF4E0, the floor and sky of the sim world (Account 1 strategy, part 4)


def studio() -> mujoco.MjModel:
    """The robot in the content look: a cream floor with a faint grid, soft shadows, no horizon."""
    spec = mujoco.MjSpec.from_file(str(ROOT / "scorpion" / "scene.xml"))
    grid = spec.texture("grid")
    grid.rgb1 = grid.rgb2 = CREAM
    grid.mark = mujoco.mjtMark.mjMARK_EDGE
    grid.markrgb = (0.86, 0.80, 0.70)
    grid.width = grid.height = 512
    floor_material = spec.material("grid")
    floor_material.reflectance = 0.0
    floor_material.specular = 0.0
    floor_material.shininess = 0.0
    floor_material.emission = 0.155  # with the fill light this keeps lit floor at full cream; a shadow is the same cream, a little darker
    floor_material.texrepeat = (10, 10)  # per metre: a line every 10 cm
    floor_material.texuniform = True
    floor = spec.geom("floor")
    floor.size = (0, 0, 0.05)  # no edge
    spec.add_texture(name="sky", type=mujoco.mjtTexture.mjTEXTURE_SKYBOX, builtin=mujoco.mjtBuiltin.mjBUILTIN_FLAT, rgb1=CREAM, rgb2=CREAM, width=64, height=384)
    for light in list(spec.lights):
        spec.delete(light)
    # one soft key light from above and to the side for the shadow, and a strong fill so nothing goes dark
    spec.worldbody.add_light(pos=(0.4, -0.5, 2.0), dir=(-0.18, 0.22, -1.0), type=mujoco.mjtLightType.mjLIGHT_DIRECTIONAL, castshadow=True,
                             diffuse=(0.30, 0.30, 0.30), specular=(0.12, 0.12, 0.12), ambient=(0, 0, 0))
    spec.worldbody.add_light(pos=(-1.0, 1.0, 0.6), dir=(0.64, -0.64, -0.42), type=mujoco.mjtLightType.mjLIGHT_DIRECTIONAL, castshadow=False,
                             diffuse=(0.14, 0.14, 0.14), specular=(0, 0, 0), ambient=(0, 0, 0))
    m = spec.compile()
    m.vis.headlight.ambient[:] = 0.50
    m.vis.headlight.diffuse[:] = 0.0  # a light on the camera would make the floor's colour depend on the camera
    m.vis.headlight.specular[:] = 0.0
    m.vis.quality.shadowsize = 8192
    m.vis.quality.offsamples = 8
    m.vis.rgba.fog[:] = (*CREAM, 1.0)
    m.vis.map.fogstart, m.vis.map.fogend = 1.5, 5.0
    m.stat.extent = 1.0
    return m

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
parser.add_argument("--still", type=float, default=None, help="write one PNG of this moment (seconds) instead of a video")
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
m = studio()
m.vis.global_.offwidth, m.vis.global_.offheight = width, height
names = [m.joint(j).name for j in range(1, m.njnt)]
assert names == meta["joints"], "the recording's joint order is not the model's"
d = mujoco.MjData(m)
renderer = mujoco.Renderer(m, height, width)
renderer.scene.flags[mujoco.mjtRndFlag.mjRND_FOG] = True  # the far floor fades into the sky: no horizon line
renderer.scene.flags[mujoco.mjtRndFlag.mjRND_REFLECTION] = False
cam = mujoco.MjvCamera()
distance, azimuth, elevation, follows = CAMERAS[args.camera]
cam.distance, cam.azimuth, cam.elevation = distance, azimuth, elevation

first = int(args.start * rate)
last = min(int((args.end if args.end is not None else len(pos) / rate) * rate), len(pos) - 1)
look = np.array([pos[first, 0], pos[first, 1], 0.06])  # the camera starts on the robot, wherever the clip starts
cam.lookat[:] = look
frames = [min(first + int(round(k * rate / args.fps)), last) for k in range(int((last - first) / rate * args.fps) + 1)]
if args.still is not None:
    t = min(int(args.still * rate), len(pos) - 1)
    d.qpos[:3], d.qpos[3:7], d.qpos[7:] = pos[t], quat[t], joints[t]
    mujoco.mj_forward(m, d)
    cam.lookat[:] = [pos[t, 0], pos[t, 1], 0.06]
    renderer.update_scene(d, cam)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{width}x{height}", "-i", "-", "-frames:v", "1", args.out],
                   input=renderer.render().tobytes(), check=True)
    print(f"{args.out}: episode {i} at {t / rate:.2f} s")
    raise SystemExit
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
