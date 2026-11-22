#!/usr/bin/env python3
"""Derive the training model from scorpion/scorpion.xml. Never edit the result by hand.

    python training/tools/derive_training_model.py [out.xml]

What changes, and why:
  * the base sits at z = 0, so the simulator's own initial state decides the height;
  * the position actuators and the keyframe are removed: the gains, the torque limit and the
    standing pose go into the training config, read from scorpion/model.json;
  * joint damping, armature and friction loss are removed from the model for the same reason.
Everything else (bodies, masses, inertias, joint axes and ranges, collision shapes, friction) is
kept as it is. The script prints what it removed and how many things it checked.
"""
import pathlib
import sys
import xml.etree.ElementTree as ET

ROOT = pathlib.Path(__file__).resolve().parents[2]
SRC = ROOT / "scorpion" / "scorpion.xml"
OUT = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "training" / "build" / "scorbi_train.xml"

tree = ET.parse(SRC)
mj = tree.getroot()
checked = 0

# meshes are found from the output file's folder
OUT.parent.mkdir(parents=True, exist_ok=True)
compiler = mj.find("compiler")
compiler.set("meshdir", str((ROOT / "scorpion" / "meshes").resolve()))

base = mj.find("worldbody/body")
assert base.get("name") == "base", base.get("name")
assert len(mj.findall("worldbody/body")) == 1, "expected the robot alone, with no world"
assert mj.find("worldbody/geom") is None, "expected no floor in scorpion.xml"
old_pos = base.get("pos")
base.set("pos", "0 0 0")
checked += 3

removed = []
for tag in ("actuator", "keyframe"):
    for el in mj.findall(tag):
        removed.append(f"<{tag}> with {len(el)} entries")
        mj.remove(el)
for default in mj.iter("default"):
    for joint in default.findall("joint"):
        for attr in ("damping", "armature", "frictionloss"):
            if attr in joint.attrib:
                removed.append(f"joint default {attr}={joint.attrib.pop(attr)}")
    for pos in default.findall("position"):
        removed.append("position default " + " ".join(f"{k}={v}" for k, v in pos.attrib.items()))
        default.remove(pos)

joints = [j.get("name") for j in mj.iter("joint") if j.get("name")]
feet = [b.get("name") for b in mj.iter("body") if b.get("name", "").endswith("_foot")]
assert len(joints) == 15, joints
assert feet == ["fl_foot", "fr_foot", "rl_foot", "rr_foot"], feet
for j in mj.iter("joint"):
    if j.get("name"):
        assert not {"damping", "armature", "frictionloss"} & set(j.attrib), j.attrib
        assert j.get("range"), j.get("name")
checked += 2 + 2 * len(joints)

tree.write(OUT, encoding="unicode")
print(f"wrote {OUT}")
print(f"base pos {old_pos} -> 0 0 0")
for r in removed:
    print("removed", r)
print(f"joints {len(joints)}, feet {len(feet)}; {checked} checks passed")
