# fmt:off
from ezmodeller import ModelConstraint


class RespectSupply(ModelConstraint):
    def set_constraint_properties(self):
        pass

    def get_gurobi_constraints_generator(self, input_data, variables):
        input_factories = input_data["factories"]
        input_supply = input_data["supply"]
        input_customers = input_data["customers"]

        index_domain = [x for x in input_factories if input_supply.get(x)]


        # Convenience aliases:
        _var_transport = variables.Transport

        return (
            sum((_var_transport[(f, c)] for c in input_customers)) <= input_supply[f]
            for f in index_domain
        )

# fmt:on
