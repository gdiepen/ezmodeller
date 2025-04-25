"""Module for defining the code for the OptimizationModel"""

import importlib
import inspect
import logging
import os
import pkgutil
from collections.abc import Callable
from pathlib import Path
from types import ModuleType
from typing import Any, Type

import gurobipy as gp

from .collections import ConstraintsCollection, VariablesCollection
from .errors import (
    OptimizationModelDuplicateConstraintDefinition,
    OptimizationModelDuplicateVariableDefinition,
    OptimizationModelModelNotGenerated,
    OptimizationModelModelNotSolved,
    OptimizationModelNotStrictError,
)
from .model_constraint import ModelConstraint
from .model_objective import ModelObjective
from .model_variable import ModelVariable

logger = logging.getLogger(__name__)


def _iter_packages(path: str, prefix: str, onerror=None):
    """Find packages recursively, including PEP420 packages"""
    yield from pkgutil.walk_packages(path, prefix, onerror)
    namespace_packages = {}
    for path_root in path:
        for sub_path in Path(path_root).iterdir():
            # TODO: filter to legal package names
            if sub_path.is_dir() and not (sub_path / "__init__.py").exists():
                ns_paths = namespace_packages.setdefault(prefix + sub_path.name, [])
                ns_paths.append(str(sub_path))
    for name, paths in namespace_packages.items():
        yield pkgutil.ModuleInfo(None, name, True)
        yield from _iter_packages(paths, name + ".", onerror)


class OptimizationModel:
    """Main object that combines a set of variables definitions and a set of constraint
    definitions and generate the corresponding gurobi model

    When instantiating the object, you have to provide the module/list of modules
    under which it will recursively start searching for ModelVariable definitions and
    a module/list of modules under which it will recursively start searching for
    ModelConstraint definitions.

    By allowing a list of modules, the framework allows for sharing variables amonst
    different optimization models.

    Each of the variables and constraints that is found and not inactive will be
    instantiated and added to the internal list of variables and constraints.

    You also have to provide a subclass of the ModelConstraint that will be used to
    define the objective for your optimization problem.

    The other two items you still need to provide are the name of the model (which
    will be used when creating the connection with gurobi) and the input_data. The
    input_data has no requirements, it is up to you do determine what you put into
    this (could be a dataclass, could be a dictionary, list, etc). The input_data
    object will be provided to each variable / constraint when it is being generated.

    Args:
        model_name (str): name of the model when connecting to Gurobi
        input_data (Any): input_data object that will be made available to all of the
            variables/constraints when they are being generated. It is up to you to
            determine what you put into this, there are no requirements from the
            framework
        variables_modules (ModuleType|list[ModuleType]): Either a single module or
            a list of modules that will each be search recurisvely for subclasses
            off ModelVariable
        constraints_modules (ModuleType|list[ModuleType]): Either a single module or
            a list of modules that will each be search recurisvely for subclasses
            off ModelConstraint
        objective_class (Type[ModelObjective]): Subclass of the ModelObjective class
            that will be used to instantiate the objective for this optimization model
        env (gurobipy.Env): Gurobipy environmnet you want to use. Leave empty to
            have an environment instantiated via the environment variables starting
            with EZMODELLER_XXX where XXX can be any of the gurobi parameters.
            If those are not found, the gurobi environment will be generated using
            the default way to create env for your model
        strict (bool): Should generating a model where the user did not define the
            dimensions or there is a mismatch in the number of dimensions, or there
            are constriants that access variables that are not in the
            required_variables list for that constraint result in an error. Defaults
            to False
    """

    def __init__(
        self,
        model_name: str,
        input_data: Any,
        variables_modules: ModuleType | list[ModuleType],
        constraints_modules: ModuleType | list[ModuleType],
        objective_class: Type[ModelObjective],
        env: gp.Env | None = None,
        strict: bool = False,
    ):

        self._input_data = input_data
        self._model_name = model_name
        self._gurobi_model: gp.Model | None = None
        self._env = env

        self._strict = strict

        self._callback: None | Callable[[gp.Model, int], None] = None

        if model_name.strip() == "":
            raise ValueError("model_name argument cannot be empty")

        if isinstance(variables_modules, list):
            self.variables_modules = variables_modules
        else:
            self.variables_modules = [variables_modules]

        if isinstance(constraints_modules, list):
            self.constraints_modules = constraints_modules
        else:
            self.constraints_modules = [constraints_modules]

        self.objective_class = objective_class

        self.variable_accessed: dict[str, int] = {}

        self._variable_values = {}
        self._objective_value = None
        self._program_status = None

        self._sol_count = None

        self._solver_options = {}

        self.constraints = ConstraintsCollection()
        self.variables = VariablesCollection()

        # Used to keep track of everything that was found
        self.__all_variable_names: list[str] = []
        self.__all_constraint_names: list[str] = []

    def __find_all_variables(self, _var_module):
        _module_path = _var_module.__path__
        _module_name = _var_module.__name__

        for _moduleinfo in _iter_packages(_module_path, prefix=_module_name + "."):
            modname = _moduleinfo.name
            ispkg = _moduleinfo.ispkg

            if not ispkg:
                var_module = importlib.import_module(modname)

                class_members = inspect.getmembers(var_module, inspect.isclass)

                for _, c in class_members:
                    if issubclass(c, ModelVariable) and not (c == ModelVariable):
                        logger.debug(
                            f"Instantiating variable from class {c.__module__}.{c.__qualname__}"
                        )
                        _var = c(self)
                        if _var.is_enabled:
                            if _var.name in self.variables:
                                _existing_var_class = self.variables[
                                    _var.name
                                ].__class__

                                msg = f'Variable with name "{_var.name}" defined in both {_existing_var_class.__module__}.{_existing_var_class.__qualname__} and {c.__module__}.{c.__qualname__}'
                                logger.error(msg)
                                raise OptimizationModelDuplicateVariableDefinition(msg)

                            self.variables[_var.name] = _var

                            self.__all_variable_names.append(_var.name)
                        else:
                            logger.debug(
                                f"DISABLED - Not instantiating variable from class {c.__module__}.{c.__qualname__}"
                            )

    def __find_all_constraints(self, _constr_module):
        _module_path = _constr_module.__path__
        _module_name = _constr_module.__name__

        for _moduleinfo in _iter_packages(
            _module_path,
            prefix=_module_name + ".",
        ):
            modname = _moduleinfo.name
            ispkg = _moduleinfo.ispkg

            if not ispkg:
                var_module = importlib.import_module(modname)

                class_members = inspect.getmembers(var_module, inspect.isclass)

                for _, c in class_members:
                    if issubclass(c, ModelConstraint) and not (c == ModelConstraint):
                        logger.debug(
                            f"Instantiating constraint from class {c.__module__}.{c.__qualname__}"
                        )
                        _constraint = c(self)

                        if _constraint.is_enabled:
                            if _constraint.name in self.constraints:
                                _existing_constraint_class = self.constraints[
                                    _constraint.name
                                ].__class__

                                msg = f'Constraint with name "{_constraint.name}" defined in both {_existing_constraint_class.__module__}.{_existing_constraint_class.__qualname__} and {c.__module__}.{c.__qualname__}'
                                logger.error(msg)
                                raise OptimizationModelDuplicateConstraintDefinition(
                                    msg
                                )

                            self.constraints[_constraint.name] = _constraint
                            # self.constraints_collection[_constraint.name] = _constraint
                            self.__all_constraint_names.append(_constraint.name)
                        else:
                            logger.warning(
                                f"DISABLED - Not instantiating constraint from class {c.__module__}.{c.__qualname__}"
                            )

    def __setup_env(self):
        logger.info("Setting up gurobi environment")
        if self._env is None:
            logger.debug(
                "No gurobi environment provided, checking for environment variables"
            )
            relevant_env_variables = [
                x for x in os.environ.keys() if x.upper().startswith("EZMODELLER_")
            ]

            if len(relevant_env_variables):
                logger.debug(
                    f"Found {len(relevant_env_variables)} environment variables starting with EZMODELLER_, using those to set up environment"
                )

                gp.disposeDefaultEnv()
                self._env = gp.Env(empty=True)

                for x in relevant_env_variables:
                    logger.debug(
                        f"    Setting gurobipy environment parameter {x.upper().replace('EZMODELLER_', '')}"
                    )
                    self._env.setParam(
                        x.upper().replace("EZMODELLER_", ""), os.environ[x]
                    )
            else:
                logger.debug(
                    "No environment variables found, creating a new default gurobi environment"
                )
                gp.disposeDefaultEnv()
                self._env = gp.Env()
        else:
            logger.debug("Using env provided when OptimizationModel was created")

        logger.debug("Ensuring gurobi environment is started")
        self._env.start()

    @property
    def gurobi_model(self) -> gp.Model:
        if self._gurobi_model is None:
            raise OptimizationModelModelNotGenerated(
                "You cannot access the gurobi_model if the model is not generated yet"
            )
        return self._gurobi_model

    def generate_gurobi_model(self):
        """Initiate the generation of the underlying gurobi model.

        By calling this function, the framework will start doing a recursive search
        for all variables and constraints under the respective module/list of modules
        and instantiates each of them into an object and calls the underlying functions
        to create the gurobi variables and gurobi constraints

        Raises:
            OptimizationModelNotStrictError raised if the user indicated the model is
                strict and if there were inconsistencies in the model like accessing
                variables that were not in the required list or mismatch in the
                dimensions and index domain number of dimensions
        """

        logger.info("Generating gurobi model")

        # First determine all variables from the variables module
        # and generate those
        for _var_module in self.variables_modules:
            self.__find_all_variables(_var_module)

        # Then determine all constraints from the cosntraints module
        # and generate those
        for _constr_module in self.constraints_modules:
            self.__find_all_constraints(_constr_module)

        self.__setup_env()

        # Create the gurobi model
        logger.debug(f"Creating gurobi model with name {self.model_name}")
        self._gurobi_model = gp.Model(self.model_name, env=self._env)

        # Now that we have all variables and all constraints, generate all index_domains
        for _var in self.variables.values():
            logger.debug(f"Creating index domain for variable {_var.name}")
            _index_domain = sorted(_var.get_index_domain(self.input_data))
            _var.index_domain = _index_domain

            if self.strict:
                if len(_var.dimensions) == 0:
                    msg = f"Model is set to strict and variable {_var.name} does not have dimensions defined"
                    logger.error(msg)
                    raise OptimizationModelNotStrictError(msg)

                if len(_index_domain):
                    if len(_index_domain):
                        _elem_domain = list(_index_domain)[0]

                        # Deal with the situation that a 1-D index domain would use the
                        # length of the string as the index_domain length
                        if isinstance(_elem_domain, str):
                            _elem_domain = [_elem_domain]

                        if len(_elem_domain) != len(_var.dimensions):
                            msg = f"Model is set to strict and number of dimensions in dimensions property of variable {_var.name} ({len(_var.dimensions)}) is not equal to the number of dimensions in the index domain ({len(_elem_domain)})"
                            logger.error(msg)
                            raise OptimizationModelNotStrictError(msg)

        # Use sorted here to ensure we always loop over the variables in the same way
        for _var_name in sorted(self.variables.keys()):
            _var = self.variables[_var_name]
            logger.debug(f"Generating gurobi variables for variable {_var.name}")
            _var.generate_gurobi_variables()

        # Now check for all variables if they have a definition and if so, add that as constraint
        for _var_name in sorted(self.variables.keys()):
            _var = self.variables[_var_name]
            logger.debug(
                f"Checking if {_var.name} has an equality constraint definition"
            )

            try:
                _var.gurobi_definition_constraints = self.gurobi_model.addConstrs(
                    _var.get_equality_constraint_generator(
                        self.input_data, self.variables
                    ),
                    name=f"{_var_name}_definition",
                )
                logger.debug(
                    f"Generated {len(_var.gurobi_definition_constraints)} constraints for symbolic {_var_name}_definition constraint of equality definition of variable"
                )

            except NotImplementedError:
                logger.debug(
                    f"Variable {_var_name} does not has an equality constraint definition"
                )

        # Set the access counter to 0 (needed to check if constraints are using this)
        for _var_name in sorted(self.variables.keys()):
            self.variable_accessed[_var_name] = 0

        # Now add the objective
        logger.debug(
            f"Instantiating objective from class {self.objective_class.__module__}.{self.objective_class.__qualname__}"
        )
        self.objective = self.objective_class(self)

        # Reset the access counter we use to check which variables the user used
        for _var in self.variables.keys():
            self.variable_accessed[_var] = 0

        self.gurobi_model.setObjective(
            self.objective.get_gurobi_objective_expression(
                self.input_data, self.variables
            )
        )
        accessed_variables = [k for k, v in self.variable_accessed.items() if v > 0]

        not_mentioned_variables = [
            x for x in accessed_variables if x not in self.objective.required_variables
        ]
        if len(not_mentioned_variables):
            msg = f"During generation of the objective the following variables were accessed that are not in the objectives required_variables list: {', '.join( sorted(not_mentioned_variables))}"
            logger.warning(msg)
            if self.strict:
                raise OptimizationModelNotStrictError(msg)

        # Use sorted here to ensure we always loop over the constraints in the same way
        for _constraint_name in sorted(self.constraints.keys()):
            # Reset the access counter we use to check which variables the user used
            for _var in self.variables.keys():
                self.variable_accessed[_var] = 0

            _constraint = self.constraints[_constraint_name]

            _generator = _constraint.get_gurobi_constraints_generator(
                self.input_data, self.variables
            )
            _constraint.gurobi_constraints = self.gurobi_model.addConstrs(
                _generator, _constraint.name
            )
            logger.debug(
                f"Generated {len(_constraint.gurobi_constraints)} constraints for symbolic constraint {_constraint.name}"
            )

            _constraint.index_domain = sorted(_constraint.gurobi_constraints.keys())

            accessed_variables = [k for k, v in self.variable_accessed.items() if v > 0]

            not_mentioned_variables = [
                x for x in accessed_variables if x not in _constraint.required_variables
            ]

            if len(not_mentioned_variables):
                msg = f"During generation of constraint {_constraint_name} the following variables were accessed that are not in the constraints' required_variables list: {', '.join( sorted(not_mentioned_variables))}"
                logger.warning(msg)
                if self.strict:
                    raise OptimizationModelNotStrictError(msg)

            if len(_constraint.gurobi_constraints):
                _element_domain = list(_constraint.gurobi_constraints.keys())[0]

                # Deal with situation that with 1-D would result in length of string
                if isinstance(_element_domain, str):
                    _element_domain = [_element_domain]

                num_dimensions_domain = len(_element_domain)
                num_dimensions = len(_constraint.dimensions)

                if self.strict:
                    if len(_constraint.dimensions) == 0:
                        msg = f"Model is set to strict and constraint {_constraint.name} does not have dimensions defined"
                        logger.error(msg)
                        raise OptimizationModelNotStrictError(msg)

                    if num_dimensions_domain != num_dimensions:
                        msg = f"Model is set to strict and number of dimensions in dimensions property of constraint {_constraint.name} ({num_dimensions}) is not equal to the number of dimensions in the index domain ({num_dimensions_domain})"
                        logger.error(msg)
                        raise OptimizationModelNotStrictError(msg)

    def solve_model(self):
        """Initiate the solve of the underlying gurobi model

        Before the model optimization is started, first it will check the object
        attribute solver_options and call the gurobi setParam function with every
        key/value combination from this dictionary.

        Also, if the callback attribute of the class is set to a non-None value, we
        will add the callback function to the gurobi model.

        After the model is solved, the following object attributes are updated:
          * variable_values: dictionary holding the optimized values for each of the
                variables. The key in the dictionary will be the symbolic var name
          * objective_value: float value holding the Objective value
          * program_status: Value of status attribute of the underlying gurobi model
        """
        logger.info(f"Optimizing the model {self.model_name}")

        for k, v in self.solver_options.items():
            logger.debug(f"Setting solver option {k} = {v}")
            self.gurobi_model.setParam(k, v)

        if self.callback is not None:
            logger.debug("Adding callback function")
            self.gurobi_model.optimize(callback=self.callback)
        else:
            self.gurobi_model.optimize()

        self._sol_count = self.gurobi_model.SolCount

        if self._sol_count > 0:
            logger.debug(f"Retrieving variable values for all variables")
            self._variable_values = {
                k: v.get_values() for k, v in self.variables.items()
            }
            self._objective_value = self.gurobi_model.ObjVal
        else:
            logger.debug(f"No solutions available, not retrieving var values")

        self._program_status = self.gurobi_model.status

    def close_gurobi_connection(self):
        """Close the connection to the gurobi server.

        Note that after calling this method, you will not be able to retrieve
        information from the underlying gurobi-based attributes anymore!
        """
        self.gurobi_model.dispose()
        self.env.dispose()

    def generate_model_typing_hints(self, output_file):
        """Generate the variables and constraints collections for this model into the
        filename provided as argument.

        Using this function, you can easily create type-hints information (e.g. the
        generated file will act as a stub file) for your model, allowing you to get
        information about which dimensions a variable/constraint is defined over and
        what the order is.

        Args:
            output_file (str): Name of the file you want to write the generated
                subclasses of VariablesCollection and ConstraintsCollection to
        """
        all_types = []

        all_variable_lines = []
        all_constraint_lines = []

        for var_name in self.__all_variable_names:
            _var = self.variables[var_name]

            var_dimensions = _var.dimensions
            var_domain = _var.get_index_domain(self.input_data)

            if len(var_dimensions) == 0:
                logger.info(
                    f"Not seeing any dimensions defined for {var_name}, will use the get_index_domain)"
                )

                if len(var_domain):
                    if not isinstance(var_domain[0], str) and len(var_domain[0]) >= 2:
                        all_variable_lines.append(
                            f"{var_name}: ModelVariable[tuple["
                            + ", ".join(len(var_domain[0]) * ["Any"])
                            + "]]"
                        )
                    else:
                        all_variable_lines.append(f"{var_name}: ModelVariable[Any]")
            else:
                # Define the types
                all_types.extend(var_dimensions)

                if len(var_dimensions) >= 2:
                    all_variable_lines.append(
                        f"{var_name}: ModelVariable[tuple["
                        + ", ".join([f"t_{x}" for x in var_dimensions])
                        + "]]"
                    )
                else:
                    all_variable_lines.append(
                        f"{var_name}: ModelVariable[t_{var_dimensions[0]}]"
                    )

        for constraint_name in self.__all_constraint_names:
            _constr = self.constraints[constraint_name]

            constr_dimensions = _constr.dimensions

            if len(constr_dimensions) == 0:
                if len(_constr.gurobi_constraints):
                    constr_domain_dim = list(_constr.gurobi_constraints)[0]

                    if isinstance(constr_domain_dim, str):
                        num_dimensions = 1
                    else:
                        num_dimensions = len(constr_domain_dim)

                    if num_dimensions >= 2:
                        all_constraint_lines.append(
                            f"{constraint_name}: ModelConstraint[tuple["
                            + ", ".join(num_dimensions * ["Any"])
                            + "]]"
                        )
                    else:
                        all_constraint_lines.append(
                            f"{constraint_name}: ModelConstraint[Any]"
                        )
                else:
                    continue
            else:
                all_types.extend(constr_dimensions)

                if len(constr_dimensions) >= 2:
                    all_constraint_lines.append(
                        f"{constraint_name}: ModelConstraint[tuple["
                        + ", ".join([f"t_{x}" for x in constr_dimensions])
                        + "]]"
                    )
                else:
                    all_constraint_lines.append(
                        f"{constraint_name}: ModelConstraint[t_{constr_dimensions[0]}]"
                    )

        with open(output_file, "w") as f:
            f.write(
                """# Automatically generated using generate_model_typing_hints function
# fmt: off
from typing import Any, TypeAlias

from ezmodeller.collections import ConstraintsCollection, VariablesCollection
from ezmodeller.model_constraint import ModelConstraint
from ezmodeller.model_variable import ModelVariable

"""
            )

            model_name = self.model_name[0].upper() + self.model_name[1:]

            if len(all_types):
                for _t in sorted(set(all_types)):
                    f.write(f"t_{_t}: TypeAlias = Any\n")

            f.write(f"\n\nclass {model_name}Variables(VariablesCollection):\n")

            f.writelines([f"    {x}\n" for x in all_variable_lines])

            f.write(f"\n\nclass {model_name}Constraints(ConstraintsCollection):\n")

            f.writelines([f"    {x}\n" for x in all_constraint_lines])

            f.write("\n\n# fmt: off\n")

    @property
    def model_name(self) -> str:
        """The name of the model to be solved. Used for identifying the model solve
        on the gurobi server, as well as the prefix when the typing hints file is
        generated.
        """
        return self._model_name

    @property
    def input_data(self) -> Any:
        """The input data provided to the OptimizationModel when it was created."""
        return self._input_data

    @property
    def env(self) -> gp.Env:
        """The gurobipy environment used for solving this model

        Raises:
            OptimizationModelModelNotGenerated in case you try to access this before
                a gurobi model is generated
        """
        if self._env is None:
            raise OptimizationModelModelNotGenerated("Gurobi model not yet generated")
        return self._env

    @property
    def strict(self) -> bool:
        """Indicator whether this model was created in strict mode, which means a
        set of additional checks will be performed
        """
        return self._strict

    @property
    def callback(self) -> None | Callable[[gp.Model, int], None]:
        """Callback function that should be added when gurobi is solving the
        generated model.
        """
        return self._callback

    @callback.setter
    def callback(self, value: Callable[[gp.Model, int], None]):
        self._callback = value

    @property
    def variable_values(self) -> dict[str, dict[Any | list[Any], float]]:
        """The variable values after a solve is finished"""
        return self._variable_values

    @property
    def objective_value(self) -> float:
        """The objective value after a solve is finished. Will raise an
        OptimizationModelModelNotSolved error in case you try to access this property
        before a model is solved"""
        if self._objective_value is None:
            raise OptimizationModelModelNotSolved(
                "Cannot access the objective_value property if model is not solved yet"
            )
        return self._objective_value

    @property
    def program_status(self) -> Any:
        """The model program status after a solve is finished"""
        return self._program_status

    @property
    def solver_options(self) -> dict[str, int | float | str]:
        """The gurobi solver options that will be used for solving the problem"""
        return self._solver_options

    @solver_options.setter
    def solver_options(self, value: dict[str, int | float | str]) -> None:
        self._solver_options = value

    @property
    def sol_count(self) -> int:
        """The number of stored solutions in the most recent optimization
        OptimizationModelModelNotSolved error in case you try to access this property
        before a model is solved"""
        if self._sol_count is None:
            raise OptimizationModelModelNotSolved(
                "Cannot access the sol_count property if model is not solved yet"
            )
        return self._sol_count
