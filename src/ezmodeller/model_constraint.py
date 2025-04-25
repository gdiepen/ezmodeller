"""Module for defining the ModelConstraint class"""

import logging
from typing import TYPE_CHECKING, Generic, TypeVar

from gurobipy import GRB, Constr

from .errors import (
    OptimizationModelMissingPropertiesError,
    OptimizationModelMissingVariablesError,
)

if TYPE_CHECKING:
    from . import OptimizationModel

logger = logging.getLogger(__name__)


D = TypeVar("D")


class ModelConstraint(Generic[D]):
    """Class that represents a symbolic constraint in your optimization model

    For a symbolic constraint, you only need to define the following items:
        * name: The name of the constraint, defaults to the name of the class you define
        * is_enabled: Whether this constraint is enabled and should be generated
            (defaults to True)
        * required_variables: list of variables this constraint depends on. If left
            empty, no checks will be performed (but you might run into key-errors if
            you try to access variables)

    You MUST implement the function
        set_constraint_properties(self)
    in your subclass definition. The framework will automatically call this function to
    set the right properties.

    Furthermore, in your subclass definition for a variable, you MUST implement the
    get_gurobi_constraints_generator(self, input_data). This function must return a
    generator that is given to the gurobipy addConstrs function to generate each
    separate constraint for this symobolic constraint

    Args:
        optimization_model (OptimizationModel): the model that this constraint is being
            added to

    Raises:
        OptimizationModelMissingVariablesError if the user updated the
            required_variables in the set_constraint_properties function with variables
            that do not exist
    """

    def __init__(self, optimization_model: "OptimizationModel"):
        self._name = ""

        self._is_enabled = True

        self.optimization_model = optimization_model
        self.input_data = optimization_model.input_data

        self.gurobi_constraints: dict[D, Constr] = {}

        self._required_variables: list[str] = []

        self._dimensions: list[str] = []

        logger.debug(
            f"Calling set_constraint_properties for new constraint class {self.__class__.__module__}.{self.__class__.__qualname__}"
        )
        if hasattr(self, "set_constraint_properties"):
            getattr(self, "set_constraint_properties")()
        else:
            raise OptimizationModelMissingPropertiesError(
                f"No set_constraint_properties function defined in constraint class {self.__class__.__module__ + '.' +self.__class__.__qualname__}"
            )

        missing_variables = [
            x
            for x in self.required_variables
            if x not in self.optimization_model.variables
        ]

        if len(missing_variables):
            raise OptimizationModelMissingVariablesError(
                f"The following required variables are not defined in the model: {', '.join(missing_variables)}"
            )

        if self.name == "":
            self.name = self.__class__.__qualname__

    def get_gurobi_constraints_generator(self, input_data, variables):
        """Function that needs to be implemented to return the generator that creates
        the actual constraints for this symbolic constraint

        Args:
            input_data: The input_data object the user created the optimization_model
                with
            variables: The VariablesCollection of all variables
        """
        raise NotImplementedError(
            f"Your class {self.__class__.__module__}.{self.__class__.__qualname__} must override the get_gurobi_constraints_generator(self, input_data) function to return a generator for the definition of this constraint"
        )

    @property
    def dimensions(self) -> list[str]:
        """List of the dimensions for this constraint. It is optional to define this
        unless you want to use the strict mode. If the dimensions are defined, they
        will be used when you generate the typing hints
        """
        return self._dimensions

    @dimensions.setter
    def dimensions(self, value: list[str]) -> None:
        self._dimensions = value

    @property
    def name(self) -> str:
        """The name of this symbolic constraint. If you set this property to the empty
        string, the framework will use the name of the class as the constraint name.
        Defaults to the empty string
        """
        return self._name

    @name.setter
    def name(self, value: str) -> None:
        self._name = value

    @property
    def required_variables(self) -> list[str]:
        """List of the required variables for this constraint. It is optional to define
        this unless you want to use the strict mode. If you use strict mode, the model
        will give an error during generation if you access variables that are not
        in the list of required variables. In non strict mode, the framework will log
        any variables accessed not in this list as warnings
        """
        return self._required_variables

    @required_variables.setter
    def required_variables(self, value: list[str]) -> None:
        self._required_variables = value

    @property
    def is_enabled(self) -> bool:
        """Should this constraint be active or not. If False, the constraint will not
        be generated for your model. Defaults to True
        """
        return self._is_enabled

    @is_enabled.setter
    def is_enabled(self, value: bool):
        self._is_enabled = value
