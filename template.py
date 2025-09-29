def deal_appraisal(email: dict):
    """Gets Asking price Reduction to achieve target profit % on GDV Target strike price Target profit % on GDV"""
    deal_appraisal_dict = {}
    
    if (email["property_details"]['asking_price'] is not None and 
        email["property_details"]['reduction_to_achieve_target_profit_percentage_gdv'] is not None):
        
        deal_appraisal_dict['asking_price'] = email["property_details"]['asking_price']
        deal_appraisal_dict['reduction_to_achieve_target_profit_percentage_gdv'] = email["property_details"]['reduction_to_achieve_target_profit_percentage_gdv']
        deal_appraisal_dict['asking_price_percent'] = 100
        deal_appraisal_dict["reduction_to_achieve_target_profit_percentage_gdv_percent"] = deal_appraisal_dict['reduction_to_achieve_target_profit_percentage_gdv']/deal_appraisal_dict['asking_price']
        deal_appraisal_dict['target_strike_price'] = deal_appraisal_dict['asking_price'] - deal_appraisal_dict['reduction_to_achieve_target_profit_percentage_gdv']
        deal_appraisal_dict['target_strike_price_percent'] = deal_appraisal_dict['target_strike_price'] / deal_appraisal_dict['asking_price']
        
        return deal_appraisal_dict
    
    else:
        deal_appraisal_dict['asking_price'] = None
        deal_appraisal_dict['reduction_to_achieve_target_profit_percentage_gdv'] = None
        deal_appraisal_dict['asking_price_percent'] = None
        deal_appraisal_dict["reduction_to_achieve_target_profit_percentage_gdv_percent"] = None
        deal_appraisal_dict['target_strike_price'] = None
        deal_appraisal_dict['target_strike_price_percent'] = None
        
        return deal_appraisal_dict
        
        

def gross_development_value(email: dict):
    """
    Transform floor data into GDV table format
    Returns a list of dictionaries representing the GDV breakdown
    """
    floors_data = email.get("property_details", {}).get("floors", [])
    
    if not floors_data:
        return []
    
    gdv_rows = []
    
    # Process each floor and accommodation type
    for floor in floors_data:
        floor_type = floor.get("floor_type", "").title() + " Floor"
        
        for accom in floor.get("accommodation_types", []):
            # Determine market type based on affordable housing flag
            market_type = "Residential - Affordable" if accom.get("affordable_housing", False) else "Residential - Open Market"
            
            # Convert area from sqft to m2 if needed (1 sqft = 0.092903 m2)
            area_sqft = accom.get("area_sqft")
            area_m2 = accom.get("area_m2")
            if area_sqft and not area_m2:
                area_m2 = round(area_sqft * 0.092903, 1)
            elif area_m2 and not area_sqft:
                area_sqft = round(area_m2 * 10.764, 1)
            
            # Calculate price per sqft if we have price per unit and area
            price_per_unit = accom.get("price_per_unit")
            price_per_sqft = accom.get("price_per_sqft")
            if price_per_unit and area_sqft and not price_per_sqft:
                price_per_sqft = round(price_per_unit / area_sqft, 2)
            
            # Calculate total amount (price per unit * number of units)
            units = accom.get("units", 0)
            amount = price_per_unit * units if price_per_unit and units else None
            
            # Format accommodation type
            accom_type_map = {
                "studio": "Studio Flat",
                "1-bed": "1 Bed Flat", 
                "2-bed": "2 Bed Flat",
                "3-bed": "3 Bed Flat",
                "4-bed": "4 Bed Flat",
                "5-bed": "5 Bed Flat"
            }
            accom_type = accom_type_map.get(accom.get("type", "").lower(), accom.get("type", "").title())
            
            row = {
                "market_type": market_type,
                "build_type": "New Build",  # Default assumption
                "floor": floor_type,
                "accommodation_type": accom_type,
                "no_of_units": units,
                "average_sqm_per_unit": area_m2,
                "average_sqft_per_unit": area_sqft,
                "price_per_unit": price_per_unit,
                "price_per_sqft": price_per_sqft,
                "amount": amount
            }
            
            gdv_rows.append(row)
    
    # Add totals row
    if gdv_rows:
        total_units = sum(row["no_of_units"] for row in gdv_rows if row["no_of_units"])
        total_amount = sum(row["amount"] for row in gdv_rows if row["amount"])
        
        # Weighted averages
        total_sqm = 0
        total_sqft = 0
        weighted_sqm_sum = 0
        weighted_sqft_sum = 0
        
        for row in gdv_rows:
            if row["no_of_units"] and row["average_sqm_per_unit"]:
                weighted_sqm_sum += row["no_of_units"] * row["average_sqm_per_unit"]
            if row["no_of_units"] and row["average_sqft_per_unit"]:
                weighted_sqft_sum += row["no_of_units"] * row["average_sqft_per_unit"]
        
        avg_sqm_per_unit = round(weighted_sqm_sum, 1) if total_units else None
        avg_sqft_per_unit = round(weighted_sqft_sum, 1) if total_units else None
        avg_price_per_unit = round(total_amount, 0) if total_units and total_amount else None
        avg_price_per_sqft = round(total_amount, 2) if weighted_sqft_sum and total_amount else None
        
        totals_row = {
            "market_type": "Residential - Total",
            "build_type": "New Build",
            "floor": "",
            "accommodation_type": "",
            "no_of_units": total_units,
            "average_sqm_per_unit": avg_sqm_per_unit,
            "average_sqft_per_unit": avg_sqft_per_unit,
            "price_per_unit": avg_price_per_unit,
            "price_per_sqft": avg_price_per_sqft,
            "amount": total_amount
        }
        
        gdv_rows.append(totals_row)
    
    return gdv_rows

def acquisition_costs(email: dict):
    if email['property_details']['asking_price']:  # Fixed: should be 'property_details' not 'property_costs'
        acquisition_dict = {}
        acquisition_dict['asking_price'] = email["property_details"]['asking_price']
        acquisition_dict['stamp_duty'] = 158002
        acquisition_dict['sourcing_fee_percent'] = 0.02
        acquisition_dict['sourcing_fee'] = acquisition_dict['sourcing_fee_percent'] * acquisition_dict['asking_price']
        acquisition_dict['building_insurance_percent'] = 0.0075
        acquisition_dict['building_insurance'] = acquisition_dict['building_insurance_percent'] * acquisition_dict['asking_price']
        acquisition_dict['legal_professional_costs_percent'] = 0.005
        acquisition_dict['legal_professional_costs'] = acquisition_dict['legal_professional_costs_percent'] * acquisition_dict['asking_price']
        
        # Calculate total acquisition costs
        acquisition_dict['total_acquisition_costs'] = (
            acquisition_dict['asking_price'] +
            acquisition_dict['stamp_duty'] +
            acquisition_dict['sourcing_fee'] +
            acquisition_dict['building_insurance'] +
            acquisition_dict['legal_professional_costs']
        )
    
    else:
        acquisition_dict = {}
        acquisition_dict['asking_price'] = None
        acquisition_dict['stamp_duty'] = None
        acquisition_dict['sourcing_fee_percent'] = None
        acquisition_dict['sourcing_fee'] = None
        acquisition_dict['building_insurance_percent'] = None
        acquisition_dict['building_insurance'] = None
        acquisition_dict['legal_professional_costs_percent'] = None
        acquisition_dict['legal_professional_costs'] = None
        acquisition_dict['total_acquisition_costs'] = None
    
    return acquisition_dict


def build_costs(gdv_dict: list, acquisition_dict: dict):
    if gdv_dict and len(gdv_dict) > 0 and gdv_dict[-1]['no_of_units'] and gdv_dict[-1]['average_sqm_per_unit']:
        build_cost_dict = {}
        
        # Calculate NIA (Net Internal Area)
        build_cost_dict['NIA'] = gdv_dict[-1]['no_of_units'] * gdv_dict[-1]['average_sqm_per_unit']
        
        # Net to Gross ratio
        build_cost_dict['net_to_gross'] = 0.2
        
        # Calculate GIA (Gross Internal Area)
        build_cost_dict['GIA'] = (1 + build_cost_dict['net_to_gross']) * build_cost_dict['NIA']
        
        # Build cost per m2
        build_cost_dict['price_per_m2'] = 1200
        
        # Total build costs
        build_cost_dict['total_build_costs'] = build_cost_dict['GIA'] * build_cost_dict['price_per_m2']
        
        # Cost per flat
        build_cost_dict['cost_per_flat'] = build_cost_dict['total_build_costs'] / gdv_dict[-1]['no_of_units']
        
        # Landscaping costs (placeholder)
        build_cost_dict['landscaping_costs'] = 0  # Set to 0 or add logic to calculate
        
        # Build contingency
        build_cost_dict['build_contingency_percent'] = 0.1
        build_cost_dict['build_contingency_amount'] = (build_cost_dict['total_build_costs'] + build_cost_dict['landscaping_costs']) * build_cost_dict['build_contingency_percent']
        
        # Build Costs Total
        build_cost_dict['build_costs_total'] = (
            build_cost_dict['total_build_costs'] + 
            build_cost_dict['landscaping_costs'] + 
            build_cost_dict['build_contingency_amount']
        )
        
    else:
        build_cost_dict = {}
        build_cost_dict['NIA'] = None
        build_cost_dict['net_to_gross'] = None
        build_cost_dict['GIA'] = None
        build_cost_dict['price_per_m2'] = None
        build_cost_dict['total_build_costs'] = None
        build_cost_dict['cost_per_flat'] = None
        build_cost_dict['landscaping_costs'] = None
        build_cost_dict['build_contingency_percent'] = None
        build_cost_dict['build_contingency_amount'] = None
        build_cost_dict['build_costs_total'] = None
    
    return build_cost_dict


def professional_fees(gdv_dict: list, acquisition_dict: dict, build_cost_dict: dict, timeline_months: int = 18):
    if gdv_dict and len(gdv_dict) > 0 and gdv_dict[-1]['amount']:  # Check if GDV data is available
        prof_fees_dict = {}
        
        # Get GDV total for percentage-based calculations
        gdv_total = gdv_dict[-1]['amount']
        total_units = gdv_dict[-1]['no_of_units']
        
        # Architect fee (percentage of GDV)
        prof_fees_dict['architect_percent'] = 0.01
        prof_fees_dict['architect_fee'] = gdv_total * prof_fees_dict['architect_percent']
        
        # Town Planner fee (percentage of GDV)
        prof_fees_dict['town_planner_percent'] = 0.001
        prof_fees_dict['town_planner_fee'] = gdv_total * prof_fees_dict['town_planner_percent']
        
        # Structural Engineer fee (percentage of GDV)
        prof_fees_dict['structural_engineer_percent'] = 0.005
        prof_fees_dict['structural_engineer_fee'] = gdv_total * prof_fees_dict['structural_engineer_percent']
        
        # Building Control (per unit)
        prof_fees_dict['building_control_per_unit'] = 1500
        prof_fees_dict['building_control_fee'] = total_units * prof_fees_dict['building_control_per_unit']
        
        # Project Management (per month)
        prof_fees_dict['project_management_per_month'] = 7000
        prof_fees_dict['project_management_months'] = timeline_months
        prof_fees_dict['project_management_fee'] = prof_fees_dict['project_management_per_month'] * prof_fees_dict['project_management_months']
        
        # Structural Warranty (percentage of acquisition + build costs)
        if build_cost_dict and build_cost_dict.get('build_costs_total'):
            prof_fees_dict['structural_warranty_percent'] = 0.01
            warranty_base = build_cost_dict['build_costs_total'] +  acquisition_dict['total_acquisition_costs']  # Could also add acquisition costs here
            prof_fees_dict['structural_warranty_fee'] = warranty_base * prof_fees_dict['structural_warranty_percent']
        else:
            prof_fees_dict['structural_warranty_percent'] = 0.01
            prof_fees_dict['structural_warranty_fee'] = None
        
        # Developers' Quantity Surveyor (per month + 1 for initial survey)
        prof_fees_dict['quantity_surveyor_per_month'] = 1200
        prof_fees_dict['quantity_surveyor_months'] = timeline_months + 1  # +1 for initial survey
        prof_fees_dict['quantity_surveyor_fee'] = prof_fees_dict['quantity_surveyor_per_month'] * prof_fees_dict['quantity_surveyor_months']
        
        # Calculate total professional fees
        fees_to_sum = [
            prof_fees_dict['architect_fee'],
            prof_fees_dict['town_planner_fee'],
            prof_fees_dict['structural_engineer_fee'],
            prof_fees_dict['building_control_fee'],
            prof_fees_dict['project_management_fee'],
            prof_fees_dict['quantity_surveyor_fee']
        ]
        
        # Add structural warranty if available
        if prof_fees_dict['structural_warranty_fee'] is not None:
            fees_to_sum.append(prof_fees_dict['structural_warranty_fee'])
        
        prof_fees_dict['professional_fees_total'] = sum(fee for fee in fees_to_sum if fee is not None)
        
    else:
        prof_fees_dict = {}
        prof_fees_dict['architect_percent'] = None
        prof_fees_dict['architect_fee'] = None
        prof_fees_dict['town_planner_percent'] = None
        prof_fees_dict['town_planner_fee'] = None
        prof_fees_dict['structural_engineer_percent'] = None
        prof_fees_dict['structural_engineer_fee'] = None
        prof_fees_dict['building_control_per_unit'] = None
        prof_fees_dict['building_control_fee'] = None
        prof_fees_dict['project_management_per_month'] = None
        prof_fees_dict['project_management_months'] = None
        prof_fees_dict['project_management_fee'] = None
        prof_fees_dict['structural_warranty_percent'] = None
        prof_fees_dict['structural_warranty_fee'] = None
        prof_fees_dict['quantity_surveyor_per_month'] = None
        prof_fees_dict['quantity_surveyor_months'] = None
        prof_fees_dict['quantity_surveyor_fee'] = None
        prof_fees_dict['professional_fees_total'] = None
    
    return prof_fees_dict

def statutory_costs(gdv_dict: list):
    if gdv_dict and len(gdv_dict) > 0 and gdv_dict[-1]['no_of_units']:
        statutory_dict = {}
        
        total_units = gdv_dict[-1]['no_of_units']
        
        # Nutrient Neutrality (per unit calculation)
        statutory_dict['nutrient_neutrality_per_unit'] = 5000  # £5k per unit based on your example
        statutory_dict['nutrient_neutrality'] = total_units * statutory_dict['nutrient_neutrality_per_unit']
        
        # Section 106 (fixed amount or could be calculated based on development size)
        statutory_dict['section_106'] = 0  # Set to 0 as shown in your example, or add calculation logic
        
        # CIL (Community Infrastructure Levy - fixed amount)
        statutory_dict['cil'] = 150000
        
        # Affordable housing (placeholder for future calculations)
        statutory_dict['affordable'] = 0  # Could be calculated based on affordable housing requirements
        
        # Calculate total statutory costs
        statutory_dict['statutory_costs_total'] = (
            statutory_dict['nutrient_neutrality'] +
            statutory_dict['section_106'] +
            statutory_dict['cil'] +
            statutory_dict['affordable']
        )
        
        # Calculate as percentage of GDV for reference
        if gdv_dict[-1]['amount']:
            statutory_dict['statutory_costs_percent'] = statutory_dict['statutory_costs_total'] / gdv_dict[-1]['amount']
        else:
            statutory_dict['statutory_costs_percent'] = None
        
    else:
        statutory_dict = {}
        statutory_dict['nutrient_neutrality_per_unit'] = None
        statutory_dict['nutrient_neutrality'] = None
        statutory_dict['section_106'] = None
        statutory_dict['cil'] = None
        statutory_dict['affordable'] = None
        statutory_dict['statutory_costs_total'] = None
        statutory_dict['statutory_costs_percent'] = None
    
    return statutory_dict

def total_development_costs(build_cost_dict: dict, prof_fees_dict: dict, statutory_dict: dict):
    if (build_cost_dict and prof_fees_dict and statutory_dict and 
        build_cost_dict.get('build_costs_total') is not None and
        prof_fees_dict.get('professional_fees_total') is not None and
        statutory_dict.get('statutory_costs_total') is not None):
        
        dev_costs_dict = {}
        
        # Individual cost components
        dev_costs_dict['build_costs_total'] = build_cost_dict['build_costs_total']
        dev_costs_dict['professional_fees_total'] = prof_fees_dict['professional_fees_total']
        dev_costs_dict['statutory_costs_total'] = statutory_dict['statutory_costs_total']
        
        # Calculate total development costs
        dev_costs_dict['total_development_costs'] = (
            dev_costs_dict['build_costs_total'] +
            dev_costs_dict['professional_fees_total'] +
            dev_costs_dict['statutory_costs_total']
        )
        
        # Calculate breakdown percentages for reference
        total = dev_costs_dict['total_development_costs']
        dev_costs_dict['build_costs_percent'] = dev_costs_dict['build_costs_total'] / total
        dev_costs_dict['professional_fees_percent'] = dev_costs_dict['professional_fees_total'] / total
        dev_costs_dict['statutory_costs_percent'] = dev_costs_dict['statutory_costs_total'] / total
        
    else:
        dev_costs_dict = {}
        dev_costs_dict['build_costs_total'] = None
        dev_costs_dict['professional_fees_total'] = None
        dev_costs_dict['statutory_costs_total'] = None
        dev_costs_dict['total_development_costs'] = None
        dev_costs_dict['build_costs_percent'] = None
        dev_costs_dict['professional_fees_percent'] = None
        dev_costs_dict['statutory_costs_percent'] = None
    
    return dev_costs_dict


def profit_pre_funding_costs(gdv_dict: list, acquisition_dict: dict, dev_costs_dict: dict):
    if (gdv_dict and len(gdv_dict) > 0 and gdv_dict[-1]['amount'] is not None and
        acquisition_dict and acquisition_dict.get('total_acquisition_costs') is not None and
        dev_costs_dict and dev_costs_dict.get('total_development_costs') is not None):
        
        profit_dict = {}
        
        # Revenue (GDV)
        profit_dict['gdv'] = gdv_dict[-1]['amount']
        
        # Cost components
        profit_dict['total_acquisition_costs'] = acquisition_dict['total_acquisition_costs']
        profit_dict['total_development_costs'] = dev_costs_dict['total_development_costs']
        
        # Total costs (before funding)
        profit_dict['total_costs_pre_funding'] = (
            profit_dict['total_acquisition_costs'] +
            profit_dict['total_development_costs']
        )
        
        # Profit before funding costs
        profit_dict['profit_pre_funding_costs'] = (
            profit_dict['gdv'] - 
            profit_dict['total_costs_pre_funding']
        )
        
        # Calculate profit margins for reference
        profit_dict['profit_margin_on_gdv'] = profit_dict['profit_pre_funding_costs'] / profit_dict['gdv']
        profit_dict['profit_margin_on_costs'] = profit_dict['profit_pre_funding_costs'] / profit_dict['total_costs_pre_funding']
        
    else:
        profit_dict = {}
        profit_dict['gdv'] = None
        profit_dict['total_acquisition_costs'] = None
        profit_dict['total_development_costs'] = None
        profit_dict['total_costs_pre_funding'] = None
        profit_dict['profit_pre_funding_costs'] = None
        profit_dict['profit_margin_on_gdv'] = None
        profit_dict['profit_margin_on_costs'] = None
    
    return profit_dict

def finance_costs(acquisition_dict: dict, dev_costs_dict: dict, timeline_months: dict = None):
    if (acquisition_dict and acquisition_dict.get('total_acquisition_costs') is not None and
        dev_costs_dict and dev_costs_dict.get('total_development_costs') is not None):
        
        finance_dict = {}
        
        # Default timeline if not provided
        if timeline_months is None:
            timeline_months = {'land_duration': 18, 'development_duration': 12}
        
        # Finance costs on Land
        finance_dict['land_ltv'] = 0.50  # 50% LTV
        finance_dict['land_lending_amount'] = acquisition_dict['total_acquisition_costs'] * finance_dict['land_ltv']
        finance_dict['land_interest_annual'] = 0.10  # 10% p.a.
        finance_dict['land_interest_monthly'] = finance_dict['land_interest_annual'] / 12
        finance_dict['land_duration_months'] = timeline_months.get('land_duration', 18)
        
        # Land interest (flat lined)
        finance_dict['land_interest_total'] = (
            finance_dict['land_lending_amount'] * 
            finance_dict['land_interest_monthly'] * 
            finance_dict['land_duration_months']
        )
        
        # Land fees
        finance_dict['land_entry_fee_percent'] = 0.02  # 2%
        finance_dict['land_entry_fee'] = finance_dict['land_lending_amount'] * finance_dict['land_entry_fee_percent']
        
        finance_dict['land_exit_fee_percent'] = 0.01  # 1%
        finance_dict['land_exit_fee'] = finance_dict['land_lending_amount'] * finance_dict['land_exit_fee_percent']
        
        # Finance costs on Development
        finance_dict['development_ltv'] = 1.00  # 100% LTV
        finance_dict['development_lending_amount'] = dev_costs_dict['total_development_costs'] * finance_dict['development_ltv']
        finance_dict['development_interest_annual'] = 0.10  # 10% p.a.
        finance_dict['development_interest_monthly'] = finance_dict['development_interest_annual'] / 12
        finance_dict['development_duration_months'] = timeline_months.get('development_duration', 12)
        
        # Development interest (phased/build curve - typically 50% of flat rate for phased drawdown)
        finance_dict['development_interest_total'] = (
            finance_dict['development_lending_amount'] * 
            finance_dict['development_interest_monthly'] * 
            finance_dict['development_duration_months'] * 0.5  # 50% for phased drawdown
        )
        
        # Development fees
        finance_dict['development_entry_fee_percent'] = 0.02  # 2%
        finance_dict['development_entry_fee'] = finance_dict['development_lending_amount'] * finance_dict['development_entry_fee_percent']
        
        finance_dict['development_exit_fee_percent'] = 0.01  # 1%
        finance_dict['development_exit_fee'] = finance_dict['development_lending_amount'] * finance_dict['development_exit_fee_percent']
        
        # Total finance costs
        finance_dict['finance_costs_total'] = (
            finance_dict['land_interest_total'] +
            finance_dict['land_entry_fee'] +
            finance_dict['land_exit_fee'] +
            finance_dict['development_interest_total'] +
            finance_dict['development_entry_fee'] +
            finance_dict['development_exit_fee']
        )
        
    else:
        finance_dict = {}
        finance_dict['land_ltv'] = None
        finance_dict['land_lending_amount'] = None
        finance_dict['land_interest_annual'] = None
        finance_dict['land_interest_monthly'] = None
        finance_dict['land_duration_months'] = None
        finance_dict['land_interest_total'] = None
        finance_dict['land_entry_fee_percent'] = None
        finance_dict['land_entry_fee'] = None
        finance_dict['land_exit_fee_percent'] = None
        finance_dict['land_exit_fee'] = None
        finance_dict['development_ltv'] = None
        finance_dict['development_lending_amount'] = None
        finance_dict['development_interest_annual'] = None
        finance_dict['development_interest_monthly'] = None
        finance_dict['development_duration_months'] = None
        finance_dict['development_interest_total'] = None
        finance_dict['development_entry_fee_percent'] = None
        finance_dict['development_entry_fee'] = None
        finance_dict['development_exit_fee_percent'] = None
        finance_dict['development_exit_fee'] = None
        finance_dict['finance_costs_total'] = None
    
    return finance_dict


def lenders_other_costs(timeline_months: dict = None):
    if timeline_months is None:
        timeline_months = {'development_duration': 12}
    
    lenders_dict = {}
    
    # Fixed lenders' costs
    lenders_dict['lenders_valuation'] = 10000
    lenders_dict['lenders_legal_costs'] = 15000
    lenders_dict['lenders_qs_initial'] = 5000
    
    # Ongoing QS costs
    lenders_dict['lenders_qs_ongoing_per_month'] = 1140
    # Duration is typically development period + 1 month for final survey
    lenders_dict['lenders_qs_ongoing_months'] = timeline_months.get('development_duration', 12) + 1
    lenders_dict['lenders_qs_ongoing_total'] = (
        lenders_dict['lenders_qs_ongoing_per_month'] * 
        lenders_dict['lenders_qs_ongoing_months']
    )
    
    # Total lenders' other costs
    lenders_dict['lenders_other_costs_total'] = (
        lenders_dict['lenders_valuation'] +
        lenders_dict['lenders_legal_costs'] +
        lenders_dict['lenders_qs_initial'] +
        lenders_dict['lenders_qs_ongoing_total']
    )
    
    return lenders_dict

def total_funding_costs(finance_dict: dict, lenders_dict: dict):
    if (finance_dict and finance_dict.get('finance_costs_total') is not None and
        lenders_dict and lenders_dict.get('lenders_other_costs_total') is not None):
        
        funding_costs_dict = {}
        
        # Individual funding cost components
        funding_costs_dict['finance_costs_total'] = finance_dict['finance_costs_total']
        funding_costs_dict['lenders_other_costs_total'] = lenders_dict['lenders_other_costs_total']
        
        # Total funding costs
        funding_costs_dict['funding_costs_total'] = (
            funding_costs_dict['finance_costs_total'] +
            funding_costs_dict['lenders_other_costs_total']
        )
        
        # Calculate breakdown percentages for reference
        total = funding_costs_dict['funding_costs_total']
        if total > 0:
            funding_costs_dict['finance_costs_percent'] = funding_costs_dict['finance_costs_total'] / total
            funding_costs_dict['lenders_costs_percent'] = funding_costs_dict['lenders_other_costs_total'] / total
        else:
            funding_costs_dict['finance_costs_percent'] = None
            funding_costs_dict['lenders_costs_percent'] = None
        
    else:
        funding_costs_dict = {}
        funding_costs_dict['finance_costs_total'] = None
        funding_costs_dict['lenders_other_costs_total'] = None
        funding_costs_dict['funding_costs_total'] = None
        funding_costs_dict['finance_costs_percent'] = None
        funding_costs_dict['lenders_costs_percent'] = None
    
    return funding_costs_dict


def selling_costs(gdv_dict: list):
    if gdv_dict and len(gdv_dict) > 0 and gdv_dict[-1]['amount'] is not None and gdv_dict[-1]['amount'] > 0:
        selling_dict = {}
        
        gdv_total = gdv_dict[-1]['amount']
        total_units = gdv_dict[-1]['no_of_units']
        
        # Marketing costs (fixed amount)
        selling_dict['marketing_costs'] = 5000
        
        # Agent fee (percentage of GDV)
        selling_dict['agent_fee_percent'] = 0.024  # 2.40%
        selling_dict['agent_fee'] = gdv_total * selling_dict['agent_fee_percent']
        
        # Legal fees (per unit and percentage)
        selling_dict['legal_fees_per_unit'] = 1517
        selling_dict['legal_fees_from_units'] = total_units * selling_dict['legal_fees_per_unit'] if total_units else 0
        selling_dict['legal_fees_percent'] = 0.01  # 1.00%
        selling_dict['legal_fees_from_percent'] = gdv_total * selling_dict['legal_fees_percent']
        
        # Use the higher of the two legal fee calculations
        selling_dict['legal_fees_total'] = max(
            selling_dict['legal_fees_from_units'], 
            selling_dict['legal_fees_from_percent']
        )
        
        # Total selling costs
        selling_dict['selling_costs_total'] = (
            selling_dict['marketing_costs'] +
            selling_dict['agent_fee'] +
            selling_dict['legal_fees_total']
        )
        
        # Calculate as percentage of GDV (now safe from division by zero)
        selling_dict['selling_costs_percent'] = selling_dict['selling_costs_total'] / gdv_total
        
    else:
        selling_dict = {}
        selling_dict['marketing_costs'] = None
        selling_dict['agent_fee_percent'] = None
        selling_dict['agent_fee'] = None
        selling_dict['legal_fees_per_unit'] = None
        selling_dict['legal_fees_from_units'] = None
        selling_dict['legal_fees_percent'] = None
        selling_dict['legal_fees_from_percent'] = None
        selling_dict['legal_fees_total'] = None
        selling_dict['selling_costs_total'] = None
        selling_dict['selling_costs_percent'] = None
    
    return selling_dict


def total_costs(acquisition_dict: dict, dev_costs_dict: dict, funding_costs_dict: dict, selling_dict: dict):
    if (acquisition_dict and acquisition_dict.get('total_acquisition_costs') is not None and
        dev_costs_dict and dev_costs_dict.get('total_development_costs') is not None and
        funding_costs_dict and funding_costs_dict.get('funding_costs_total') is not None and
        selling_dict and selling_dict.get('selling_costs_total') is not None):
        
        total_costs_dict = {}
        
        # Individual cost components
        total_costs_dict['acquisition_costs'] = acquisition_dict['total_acquisition_costs']
        total_costs_dict['development_costs'] = dev_costs_dict['total_development_costs']
        total_costs_dict['funding_costs'] = funding_costs_dict['funding_costs_total']
        total_costs_dict['selling_costs'] = selling_dict['selling_costs_total']
        
        # Total costs
        total_costs_dict['total_costs'] = (
            total_costs_dict['acquisition_costs'] +
            total_costs_dict['development_costs'] +
            total_costs_dict['funding_costs'] +
            total_costs_dict['selling_costs']
        )
        
        # Calculate breakdown percentages
        total = total_costs_dict['total_costs']
        total_costs_dict['acquisition_costs_percent'] = total_costs_dict['acquisition_costs'] / total
        total_costs_dict['development_costs_percent'] = total_costs_dict['development_costs'] / total
        total_costs_dict['funding_costs_percent'] = total_costs_dict['funding_costs'] / total
        total_costs_dict['selling_costs_percent'] = total_costs_dict['selling_costs'] / total
        
    else:
        total_costs_dict = {}
        total_costs_dict['acquisition_costs'] = None
        total_costs_dict['development_costs'] = None
        total_costs_dict['funding_costs'] = None
        total_costs_dict['selling_costs'] = None
        total_costs_dict['total_costs'] = None
        total_costs_dict['acquisition_costs_percent'] = None
        total_costs_dict['development_costs_percent'] = None
        total_costs_dict['funding_costs_percent'] = None
        total_costs_dict['selling_costs_percent'] = None
    
    return total_costs_dict

def net_profit_analysis(gdv_dict: list, total_costs_dict: dict):
    if (gdv_dict and len(gdv_dict) > 0 and gdv_dict[-1]['amount'] is not None and
        total_costs_dict and total_costs_dict.get('total_costs') is not None):
        
        profit_dict = {}
        
        gdv_total = gdv_dict[-1]['amount']
        total_costs = total_costs_dict['total_costs']
        
        # Net profit
        profit_dict['net_profit'] = gdv_total - total_costs
        
        # Net profit margins
        profit_dict['net_profit_on_gdv'] = profit_dict['net_profit'] / gdv_total
        profit_dict['net_profit_on_costs'] = profit_dict['net_profit'] / total_costs
        
    else:
        profit_dict = {}
        profit_dict['net_profit'] = None
        profit_dict['net_profit_on_gdv'] = None
        profit_dict['net_profit_on_costs'] = None
    
    return profit_dict


def lending_analysis(total_costs_dict: dict, gdv_dict: list, own_funds_invested: float = None):
    if (total_costs_dict and total_costs_dict.get('total_costs') is not None and
        gdv_dict and len(gdv_dict) > 0 and gdv_dict[-1]['amount'] is not None):
        
        lending_dict = {}
        
        total_costs = total_costs_dict['total_costs']
        gdv_total = gdv_dict[-1]['amount']
        
        # Lenders' criteria
        lending_dict['ltc_criteria'] = 0.85  # 85%
        lending_dict['ltgdv_criteria'] = 0.70  # 70%
        
        # Maximum loan amounts based on criteria
        lending_dict['max_loan_ltc'] = total_costs * lending_dict['ltc_criteria']
        lending_dict['max_loan_ltgdv'] = gdv_total * lending_dict['ltgdv_criteria']
        
        # Maximum loan amount (lower of the two)
        lending_dict['maximum_loan_amount'] = min(
            lending_dict['max_loan_ltc'], 
            lending_dict['max_loan_ltgdv']
        )
        
        # Calculate shortfalls
        if lending_dict['max_loan_ltc'] < total_costs:
            lending_dict['reduce_costs_by'] = total_costs - lending_dict['max_loan_ltc']
        else:
            lending_dict['reduce_costs_by'] = 0
            
        if lending_dict['max_loan_ltgdv'] < lending_dict['maximum_loan_amount']:
            lending_dict['reduce_loan_by'] = lending_dict['maximum_loan_amount'] - lending_dict['max_loan_ltgdv']
        else:
            lending_dict['reduce_loan_by'] = 0
        
        # Day 1 funding analysis
        # Assuming land advance is difference between max loan and development costs
        development_costs = total_costs_dict.get('development_costs', 0) + total_costs_dict.get('funding_costs', 0)
        lending_dict['max_lenders_land_advance_day1'] = lending_dict['maximum_loan_amount'] - development_costs
        lending_dict['own_equity_needed_day1'] = total_costs_dict.get('acquisition_costs', 0) - lending_dict['max_lenders_land_advance_day1']
        
        if own_funds_invested and lending_dict['own_equity_needed_day1'] > own_funds_invested:
            lending_dict['shortfall_equity_needed_day1'] = lending_dict['own_equity_needed_day1'] - own_funds_invested
        else:
            lending_dict['shortfall_equity_needed_day1'] = 0
            
        # Return on own funds (if provided)
        if own_funds_invested:
            net_profit = gdv_total - total_costs
            lending_dict['return_on_own_funds'] = net_profit / own_funds_invested
            # Assuming 18 month project duration
            lending_dict['return_on_own_funds_per_annum'] = lending_dict['return_on_own_funds'] / (18/12)
        else:
            lending_dict['return_on_own_funds'] = None
            lending_dict['return_on_own_funds_per_annum'] = None
            
    else:
        lending_dict = {}
        lending_dict['ltc_criteria'] = None
        lending_dict['ltgdv_criteria'] = None
        lending_dict['max_loan_ltc'] = None
        lending_dict['max_loan_ltgdv'] = None
        lending_dict['maximum_loan_amount'] = None
        lending_dict['reduce_costs_by'] = None
        lending_dict['reduce_loan_by'] = None
        lending_dict['max_lenders_land_advance_day1'] = None
        lending_dict['own_equity_needed_day1'] = None
        lending_dict['shortfall_equity_needed_day1'] = None
        lending_dict['return_on_own_funds'] = None
        lending_dict['return_on_own_funds_per_annum'] = None
    
    return lending_dict


def post_development_analysis(gdv_dict: list, total_units: int = 84, rental_per_unit_per_month: float = 1200):
    if gdv_dict and len(gdv_dict) > 0 and gdv_dict[-1]['amount'] is not None:
        
        post_dev_dict = {}
        
        gdv_total = gdv_dict[-1]['amount']
        
        # Rental income
        post_dev_dict['rental_income_per_annum'] = total_units * rental_per_unit_per_month * 12
        
        # Service charges
        post_dev_dict['service_charges_percent'] = 0.10  # 10%
        post_dev_dict['service_charges'] = -post_dev_dict['rental_income_per_annum'] * post_dev_dict['service_charges_percent']
        
        # Net rental income
        post_dev_dict['net_rental_income'] = post_dev_dict['rental_income_per_annum'] + post_dev_dict['service_charges']
        
        # Interest on term loan
        post_dev_dict['term_loan_ltv'] = 0.65  # 65% LTV
        post_dev_dict['term_loan_amount'] = gdv_total * post_dev_dict['term_loan_ltv']
        post_dev_dict['term_loan_interest_rate'] = 0.07  # 7% p.a.
        post_dev_dict['interest_on_term_loan'] = -post_dev_dict['term_loan_amount'] * post_dev_dict['term_loan_interest_rate']
        
        # Net cashflow per annum
        post_dev_dict['net_cashflow_per_annum'] = (
            post_dev_dict['net_rental_income'] + 
            post_dev_dict['interest_on_term_loan']
        )
        
    else:
        post_dev_dict = {}
        post_dev_dict['rental_income_per_annum'] = None
        post_dev_dict['service_charges_percent'] = None
        post_dev_dict['service_charges'] = None
        post_dev_dict['net_rental_income'] = None
        post_dev_dict['term_loan_ltv'] = None
        post_dev_dict['term_loan_amount'] = None
        post_dev_dict['term_loan_interest_rate'] = None
        post_dev_dict['interest_on_term_loan'] = None
        post_dev_dict['net_cashflow_per_annum'] = None
    
    return post_dev_dict


def funding_workings(acquisition_dict: dict, dev_costs_dict: dict, statutory_dict: dict, 
                    funding_costs_dict: dict, selling_dict: dict, finance_dict: dict):
    if all([acquisition_dict, dev_costs_dict, statutory_dict, funding_costs_dict, selling_dict, finance_dict]):
        
        funding_workings_dict = {}
        
        # Get loan amounts from finance calculations (with None checks)
        land_loan = finance_dict.get('land_lending_amount', 0) or 0
        development_loan = finance_dict.get('development_lending_amount', 0) or 0
        
        # Acquisition costs breakdown (with None checks)
        asking_price = acquisition_dict.get('asking_price', 0) or 0
        funding_workings_dict['asking_price'] = {
            'own': asking_price - land_loan,
            'borrow': land_loan,
            'total': asking_price
        }
        
        # Other acquisition costs (typically own funds) - with None checks
        stamp_duty = acquisition_dict.get('stamp_duty', 0) or 0
        sourcing_fee = acquisition_dict.get('sourcing_fee', 0) or 0
        building_insurance = acquisition_dict.get('building_insurance', 0) or 0
        legal_costs = acquisition_dict.get('legal_professional_costs', 0) or 0
        
        funding_workings_dict['stamp_duty'] = {
            'own': stamp_duty,
            'borrow': 0,
            'total': stamp_duty
        }
        
        funding_workings_dict['sourcing_fee'] = {
            'own': sourcing_fee,
            'borrow': 0,
            'total': sourcing_fee
        }
        
        funding_workings_dict['building_insurance'] = {
            'own': building_insurance,
            'borrow': 0,
            'total': building_insurance
        }
        
        funding_workings_dict['legal_professional_costs'] = {
            'own': legal_costs,
            'borrow': 0,
            'total': legal_costs
        }
        
        # Acquisition costs total
        acq_own = (asking_price - land_loan) + stamp_duty + sourcing_fee + building_insurance + legal_costs
        acq_borrow = land_loan
        acq_total = acquisition_dict.get('total_acquisition_costs', 0) or 0
        
        funding_workings_dict['acquisition_costs_total'] = {
            'own': acq_own,
            'borrow': acq_borrow,
            'total': acq_total
        }
        
        # Development costs (typically borrowed) - with None checks
        build_costs_total = dev_costs_dict.get('build_costs_total', 0) or 0
        prof_fees_total = dev_costs_dict.get('professional_fees_total', 0) or 0
        
        funding_workings_dict['build_costs_total'] = {
            'own': 0,
            'borrow': build_costs_total,
            'total': build_costs_total
        }
        
        funding_workings_dict['professional_fees_total'] = {
            'own': 0,
            'borrow': prof_fees_total,
            'total': prof_fees_total
        }
        
        # Statutory costs (typically borrowed) - with None checks
        statutory_total = statutory_dict.get('statutory_costs_total', 0) or 0
        funding_workings_dict['statutory_costs_total'] = {
            'own': 0,
            'borrow': statutory_total,
            'total': statutory_total
        }
        
        # Funding costs (typically own funds) - with None checks
        funding_total = funding_costs_dict.get('funding_costs_total', 0) or 0
        funding_workings_dict['funding_costs_total'] = {
            'own': funding_total,
            'borrow': 0,
            'total': funding_total
        }
        
        # Selling costs (typically own funds) - with None checks
        selling_total = selling_dict.get('selling_costs_total', 0) or 0
        funding_workings_dict['selling_costs_total'] = {
            'own': selling_total,
            'borrow': 0,
            'total': selling_total
        }
        
        # Calculate totals
        total_own = (acq_own + funding_total + selling_total)
        total_borrow = (acq_borrow + build_costs_total + prof_fees_total + statutory_total)
        total_costs = total_own + total_borrow
        
        funding_workings_dict['total_costs'] = {
            'own': total_own,
            'borrow': total_borrow,
            'total': total_costs
        }
        
        return funding_workings_dict
    
    else:
        # Return structure with None values if inputs are missing
        categories = ['asking_price', 'stamp_duty', 'sourcing_fee', 'building_insurance', 
                     'legal_professional_costs', 'acquisition_costs_total', 'build_costs_total',
                     'professional_fees_total', 'statutory_costs_total', 'funding_costs_total',
                     'selling_costs_total', 'total_costs']
        
        funding_workings_dict = {}
        for category in categories:
            funding_workings_dict[category] = {
                'own': None,
                'borrow': None,
                'total': None
            }
        
        return funding_workings_dict

def calculate_kpis(email_dict: dict, funding_workings_dict: dict, net_profit_dict: dict, 
                  lending_dict: dict, post_dev_dict: dict, timeline_months: int = 18):
    if all([funding_workings_dict, net_profit_dict, lending_dict]):
        
        kpis_dict = {}
        
        # Basic deal info
        kpis_dict['deal_type'] = email_dict.get('deal_type', 'Unknown')
        kpis_dict['higher_risk_building'] = False  # Default assumption
        
        # Own funds needed calculation (with None checks)
        total_own_funds = funding_workings_dict.get('total_costs', {}).get('own', 0) or 0
        kpis_dict['own_funds_needed'] = total_own_funds
        
        # Land purchase (own funds portion)
        kpis_dict['land_purchase_own_funds'] = funding_workings_dict.get('acquisition_costs_total', {}).get('own', 0) or 0
        
        # Shortfall due to lending criteria
        kpis_dict['shortfall_due_to_lending_criteria'] = lending_dict.get('shortfall_equity_needed_day1', 0) or 0
        
        # Net profit
        kpis_dict['net_profit'] = net_profit_dict.get('net_profit', 0) or 0
        
        # Timeline
        kpis_dict['timeline_months'] = timeline_months or 18  # Default to 18 if None
        
        # Return on own funds
        if total_own_funds and total_own_funds > 0:
            net_profit = net_profit_dict.get('net_profit', 0) or 0
            kpis_dict['return_on_own_funds'] = net_profit / total_own_funds
            kpis_dict['return_on_own_funds_per_annum'] = kpis_dict['return_on_own_funds'] / (kpis_dict['timeline_months'] / 12)
        else:
            kpis_dict['return_on_own_funds'] = None
            kpis_dict['return_on_own_funds_per_annum'] = None
        
        # Lending criteria compliance
        total_costs = funding_workings_dict.get('total_costs', {}).get('total', 0) or 0
        max_loan = lending_dict.get('maximum_loan_amount', 0) or 0
        
        if total_costs > 0:
            actual_ltc = max_loan / total_costs
            ltc_criteria = lending_dict.get('ltc_criteria', 0.85) or 0.85
            kpis_dict['lending_criteria_ltc'] = "Yes" if actual_ltc <= ltc_criteria else "No"
        else:
            kpis_dict['lending_criteria_ltc'] = "Unknown"
        
        # LTGDV compliance (with proper None handling)
        gdv_total = email_dict.get('property_details', {}).get('gdv', 0) or 0
        if gdv_total and gdv_total > 0:  # Check for both None and > 0
            actual_ltgdv = max_loan / gdv_total
            ltgdv_criteria = lending_dict.get('ltgdv_criteria', 0.70) or 0.70
            kpis_dict['lending_criteria_ltgdv'] = "Yes" if actual_ltgdv <= ltgdv_criteria else "No"
        else:
            kpis_dict['lending_criteria_ltgdv'] = "Unknown"
        
        # Post development metrics
        if post_dev_dict:
            # Own funds left in deal (assuming refinance at 65% LTV)
            term_loan_amount = post_dev_dict.get('term_loan_amount', 0) or 0
            total_invested = total_own_funds + max_loan
            kpis_dict['own_funds_left_in_deal'] = total_invested - term_loan_amount
            
            # Yearly net cashflow
            kpis_dict['yearly_net_cashflow'] = post_dev_dict.get('net_cashflow_per_annum', 0) or 0
            
            # Annual yield on own funds
            if kpis_dict['own_funds_left_in_deal'] and kpis_dict['own_funds_left_in_deal'] > 0:
                kpis_dict['annual_yield_on_own_funds'] = kpis_dict['yearly_net_cashflow'] / kpis_dict['own_funds_left_in_deal']
            else:
                kpis_dict['annual_yield_on_own_funds'] = None
        else:
            kpis_dict['own_funds_left_in_deal'] = None
            kpis_dict['yearly_net_cashflow'] = None
            kpis_dict['annual_yield_on_own_funds'] = None
        
        # Travel distance (from property details or assumptions)
        property_details = email_dict.get('property_details', {})
        kpis_dict['travel_distance_miles'] = 64.1  # Default or extract from email
        kpis_dict['car_travel_time'] = "1h 12m"  # Default or extract from email
        kpis_dict['train_travel_time'] = "2h 51m"  # Default or extract from email
        
    else:
        kpis_dict = {}
        keys = ['deal_type', 'higher_risk_building', 'own_funds_needed', 'land_purchase_own_funds',
                'shortfall_due_to_lending_criteria', 'net_profit', 'timeline_months', 
                'return_on_own_funds', 'return_on_own_funds_per_annum', 'lending_criteria_ltc',
                'lending_criteria_ltgdv', 'own_funds_left_in_deal', 'yearly_net_cashflow',
                'annual_yield_on_own_funds', 'travel_distance_miles', 'car_travel_time', 'train_travel_time']
        
        for key in keys:
            kpis_dict[key] = None
    
    return kpis_dict


