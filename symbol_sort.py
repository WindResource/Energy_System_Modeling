# List of symbols and definitions (for reference)
symbols_definitions = [
    ("A_{wb}", "Weibull scale parameter, in meters per second"),
    ("D", "Distance between points, in kilometers"),
    ("Delta v", "Step size between wind speeds, in meters per second"),
    ("D_p", "Distance to the closest port, in kilometers"),
    ("D_{wt}", "Wind turbine rotor diameter, in meters"),
    ("E", "Electrical energy, in megawatt-hours"),
    ("F_i", "Contribution to energy production at wind speed v_i, in megawatts"),
    ("H", "Height parameter, in meters"),
    ("I_c", "Binary indicator variable for ice cover presence"),
    ("K_{max}", "Capacity limit factor"),
    ("K_{vs}", "Vessel's loading capacity, in units per lift"),
    ("L_c", "Length of a cable, in kilometers"),
    ("N_c", "Number of parallel cables"),
    ("P", "Power capacity parameter, in megawatts"),
    ("P_F", "Power factor"),
    ("\\Phi^{(s)}", "Progression level for stage s"),
    ("P_i", "Geographic coordinates of point P_i, in radians"),
    ("P_{th}", "Capacity threshold, in megawatts"),
    ("R", "Power capacity ratio"),
    ("R_{d,vs}", "Vessel's day rate, in thousands of euros per day"),
    ("R_E", "Radius of the Earth, in kilometers"),
    ("S", "Spacing, in meters or kilometers"),
    ("T_y", "Hours in a year"),
    ("Y", "Year"),
    ("Z", "Buffer zone, in kilometers"),
    ("C", "Cost parameter, in millions of euros"),
    ("\\mathcal{C}", "Set of all countries within the scope of the study"),
    ("\\mathcal{G}", "Set of all feasible energy system components within the system"),
    ("\\mathcal{N}", "Set of feasible wind farms, energy hubs or onshore substations within the system"),
    ("\\mathcal{V}", "Set of feasible export, or onshore cables within the system"),
    ("\\mathbb{R}_{geq 0}", "Set of non-negative real numbers"),
    ("c", "Cost variable, in millions of euros"),
    ("f_{pdf}", "Probability Density Function"),
    ("k", "Coefficient or factor"),
    ("k_{ice}", "Ice cover cost factor"),
    ("k_{wb}", "Weibull shape parameter"),
    ("n", "Natural number"),
    ("r", "Discount rate"),
    ("s", "Stage in the multi-stage optimization model"),
    ("v", "Speed parameter, in meters per second"),
    ("v_{cut-in}", "Cut-in wind speed for wind turbine, in meters per second"),
    ("v_{cut-out}", "Cut-out wind speed for wind turbine, in meters per second"),
    ("y", "Year"),
    ("\\alpha", "Power law exponent"),
    ("\\alpha_{wf}", "Wind farm power capacity allocation variable, in megawatts"),
    ("\\beta_{eh}", "Energy hub activation variable"),
    ("\\epsilon_0", "Zero threshold parameter"),
    ("\\lambda_i", "Longitude of point P_i, in radians"),
    ("\\phi_i", "Latitude of point P_i, in radians")
]

# List of abbreviations and definitions (provided in the tables)
abbreviations = [
    # ("DE", "Germany"),
    # ("DK", "Denmark"),
    # ("EE", "Estonia"),
    # ("FI", "Finland"),
    # ("LT", "Lithuania"),
    # ("LV", "Latvia"),
    # ("PL", "Poland"),
    # ("SE", "Sweden"),
    # ("EU", "European Union"),
    ("AEP", "Annual Energy Production"),
    ("AHV", "Anchor Handling Vessel"),
    ("AIS", "Assumed In this Study"),
    ("add.", "Additional"),
    ("$avail$", "Availability"),
    ("$avg$", "Average"),
    ("$base$", "Baseline"),
    ("C", "Combined"),
    ("$cc$", "Country"),
    ("cont.", "Contribution"),
    ("$curr$", "Current (year)"),
    ("D", "Direct"),
    ("$d$", "Day"),
    ("$deco$", "Decommissioning"),
    ("$E$", "Earth"),
    ("EEZ", "Exclusive Economic Zone"),
    ("EMODnet", "European Marine Observation and Data Network"),
    ("$ec$", "Export Cable"),
    ("$eh$", "Energy Hub"),
    ("$equi$", "Equipment"),
    ("$F$", "Factor"),
    ("$foss$", "Fossil"),
    ("GIS", "Geographic Information System"),
    ("HELCOM", "Baltic Marine Environment Protection Commission"),
    ("HLCV", "Heavy-Lift Cargo Vessel"),
    ("HS", "Hub-and-Spoke"),
    ("HVDC", "High-Voltage Direct Current"),
    ("$hh$", "Hub Height"),
    ("ID", "Identifier"),
    ("IEA", "International Energy Agency"),
    ("ISO", "International Organization for Standardization"),
    ("$iac$", "Inter Array Cable"),
    ("$inst$", "Installation"),
    ("int.", "International"),
    ("L", "Large"),
    ("$lin$", "Linear"),
    ("$load$", "Loading"),
    ("M", "Medium"),
    ("$max$", "Maximum"),
    ("MPA", "Marine Protected Area"),
    ("MS", "Multi-Stage"),
    ("MST", "Minimum Spanning Tree"),
    ("N", "Northern Hemisphere"),
    ("ONSS", "Onshore Substation"),
    ("$onss$", "Onshore Substation"),
    ("$onc$", "Onshore Cable"),
    ("$oper$", "Operating"),
    ("$oss$", "Offshore Substation"),
    ("PDF", "Probability Density Function"),
    ("PSIV", "Self-Propelled Installation Vessel"),
    ("PV", "Present Value"),
    ("$p$", "Port"),
    ("RWT", "Reference Wind Turbine"),
    ("S", "Small"),
    ("SS", "Single-Stage"),
    ("$subs$", "Substation"),
    ("$supp$", "Support structure"),
    ("TC", "Transmission Cable"),
    ("$tc$", "Transmission Cable"),
    ("$th$", "Threshold"),
    ("$tot$", "Total"),
    ("$turb$", "Turbine"),
    ("UTM", "Universal Transverse Mercator"),
    ("V", "Very Small"),
    ("$vs$", "Vessel"),
    ("$w$", "Water"),
    ("$wb$", "Weibull"),
    ("WF", "Wind Farm"),
    ("$wf$", "Wind Farm"),
    ("WGS84", "World Geodetic System 1984"),
    ("$wfss$", "Wind Farm Substation"),
    ("$wt$", "Wind Turbine"),
    ("$y$", "Year")
]


import re

def sorting_key(symbol):
    """
    Define the sorting order where Latin letters and abbreviations come first, followed by Greek letters.
    Within each group, symbols are first sorted by base character, and then by case (uppercase first, lowercase second).
    Dollar signs are ignored in the sorting.
    """
    # Unpack the symbol tuple
    symbol_name, description = symbol

    # Remove LaTeX commands and dollar signs before sorting
    clean_symbol = re.sub(r"(\\mathcal|\\mathbb|\{|\}|_|\^|\(|\)|\$)", "", symbol_name)

    # Sorting Greek letters
    greek_letters = {
        'alpha': 0, 'beta': 1, 'gamma': 2, 'delta': 3, 'epsilon': 4, 'zeta': 5, 'eta': 6, 'theta': 7,
        'iota': 8, 'kappa': 9, 'lambda': 10, 'mu': 11, 'nu': 12, 'xi': 13, 'omicron': 14, 'pi': 15,
        'rho': 16, 'sigma': 17, 'tau': 18, 'upsilon': 19, 'phi': 20, 'chi': 21, 'psi': 22, 'omega': 23
    }

    # First handle Greek symbols
    greek_match = re.match(r'\\([a-zA-Z]+)', clean_symbol)
    if greek_match:
        greek_symbol = greek_match.group(1).lower()  # Base Greek letter (case insensitive)

        if greek_symbol in greek_letters:
            # Distinguish between uppercase and lowercase by checking the first character after \
            is_uppercase_greek = symbol_name[1].isupper()

            # Group Greek uppercase first, then lowercase (after Latin)
            if is_uppercase_greek:
                return (2, greek_letters[greek_symbol], 0)  # Greek uppercase
            else:
                return (2, greek_letters[greek_symbol], 1)  # Greek lowercase

    # For Latin characters and abbreviations
    if clean_symbol and clean_symbol[0].isalpha():
        base_char = clean_symbol[0].upper()  # Normalize to uppercase for case-insensitive sorting

        # Distinguish between uppercase and lowercase for Latin letters
        is_uppercase = clean_symbol[0].isupper()

        # Sorting priority:
        # 1. Latin letters and abbreviations first (uppercase followed by lowercase)
        # 2. Calligraphic and Blackboard styles for uppercase (Latin)

        if is_uppercase:
            # Uppercase Latin: Plain, Calligraphic, Blackboard
            if not ("mathcal" in symbol_name or "mathbb" in symbol_name):
                return (1, base_char, 0, 0)  # Plain uppercase
            elif "mathcal" in symbol_name:
                return (1, base_char, 0, 1)  # Calligraphic uppercase
            elif "mathbb" in symbol_name:
                return (1, base_char, 0, 2)  # Blackboard uppercase
        else:
            return (1, base_char, 1, 0)  # Plain lowercase Latin

    return (3, symbol_name, 2, 0)  # Default catch-all


def sort_symbols(symbols_definitions):
    """
    Sort the symbols based on the custom LaTeX-style grouping and ordering.
    """
    return sorted(symbols_definitions, key=sorting_key)


# Sort the symbols and abbreviations
sorted_symbols = sort_symbols(abbreviations)

# Display the sorted list
for symbol, description in sorted_symbols:
    print(f"{symbol}: {description}")





# # Sort the symbols
# sorted_symbols = sort_symbols(symbols_definitions)

# # Display the sorted list
# for symbol, description in sorted_symbols:
#     print(f"{symbol}: {description}")
