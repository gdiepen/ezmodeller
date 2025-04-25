from gurobipy import GRB

from ezmodeller import ModelVariable


class Transport(ModelVariable):
    def set_variable_properties(self):
        self.var_type = GRB.CONTINUOUS

        self.var_lb = 0
        self.var_ub = GRB.INFINITY

    def get_index_domain(self, input_data):
        return sorted(input_data["transport_cost"].keys())
