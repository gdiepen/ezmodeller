import logging
import pprint

import diet_problem.constraints
import diet_problem.objective.min_total_cost
import diet_problem.variables
from diet_problem_input import get_diet_problem_input

from ezmodeller import OptimizationModel

logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s [%(levelname)8s] - %(name)s - %(message)s"
)

logging.getLogger("gurobipy").setLevel(logging.WARNING)


if __name__ == "__main__":
    input_data = get_diet_problem_input()

    diet_model = OptimizationModel(
        "Diet",
        input_data,
        diet_problem.variables,
        diet_problem.constraints,
        diet_problem.objective.min_total_cost.MinTotalDietCost,
        strict=True,
    )

    # Generate the gurobi model based on all variables/constraints/input data
    diet_model.generate_gurobi_model()

    # Generate the typing hints files for the variables/constraints
    diet_model.generate_model_typing_hints("diet_problem_typing_hints.py")

    # Write the LP file of the generated model
    diet_model.gurobi_model.write("diet_problem.lp")

    # Solve the model
    diet_model.solve_model()

    # Disconnect from the gurobi server again (note: you cannot access any gurobi
    # specific items anymore after this!)
    diet_model.close_gurobi_connection()

    print()
    print()
    print()
    print(f"Objective value = {diet_model.objective_value}")
    print("Optimal Variable values:")
    pprint.pprint(diet_model.variable_values)
