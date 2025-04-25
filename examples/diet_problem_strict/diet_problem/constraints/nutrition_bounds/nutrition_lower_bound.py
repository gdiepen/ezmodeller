# fmt: off
from diet_problem_typing_hints import DietVariables

from ezmodeller import ModelConstraint


class NutritionLowerBound(ModelConstraint):

    def set_constraint_properties(self):
        self.dimensions = ["category"]
        self.required_variables = ["Buy"]


    def get_gurobi_constraints_generator(self, input_data, variables:DietVariables):
        input_categories = input_data["categories"]
        nutrition_values = input_data["nutritionValues"]
        min_nutrition_values = input_data["minNutrition"]
        foods = input_data["foods"]

        # Only for those lines for which we have a min defined
        index_domain = [x for x in input_categories if min_nutrition_values[x]]

         
        # Convenience aliases, using the fact that the framework makes the name available
        # as an attribute
        _var_buy = variables.Buy



        # For every category, the total sum of this nutrition value provided by the
        # bought foods should be >= min required value
        return (

                sum( 
                    nutrition_values[(f,c)] * _var_buy[f] 

                    for f in foods 
                )

                >=

                min_nutrition_values[c]

                for c in index_domain
            )
# fmt: on
