"""Entity components (hybrid model, approved 2026-07-27).

A Component is a plain data holder with optional minimal behavior. Entities
compose components instead of using inheritance trees - see
docs/development/FRAMEWORK_EVALUATION.md section 6. This is deliberately NOT a
full ECS framework. Infrastructure only - no gameplay components here.
"""

from __future__ import annotations


class Component:
    """Marker base class for entity components."""

    __slots__ = ()
