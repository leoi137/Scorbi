"""Scorbi's flat-ground velocity task, version 0 (training plan, part 5).

One policy drives the 12 leg joints from body-frame speed commands. It never sees base linear
velocity, a height scan or history; the critic sees more. Every setting here is a starting point.
"""

import math

from isaaclab_newton.physics import MJWarpSolverCfg, NewtonCfg

import isaaclab.sim as sim_utils
from isaaclab.assets import ArticulationCfg, AssetBaseCfg
from isaaclab.envs import ManagerBasedRLEnvCfg
from isaaclab.managers import EventTermCfg as EventTerm
from isaaclab.managers import ObservationGroupCfg as ObsGroup
from isaaclab.managers import ObservationTermCfg as ObsTerm
from isaaclab.managers import RewardTermCfg as RewTerm
from isaaclab.managers import SceneEntityCfg
from isaaclab.managers import TerminationTermCfg as DoneTerm
from isaaclab.scene import InteractiveSceneCfg
from isaaclab.sensors import ContactSensorCfg
from isaaclab.sim import SimulationCfg
from isaaclab.terrains import TerrainImporterCfg
from isaaclab.utils import configclass, replace
from isaaclab.utils.noise import UniformNoiseCfg as Unoise

import isaaclab_tasks.core.velocity.mdp as mdp

from .actions import LegActionWithScriptedArmCfg
from .robot import LEG_JOINTS, SCORBI_CFG

# The website's command limits and what is trained (plan 2.6): a little wider, so the website
# always drives inside the trained range.
TRAIN_RANGES = dict(lin_vel_x=(-0.12, 0.15), lin_vel_y=(-0.10, 0.10), ang_vel_z=(-1.2, 1.2))
# Width of the tracking reward: half the top command (plan 5.3).
LIN_STD = 0.075
ANG_STD = 0.6

LEGS = SceneEntityCfg("robot", joint_names=LEG_JOINTS, preserve_order=True)


@configclass
class ScorbiSceneCfg(InteractiveSceneCfg):
    terrain = TerrainImporterCfg(
        prim_path="/World/ground",
        terrain_type="plane",
        collision_group=-1,
        physics_material=sim_utils.RigidBodyMaterialCfg(
            friction_combine_mode="multiply",
            restitution_combine_mode="multiply",
            static_friction=1.0,
            dynamic_friction=1.0,
        ),
        debug_vis=False,
    )
    robot: ArticulationCfg = replace(SCORBI_CFG, prim_path="{ENV_REGEX_NS}/Robot")
    contact_forces = ContactSensorCfg(prim_path="{ENV_REGEX_NS}/Robot/.*", history_length=3, track_air_time=True)
    sky_light = AssetBaseCfg(prim_path="/World/skyLight", spawn=sim_utils.DomeLightCfg(intensity=750.0))


@configclass
class CommandsCfg:
    base_velocity = mdp.UniformVelocityCommandCfg(
        asset_name="robot",
        resampling_time_range=(10.0, 10.0),
        rel_standing_envs=0.1,
        rel_heading_envs=0.0,
        # Heading mode off: the website turns heading error into a turn rate itself (plan 5.2).
        heading_command=False,
        debug_vis=False,
        ranges=mdp.UniformVelocityCommandCfg.Ranges(heading=None, **TRAIN_RANGES),
    )


@configclass
class ActionsCfg:
    # target = standing pose + 0.25 x action, for the 12 leg joints in the model's order
    # The arm is held by script inside the same term (see actions.py).
    joint_pos = LegActionWithScriptedArmCfg(
        asset_name="robot", joint_names=LEG_JOINTS, preserve_order=True, scale=0.25, use_default_offset=True
    )


@configclass
class ObservationsCfg:
    @configclass
    class PolicyCfg(ObsGroup):
        """What the website and the real robot can also measure: 51 numbers."""

        base_ang_vel = ObsTerm(func=mdp.base_ang_vel, noise=Unoise(n_min=-0.2, n_max=0.2))
        projected_gravity = ObsTerm(func=mdp.projected_gravity, noise=Unoise(n_min=-0.05, n_max=0.05))
        velocity_commands = ObsTerm(func=mdp.generated_commands, params={"command_name": "base_velocity"})
        joint_pos = ObsTerm(func=mdp.joint_pos_rel, noise=Unoise(n_min=-0.01, n_max=0.01))
        joint_vel = ObsTerm(func=mdp.joint_vel_rel, noise=Unoise(n_min=-0.5, n_max=0.5))
        actions = ObsTerm(func=mdp.last_action)

        def __post_init__(self):
            self.enable_corruption = True
            self.concatenate_terms = True

    @configclass
    class CriticCfg(ObsGroup):
        """Everything the actor sees, without noise, plus what only the simulator knows."""

        base_lin_vel = ObsTerm(func=mdp.base_lin_vel)
        base_ang_vel = ObsTerm(func=mdp.base_ang_vel)
        projected_gravity = ObsTerm(func=mdp.projected_gravity)
        velocity_commands = ObsTerm(func=mdp.generated_commands, params={"command_name": "base_velocity"})
        joint_pos = ObsTerm(func=mdp.joint_pos_rel)
        joint_vel = ObsTerm(func=mdp.joint_vel_rel)
        actions = ObsTerm(func=mdp.last_action)
        base_height = ObsTerm(func=mdp.base_pos_z)

        def __post_init__(self):
            self.enable_corruption = False
            self.concatenate_terms = True

    policy: PolicyCfg = PolicyCfg()
    critic: CriticCfg = CriticCfg()


@configclass
class EventsCfg:
    reset_base = EventTerm(
        func=mdp.reset_root_state_uniform,
        mode="reset",
        params={
            "pose_range": {"x": (-0.2, 0.2), "y": (-0.2, 0.2), "yaw": (-3.14, 3.14)},
            "velocity_range": {},
        },
    )
    reset_robot_joints = EventTerm(
        func=mdp.reset_joints_by_offset,
        mode="reset",
        params={"position_range": (-0.05, 0.05), "velocity_range": (0.0, 0.0)},
    )


@configclass
class RewardsCfg:
    """Rung 0 of the reward ladder (plan 5.4): the two tracking terms and nothing else."""

    track_lin_vel_xy_exp = RewTerm(
        func=mdp.track_lin_vel_xy_exp, weight=1.0, params={"command_name": "base_velocity", "std": LIN_STD}
    )
    track_ang_vel_z_exp = RewTerm(
        func=mdp.track_ang_vel_z_exp, weight=0.5, params={"command_name": "base_velocity", "std": ANG_STD}
    )


@configclass
class TerminationsCfg:
    time_out = DoneTerm(func=mdp.time_out, time_out=True)
    # A fall: the body touches the ground, or tips past 60 degrees.
    base_contact = DoneTerm(
        func=mdp.illegal_contact,
        params={"sensor_cfg": SceneEntityCfg("contact_forces", body_names="base"), "threshold": 0.5},
    )
    bad_orientation = DoneTerm(func=mdp.bad_orientation, params={"limit_angle": math.radians(60.0)})


@configclass
class ScorbiFlatEnvCfg(ManagerBasedRLEnvCfg):
    sim: SimulationCfg = SimulationCfg(
        physics=NewtonCfg(
            solver_cfg=MJWarpSolverCfg(
                njmax=100,
                nconmax=40,
                cone="pyramidal",
                impratio=1.0,
                integrator="implicitfast",
                use_mujoco_contacts=True,
            ),
            num_substeps=1,
            debug_mode=False,
        )
    )
    scene: ScorbiSceneCfg = ScorbiSceneCfg(num_envs=4096, env_spacing=1.0)
    observations: ObservationsCfg = ObservationsCfg()
    actions: ActionsCfg = ActionsCfg()
    commands: CommandsCfg = CommandsCfg()
    rewards: RewardsCfg = RewardsCfg()
    terminations: TerminationsCfg = TerminationsCfg()
    events: EventsCfg = EventsCfg()

    def __post_init__(self):
        # Control every 0.02 s, as the website does: 4 physics steps of 0.005 s.
        self.decimation = 4
        self.sim.dt = 0.005
        self.episode_length_s = 20.0
        self.sim.render_interval = self.decimation
        self.sim.physics_material = self.scene.terrain.physics_material
        self.scene.contact_forces.update_period = self.sim.dt
