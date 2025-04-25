"""Module for defining the ModelObjective class"""

import logging

from gurobipy import GRB

from .errors import OptimizationModelMissingPropertiesError

logger = logging.getLogger(__name__)


class ModelObjective:
    """Class that represents the objective of your optimization model

    For the objective, you only need to define the following items:
        * direction: The direction of optimization. Defaults to GRB.MINIMIZE.
        * required_variables: list of variables this objective depends on. If left
            empty, no checks will be performed (but you might run into key-errors if
            you try to access variables)

    You MUST implement the function
        set_objective_properties(self)
    in your subclass definition. The framework will automatically call this function to
    set the right properties.

    Furthermore, in your subclass definition for a variable, you MUST implement the
    get_gurobi_objective_expression(self, input_data). This function must return a
    generator that is given to the gurobipy function to set the objective

    Args:
        optimization_model (OptimizationModel): the model that this constraint is being
            added to

    Raises:
        OptimizationModelMissingVariablesError if the user updated the
            required_variables in the set_constraint_properties function with variables
            that do not exist
    """

    def __init__(self, optimization_model):
        self.optimization_model = optimization_model

        self.direction = GRB.MINIMIZE
        self.required_variables = []

        logger.debug(
            f"Calling set_objective_properties for new objective class {self.__class__.__module__}.{self.__class__.__qualname__}"
        )
        if hasattr(self, "set_objective_properties"):
            getattr(self, "set_objective_properties")()
        else:
            raise OptimizationModelMissingPropertiesError(
                f"No set_objective_properties function defined in objective class {self.__class__.__module__ + '.' +self.__class__.__qualname__}"
            )

        missing_variables = [
            x
            for x in self.required_variables
            if x not in self.optimization_model.variables
        ]

        if len(missing_variables):
            raise Exception(
                f"The following required variables are not defined in the model: {', '.join(missing_variables)}"
            )

    def get_gurobi_objective_expression(self, input_data, variables):
        """Function that needs to be implemented to return the generator that creates
        the actual objective for your model

        Args:
            input_data: The input_data object the user created the optimization_model
                with
            variables: The VariablesCollection of all variables
        """
        raise NotImplementedError()
