class OptimizationModelError(Exception):
    pass


class OptimizationModelMissingPropertiesError(OptimizationModelError):
    pass


class OptimizationModelDuplicateVariableDefinition(OptimizationModelError):
    pass


class OptimizationModelDuplicateConstraintDefinition(OptimizationModelError):
    pass


class OptimizationModelMissingVariablesError(OptimizationModelError):
    pass


class OptimizationModelNotStrictError(OptimizationModelError):
    pass


class OptimizationModelModelNotGenerated(OptimizationModelError):
    pass


class OptimizationModelModelNotSolved(OptimizationModelError):
    pass
