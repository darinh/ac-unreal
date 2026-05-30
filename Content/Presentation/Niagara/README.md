# Content/Presentation/Niagara/

Re-authored particle effects (war-magic, item-magic, cast windups,
projectile trails, impact bursts, footstep dust, etc.).

## Hard rule: gameplay timing lives in the SIM, not here

The visual durations / colors / shapes of these effects are FREE TO
DIVERGE from the original. But:

- The frame at which a spell becomes **fizzle-able** (input window) is
  defined in the simulation spec, NOT here.
- The frame at which a projectile **leaves the caster** (launch frame)
  is defined in the simulation spec.
- The frame at which a melee swing **applies damage** is defined in
  the simulation spec.
- The visible muzzle flash / trail / hit burst can be timed however
  looks best.

The brief is explicit:
> Re-author particle effects in Niagara for looks, but keep any
> gameplay-relevant timing (cast windows, projectile speed,
> damage-application frames) bound to the simulation spec, not to
> the visual.

When Niagara systems are added, route their gameplay-coupled events
through the C++ sim layer (via blueprint or gameplay tags), NOT through
Niagara's own time cursor. A 60-FPS render frame and a 30-Hz sim tick
will desync; the visual lerps, the sim ticks discretely.

## Subdirectories

- `Spells/` — per-school magic systems (War, Life, Item, Creature, etc.)
- `Combat/` — melee impact, blood, weapon trails
- `Environment/` — footstep dust, ambient wisps, weather
- `UI/` — UI effects (cast bars, button feedback)

All currently empty.
