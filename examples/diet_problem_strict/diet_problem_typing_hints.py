# Automatically generated using generate_model_typing_hints function
from typing import Any

from ezmodeller.collections import ConstraintsCollection, VariablesCollection
from ezmodeller.model_constraint import ModelConstraint
from ezmodeller.model_variable import ModelVariable

type t_category = Any
type t_food = Any


class DietVariables(VariablesCollection):
    Buy: ModelVariable[t_food]


class DietConstraints(ConstraintsCollection):
    NutritionLowerBound: ModelConstraint[t_category]
    overruled_nutrition_upper_bound: ModelConstraint[t_category]
