# fmt: off
from ezmodeller import ModelConstraint


class NutritionUpperBound(ModelConstraint):

    def set_constraint_properties(self):
        # Instead of having the framework use the default based on the
        # class name, we want to overrule it with the following name
        # You will see this name in lp files you generate or in the
        # generated 
        self.name = "overruled_nutrition_upper_bound"

        self.dimensions = ["category"]
        self.required_variables = ["Buy"]


    def get_gurobi_constraints_generator(self, input_data, variables):

        input_categories = input_data["categories"]
        nutrition_values = input_data["nutritionValues"]
        max_nutrition_values = input_data["maxNutrition"]
        foods = input_data["foods"]

        # Only for those lines for which we have a max defined
        index_domain = [x for x in input_categories if max_nutrition_values[x]]


        # Convenience aliases, using the fact that the framework makes the name available
        # as a dictionary 
        _var_buy  = variables["Buy"]

        # For every category, the total sum of this nutrition value provided by the
        # bought foods should be <= max required value
        return (

                sum( 
                    nutrition_values[(f,c)] * _var_buy[f] 

                    for f in foods 
                )

                <=

                max_nutrition_values[c]

                for c in index_domain
            )

# fmt: off
