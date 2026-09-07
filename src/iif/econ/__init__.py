"""Econometría del panel departamental anual: estimación, diagnóstico y robustez."""

from iif.econ.frame import estimation_sample, load_frame
from iif.econ.panel import Estimacion, by_dimension, in_changes, pooled_entity_only, two_way_fe

__all__ = [
    "Estimacion",
    "by_dimension",
    "estimation_sample",
    "in_changes",
    "load_frame",
    "pooled_entity_only",
    "two_way_fe",
]
