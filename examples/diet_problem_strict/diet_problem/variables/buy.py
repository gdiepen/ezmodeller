from gurobipy import GRB

from ezmodeller import ModelVariable


class Buy(ModelVariable):
    def set_variable_properties(self):
        self.var_type = GRB.CONTINUOUS

        self.var_lb = 0
        self.var_ub = GRB.INFINITY

        self.dimensions = ["food"]

    def get_index_domain(self, input_data):
        return input_data["foods"]
