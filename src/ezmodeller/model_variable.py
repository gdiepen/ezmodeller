"""Module for defining the ModelVariable class"""

import logging
from typing import TYPE_CHECKING, Generic, Sequence, TypeVar

from gurobipy import GRB, Constr, Var

if TYPE_CHECKING:
    from . import OptimizationModel

from .errors import OptimizationModelMissingPropertiesError

logger = logging.getLogger(__name__)

D = TypeVar("D")


class ModelVariable(Generic[D]):
    """Class that represents a symbolic variable in your optimization model

    You MUST implement the functions in your subclass definition:

        * set_variable_properties(self)
        * get_index_domain(self, input_data)

    The framework will automatically call the first to set the right properties
    based on what you need them to be for your variable:

    For a symbolic variable, you only need to define the following items:
        * var_type: The gurobi type of the variable (defaults to GRB.CONTINUOUS)
        * var_lb: The lowerbound of the variable (defaults to 0)
        * var_ub: The upperbound of the variable (defaults to GRB.INFINITY or 1 when
            you define the var_type to be GRB.BINARY)
        * name: The name of the variable, defaults to the name of the class you
            define
        * is_enabled: Whether this variable is enabled and should be generated
            (defaults to True)
        * dimensions: Optionally the list of dimensions that is used to generate
            the typing hints. Must be implemented if you use strict=True for your
            OptimizationModel



    The second function (get_index_domain) must return the index domain for your
    symbolic variable (i.e. for which combination of indices should a variable
    be generated)

    You optionally can also implement the function

        * get_equality_constraint_generator(self, input_data, variables)

    which would instruct the framework to generate the corresponding equality
    constraint for this variable. This is useful for situations like inventory
    balance constraints


        inventory(t) = inventory(t-1) + produced(t) - demand(t)


    where otherwise you would need to define the equality constraint somehwere
    else explicitly

    Args:
        optimization_model (OptimizationModel): the model that this variable is
            being added to
    """

    def __init__(self, optimization_model: "OptimizationModel"):
        self._name = ""

        self._is_enabled: bool = True

        self.optimization_model = optimization_model

        self.input_data = optimization_model.input_data

        self._var_type = GRB.CONTINUOUS
        # self.var_lb: float  = 0
        self.var_lb = 0

        self._var_ub: float = GRB.INFINITY

        self._dimensions: list[str] = []

        self.gurobi_variables: dict[D, Var] = {}
        self.gurobi_definition_constraints: dict[D, Constr] = {}

        logger.debug(
            f"Calling set_variable_properties for new variable class {self.__class__.__module__}.{self.__class__.__qualname__}"
        )

        try:
            if hasattr(self, "set_variable_properties"):
                getattr(self, "set_variable_properties")()
            else:
                raise OptimizationModelMissingPropertiesError(
                    f"No set_variable_properties function defined in variable class {self.__class__.__module__ + '.' +self.__class__.__qualname__}"
                )
        except NotImplementedError as e:
            raise OptimizationModelMissingPropertiesError(
                f"No set_variable_properties function defined in variable class {self.__class__.__module__ + '.' +self.__class__.__qualname__}"
            )

        if self.name == "":
            self.name = self.__class__.__qualname__

        if self.var_type == GRB.BINARY:
            self.var_lb = 0
            self.var_ub = 1

    def set_variable_properties(self) -> None:
        """Function that MUST be implemented to set the different (optional)
        properties of this symbolic variable:
            * var_type: The gurobi type of the variable (defaults to GRB.CONTINUOUS)
            * var_lb: The lowerbound of the variable (defaults to 0)
            * var_ub: The upperbound of the variable (defaults to GRB.INFINITY or 1 when
                you define the var_type to be GRB.BINARY)
            * name: The name of the variable, defaults to the name of the class you
                define
            * is_enabled: Whether this variable is enabled and should be generated
                (defaults to True)

        If you want to keep everything to the defaults for this function, implement
        this function with just a pass statement
        """
        raise NotImplementedError(
            f"Your class {self.__class__.__module__}.{self.__class__.__qualname__} must override the set_variable_properties(self) function to set the properties for this variable"
        )

    def get_index_domain(self, input_data) -> Sequence:
        """Function that needs to be implemented to return the index domain for this
        symbolic variable

        Args:
            input_data: The input_data object the user created the optimization_model
                with
        """
        raise NotImplementedError(
            f"Your class {self.__class__.__module__}.{self.__class__.__qualname__} must override the get_index_domain(self, input_data) function to return the list that represents the index domain of this variable"
        )

    def get(self, _element: D, default: Var | float | int) -> Var | float | int:
        try:
            return self.__getitem__(_element)
        except KeyError:
            return default

    def __getitem__(self, _element: D) -> Var:
        self.optimization_model.variable_accessed[self.name] = (
            self.optimization_model.variable_accessed.get(self.name, 0) + 1
        )
        return self.gurobi_variables[_element]

    def generate_gurobi_variables(self):
        gurobi_model = self.optimization_model.gurobi_model

        self.gurobi_variables = gurobi_model.addVars(
            self.get_index_domain(self.input_data),
            name=self.name,
            vtype=self.var_type,
            lb=self.var_lb,
            ub=self.var_ub,
        )
        logger.debug(
            f"Generated {len(self.gurobi_variables)} Gurobi variables for the symbolic variable {self.name}"
        )

    def get_values(self):
        logger.debug(f"Retrieving variable values from gurobi for variable {self.name}")
        return {
            element: self.gurobi_variables[element].X
            for element in self.gurobi_variables
        }

    def get_equality_constraint_generator(self, input_data, variables):
        """Function that can be implemented to return the generator that creates
        the actual equality constraints for the definition of this symbolic variable

        Args:
            input_data: The input_data object the user created the optimization_model
                with
            variables: The VariablesCollection of all variables
        """
        raise NotImplementedError(
            f"Your class {self.__class__.__module__}.{self.__class__.__qualname__} does not override the get_equality_constraint_generator(self, input_data) function to return a generator for the equality constraints for this variable"
        )

    @property
    def is_enabled(self) -> bool:
        """Should this variable be active or not. If False, the variable will not be
        generated for your model. Defaults to True
        """
        return self._is_enabled

    @is_enabled.setter
    def is_enabled(self, value: bool):
        self._is_enabled = value

    @property
    def var_type(self) -> str:
        """Type of this variable (either GRB.CONTINUOUS, GRB.INTEGER, or GRB.BINARY).
        Defaults to GRB.CONTINUOUS
        """
        return self._var_type

    @var_type.setter
    def var_type(self, value: str) -> None:
        self._var_type = value

    @property
    def var_lb(self) -> float:
        """Lower bound of the variable, defaults to 0"""
        return self._var_lb

    @var_lb.setter
    def var_lb(self, value: float) -> None:
        self._var_lb = value

    @property
    def var_ub(self) -> float:
        """Upper bound of the variable, defaults to GRB.INFINITY"""
        return self._var_ub

    @var_ub.setter
    def var_ub(self, value: float) -> None:
        self._var_ub = value

    @property
    def dimensions(self) -> list[str]:
        """List of the dimensions for this variable. It is optional to define this
        unless you want to use the strict mode. If the dimensions are defined, they
        will be used when you generate the typing hints
        """
        return self._dimensions

    @dimensions.setter
    def dimensions(self, value: list[str]) -> None:
        self._dimensions = value

    @property
    def name(self) -> str:
        """The name of this symbolic variable. If you set this property to the empty
        string, the framework will use the name of the class as the variable name.
        Defaults to the empty string
        """
        return self._name

    @name.setter
    def name(self, value: str) -> None:
        self._name = value
