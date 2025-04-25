def get_transport_problem_input():
    supply = {
        "Amsterdam": 50,
        "Groningen": 375,
        "Maastricht": 175,
    }
    factories = sorted(supply.keys())

    demand = {
        "Utrecht": 100,
        "Haarlem": 200,
        "Zwolle": 300,
    }

    customers = sorted(demand.keys())

    transport_cost = {
        ("Amsterdam", "Utrecht"): 10,
        ("Amsterdam", "Haarlem"): 20,
        ("Amsterdam", "Zwolle"): 30,
        ("Groningen", "Utrecht"): 40,
        ("Groningen", "Haarlem"): 50,
        ("Groningen", "Zwolle"): 60,
        ("Maastricht", "Utrecht"): 70,
        ("Maastricht", "Haarlem"): 80,
        ("Maastricht", "Zwolle"): 90,
    }

    input_data = {
        "factories": factories,
        "supply": supply,
        "customers": customers,
        "demand": demand,
        "transport_cost": transport_cost,
    }

    return input_data
