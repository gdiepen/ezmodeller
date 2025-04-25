from dataclasses import dataclass, field


@dataclass(init=False)
class VariablesCollection:
    """Special dataclass based class to hold all of the variables that are part of an
    optimization model.

    By subclassing this VariablesCollection class you can easily get type-hints about
    the index domain of each of the variables (e.g. Transport variable is defined over
    the domain (factory, customer)

    The optimization_model class includes a convenience function
    generate_collections_scripts to quickly generate the corresponding specific
    subclasses of the VariablesCollection and ConstraintsCollection for the current
    model
    """

    __all_variables: dict = field(init=False)

    def __init__(self):
        self.__all_variables = {}

    def __setattr__(self, prop, val):
        super().__setattr__(prop, val)

    def __getattribute__(self, name):
        return super().__getattribute__(name)

    def __getitem__(self, key):
        if not hasattr(self, key):
            setattr(self, key, {})

        return getattr(self, key)

    def __setitem__(self, key, elem):
        self.__all_variables[key] = elem

        setattr(self, key, elem)

    def __contains__(self, a):
        return a in self.__all_variables

    def values(self):
        return self.__all_variables.values()

    def keys(self):
        return self.__all_variables.keys()

    def items(self):
        return self.__all_variables.items()


@dataclass(init=False)
class ConstraintsCollection:
    """Special dataclass based class to hold all of the constraints that are part of an
    optimization model.

    By subclassing this ConstraintsCollection class you can easily get type-hints about
    the index domain of each of the constraints (e.g. RespectSupply variable is defined
    over the domain (factory)

    The optimization_model class includes a convenience function
    generate_collections_scripts to quickly generate the corresponding specific
    subclasses of the VariablesCollection and ConstraintsCollection for the current
    model
    """

    __all_constraints: dict = field(init=False)

    def __init__(self):
        self.__all_constraints = {}

    def __setattr__(self, prop, val):
        super().__setattr__(prop, val)

    def __getattribute__(self, name):
        return super().__getattribute__(name)

    def __getitem__(self, key):
        if not hasattr(self, key):
            setattr(self, key, {})

        return getattr(self, key)

    def __setitem__(self, key, elem):
        self.__all_constraints[key] = elem

        setattr(self, key, elem)

    def __contains__(self, a):
        return a in self.__all_constraints

    def values(self):
        return self.__all_constraints.values()

    def keys(self):
        return self.__all_constraints.keys()

    def items(self):
        return self.__all_constraints.items()
