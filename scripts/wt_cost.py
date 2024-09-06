
def check_supp(water_depth):
    """
    Determines the support structure type based on water depth.

    Parameters:
        water_depth (float): Water depth at the turbine location.

    Returns:
        str: Support structure type ('monopile', 'jacket', 'floating').
    """
    if water_depth < 25:
        return "monopile"
    elif 25 <= water_depth < 55:
        return "jacket"
    elif 55 <= water_depth:
        return "floating"

def calc_equip_cost(first_year, water_depth, support_structure, ice_cover, turbine_capacity):
    """
    Calculates the equipment cost based on water depth, support structure, ice cover, and turbine capacity.

    Parameters:
        water_depth (float): Water depth at the turbine location.
        support_structure (str): Type of support structure.
        ice_cover (int): Indicator if the area is ice-covered (1 for Yes, 0 for No).
        turbine_capacity (float): Capacity of the turbine.

    Returns:
        tuple: Calculated support structure cost and turbine cost.
    """
    if first_year == 2030:
        support_structure_coeff = {
            'monopile': (181, 552, 370),
            'jacket': (103, -2043, 478),
            'floating': (0, 697, 1223)
        }
        turbine_coeff = 1200 * 1e3  # Coefficient for turbine cost (EU/MW)
    elif first_year == 2040:
        support_structure_coeff = {
            'monopile': (176, 536, 270),
            'jacket': (100, -1986, 375),
            'floating': (0, 678, 1034)
        }
        turbine_coeff = 1100 * 1e3  # Coefficient for turbine cost (EU/MW)
    elif first_year == 2050:
        support_structure_coeff = {
            'monopile': (171, 521, 170),
            'jacket': (97, -1930, 658),
            'floating': (0, 658, 844)
        }
        turbine_coeff = 1000 * 1e3  # Coefficient for turbine cost (EU/MW)

    c1, c2, c3 = support_structure_coeff[support_structure]  # Get coefficients for the support structure
    supp_cost = turbine_capacity * (c1 * (water_depth ** 2) + c2 * water_depth + c3 * 1e3)
    
    if ice_cover == 1:
        turbine_coeff *= (1 + 0.4 * 0.5714) # REDUCED BY 60%

    turbine_cost = turbine_capacity * turbine_coeff

    # Millions of Euros
    supp_cost *= 1e-6
    turbine_cost *= 1e-6
    
    return supp_cost, turbine_cost

def calc_inst_deco_cost(water_depth, port_distance, turbine_capacity, operation):
    """
    Calculate installation or decommissioning cost based on the water depth, port distance,
    and rated power of the wind turbines.

    Parameters:
        water_depth (float): Water depth at the turbine location in m.
        port_distance (float): Distance to the port in km.
        turbine_capacity (float): Capacity of the turbine in MW.
        operation (str): Type of operation ('installation' or 'decommissioning').

    Returns:
        float: Calculated cost in Euros.
    """
    port_distance *= 1e-3 # Port distance in km
    
    inst_coeff = {
        'PSIV': ((40 / turbine_capacity), 18.5, 24, 144, 200),
        'Tug': ((1/3), 7.5, 5, 0, 2.5),
        'AHV': (7, 18.5, 30, 90, 40)
    }

    deco_coeff = {
        'PSIV': ((40 / turbine_capacity), 18.5, 24, 144, 200),
        'Tug': ((1/3), 7.5, 5, 0, 2.5),
        'AHV': (7, 18.5, 30, 30, 40)
    }

    coeff = inst_coeff if operation == 'inst' else deco_coeff  # Choose coefficients based on operation type

    support_structure = check_supp(water_depth)

    if support_structure in ['monopile', 'jacket']:
        c1, c2, c3, c4, c5 = coeff['PSIV']
        total_cost = ((1 / c1) * ((2 * port_distance)/c2 + c3) + c4) * ((c5 * 1e3) / 24)
    elif support_structure == 'floating':
        total_cost = 0
        for vessel_type in ['Tug', 'AHV']:
            c1, c2, c3, c4, c5 = coeff[vessel_type]
            vessel_cost = ((1 / c1) * ((2 * port_distance)/c2 + c3) + c4) * ((c5 * 1e3) / 24)
            total_cost += vessel_cost

    total_cost *= 1e-6 # Millions of Euros

    return total_cost