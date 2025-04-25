# fmt: off
from gurobipy import GRB
from transport_problem_typing_hints import TransportProblemVariables

from ezmodeller import ModelObjective


class MinTotalTransportCost(ModelObjective):
    def set_objective_properties(self):
        self.direction = GRB.MINIMIZE
        self.required_variables = ["Transport"]

    def get_gurobi_objective_expression(
        self, input_data, variables: TransportProblemVariables
    ):
        _var_transport = variables.Transport
        _transport_cost = input_data["transport_cost"]

        return sum(
            (
                _var_transport[(f, c)] 
                * 
                _transport_cost[(f, c)]
            )

            for (f, c) in _var_transport.get_index_domain(input_data)
        )

# fmt: on
