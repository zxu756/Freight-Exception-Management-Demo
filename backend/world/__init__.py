"""
World simulation core - the single shared "New Zealand" state all freight
modes (air/road/sea) read from, so the demo behaves like one coherent world.

Submodules:
- clock: the single time authority (WorldClock) driving the whole simulation.
- weather: (upcoming) regional weather engine.
- causality: (upcoming) cross-domain event propagation.
"""
from .clock import world_clock  # noqa: F401
