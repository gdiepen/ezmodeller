# fmt: off
from transport_problem_typing_hints import TransportProblemVariables

from ezmodeller import ModelConstraint


class RespectDemand(ModelConstraint):
    def set_constraint_properties(self):
        self.required_variables = ["Transport"]
        self.dimensions = ["customer"]

    def get_gurobi_constraints_generator(self, input_data, variables:TransportProblemVariables):
        input_factories = input_data["factories"]
        input_demand = input_data["demand"]
        input_customers = input_data["customers"]

        index_domain = [x for x in input_customers if input_demand.get(x)]


        _var_transport = variables.Transport

        return (


            sum(
                _var_transport[(f, c)] 

                for f in input_factories
            ) 

            == 

            input_demand[c]


            for c in index_domain
        )
# fmt: on
