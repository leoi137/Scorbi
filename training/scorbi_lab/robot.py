"""Scorbi as an Isaac Lab articulation.

Every number comes from scorpion/model.json, the file build_model.py writes from the CAD. The
shapes, masses and joint ranges come from the USD that training/tools/derive_training_model.py and
Isaac Lab's MJCF converter make from scorpion/scorpion.xml.
"""

import json
import pathlib

from isaaclab_newton.sim.schemas import NewtonArticulationCfg

import isaaclab.sim as sim_utils
from isaaclab.actuators import ImplicitActuatorCfg
from isaaclab.assets.articulation import ArticulationCfg

REPO = pathlib.Path(__file__).resolve().parents[2]
MODEL = json.loads((REPO / "scorpion" / "model.json").read_text())
USD_PATH = REPO / "training" / "build" / "usd" / "scorbi_train" / "scorbi_train.usda"

JOINTS: list[str] = [j["name"] for j in MODEL["joints"]]
"""All 15 joints in the model's fixed order (the website's order). Isaac Lab orders joints its own way: map by name."""

LEG_JOINTS: list[str] = [n for n in JOINTS if n[:2] in ("fl", "fr", "rl", "rr")]
ARM_JOINTS: list[str] = [n for n in JOINTS if n not in LEG_JOINTS]
FEET: list[str] = list(MODEL["feet"])
STAND: dict[str, float] = dict(MODEL["stand"]["joints"])
STAND_HEIGHT: float = MODEL["stand"]["base_height"]
MOTOR: dict[str, float] = dict(MODEL["motor"])

assert len(LEG_JOINTS) == 12 and len(ARM_JOINTS) == 3, (LEG_JOINTS, ARM_JOINTS)

SCORBI_CFG = ArticulationCfg(
    spawn=sim_utils.UsdFileCfg(
        usd_path=str(USD_PATH),
        activate_contact_sensors=True,
        articulation_props=NewtonArticulationCfg(self_collision_enabled=False),
    ),
    articulation_root_prim_path="/Geometry/base",
    init_state=ArticulationCfg.InitialStateCfg(
        pos=(0.0, 0.0, STAND_HEIGHT),
        joint_pos=STAND,
        joint_vel={".*": 0.0},
    ),
    actuators={
        # One position-controlled servo model for all 15 joints. MuJoCo's kv (0.12) and joint damping
        # (0.05) are one number here, as robot/README.md says.
        "servos": ImplicitActuatorCfg(
            joint_names_expr=[".*"],
            stiffness=MOTOR["kp"],
            damping=MOTOR["kv"] + MOTOR["damping"],
            armature=MOTOR["armature"],
            friction=MOTOR["frictionloss"],
            joint_effort_limit=MOTOR["effort"],
            joint_velocity_limit=MOTOR["velocity"],
        ),
    },
)
