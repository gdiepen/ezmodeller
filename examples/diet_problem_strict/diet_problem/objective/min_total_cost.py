# fmt: off
from diet_problem_typing_hints import DietVariables
from gurobipy import GRB

from ezmodeller import ModelObjective


class MinTotalDietCost(ModelObjective):

    def set_objective_properties(self):
        self.direction = GRB.MINIMIZE
        self.required_variables = ["Buy"]


    def get_gurobi_objective_expression(self, input_data, variables:DietVariables):

        _var_buy = variables.Buy

        _coeff_cost = input_data["cost"]

        return sum( 

            (
                _var_buy[i] 
                * 
                _coeff_cost[i]
            )

            for i in _var_buy.get_index_domain(input_data)
        )

# fmt: on
