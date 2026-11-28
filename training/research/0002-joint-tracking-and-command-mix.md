# 0002 · Decision: one joint tracking term, and a command mix with a floor

22 November 2026, 05:25 UTC. Before any training run. Changes the plan's part 5.2 to 5.4.

## What the plan asked for

Two tracking terms (linear weight 1.0, turn weight 0.5, widths 0.075 m/s and 0.6 rad/s), a floor on
commanded speed, and an oracle check that a motionless robot earns under 30% of a walking robot's
income. Bestiary's definition is used: the share is over robots told to move; a robot told to stand
and standing earns honestly.

## What the arithmetic showed

With two separate terms, a robot standing still is paid in full for every axis commanded zero: the
turn term on a straight walk, the linear term on a spin on the spot. Worked out by hand for a
planar floor of 0.06 m/s and turn rates under 0.3 rad/s snapped to zero: about 33% on walk commands
and 76% on spin commands. Scorbi must spin on the spot (skill 4) and walk straight (skills 2, 6, 7),
so no mix with two separate terms gets under 30%.

## Decision

- **Reward:** one term, `track_twist_exp` = exp(-(linear error / 0.075)² - (turn error / 0.6)²),
  weight 1.5. It is the product of the two stock kernels. Standing still only pays when told to stand.
- **Commands** (`scorbi_lab/commands.py`, ported from Bestiary's dead-zone sampler): 10% stand; of
  the rest 15% spin on the spot at 0.3 to 1.2 rad/s; the others walk with the planar speed raised to
  0.06 m/s and turn rates under 0.3 rad/s snapped to zero. Heading mode off.

## Measured by the oracle (169 checks, 0 problems; 8,192 commands; robots standing on zero action)

| | Share of a walking robot's income earned by standing still |
|---|---|
| All robots told to move | 14.2% |
| Walk commands | 11.8% |
| Spin commands | 28.5% |
| Told to stand | 100% |

Standing share 9.6%, spin share of the rest 14.6%, straight walks 25.0% of walk commands, slowest
walk command 0.0600 m/s, slowest spin 0.301 rad/s.

## What could be wrong with this

The joint term pays little until both parts are right. A command of 0.12 m/s with 1.0 rad/s pays a
standing robot 0.005 and a robot that only fixes its speed 0.06, where the separate terms would pay
that fix 0.92. Walks with a turn may learn late or not at all. The website steers by heading, so
walk-with-turn matters. Watch cells 9 and 10 (curves) against cells 2 and 3 (straight). If the
curves lag, the first probe to run adds the two separate kernels back at a small weight.

The stock reward (two terms, width 0.5, uniform commands) is still run once on purpose, as the
"standing still" probe in block C.
