# Automatically generated using generate_model_typing_hints function
from typing import Any

from ezmodeller.collections import ConstraintsCollection, VariablesCollection
from ezmodeller.model_constraint import ModelConstraint
from ezmodeller.model_variable import ModelVariable

type t_customer = Any
type t_factory = Any
type t_from_factory = Any
type t_to_customer = Any


class TransportProblemVariables(VariablesCollection):
    Transport: ModelVariable[tuple[t_from_factory, t_to_customer]]


class TransportProblemConstraints(ConstraintsCollection):
    RespectDemand: ModelConstraint[t_customer]
    RespectSupply: ModelConstraint[t_factory]
