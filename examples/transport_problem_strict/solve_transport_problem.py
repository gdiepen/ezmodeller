import logging
import pprint

import transport_problem.constraints
import transport_problem.objective.min_total_cost
import transport_problem.variables
from transport_problem_input import get_transport_problem_input

from ezmodeller import OptimizationModel

# logging.basicConfig(level=logging.DEBUG, format= '%(asctime)s [%(levelname)8s] - %(message)s (%(filename)s:%(lineno)s)')
logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s [%(levelname)8s] - %(name)s - %(message)s"
)

logging.getLogger("gurobipy").setLevel(logging.WARNING)


if __name__ == "__main__":
    input_data = get_transport_problem_input()

    transport_problem = OptimizationModel(
        "TransportProblem",
        input_data,
        transport_problem.variables,
        transport_problem.constraints,
        transport_problem.objective.min_total_cost.MinTotalTransportCost,
        strict=True,
    )

    # Generate the gurobi model based on all variables/constraints/input data
    transport_problem.generate_gurobi_model()

    # Generate the typing hints files for the variables/constraints
    transport_problem.generate_model_typing_hints("transport_problem_typing_hints.py")

    # Write the LP file of the generated model
    transport_problem.gurobi_model.write("transport_problem.lp")

    # Solve the model
    transport_problem.solve_model()

    # Disconnect from the gurobi server again (note: you cannot access any gurobi
    # specific items anymore after this!)
    transport_problem.close_gurobi_connection()

    print()
    print()
    print()
    print(f"Objective value = {transport_problem.objective_value}")
    print("Optimal Variable values:")
    pprint.pprint(transport_problem.variable_values)
