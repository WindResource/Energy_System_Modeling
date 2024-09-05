"""
Wind Farm Optimization Model Setup

This script sets up and solves an optimization problem for selecting wind farms, energy hubs,
and their connections to minimize total cost while adhering to operational constraints. It considers
the cost of selecting wind farms and substations, plus the cost associated with connecting these
entities based on distances. It ensures configurations meet specified requirements, including
connection feasibility, capacity limitations, and distance constraints.

- generate_connections_and_cost(wind_farms, offshore_ss, onshore_ss, cost_per_distance_unit): Generates
    possible connections between entities and calculates associated cost based on distances.
    Parameters:
    - wind_farms (dict): Dictionary of wind farms with 'coordinates'.
    - offshore_ss (dict): Dictionary of energy hubs with 'coordinates'.
    - onshore_ss (dict): Dictionary of onshore substations with 'coordinates'.
    - cost_per_distance_unit (float): Cost factor per unit of distance (e.g., per kilometer).
    Returns:
    - tuple of (dict, dict): Two dictionaries, one for connection cost and one for distances, 
    with tuple ids representing connections (e.g., ('WF1', 'OSS1')).

- add_constraints(model, wind_farms, offshore_ss, onshore_ss, connections_cost, distances,
        min_total_capacity, max_wf_eh_dist, max_eh_ss_dist, universal_offshore_ss_max_capacity):
    Adds operational constraints to the optimization model, including capacity and distance limitations.
    Parameters:
    - model (ConcreteModel): The Pyomo model.
    - wind_farms (dict): Dictionary of wind farms.
    - offshore_ss (dict): Dictionary of energy hubs.
    - onshore_ss (dict): Dictionary of onshore substations.
    - connections_cost (dict): Dictionary of connection cost.
    - distances (dict): Dictionary of distances between entities.
    - min_total_capacity (float): Minimum total capacity requirement for selected wind farms.
    - max_wf_eh_dist (float): Maximum allowed distance from wind farms to energy hubs.
    - max_eh_ss_dist (float): Maximum allowed distance from energy hubs to onshore substations.
    - universal_offshore_ss_max_capacity (float): Maximum capacity for any energy hub.
    
The optimization model is solved using Pyomo with GLPK as the solver. The solution includes selected
wind farms, energy hubs, and connections between them, adhering to defined constraints.
"""

from pyomo.environ import *
import numpy as np
import os
import pandas as pd
import openpyxl
from itertools import product
from scripts.present_value import present_value_single
from scripts.eh_cost import check_supp, equip_cost_lin, inst_deco_cost_lin

def eh_cost_lin(first_year, water_depth, ice_cover, port_distance, eh_capacity, eh_active):
    """
    Estimate the cost associated with an energy hub based on various parameters.

    Parameters:
    - water_depth (float): Water depth at the location of the energy hub.
    - ice_cover (int): Indicator of ice cover presence (1 for presence, 0 for absence).
    - port_distance (float): Distance from the offshore location to the nearest port.
    - eh_capacity (float): Capacity of the energy hub.
    - polarity (str, optional): Polarity of the substation ('AC' or 'DC'). Defaults to 'AC'.

    Returns:
    - float: Estimated total cost of the energy hub.
    """
    # Determine support structure
    supp_structure = check_supp(water_depth)
    
    # Calculate equipment cost
    conv_cost, equip_cost = equip_cost_lin(water_depth, supp_structure, ice_cover, eh_capacity, eh_active)

    # Calculate installation and decommissioning cost
    inst_cost = eh_active * inst_deco_cost_lin(supp_structure, port_distance, "inst")
    deco_cost = eh_active * inst_deco_cost_lin(supp_structure, port_distance, "deco")

    # Calculate yearly operational cost
    ope_cost_yearly = 0.03 * conv_cost
    
    # Calculate present value of cost    
    eh_cost = present_value_single(first_year, equip_cost, inst_cost, ope_cost_yearly, deco_cost)
    
    return eh_cost

def onss_cost_lin(first_year, capacity, threshold):
    """
    Calculate the cost for ONSS expansion above a certain capacity.

    Parameters:
    - capacity (float): The total capacity in MW for which the cost is to be calculated.
    - threshold (float): The capacity threshold in MW specific to the ONSS above which cost are incurred.
    
    Returns:
    - (float) Cost of expanding the ONSS if the capacity exceeds the threshold.
    """
    
    threshold_equip_cost = 0.02287 # Million EU/ MW
    
    # Calculate the cost function: difference between capacity and threshold multiplied by the cost factor
    equip_cost = (capacity - threshold) * threshold_equip_cost
    
    ope_cost_yearly = 0.015 * equip_cost
    
    inst_cost, deco_cost = 0, 0
    
    # Calculate present value
    total_cost = present_value_single(first_year, equip_cost, inst_cost, ope_cost_yearly, deco_cost)
    
    return total_cost

def ec1_cost_fun(first_year, distance, capacity, function="lin"):
    """
    Calculate the cost associated with selecting export cables for a given length, desired capacity,
    and desired voltage.

    Parameters:
        length (float): The length of the cable (in meters).
        desired_capacity (float): The desired capacity of the cable (in watts).
        desired_voltage (int): The desired voltage of the cable (in kilovolts).

    Returns:
        tuple: A tuple containing the equipment cost, installation cost, and total cost
                associated with the selected HVAC cables.
    """

    cable_length = 1.10 * distance
    cable_capacity = 348 # MW
    cable_equip_cost = 0.860 #Meu/km
    cable_inst_cost = 0.540 #Meu/km
    capacity_factor = 0.95
    
    if function == "lin":
        parallel_cables = capacity / (cable_capacity * capacity_factor)
    elif function == "ceil":
        parallel_cables = np.ceil(capacity / (cable_capacity * capacity_factor))
    
    equip_cost = parallel_cables * cable_length * cable_equip_cost
    inst_cost = parallel_cables * cable_length * cable_inst_cost
    
    ope_cost_yearly = 0.2 * 1e-2 * equip_cost
    
    deco_cost = 0.5 * inst_cost

    # Calculate present value
    total_cost = present_value_single(first_year, equip_cost, inst_cost, ope_cost_yearly, deco_cost)

    return total_cost

def ec2_cost_fun(first_year, distance, capacity, function="lin"):
    """
    Calculate the cost associated with selecting export cables for a given length, desired capacity,
    and desired voltage.

    Parameters:
        length (float): The length of the cable (in meters).
        desired_capacity (float): The desired capacity of the cable (in watts).
        desired_voltage (int): The desired voltage of the cable (in kilovolts).

    Returns:
        tuple: A tuple containing the equipment cost, installation cost, and total cost
                associated with the selected HVAC cables.
    """

    cable_length = 1.10 * distance + 2 # km Accounting for the offshore to onshore transition
    cable_capacity = 348 # MW
    cable_equip_cost = 0.860 # Million EU/km
    cable_inst_cost = 0.540 # Million EU/km
    capacity_factor = 0.95
    
    if function == "lin":
        parallel_cables = capacity / (cable_capacity * capacity_factor)
    elif function == "ceil":
        parallel_cables = np.ceil(capacity / (cable_capacity * capacity_factor))
    
    equip_cost = parallel_cables * cable_length * cable_equip_cost
    inst_cost = parallel_cables * cable_length * cable_inst_cost
    
    ope_cost_yearly = 0.2 * 1e-2 * equip_cost
    
    deco_cost = 0.5 * inst_cost

    # Calculate present value
    total_cost = present_value_single(first_year, equip_cost, inst_cost, ope_cost_yearly, deco_cost)

    return total_cost

def ec3_cost_fun(first_year, distance, capacity, function="lin"):
    """
    Calculate the cost associated with selecting export cables for a given length, desired capacity,
    and desired voltage.

    Parameters:
        length (float): The length of the cable (in meters).
        desired_capacity (float): The desired capacity of the cable (in watts).
        desired_voltage (int): The desired voltage of the cable (in kilovolts).

    Returns:
        tuple: A tuple containing the equipment cost, installation cost, and total cost
                associated with the selected HVAC cables.
    """

    cable_length = 1.10 * distance + 2 # km Accounting for the offshore to onshore transition
    cable_capacity = 348 # MW
    cable_equip_cost = 0.860 # Million EU/km
    cable_inst_cost = 0.540 # Million EU/km
    capacity_factor = 0.95
    
    if function == "lin":
        parallel_cables = capacity / (cable_capacity * capacity_factor)
    elif function == "ceil":
        parallel_cables = np.ceil(capacity / (cable_capacity * capacity_factor))
    
    equip_cost = parallel_cables * cable_length * cable_equip_cost
    inst_cost = parallel_cables * cable_length * cable_inst_cost
    
    ope_cost_yearly = 0.2 * 1e-2 * equip_cost
    
    deco_cost = 0.5 * inst_cost

    # Calculate present value
    total_cost = present_value_single(first_year, equip_cost, inst_cost, ope_cost_yearly, deco_cost)

    return total_cost

def onc_cost_fun(first_year, distance, capacity, function="lin"):
    """
    Calculate the cost associated with selecting onshore substation cables for a given length and desired capacity.

    Parameters:
        distance (float): The length of the cable (in kilometers).
        capacity (float): The desired capacity of the cable (in MW).

    Returns:
        float: The total cost associated with the selected onshore substation cables.
    """
    cable_length = 1.10 * distance
    cable_capacity = 348  # MW (assuming same as export cable capacity)
    cable_equip_cost = 0.860  # Million EU/km
    cable_inst_cost = 0.540 * 0.5  # Million EU/km
    capacity_factor = 0.95
    
    if function == "lin":
        parallel_cables = capacity / (cable_capacity * capacity_factor)
    elif function == "ceil":
        parallel_cables = np.ceil(capacity / (cable_capacity * capacity_factor))
    
    equip_cost = parallel_cables * cable_length * cable_equip_cost
    inst_cost = parallel_cables * cable_length * cable_inst_cost
    
    ope_cost_yearly = 0.2 * 1e-2 * equip_cost
    deco_cost = 0.5 * inst_cost

    # Assuming a placeholder for present value calculation (to be defined)
    total_cost = present_value_single(first_year, equip_cost, inst_cost, ope_cost_yearly, deco_cost)

    return total_cost

def wf_cost_lin(wf_cost, wf_total_cap, wf_cap):
    """
    Calculate the cost of selecting and operating each wind farm based on the selected capacity.
    The cost is proportional to the selected capacity.
    
    Parameters:
    - wf_cost (float): The cost of the wind farm.
    - wf_total_cap (float): The total available capacity of the wind farm.
    - wf_cap (float): The selected capacity of the wind farm.
    
    Returns:
    - float: The calculated cost for the selected capacity.
    """
    return value(wf_cost) * (wf_cap / wf_total_cap)

def haversine(lon1, lat1, lon2, lat2):
    """
    Calculate the great-circle distance between two points in kilometers
    on the Earth (specified in decimal degrees) using NumPy for calculations.
    """
    # Convert decimal degrees to radians
    lon1, lat1, lon2, lat2 = map(np.radians, [lon1, lat1, lon2, lat2])

    # Haversine formula
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = np.sin(dlat/2.0)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon/2.0)**2
    c = 2 * np.arcsin(np.sqrt(a))
    r = 6371  # Radius of Earth in kilometers
    return c * r

def find_viable_ec1(wf_lon, wf_lat, eh_lon, eh_lat):
    """
    Find all pairs of offshore wind farms and energy hubs within 150km,
    ensuring that they belong to the same country based on their ISO codes.
    
    Parameters are dictionaries indexed by IDs with longitude, latitude, and ISO codes.
    """
    connections = []
    for wf_id, eh_id in product(wf_lon.keys(), eh_lon.keys()):
        # Calculate the distance first to see if they are within the viable range
        distance = haversine(wf_lon[wf_id], wf_lat[wf_id], eh_lon[eh_id], eh_lat[eh_id])
        if distance <= 250:  # Check if the distance is within 150 km
            connections.append((int(wf_id), int(eh_id)))
    return connections

def find_viable_ec2(eh_lon, eh_lat, onss_lon, onss_lat):
    """
    Find all pairs of offshore and onshore substations within 300km,
    ensuring that they belong to the same country based on their ISO codes.
    
    Parameters are dictionaries indexed by substation IDs with longitude, latitude, and ISO codes.
    """
    connections = []
    for eh_id, onss_id in product(eh_lon.keys(), onss_lon.keys()):
        # Calculate the distance first to see if they are within the viable range
        distance = haversine(eh_lon[eh_id], eh_lat[eh_id], onss_lon[onss_id], onss_lat[onss_id])
        if distance <= 250:  # Check if the distance is within 300 km
            connections.append((int(eh_id), int(onss_id)))
    return connections

def find_viable_ec3(wf_lon, wf_lat, onss_lon, onss_lat):
    """
    Find all pairs of wind farms and onshore substations within 450km,
    ensuring that they belong to the same country based on their ISO codes.
    
    Parameters are dictionaries indexed by IDs with longitude, latitude, and ISO codes.
    """
    connections = []
    for wf_id, onss_id in product(wf_lon.keys(), onss_lon.keys()):
        distance = haversine(wf_lon[wf_id], wf_lat[wf_id], onss_lon[onss_id], onss_lat[onss_id])
        if distance <= 500:  # Check if the distance is within 450 km
            connections.append((int(wf_id), int(onss_id)))
    return connections

def find_viable_onc(onss_lon, onss_lat):
    """
    Find all pairs of onshore substations within 100km,
    ensuring that they belong to the same country based on their ISO codes.
    
    Parameters are dictionaries indexed by IDs with longitude, latitude, and ISO codes.
    """
    connections = []
    for onss_id1, onss_id2 in product(onss_lon.keys(), repeat=2):
        if onss_id1 != onss_id2:  # Prevent self-connections
            distance = haversine(onss_lon[onss_id1], onss_lat[onss_id1], onss_lon[onss_id2], onss_lat[onss_id2])
            if distance <= 250:  # Check if the distance is within 100 km
                connections.append((int(onss_id1), int(onss_id2)))
    return connections

def get_viable_entities(viable_ec1, viable_ec2, viable_ec3):
    """
    Identifies unique wind farm, energy hub, and onshore substation IDs
    based on their involvement in viable export and export cable connections.

    Parameters:
    - viable_ec1 (list of tuples): List of tuples, each representing a viable connection
        between a wind farm and an energy hub (wf_id, eh_id).
    - viable_ec2 (list of tuples): List of tuples, each representing a viable connection
        between an energy hub and an onshore substation (eh_id, onss_id).
    - viable_ec3 (list of tuples): List of tuples, each representing a viable direct connection
        between a wind farm and an onshore substation (wf_id, onss_id).

    Returns:
    - viable_wf (set): Set of wind farm IDs with at least one viable connection to an energy hub or onshore substation.
    - viable_eh (set): Set of energy hub IDs involved in at least one viable connection
        either to a wind farm or an onshore substation.
    - viable_onss (set): Set of onshore substation IDs with at least one viable connection to an energy hub or wind farm.
    """
    viable_wf = set()
    viable_eh = set()
    viable_onss = set()

    # Extract unique wind farm and energy hub IDs from export connections
    for wf_id, eh_id in viable_ec1:
        viable_wf.add(int(wf_id))
        viable_eh.add(int(eh_id))

    # Extract unique offshore and onshore substation IDs from export cable connections
    for eh_id, onss_id in viable_ec2:
        viable_eh.add(int(eh_id))
        viable_onss.add(int(onss_id))

    # Extract unique wind farm and onshore substation IDs from direct connections
    for wf_id, onss_id in viable_ec3:
        viable_wf.add(int(wf_id))
        viable_onss.add(int(onss_id))

    return viable_wf, viable_eh, viable_onss

def opt_model(workspace_folder, model_type=0, cross_border=1, multi_stage=0, linear_result=0):
    """
    Create an optimization model for offshore wind farm layout optimization.

    Parameters:
    - workspace_folder (str): The path to the workspace folder containing datasets.
    - model_type (int): The type of the model (0, 1, or 2).
    - cross_border (int): Whether to allow cross-border connections (0 or 1).
    - multi_stage (int): 0 for a single stage optimization for 2050, 1 for a multistage optimization for 2030, 2040, 2050.

    Returns:
    - model: Pyomo ConcreteModel object representing the optimization model.
    """
    """
    Initialise model
    """
    print("Initialising model...")
    
    # Create a Pyomo model
    model = ConcreteModel()
    
    # Mapping ISO country codes of Baltic Sea countries to unique integers
    iso_to_int_mp = {
        'DE': 1,  # Germany
        'DK': 2,  # Denmark
        'EE': 3,  # Estonia
        'FI': 4,  # Finland
        'LV': 5,  # Latvia
        'LT': 6,  # Lithuania
        'PL': 7,  # Poland
        'SE': 8   # Sweden
    }
    
    "Define Sensitivity Parameters"
    
    # Sensitivity factors
    sf_wf = 1
    sf_eh = 1
    sf_ec1 = 1
    sf_ec2 = 1
    sf_ec3 = 1
    sf_onss = 1
    sf_onc = 1
    
    "Define General Parameters"
    
    note_to_write = "This result contains model_type=0, cross_border=1, multi_stage=0, linear_result=1"
    
    zero_th = 1e-3 # Define the zero threshold parameter
    
    wt_cap = 15  # Define the wind turbine capacity (MW)
    eh_cap_lim = 2500 # Define the energy hub capacity limit (MW)
    onss_cap_lim_fac= 2.5 # Define the onshore substation capacity limit factor
    
    # Select countries to be included in the optimization
    select_countries = {
        'DE': 1,  # Germany
        'DK': 1,  # Denmark
        'EE': 1,  # Estonia
        'FI': 1,  # Finland
        'LV': 1,  # Latvia
        'LT': 1,  # Lithuania
        'PL': 1,  # Poland
        'SE': 1   # Sweden
    }
    
    # Define the base capacity fractions for the final year (national connections)
    base_country_cf_sf_n = {
        'DE': 100 * 1e-2,  # Germany, limited to 100%
        'DK': 5.63 * 1e-2,  # Denmark
        'EE': 12.19 * 1e-2,  # Estonia
        'FI': 7.92 * 1e-2,  # Finland
        'LV': 5.09 * 1e-2,  # Latvia
        'LT': 2.82 * 1e-2,  # Lithuania
        'PL': 100 * 1e-2,  # Poland, limited to 100%
        'SE': 2.01 * 1e-2   # Sweden
    }
    
    # Define the base capacity fractions for the final year (international connections)
    base_country_cf_sf_i = {
        'DE': 100 * 1e-2,  # Germany, limited to 100%
        'DK': 5.63 * 1e-2,  # Denmark
        'EE': 12.19 * 1e-2,  # Estonia
        'FI': 7.92 * 1e-2,  # Finland
        'LV': 5.09 * 1e-2,  # Latvia
        'LT': 2.82 * 1e-2,  # Lithuania
        'PL': 100 * 1e-2,  # Poland, limited to 100%
        'SE': 2.01 * 1e-2   # Sweden
    }
    
    solver_options = {
        'limits/gap': 0,                  # Stop when the relative optimality gap is 0.6%
        'limits/nodes': 1e4,                 # Maximum number of nodes in the search tree
        'limits/solutions': -1,             # Limit on the number of solutions found
        'limits/time': 3600,                 # Set a time limit of 3600 seconds (1 hour)
        'numerics/feastol': 1e-5,           # Feasibility tolerance for constraints
        'numerics/dualfeastol': 1e-5,       # Tolerance for dual feasibility conditions
        'presolving/maxrounds': -1,          # Maximum number of presolve iterations (-1 for no limit)
        'propagating/maxrounds': -1,         # Maximum number of propagation rounds (-1 for no limit)
        'propagating/maxroundsroot': -1,     # Propagation rounds at the root node
        'separating/maxrounds': -1,          # Maximum cut rounds at non-root nodes
        'display/verblevel': 4               # Verbosity level to display detailed information about the solution process
    }
    
    "Define Single Stage Optimization Parameters"
    
    # Define the year to be optimized for single stage
    first_year_sf = 2040
    
    if cross_border == 0:
        base_country_cf_sf = base_country_cf_sf_n
    elif cross_border == 1:
        base_country_cf_sf = base_country_cf_sf_i
    
    # Adjust base capacity fractions for each country based on a selection parameter (select_countries)
    adj_country_cf_sf = {iso: base_country_cf_sf[iso] * select_countries[iso] for iso in base_country_cf_sf}

    # Convert adjusted country capacity fractions to use integer keys instead of ISO country codes
    country_cf_sf = {int(iso_to_int_mp[iso]): adj_country_cf_sf[iso] for iso in adj_country_cf_sf}
    
    "Define Multi Stage Optimization Parameters"
    
    # Define the years to be optimized for multi-stage
    first_year_mf_1 = 2030
    first_year_mf_2 = 2040
    first_year_mf_3 = 2050

    # Define the development fractions for each year
    dev_frac_mf_1 = 0.3056
    dev_frac_mf_2 = 0.7115
    dev_frac_mf_3 = 1.00
    
    if cross_border == 0:
        base_country_cf_mf = base_country_cf_sf_n
    elif cross_border == 1:
        base_country_cf_mf = base_country_cf_sf_i

    # Calculate base capacity fractions for 2030 and 2040 using development fractions
    base_country_cf_mf_1 = {country: dev_frac_mf_1 * cf for country, cf in base_country_cf_mf.items()}
    base_country_cf_mf_2 = {country: dev_frac_mf_2 * cf for country, cf in base_country_cf_mf.items()}
    base_country_cf_mf_3 = {country: dev_frac_mf_3 * cf for country, cf in base_country_cf_mf.items()}

    # Adjust base capacity fractions for each country based on a selection parameter (select_countries)
    adj_country_cf_mf_1 = {iso: base_country_cf_mf_1[iso] * select_countries[iso] for iso in base_country_cf_mf_1}
    adj_country_cf_mf_2 = {iso: base_country_cf_mf_2[iso] * select_countries[iso] for iso in base_country_cf_mf_2}
    adj_country_cf_mf_3 = {iso: base_country_cf_mf_3[iso] * select_countries[iso] for iso in base_country_cf_mf_3}

    # Convert adjusted country capacity fractions to use integer keys instead of ISO country codes
    country_cf_mf_1 = {int(iso_to_int_mp[iso]): adj_country_cf_mf_1[iso] for iso in adj_country_cf_mf_1}
    country_cf_mf_2 = {int(iso_to_int_mp[iso]): adj_country_cf_mf_2[iso] for iso in adj_country_cf_mf_2}
    country_cf_mf_3 = {int(iso_to_int_mp[iso]): adj_country_cf_mf_3[iso] for iso in adj_country_cf_mf_3}

    """
    Process data
    """
    print("Processing data...")
    
    # Load datasets
    wf_dataset_file = os.path.join(workspace_folder, 'wf_data.npy')
    eh_dataset_file = os.path.join(workspace_folder, 'eh_data.npy')
    onss_dataset_file = os.path.join(workspace_folder, 'onss_data.npy')
    
    wf_dataset = np.load(wf_dataset_file, allow_pickle=True)
    eh_dataset = np.load(eh_dataset_file, allow_pickle=True)
    onss_dataset = np.load(onss_dataset_file, allow_pickle=True)

    # Component identifiers
    wf_ids = [int(data[0]) for data in wf_dataset]
    eh_ids = [int(data[0]) for data in eh_dataset]
    onss_ids = [int(data[0]) for data in onss_dataset]

    # Wind farm data
    wf_iso, wf_lon, wf_lat, wf_cap, wf_cost_1, wf_cost_2, wf_cost_3 = {}, {}, {}, {}, {}, {}, {}

    for data in wf_dataset:
        id = int(data[0])
        wf_iso[id] = iso_to_int_mp[data[1]]
        wf_lon[id] = float(data[2])
        wf_lat[id] = float(data[3])
        wf_cap[id] = float(data[4])
        wf_cost_1[id] = float(data[5])
        wf_cost_2[id] = float(data[6])
        wf_cost_3[id] = float(data[7])

    # Offshore substation data
    eh_iso, eh_lon, eh_lat, eh_wdepth, eh_icover, eh_pdist = {}, {}, {}, {}, {}, {}

    for data in eh_dataset:
        id = int(data[0])
        eh_iso[id] = iso_to_int_mp[data[1]]
        eh_lon[id] = float(data[2])
        eh_lat[id] = float(data[3])
        eh_wdepth[id] = int(data[4])
        eh_icover[id] = int(data[5])
        eh_pdist[id] = float(data[6])
    
    # Onshore substation data
    onss_iso, onss_lon, onss_lat, onss_thold = {}, {}, {}, {}

    for data in onss_dataset:
        id = int(data[0])
        onss_iso[id] = iso_to_int_mp[data[1]]
        onss_lon[id] = float(data[2])
        onss_lat[id] = float(data[3])
        onss_thold[id] = float(data[4])

    """
    Define model parameters
    """
    print("Defining model parameters...")
    
    # Identifiers model components
    model.wf_ids = Set(initialize=wf_ids)
    model.eh_ids = Set(initialize=eh_ids)
    model.onss_ids = Set(initialize=onss_ids)
    
    # Define the set of countries based on the ISO codes
    model.country_ids = Set(initialize=iso_to_int_mp.values())
    
    # Wind farm model parameters
    model.wf_iso = Param(model.wf_ids, initialize=wf_iso, within=NonNegativeIntegers)
    model.wf_lon = Param(model.wf_ids, initialize=wf_lon, within=NonNegativeReals)
    model.wf_lat = Param(model.wf_ids, initialize=wf_lat, within=NonNegativeReals)
    model.wf_cap = Param(model.wf_ids, initialize=wf_cap, within=NonNegativeIntegers)

    model.wf_cost = Param(model.wf_ids, initialize=wf_cost_1, within=NonNegativeReals, mutable=True)
    model.wf_cost_1 = Param(model.wf_ids, initialize=wf_cost_1, within=NonNegativeReals)
    model.wf_cost_2 = Param(model.wf_ids, initialize=wf_cost_2, within=NonNegativeReals)
    model.wf_cost_3 = Param(model.wf_ids, initialize=wf_cost_3, within=NonNegativeReals)

    # Offshore substation model parameters
    model.eh_iso = Param(model.eh_ids, initialize=eh_iso, within=NonNegativeIntegers)
    model.eh_lon = Param(model.eh_ids, initialize=eh_lon, within=NonNegativeReals)
    model.eh_lat = Param(model.eh_ids, initialize=eh_lat, within=NonNegativeReals)
    model.eh_wdepth = Param(model.eh_ids, initialize=eh_wdepth, within=NonNegativeIntegers)
    model.eh_icover = Param(model.eh_ids, initialize=eh_icover, within=Binary)
    model.eh_pdist = Param(model.eh_ids, initialize=eh_pdist, within=NonNegativeIntegers)

    # Onshore substation model parameters
    model.onss_iso = Param(model.onss_ids, initialize=onss_iso, within=NonNegativeIntegers)
    model.onss_lon = Param(model.onss_ids, initialize=onss_lon, within=NonNegativeReals)
    model.onss_lat = Param(model.onss_ids, initialize=onss_lat, within=NonNegativeReals)
    model.onss_thold = Param(model.onss_ids, initialize=onss_thold, within=NonNegativeIntegers)

    # Define parameters for capacity fractions for each year
    model.country_cf = Param(model.country_ids, initialize=country_cf_sf, within=NonNegativeReals, mutable=True)
    # Single stage
    model.country_cf_sf = Param(model.country_ids, initialize=country_cf_sf, within=NonNegativeReals)
    # Multi stage
    model.country_cf_mf_1 = Param(model.country_ids, initialize=country_cf_mf_1, within=NonNegativeReals)
    model.country_cf_mf_2 = Param(model.country_ids, initialize=country_cf_mf_2, within=NonNegativeReals)
    model.country_cf_mf_3 = Param(model.country_ids, initialize=country_cf_mf_3, within=NonNegativeReals)
    
    # Define the first years
    model.first_year = Param(initialize=first_year_sf, within=NonNegativeIntegers, mutable=True)
    # Single stage
    model.first_year_sf = Param(initialize=first_year_sf, within=NonNegativeIntegers)
    # Multi stage
    model.first_year_mf_1 = Param(initialize=first_year_mf_1, within=NonNegativeIntegers)
    model.first_year_mf_2 = Param(initialize=first_year_mf_2, within=NonNegativeIntegers)
    model.first_year_mf_3 = Param(initialize=first_year_mf_3, within=NonNegativeIntegers)

    """
    Define decision variables
    """
    print("Defining decision variables...")
    
    # Calculate viable connections
    viable_ec1 = find_viable_ec1(wf_lon, wf_lat, eh_lon, eh_lat)
    viable_ec2 = find_viable_ec2(eh_lon, eh_lat, onss_lon, onss_lat)
    viable_ec3 = find_viable_ec3(wf_lon, wf_lat, onss_lon, onss_lat)
    viable_onc = find_viable_onc(onss_lon, onss_lat)
    
    model.viable_ec1_ids = Set(initialize=viable_ec1, dimen=2)
    model.viable_ec2_ids = Set(initialize=viable_ec2, dimen=2)
    model.viable_ec3_ids = Set(initialize=viable_ec3, dimen=2)
    model.viable_onc_ids = Set(initialize=viable_onc, dimen=2)
    
    # Calculate viable entities based on the viable connections
    model.viable_wf_ids, model.viable_eh_ids, model.viable_onss_ids = get_viable_entities(viable_ec1, viable_ec2, viable_ec3)
    
    # Initialize variables without time index for capacity
    model.wf_cap_var = Var(model.viable_wf_ids, within=NonNegativeReals)
    model.onss_cap_var = Var(model.viable_onss_ids, within=NonNegativeReals)
    model.onc_cap_var = Var(model.viable_onc_ids, within=NonNegativeReals)
    
    if model_type == 0: # Point-to-point connections
        model.eh_cap_var = Var(model.viable_eh_ids, within=NonNegativeReals, bounds=(0, 0))
        model.ec1_cap_var = Var(model.viable_ec1_ids, within=NonNegativeReals, bounds=(0, 0))
        model.ec2_cap_var = Var(model.viable_ec2_ids, within=NonNegativeReals, bounds=(0, 0))
        model.ec3_cap_var = Var(model.viable_ec3_ids, within=NonNegativeReals)
    elif model_type == 1: # Hub-and-spoke connections
        model.eh_cap_var = Var(model.viable_eh_ids, within=NonNegativeReals)
        model.ec1_cap_var = Var(model.viable_ec1_ids, within=NonNegativeReals)
        model.ec2_cap_var = Var(model.viable_ec2_ids, within=NonNegativeReals)
        model.ec3_cap_var = Var(model.viable_ec3_ids, within=NonNegativeReals, bounds=(0, 0))
    elif model_type == 2: # Combined connections
        model.eh_cap_var = Var(model.viable_eh_ids, within=NonNegativeReals)
        model.ec1_cap_var = Var(model.viable_ec1_ids, within=NonNegativeReals)
        model.ec2_cap_var = Var(model.viable_ec2_ids, within=NonNegativeReals)
        model.ec3_cap_var = Var(model.viable_ec3_ids, within=NonNegativeReals)

    model.onss_cost_var = Var(model.viable_onss_ids, within=NonNegativeReals)

    model.wf_country_alloc_var = Var(model.viable_wf_ids, model.country_ids, within=NonNegativeReals)
    
    # Define the binary variable for each energy hub
    model.eh_active_bin_var = Var(model.viable_eh_ids, within=Binary)
    
    # Ensure the results directory exists
    results_dir = os.path.join(workspace_folder, "results", "combined")
    if not os.path.exists(results_dir):
        os.makedirs(results_dir)
    
    tpe = ["d", "hs", "c"][model_type]
    crb = ["n", "in"][cross_border]
    stg = ["sf", "mf"][multi_stage]
    
    # Print total available wind farm capacity per country
    print("Total available wind farm capacity per country:")
    for country, country_code in iso_to_int_mp.items():
        total_capacity = sum(wf_cap[wf] for wf in wf_ids if wf_iso[wf] == country_code)
        print(f"{country}: {total_capacity} MW")
    
    # Create a DataFrame for variable counts
    variable_counts_df = pd.DataFrame({
        "Variable": [
            "wf_cost_var", 
            "eh_cost_var", 
            "onss_cost_var", 
            "ec1_cost_var", 
            "ec2_cost_var", 
            "ec3_cost_var", 
            "onc_cost_var", 
            "wf_country_alloc_var", 
            "eh_active_bin_var"
        ],
        "Count": [
            len(model.viable_wf_ids),
            len(model.viable_eh_ids),
            len(model.viable_onss_ids),
            len(model.viable_ec1_ids),
            len(model.viable_ec2_ids),
            len(model.viable_ec3_ids),
            len(model.viable_onc_ids),
            len(model.viable_wf_ids) * len(model.country_ids),
            len(model.viable_eh_ids)
        ]
    })

    # Define file path and save to Excel
    variable_counts_df.to_excel(os.path.join(results_dir, f'r_{stg}_{tpe}_{crb}_variable_counts.xlsx'), index=False)
    print(f'Saved variable counts as .xlsx')

    # Create and write the note to a text file
    with open(os.path.join(results_dir, f'r_{stg}_{tpe}_{crb}_note.txt'), 'w') as file:
        file.write(note_to_write)
    print(f'Saved note as .txt')

    """
    Define Expressions
    """
    print("Defining expressions...")

    """
    Define expressions for wind farms (WF)
    """
    def wf_cost_rule(model, wf):
        return sf_wf * wf_cost_lin(model.wf_cost[wf], model.wf_cap[wf], model.wf_cap_var[wf])
    model.wf_cost_exp = Expression(model.viable_wf_ids, rule=wf_cost_rule)

    """
    Define distance and capacity expressions for Inter-Array Cables (IAC)
    """
    def ec1_distance_rule(model, wf, eh):
        return haversine(model.wf_lon[wf], model.wf_lat[wf], model.eh_lon[eh], model.eh_lat[eh])
    model.ec1_dist_exp = Expression(model.viable_ec1_ids, rule=ec1_distance_rule)

    def ec1_cost_rule(model, wf, eh):
        return sf_ec1 * ec1_cost_fun(value(model.first_year), model.ec1_dist_exp[wf, eh], model.ec1_cap_var[wf, eh])
    model.ec1_cost_exp = Expression(model.viable_ec1_ids, rule=ec1_cost_rule)

    """
    Define expressions for the Energy Hub (EH) capacity
    """
    def eh_cost_rule_with_binary(model, eh):
        return sf_eh * eh_cost_lin(value(model.first_year), model.eh_wdepth[eh], model.eh_icover[eh], model.eh_pdist[eh], model.eh_cap_var[eh], model.eh_active_bin_var[eh])
    model.eh_cost_exp = Expression(model.viable_eh_ids, rule=eh_cost_rule_with_binary)

    """
    Define distance and capacity expressions for Export Cables (EC)
    """
    def ec2_distance_rule(model, eh, onss):
        return haversine(model.eh_lon[eh], model.eh_lat[eh], model.onss_lon[onss], model.onss_lat[onss])
    model.ec2_dist_exp = Expression(model.viable_ec2_ids, rule=ec2_distance_rule)

    def ec2_cost_rule(model, eh, onss):
        return sf_ec2 * ec2_cost_fun(value(model.first_year), model.ec2_dist_exp[eh, onss], model.ec2_cap_var[eh, onss])
    model.ec2_cost_exp = Expression(model.viable_ec2_ids, rule=ec2_cost_rule)

    """
    Define distance and capacity expressions for direct connections (WF to ONSS)
    """
    def ec3_distance_rule(model, wf, onss):
        return haversine(model.wf_lon[wf], model.wf_lat[wf], model.onss_lon[onss], model.onss_lat[onss])
    model.ec3_dist_exp = Expression(model.viable_ec3_ids, rule=ec3_distance_rule)

    def ec3_cost_rule(model, wf, onss):
        return sf_ec3 * ec3_cost_fun(value(model.first_year), model.ec3_dist_exp[wf, onss], model.ec3_cap_var[wf, onss])
    model.ec3_cost_exp = Expression(model.viable_ec3_ids, rule=ec3_cost_rule)

    """
    Define expressions for Onshore Substation (ONSS) capacity
    """
    def onss_cost_rule(model, onss):
        return sf_onss * onss_cost_lin(value(model.first_year), model.onss_cap_var[onss], model.onss_thold[onss])
    model.onss_cost_exp = Expression(model.viable_onss_ids, rule=onss_cost_rule)

    """
    Define expressions for Onshore Substation Cables (ONC)
    """
    def onc_distance_rule(model, onss1, onss2):
        return haversine(model.onss_lon[onss1], model.onss_lat[onss1], model.onss_lon[onss2], model.onss_lat[onss2])
    model.onc_dist_exp = Expression(model.viable_onc_ids, rule=onc_distance_rule)

    def onc_cost_rule(model, onss1, onss2):
        return sf_onc * onc_cost_fun(value(model.first_year), model.onc_dist_exp[onss1, onss2], model.onc_cap_var[onss1, onss2])
    model.onc_cost_exp = Expression(model.viable_onc_ids, rule=onc_cost_rule)

    """
    Define Constraints
    """
    print("Defining capacity allocation constraints...")

    if cross_border == 1:
        def wf_country_cap_rule(model, country):
            """
            Wind Farm Capacity Allocation Constraint (National)
            
            Ensures that each country is assigned enough capacity from the country's total available wind farm capacity to meet its required minimum.
            """
            min_req_cap_country = model.country_cf[country] * sum(model.wf_cap[wf] for wf in model.viable_wf_ids if model.wf_iso[wf] == country)
            cap_country = sum(model.wf_country_alloc_var[wf, country] for wf in model.viable_wf_ids)
            return cap_country >= min_req_cap_country
        model.wf_country_cap_con = Constraint(model.country_ids, rule=wf_country_cap_rule)
    elif cross_border == 0:
        def wf_country_cap_rule(model, country):
            """
            Wind Farm Capacity Allocation Constraint (International)
            
            Ensures that each country is assigned enough capacity from the total available wind farm capacity to meet its required minimum.
            """
            min_req_cap_country = model.country_cf[country] * sum(model.wf_cap[wf] for wf in model.viable_wf_ids if model.wf_iso[wf] == country)
            cap_country = sum(model.wf_country_alloc_var[wf, country] for wf in model.viable_wf_ids if model.wf_iso[wf] == country)
            return cap_country >= min_req_cap_country
        model.wf_country_cap_con = Constraint(model.country_ids, rule=wf_country_cap_rule)
    
    def wf_alloc_rule(model, wf):
        """
        Wind Farm Capacity Constraint
        
        Ensures that each wind farm's total assigned capacity equals its selected wind farm capacity.
        """
        return sum(model.wf_country_alloc_var[wf, country] for country in model.country_ids) == model.wf_cap_var[wf]
    model.wf_alloc_con = Constraint(model.viable_wf_ids, rule=wf_alloc_rule)

    def wf_cap_rule(model, wf):
        """
        Wind Farm Capacity Limit Constraint
        
        Ensures that each wind farm's selected capacity does not exceed its total available capacity.
        """
        return model.wf_cap_var[wf] <= model.wf_cap[wf]
    model.wf_cap_con = Constraint(model.viable_wf_ids, rule=wf_cap_rule)

    print("Defining network constraints...")
    
    def wf_connection_rule(model, wf, country):
        """
        Wind Farm Network Constraint
        
        Ensures that each wind farm's assigned capacities are connected to the corresponding country's energy hub or onshore substation.
        """
        connect_to_eh = sum(model.ec1_cap_var[wf, eh] for eh in model.viable_eh_ids if (wf, eh) in model.viable_ec1_ids and model.eh_iso[eh] == country)
        connect_to_onss = sum(model.ec3_cap_var[wf, onss] for onss in model.viable_onss_ids if (wf, onss) in model.viable_ec3_ids and model.onss_iso[onss] == country)
        return connect_to_eh + connect_to_onss >= model.wf_country_alloc_var[wf, country]
    model.wf_connection_con = Constraint(model.viable_wf_ids, model.country_ids, rule=wf_connection_rule)

    def eh_cap_connect_rule(model, eh):
        """
        Energy Hub Capacity Constraint
        
        Ensures that each energy hub's capacity matches or exceeds the total connected wind farm capacity.
        """
        connect_from_wf = sum(model.ec1_cap_var[wf, eh] for wf in model.viable_wf_ids if (wf, eh) in model.viable_ec1_ids)
        return model.eh_cap_var[eh] >= connect_from_wf
    model.eh_cap_connect_con = Constraint(model.viable_eh_ids, rule=eh_cap_connect_rule)

    def max_eh_cap_rule(model, eh):
        """
        Energy Hub Capacity Limit Constraint
        
        Ensures that each energy hub's capacity does not exceed a specified capacity limit.
        """
        return model.eh_cap_var[eh] <= eh_cap_lim
    model.max_eh_cap_con = Constraint(model.viable_eh_ids, rule=max_eh_cap_rule)
    
    def eh_active_rule(model, eh):
        """
        Energy Hub Activation Constraint
        
        Ensures that the energy hub's total cost can only be positive if its capacity is greater than zero.
        """
        return model.eh_cap_var[eh] <= model.eh_active_bin_var[eh] * eh_cap_lim + zero_th
    model.eh_cap_to_active_con = Constraint(model.viable_eh_ids, rule=eh_active_rule)

    def eh_to_onss_connection_rule(model, eh):
        """
        Energy Hub Network Constraint
        
        Ensures that each energy hub's capacity is connected to the corresponding country's onshore substation.
        """
        country = model.eh_iso[eh]
        connect_to_onss = sum(model.ec2_cap_var[eh, onss] for onss in model.viable_onss_ids if (eh, onss) in model.viable_ec2_ids and model.onss_iso[onss] == country)
        return connect_to_onss >= model.eh_cap_var[eh]
    model.eh_to_onss_connect_con = Constraint(model.viable_eh_ids, rule=eh_to_onss_connection_rule)

    def onss_cap_connect_rule(model, onss):
        """
        Onshore Substation Capacity Constraint
        
        Ensures that each substation's capacity is at least equal to the net connected capacity of connected wind farms, energy hubs and other domestic substations.
        """
        country = model.onss_iso[onss]
        connect_from_eh = sum(model.ec2_cap_var[eh, onss] for eh in model.viable_eh_ids if (eh, onss) in model.viable_ec2_ids)
        connect_from_wf = sum(model.ec3_cap_var[wf, onss] for wf in model.viable_wf_ids if (wf, onss) in model.viable_ec3_ids)
        distribute_to_others = sum(model.onc_cap_var[onss, other_onss] for other_onss in model.viable_onss_ids if (onss, other_onss) in model.viable_onc_ids and model.onss_iso[other_onss] == country)
        receive_from_others = sum(model.onc_cap_var[other_onss, onss] for other_onss in model.viable_onss_ids if (other_onss, onss) in model.viable_onc_ids and model.onss_iso[other_onss] == country)
        
        return model.onss_cap_var[onss] >= connect_from_eh + connect_from_wf + receive_from_others - distribute_to_others
    model.onss_cap_connect_con = Constraint(model.viable_onss_ids, rule=onss_cap_connect_rule)

    print("Defining capacity limit constraints...")
    
    def max_onss_cap_rule(model, onss):
        """
        Onshore Substation Capacity Limit Constraint
        
        Ensures that each substation's capacity does not exceed a specified factor of its threshold value.
        """
        return model.onss_cap_var[onss] <= onss_cap_lim_fac * model.onss_thold[onss]
    model.max_onss_cap_con = Constraint(model.viable_onss_ids, rule=max_onss_cap_rule)
    
    print("Defining cost constraints...")
    
    def onss_cost_rule(model, onss):
        """
        Onshore Substation Cost Variable Constraint
        
        Ensures that the substation's total cost in non-negative.
        """
        return model.onss_cost_var[onss] >= model.onss_cost_exp[onss]
    model.onss_cost_con = Constraint(model.viable_onss_ids, rule=onss_cost_rule)
    
    """
    Define Objective function
    """
    print("Defining objective function...")

    def global_cost_rule(model):
        """
        Calculate the total cost of the energy system for a specific year.
        This includes the cost of selecting and connecting wind farms, energy hubs, and onshore substations.
        The objective is to minimize this total cost for each year separately.
        """
        wf_total_cost = sum(model.wf_cost_exp[wf] for wf in model.viable_wf_ids)
        eh_total_cost = sum(model.eh_cost_exp[eh] for eh in model.viable_eh_ids)
        onss_total_cost = sum(model.onss_cost_var[onss] for onss in model.viable_onss_ids)
        ec1_total_cost = sum(model.ec1_cost_exp[wf, eh] for (wf, eh) in model.viable_ec1_ids)
        ec2_total_cost = sum(model.ec2_cost_exp[eh, onss] for (eh, onss) in model.viable_ec2_ids)
        ec3_total_cost = sum(model.ec3_cost_exp[wf, onss] for (wf, onss) in model.viable_ec3_ids)
        onc_total_cost = sum(model.onc_cost_exp[onss1, onss2] for (onss1, onss2) in model.viable_onc_ids)
        
        onss_total_cap_aux = sum(model.onss_cap_var[onss] for onss in model.viable_onss_ids) # Ensures that the onss capacity is zero when not connected
        
        total_cost = wf_total_cost + eh_total_cost + ec1_total_cost + ec2_total_cost + ec3_total_cost + onss_total_cost + onc_total_cost + onss_total_cap_aux

        return total_cost
    model.global_cost_obj = Objective(rule=global_cost_rule, sense=minimize)

    """
    Solve the model
    """
    print("Solving the model...")
    
    # Set the path to the SCIP solver executable
    scip_path = "C:\\Program Files\\SCIPOptSuite 9.0.0\\bin\\scip.exe"
    
    # Write options to a parameter file
    param_file_path = os.path.join(workspace_folder, "scip_params.set")
    
    # Create solver object and specify the solver executable path
    solver = SolverFactory('scip', executable=scip_path)
    
    with open(param_file_path, 'w') as param_file:
        for key, val in solver_options.items():
            param_file.write(f"{key} = {val}\n")

    def rnd_f(e):
            return round(value(e), 6)
    
    def nearest_wt_cap(cap):
        """
        Round up the capacity to the nearest multiple of the wind turbine capacity.
        """
        return int(np.ceil(value(cap) / wt_cap)) * wt_cap
    
    def save_results(model, year, prev_capacity):
        """
        Save the IDs of selected components of the optimization model along with all their corresponding parameters,
        including directly retrieved capacity and cost from the model expressions, into both .npy and Excel files as structured arrays.

        Parameters:
        - model: The optimized Pyomo model.
        - workspace_folder: The path to the directory where results will be saved.
        - year: The year for which the results are being saved.
        """

        # Mapping ISO country codes of Baltic Sea countries to unique integers
        int_to_iso_mp = {
            1: 'DE',  # Germany
            2: 'DK',  # Denmark
            3: 'EE',  # Estonia
            4: 'FI',  # Finland
            5: 'LV',  # Latvia
            6: 'LT',  # Lithuania
            7: 'PL',  # Poland
            8: 'SE'   # Sweden
        }

        selected_components = {}

        # Define and aggregate data for wind farms
        wf_data = []
        for wf in model.viable_wf_ids:
            if value(model.wf_cap_var[wf]) > zero_th:
                wf_id = wf
                wf_iso = int_to_iso_mp[int(model.wf_iso[wf])]
                wf_lon = model.wf_lon[wf]
                wf_lat = model.wf_lat[wf]
                wf_capacity = rnd_f(model.wf_cap_var[wf])
                wf_cap_diff = wf_capacity - prev_capacity.get('wf_cap_var', {}).get(wf, 0)
                wf_rate = rnd_f(value(wf_capacity) / value(model.wf_cap[wf]))
                wf_cost_param = {2030: model.wf_cost_1, 2040: model.wf_cost_2, 2050: model.wf_cost_3}.get(value(model.first_year_sf))
                if linear_result == 1:
                    wf_cost = sf_wf * rnd_f(value(wf_cap_diff) / value(model.wf_cap[wf]) * value(model.wf_cost[wf]))
                    wf_cost_sf = sf_wf * rnd_f(value(model.wf_cap_var[wf]) / value(model.wf_cap[wf]) * value(wf_cost_param[wf]))
                if linear_result == 0:
                    wf_cost = sf_wf * rnd_f(nearest_wt_cap(wf_cap_diff) / value(model.wf_cap[wf]) * value(model.wf_cost[wf]))
                    wf_cost_sf = sf_wf * rnd_f(nearest_wt_cap(model.wf_cap_var[wf]) / value(model.wf_cap[wf]) * value(wf_cost_param[wf]))
                wf_data.append((wf_id, wf_iso, wf_lon, wf_lat, wf_capacity, wf_cost, wf_rate, wf_cost_sf))

        selected_components['wf_ids'] = {
            'data': np.array(wf_data, dtype=[('id', int), ('iso', 'U2'), ('lon', float), ('lat', float), ('capacity', int), ('cost', float), ('rate', float), ('cost_sf', float)]),
            'headers': "ID, ISO, Longitude, Latitude, Capacity, Cost, Rate, Cost SF"
        }

        # Define and aggregate data for energy hubs
        eh_data = []
        for eh in model.viable_eh_ids:
            if value(model.eh_cap_var[eh]) > zero_th:
                eh_id = eh
                eh_iso = int_to_iso_mp[int(model.eh_iso[eh])]
                eh_lon = model.eh_lon[eh]
                eh_lat = model.eh_lat[eh]
                eh_water_depth = model.eh_wdepth[eh]
                eh_ice_cover = model.eh_icover[eh]
                eh_port_dist = model.eh_pdist[eh]
                eh_capacity = rnd_f(model.eh_cap_var[eh])
                eh_cap_diff = eh_capacity - prev_capacity.get('eh_cap_var', {}).get(eh, 0)
                eh_cost = sf_eh * rnd_f(eh_cost_lin(value(model.first_year), model.eh_wdepth[eh], model.eh_icover[eh], model.eh_pdist[eh], eh_cap_diff, model.eh_active_bin_var[eh]))
                eh_cost_sf = sf_eh * rnd_f(eh_cost_lin(value(model.first_year_sf), model.eh_wdepth[eh], model.eh_icover[eh], model.eh_pdist[eh], value(model.eh_cap_var[eh]), model.eh_active_bin_var[eh]))
                eh_data.append((eh_id, eh_iso, eh_lon, eh_lat, eh_water_depth, eh_ice_cover, eh_port_dist, eh_capacity, eh_cost, eh_cost_sf))

        selected_components['eh_ids'] = {
            'data': np.array(eh_data, dtype=[('id', int), ('iso', 'U2'), ('lon', float), ('lat', float), ('water_depth', int), ('ice_cover', int), ('port_dist', int), ('capacity', float), ('cost', float), ('cost_sf', float)]),
            'headers': "ID, ISO, Longitude, Latitude, Water Depth, Ice Cover, Port Distance, Capacity, Cost, Cost SF"
        }

        # Define and aggregate data for onshore substations
        onss_data = []
        for onss in model.viable_onss_ids:
            if value(model.onss_cap_var[onss]) > zero_th:
                onss_id = onss
                onss_iso = int_to_iso_mp[int(model.onss_iso[onss])]
                onss_lon = model.onss_lon[onss]
                onss_lat = model.onss_lat[onss]
                onss_threshold = model.onss_thold[onss]
                onss_capacity = rnd_f(model.onss_cap_var[onss])
                onss_cap_diff = onss_capacity - prev_capacity.get('onss_ids', {}).get(onss, 0)
                onss_cost = sf_onss * rnd_f(max(0, onss_cost_lin(value(model.first_year), onss_cap_diff, model.onss_thold[onss])))
                onss_cost_sf = sf_onss * rnd_f(max(0, onss_cost_lin(value(model.first_year_sf), value(model.onss_cap_var[onss]), value(model.onss_thold[onss]))))
                onss_data.append((onss_id, onss_iso, onss_lon, onss_lat, onss_threshold, onss_capacity, onss_cost, onss_cost_sf))

        selected_components['onss_ids'] = {
            'data': np.array(onss_data, dtype=[('id', int), ('iso', 'U2'), ('lon', float), ('lat', float), ('threshold', int), ('capacity', float), ('cost', float), ('cost_sf', float)]),
            'headers': "ID, ISO, Longitude, Latitude, Threshold, Capacity, Cost, Cost SF"
        }

        # Export cable ID counter
        ec_id_counter = 1

        # Create ec1_ids with export cable ID, single row for each cable
        ec1_data = []
        for wf, eh in model.viable_ec1_ids:
            if value(model.ec1_cap_var[wf, eh]) > zero_th:
                ec1_cap = rnd_f(model.ec1_cap_var[wf, eh])
                ec1_cap_diff = ec1_cap - prev_capacity.get('ec1_cap_var', {}).get((wf, eh), 0)
                dist1 = rnd_f(haversine(model.wf_lon[wf], model.wf_lat[wf], model.eh_lon[eh], model.eh_lat[eh]))
                if linear_result == 1:
                    ec1_cost_sf = sf_ec1 * rnd_f(ec1_cost_fun(value(model.first_year_sf), dist1, value(model.ec1_cap_var[wf, eh]), "lin"))
                    ec1_cost = sf_ec1 * rnd_f(ec1_cost_fun(value(model.first_year), dist1, ec1_cap_diff, "lin"))
                if linear_result == 0:
                    ec1_cost_sf = sf_ec1 * rnd_f(ec1_cost_fun(value(model.first_year_sf), dist1, value(model.ec1_cap_var[wf, eh]), "ceil"))
                    ec1_cost = sf_ec1 * rnd_f(ec1_cost_fun(value(model.first_year), dist1, ec1_cap_diff, "ceil"))
                ec1_data.append((ec_id_counter, int_to_iso_mp[int(model.eh_iso[eh])], wf, eh, model.wf_lon[wf], model.wf_lat[wf], model.eh_lon[eh], model.eh_lat[eh], dist1, ec1_cap, ec1_cost, ec1_cost_sf))
                ec_id_counter += 1

        selected_components['ec1_ids'] = {
            'data': np.array(ec1_data, dtype=[('ec_id', int), ('iso', 'U2'), ('comp_1_id', int), ('comp_2_id', int), ('lon_1', float), ('lat_1', float), ('lon_2', float), ('lat_2', float), ('distance', float), ('capacity', float), ('cost', float), ('cost_sf', float)]),
            'headers': "EC_ID, ISO, Comp_1_ID, Comp_2_ID, Lon_1, Lat_1, Lon_2, Lat_2, Distance, Capacity, Cost, Cost SF"
        }

        # Create ec2_ids with export cable ID, single row for each cable
        ec2_data = []
        ec_id_counter = 1
        for eh, onss in model.viable_ec2_ids:
            if value(model.ec2_cap_var[eh, onss]) > zero_th:
                ec2_cap = rnd_f(model.ec2_cap_var[eh, onss])
                ec2_cap_diff = ec2_cap - prev_capacity.get('ec2_cap_var', {}).get((eh, onss), 0)
                dist2 = rnd_f(haversine(model.eh_lon[eh], model.eh_lat[eh], model.onss_lon[onss], model.onss_lat[onss]))
                if linear_result == 1:
                    ec2_cost = sf_ec2 * rnd_f(ec2_cost_fun(value(model.first_year), dist2, ec2_cap_diff, "lin"))
                    ec2_cost_sf = sf_ec2 * rnd_f(ec2_cost_fun(value(model.first_year_sf), dist2, value(model.ec2_cap_var[eh, onss]), "lin"))
                if linear_result == 0:
                    ec2_cost = sf_ec2 * rnd_f(ec2_cost_fun(value(model.first_year), dist2, ec2_cap_diff, "ceil"))
                    ec2_cost_sf = sf_ec2 * rnd_f(ec2_cost_fun(value(model.first_year_sf), dist2, value(model.ec2_cap_var[eh, onss]), "ceil"))
                ec2_data.append((ec_id_counter, int_to_iso_mp[int(model.onss_iso[onss])], eh, onss, model.eh_lon[eh], model.eh_lat[eh], model.onss_lon[onss], model.onss_lat[onss], dist2, ec2_cap, ec2_cost, ec2_cost_sf))
                ec_id_counter += 1

        selected_components['ec2_ids'] = {
            'data': np.array(ec2_data, dtype=[('ec_id', int), ('iso', 'U2'), ('comp_1_id', int), ('comp_2_id', int), ('lon_1', float), ('lat_1', float), ('lon_2', float), ('lat_2', float), ('distance', float), ('capacity', float), ('cost', float), ('cost_sf', float)]),
            'headers': "EC_ID, ISO, Comp_1_ID, Comp_2_ID, Lon_1, Lat_1, Lon_2, Lat_2, Distance, Capacity, Cost, Cost SF"
        }

        # Create ec3_ids with export cable ID, single row for each cable
        ec3_data = []
        ec_id_counter = 1
        for wf, onss in model.viable_ec3_ids:
            if value(model.ec3_cap_var[wf, onss]) > zero_th:
                ec3_cap = rnd_f(model.ec3_cap_var[wf, onss])
                ec3_cap_diff = ec3_cap - prev_capacity.get('ec3_cap_var', {}).get((wf, onss), 0)
                dist3 = rnd_f(haversine(model.wf_lon[wf], model.wf_lat[wf], model.onss_lon[onss], model.onss_lat[onss]))
                if linear_result == 1:
                    ec3_cost = sf_ec3 * rnd_f(ec3_cost_fun(value(model.first_year), dist3, ec3_cap_diff, "lin"))
                    ec3_cost_sf = sf_ec3 * rnd_f(ec3_cost_fun(value(model.first_year_sf), dist3, value(model.ec3_cap_var[wf, onss]), "lin"))
                if linear_result == 0:
                    ec3_cost = sf_ec3 * rnd_f(ec3_cost_fun(value(model.first_year), dist3, ec3_cap_diff, "ceil"))
                    ec3_cost_sf = sf_ec3 * rnd_f(ec3_cost_fun(value(model.first_year_sf), dist3, value(model.ec3_cap_var[wf, onss]), "ceil"))
                ec3_data.append((ec_id_counter, int_to_iso_mp[int(model.onss_iso[onss])], wf, onss, model.wf_lon[wf], model.wf_lat[wf], model.onss_lon[onss], model.onss_lat[onss], dist3, ec3_cap, ec3_cost, ec3_cost_sf))
                ec_id_counter += 1

        selected_components['ec3_ids'] = {
            'data': np.array(ec3_data, dtype=[('ec_id', int), ('iso', 'U2'), ('comp_1_id', int), ('comp_2_id', int), ('lon_1', float), ('lat_1', float), ('lon_2', float), ('lat_2', float), ('distance', float), ('capacity', float), ('cost', float), ('cost_sf', float)]),
            'headers': "EC_ID, ISO, Comp_1_ID, Comp_2_ID, Lon_1, Lat_1, Lon_2, Lat_2, Distance, Capacity, Cost, Cost SF"
        }

        # Create onc_ids with onshore cable ID, single row for each cable
        onc_data = []
        onc_id_counter = 1
        for onss1, onss2 in model.viable_onc_ids:
            if value(model.onc_cap_var[onss1, onss2]) is not None and value(model.onc_cap_var[onss1, onss2]) > zero_th:
                onc_cap = rnd_f(model.onc_cap_var[onss1, onss2])
                onc_cap_diff = onc_cap - prev_capacity.get('onc_ids', {}).get((onss1, onss2), 0)
                dist4 = rnd_f(haversine(model.onss_lon[onss1], model.onss_lat[onss1], model.onss_lon[onss2], model.onss_lat[onss2]))
                if linear_result == 1:
                    onc_cost = sf_onc * rnd_f(onc_cost_fun(value(model.first_year), dist4, onc_cap_diff, "lin"))
                    onc_cost_sf = sf_onc * rnd_f(onc_cost_fun(value(model.first_year_sf), dist4, value(model.onc_cap_var[onss1, onss2]), "lin"))
                if linear_result == 0:
                    onc_cost = sf_onc * rnd_f(onc_cost_fun(value(model.first_year), dist4, onc_cap_diff, "ceil"))
                    onc_cost_sf = sf_onc * rnd_f(onc_cost_fun(value(model.first_year_sf), dist4, value(model.onc_cap_var[onss1, onss2]), "ceil"))
                onc_data.append((onc_id_counter, int_to_iso_mp[int(model.onss_iso[onss1])], onss1, onss2, model.onss_lon[onss1], model.onss_lat[onss1], model.onss_lon[onss2], model.onss_lat[onss2], dist4, onc_cap, onc_cost, onc_cost_sf))
                onc_id_counter += 1

        selected_components['onc_ids'] = {
            'data': np.array(onc_data, dtype=[('ec_id', int), ('iso', 'U2'), ('comp_1_id', int), ('comp_2_id', int), ('lon_1', float), ('lat_1', float), ('lon_2', float), ('lat_2', float), ('distance', float), ('capacity', float), ('cost', float), ('cost_sf', float)]),
            'headers': "ONC_ID, ISO, Comp_1_ID, Comp_2_ID, Lon_1, Lat_1, Lon_2, Lat_2, Distance, Capacity, Cost, Cost SF"
        }

        # Save the .npy files and Excel files for each component
        for component, data in selected_components.items():
            # Save as .npy file
            npy_file_path = os.path.join(results_dir, f'r_{stg}_{tpe}_{crb}_{component}_{year}.npy')
            np.save(npy_file_path, data['data'])
            print(f'Saved {component} data as .npy')

            # Save as Excel file
            df = pd.DataFrame(data['data'])
            excel_file_path = os.path.join(results_dir, f'r_{stg}_{tpe}_{crb}_{component}_{year}.xlsx')
            df.to_excel(excel_file_path, index=False)
            print(f'Saved {component} data as .xlsx')

        # Calculate overall totals
        overall_totals = {'wf_ids': {'capacity': 0, 'cost': 0},
                        'eh_ids': {'capacity': 0, 'cost': 0},
                        'onss_ids': {'capacity': 0, 'cost': 0},
                        'ec1_ids': {'capacity': 0, 'cost': 0},
                        'ec2_ids': {'capacity': 0, 'cost': 0},
                        'ec3_ids': {'capacity': 0, 'cost': 0},
                        'onc_ids': {'capacity': 0, 'cost': 0},
                        'overall': {'capacity': 0, 'cost': 0}}

        for component, data in selected_components.items():
            for entry in data['data']:
                overall_totals[component]['capacity'] += entry['capacity']
                overall_totals[component]['cost'] += entry['cost']
            overall_totals['overall']['capacity'] += overall_totals[component]['capacity']
            overall_totals['overall']['cost'] += overall_totals[component]['cost']

        # Save the overall totals in an Excel file
        overall_df = pd.DataFrame([(component, rnd_f(values['capacity']), rnd_f(values['cost'])) for component, values in overall_totals.items()],
                                columns=["Component", "Total Capacity", "Total Cost"])
        total_excel_file_path = os.path.join(results_dir, f'r_{stg}_{tpe}_{crb}_global_{year}.xlsx')
        overall_df.to_excel(total_excel_file_path, index=False)
        print(f'Saved overall total capacities and cost as .xlsx')
        

    def solve_single_stage(model, workspace_folder):
        # Use country_cf_2050 for the single stage optimization
        country_cf_param = model.country_cf_sf
        year_param = value(model.first_year_sf)
        
        if year_param == 2030:
            wf_cost_param = model.wf_cost_1
        if year_param == 2040:     
            wf_cost_param = model.wf_cost_2
        if year_param == 2050:
            wf_cost_param = model.wf_cost_3     
        
        model.country_cf.store_values(country_cf_param)  # Update country_cf for the single stage optimization for 2050
        model.first_year.store_values(year_param)  # Update first_year
        model.wf_cost.store_values(wf_cost_param)
        
        # Initialize previous capacities dictionary with zero capacities (needed for save_results function)
        prev_capacity = {
            'onss_ids': {onss: 0 for onss in model.viable_onss_ids},
            'onc_ids': {(onss1, onss2): 0 for onss1, onss2 in model.viable_onc_ids}
        }

        # Path to the log file
        logfile_path = os.path.join(workspace_folder, "results", "combined", f"r_{stg}_{tpe}_{crb}_solverlog_{year_param}.txt")
        
        # Solve the model, passing the parameter file as an option
        results = solver.solve(model, tee=True, logfile=logfile_path, options=solver_options)
            
        # Detailed checking of solver results
        if results.solver.status == SolverStatus.ok:
            if results.solver.termination_condition == TerminationCondition.optimal:
                print(f"Solver found an optimal solution for {year_param}.")
            else:
                print(f"Solver stopped due to limit for {year_param}.")
                print(f"Objective value: {rnd_f(model.global_cost_obj)}")
            save_results(model, year_param, prev_capacity)
        elif results.solver.status == SolverStatus.error:
            print(f"Solver error occurred for {year_param}. Check solver log for more details.")
        elif results.solver.status == SolverStatus.warning:
            print(f"Solver finished with warnings for {year_param}. Results may not be reliable.")
        else:
            print(f"Unexpected solver status for {year_param}: {results.solver.status}. Check solver log for details.")

        print(f"Solver log for {year_param} saved to {os.path.join(workspace_folder, 'results', 'combined', 'c_solverlog_2050.txt')}")

    def enforce_increase_variables(model, prev_capacity):
        """
        Ensure that capacities only increase and not decrease between stages by adding constraints.
        """
        capacity_vars = {
            'onss_cap_var': model.onss_cap_var,
            'onc_cap_var': model.onc_cap_var,
            'wf_cap_var': model.wf_cap_var,
            'eh_cap_var': model.eh_cap_var,
            'ec1_cap_var': model.ec1_cap_var,
            'ec2_cap_var': model.ec2_cap_var,
            'ec3_cap_var': model.ec3_cap_var
        }
        
        for var_name, var in capacity_vars.items():
            for index in var:
                prev_cap = prev_capacity[var_name].get(index, 0)
                if prev_cap > zero_th:
                    var[index].setlb(prev_cap)

    def solve_multi_stage(model, workspace_folder):
        """
        Solve the model for multiple stages ensuring capacities only increase.
        """
        # Parameters for each stage
        country_cf_params = {
            first_year_mf_1: model.country_cf_mf_1,
            first_year_mf_2: model.country_cf_mf_2,
            first_year_mf_3: model.country_cf_mf_3
        }
        wf_cost_params = {
            first_year_mf_1: model.wf_cost_1,
            first_year_mf_2: model.wf_cost_2,
            first_year_mf_3: model.wf_cost_3
        }
        
        # Initial capacities
        prev_capacity = {
            'onss_cap_var': {onss: 0 for onss in model.viable_onss_ids},
            'onc_cap_var': {(onss1, onss2): 0 for onss1, onss2 in model.viable_onc_ids},
            'wf_cap_var': {wf: 0 for wf in model.viable_wf_ids},
            'eh_cap_var': {eh: 0 for eh in model.viable_eh_ids},
            'ec1_cap_var': {index: 0 for index in model.ec1_cap_var},
            'ec2_cap_var': {index: 0 for index in model.ec2_cap_var},
            'ec3_cap_var': {index: 0 for index in model.ec3_cap_var}
        }
        
        for year in [first_year_mf_1, first_year_mf_2, first_year_mf_3]:
            print(f"Solving for {year}...")
            
            model.country_cf.store_values(country_cf_params[year])
            model.first_year.store_values(year)
            model.wf_cost.store_values(wf_cost_params[year])
            
            logfile_path = os.path.join(workspace_folder, "results", "combined", f"r_{stg}_{tpe}_{crb}_solverlog_{year}.txt")
            results = solver.solve(model, tee=True, logfile=logfile_path, options=solver_options)
            
            if results.solver.status == SolverStatus.ok:
                status_msg = "optimal solution" if results.solver.termination_condition == TerminationCondition.optimal else "stopped due to limit"
                print(f"Solver found an {status_msg} for {year}.")
                save_results(model, year, prev_capacity)
                
                for var_name in prev_capacity.keys():
                    var = getattr(model, var_name)
                    prev_capacity[var_name] = {index: round(var[index].value) for index in var if var[index].value > zero_th}
                
                enforce_increase_variables(model, prev_capacity)
            else:
                status_msg = "error" if results.solver.status == SolverStatus.error else "warnings"
                print(f"Solver finished with {status_msg} for {year}. Results may not be reliable. Check solver log for more details.")
            
            print(f"Solver log for {year} saved to {logfile_path}")

    # Decide whether to run single stage or multistage optimization
    if multi_stage == 0:
        print(f"Performing single stage optimization for {first_year_sf}...")
        solve_single_stage(model, workspace_folder)
    elif multi_stage == 1:
        print(f"Performing multistage optimization for {first_year_mf_1}, {first_year_mf_2}, and {first_year_mf_3}...")
        solve_multi_stage(model, workspace_folder)

    return None

# Define the main block
if __name__ == "__main__":
    # Specify the workspace folder
    workspace_folder = "C:\\Users\\cflde\\Documents\\Graduation Project\\ArcGIS Pro\\BalticSea\\Results\\datasets"

    # Call the optimization model function
    opt_model(workspace_folder)