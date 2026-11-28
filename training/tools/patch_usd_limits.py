#!/usr/bin/env python3
"""Give the converted USD the joint-limit behaviour of scorpion.xml. Run after every conversion.

    python training/tools/patch_usd_limits.py [training/build/usd/scorbi_train]

The MJCF-to-USD converter does not carry MuJoCo's joint-limit setting (`solreflimit`), because
scorpion.xml leaves it at MuJoCo's default (0.02 s, critically damped). Newton then makes up its
own from a stiffness and damping, which came out as 0.008 to 0.012 s with a damping ratio of 0.2:
stiffer than a 0.005 s step can hold. A leg driven into its limit could throw the robot into the
air (research 0003). This writes MuJoCo's default onto every joint, which Newton then uses as it is.
"""
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
folder = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "training" / "build" / "usd" / "scorbi_train"
path = folder / "payloads" / "Physics" / "physics.usda"
text = path.read_text()
text = re.sub(r"\n[ \t]*double\[\] mjc:solreflimit = [^\n]*", "", text)  # run twice, same result
text, count = re.subn(r"\n([ \t]*)(float physics:upperLimit = [^\n]*)", r"\n\1\2\n\1double[] mjc:solreflimit = [0.02, 1]", text)
assert count == 15, f"expected 15 joints with limits, found {count}"
path.write_text(text)
print(f"{path}: mjc:solreflimit = [0.02, 1] on {count} joints")
