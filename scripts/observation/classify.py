"""State classification interface (read-only)."""
from __future__ import annotations
from typing import Dict, List
from . import loader


def state_class_map():
    return loader.load_state_class()


def class_of(state_id):
    return state_class_map().get(int(state_id), "UNKNOWN")


def states_by_class(klass):
    if klass not in loader.VALID_CLASSES:
        raise ValueError(f"unknown class: {klass}; valid: {sorted(loader.VALID_CLASSES)}")
    m = state_class_map()
    return sorted([sid for sid, k in m.items() if k == klass])


def invariant_states():    return states_by_class("INVARIANT")
def conditional_states():  return states_by_class("CONDITIONAL")
def trap_states():         return states_by_class("TRAP")
def dead_states():         return states_by_class("DEAD")
def ambiguous_states():    return states_by_class("AMBIGUOUS")
def insufficient_states(): return states_by_class("INSUFFICIENT")


def class_distribution():
    m = state_class_map()
    out = {k: 0 for k in loader.VALID_CLASSES}
    for v in m.values():
        out[v] = out.get(v, 0) + 1
    return out
