from flask import Flask, jsonify, send_from_directory, request
import sqlite3
import os

app = Flask(__name__)
DB_PATH = r'C:\Users\kvsha\Desktop\sample_project\mydata.db'

@app.route('/')
def serve_dashboard():
    return send_from_directory(os.path.dirname(__file__), 'metrics_dashboard.html')

@app.route('/api/lag-options')
def get_lag_options():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT Lag FROM ActivityRelationshipView ORDER BY CAST(Lag AS REAL)")
    lags = [row[0] for row in cursor.fetchall()]
    conn.close()
    return jsonify(lags)

@app.route('/api/free-float-options')
def get_free_float_options():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT FreeFloat FROM ActivityRelationshipView ORDER BY CAST(FreeFloat AS REAL)")
    free_floats = [row[0] for row in cursor.fetchall()]
    conn.close()
    return jsonify(free_floats)

@app.route('/api/project-options')
def get_project_options():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        # Get project options using proj_short_name from PROJECT table
        cursor.execute("SELECT proj_id, proj_short_name FROM PROJECT ORDER BY proj_short_name")
        projects = cursor.fetchall()
        # Return as list of dictionaries with both ID and name
        project_options = [{"id": proj[0], "name": proj[1]} for proj in projects]
    except sqlite3.OperationalError as e:
        print(f"Error fetching project options: {e}")
        project_options = []
    except Exception as e:
        print(f"Unexpected error in project options: {e}")
        project_options = []
    conn.close()
    return jsonify(project_options)

@app.route('/api/typical-fs0d')
def typical_fs0d():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    relationship_type = request.args.get('relationship_type')
    driving = request.args.get('driving')
    lag = request.args.get('lag')
    free_float = request.args.get('free_float')
    project_id = request.args.get('project_id') # Re-added filter parameter

    filters = []

    # Apply base filter for Relationship_Status
    filters.append("Relationship_Status = 'Incomplete'")

    # Removed hardcoded Lag = 0, now dynamic filter is applied below

    # Apply RelationshipType filter
    if relationship_type and relationship_type != 'All':
        filters.append(f"RelationshipType = '{relationship_type}'")
    else:
        filters.append("RelationshipType IN ('PR_FS', 'PR_FS1')") # Default behavior

    # Apply Driving filter
    if driving and driving != 'All':
        filters.append(f"Driving = '{driving}'")

    # Apply Lag filter
    if lag and lag != 'All':
        filters.append(f"Lag = {lag}")

    # Apply FreeFloat filter
    if free_float and free_float != 'All':
        filters.append(f"FreeFloat = {free_float}")

    # Project filter
    if project_id and project_id != 'All':
        filters.append(f"Project_ID = '{project_id}'") 

    where_clause = " AND ".join(filters)
    if where_clause:
        where_clause = "WHERE " + where_clause

    query = f'''
        SELECT 
            Activity_ID, Activity_ID2, Activity_Name, Activity_Name2, RelationshipType, Lag, Driving, FreeFloat, Lead, ExcessiveLag, Relationship_Status
        FROM ActivityRelationshipView
        {where_clause}
    '''
    cursor.execute(query)
    rows = cursor.fetchall()
    conn.close()
    # Map to dicts for JSON
    data = [
        {
            "Pred. ID": row[0],
            "Succ. ID": row[1],
            "Pred. Name": row[2],
            "Succ. Name": row[3],
            "Relationship type": row[4],
            "Lag": row[5],
            "Driving": row[6],
            "FreeFloat": row[7],
            "Lead": row[8],
            "ExcessiveLag": row[9],
            "Relationship_Status": row[10]
        }
        for row in rows
    ]
    return jsonify(data)

@app.route('/api/finalactivitykpi')
def get_final_activity_kpi():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    relationship_type = request.args.get('relationship_type')
    driving = request.args.get('driving')
    lag = request.args.get('lag')
    free_float = request.args.get('free_float')
    project_id = request.args.get('project_id') # Re-added filter parameter

    # Base filters for both Total and Remaining relationships
    base_filters = []
    
    if relationship_type and relationship_type != 'All':
        base_filters.append(f"RelationshipType = '{relationship_type}'")
    else:
        base_filters.append("RelationshipType IN ('PR_FS', 'PR_FS1')")

    if driving and driving != 'All':
        base_filters.append(f"Driving = '{driving}'")

    if lag and lag != 'All':
        base_filters.append(f"Lag = {lag}")

    if free_float and free_float != 'All':
        base_filters.append(f"FreeFloat = {free_float}")

    # Project filter
    if project_id and project_id != 'All':
        base_filters.append(f"Project_ID = '{project_id}'")

    # Total Relationships (all relationships matching base filters, regardless of status)
    total_filters = base_filters.copy()
    total_where_clause = " AND ".join(total_filters)
    if total_where_clause:
        total_where_clause = "WHERE " + total_where_clause

    cursor.execute(f'SELECT COUNT(*) FROM ActivityRelationshipView {total_where_clause}')
    total_relationships = cursor.fetchone()[0]

    # Remaining Relationships (only incomplete relationships)
    remaining_filters = base_filters.copy()
    remaining_filters.append("Relationship_Status = 'Incomplete'")
    remaining_where_clause = " AND ".join(remaining_filters)
    if remaining_where_clause:
        remaining_where_clause = "WHERE " + remaining_where_clause

    cursor.execute(f'SELECT COUNT(*) FROM ActivityRelationshipView {remaining_where_clause}')
    remaining_relationships = cursor.fetchone()[0]

    # Lag Count (Lag > 0 and Relationship_Status = 'Incomplete' with current RelationshipType and Driving filters)
    lag_count_filters = []
    lag_count_filters.append("Lag > 0") # Specific for Lag_Count, not conflicting with general Lag filter
    lag_count_filters.append("Relationship_Status = 'Incomplete'")

    if relationship_type and relationship_type != 'All':
        lag_count_filters.append(f"RelationshipType = '{relationship_type}'")
    else:
        lag_count_filters.append("RelationshipType IN ('PR_FS', 'PR_FS1')")

    if driving and driving != 'All':
        lag_count_filters.append(f"Driving = '{driving}'")

    # For Lag Count, if a general 'Lag' filter is applied, it takes precedence over 'Lag > 0'
    # This ensures that if user selects 'Lag = 0', Lag Count becomes 0 and is not affected by 'Lag > 0'
    if lag and lag != 'All':
        # If a specific lag is selected, override the 'Lag > 0' condition for lag_count_filters
        # This handles cases where user selects Lag=0, and we shouldn't count any Lag > 0
        if "Lag > 0" in lag_count_filters:
            lag_count_filters.remove("Lag > 0")
        lag_count_filters.append(f"Lag = {lag}")
    
    if free_float and free_float != 'All':
        lag_count_filters.append(f"FreeFloat = {free_float}")

    # Project filter
    if project_id and project_id != 'All':
        lag_count_filters.append(f"Project_ID = '{project_id}'")

    lag_count_where_clause = " AND ".join(lag_count_filters)
    if lag_count_where_clause:
        lag_count_where_clause = "WHERE " + lag_count_where_clause

    cursor.execute(f'SELECT COUNT(*) FROM ActivityRelationshipView {lag_count_where_clause}')
    lag_count = cursor.fetchone()[0]

    # Relationship (%)
    relationship_percentage = 0
    if remaining_relationships > 0:
        relationship_percentage = (float(total_relationships) / remaining_relationships) * 100

    conn.close()

    kpi_data = {
        "Total_Relationship_Count": total_relationships,
        "Remaining_Relationship_Count": remaining_relationships,
        "Lag_Count": lag_count,
        "Relationship_Percentage": round(relationship_percentage, 2)
    }
    return jsonify(kpi_data)

@app.route('/api/relationship-type-counts')
def get_relationship_type_counts():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    relationship_type_param = request.args.get('relationship_type')
    driving = request.args.get('driving')
    lag = request.args.get('lag')
    free_float = request.args.get('free_float')
    project_id = request.args.get('project_id') # Re-added filter parameter

    filters = []
    # Removed hardcoded Lag = 0 and Relationship_Status = 'Incomplete'
    # Filters will now come from dynamic selection

    # Apply RelationshipType filter based on selection
    if relationship_type_param and relationship_type_param != 'All':
        filters.append(f"RelationshipType = '{relationship_type_param}'")
    else:
        filters.append("RelationshipType IN ('PR_FS', 'PR_FS1')") # Default for the donut chart

    if driving and driving != 'All':
        filters.append(f"Driving = '{driving}'")

    if lag and lag != 'All':
        filters.append(f"Lag = {lag}")

    if free_float and free_float != 'All':
        filters.append(f"FreeFloat = {free_float}")

    # Project filter
    if project_id and project_id != 'All':
        filters.append(f"Project_ID = '{project_id}'")

    where_clause = " AND ".join(filters)
    if where_clause:
        where_clause = "WHERE " + where_clause

    # Query the database for actual relationship type counts
    cursor.execute(f"SELECT RelationshipType, COUNT(*) FROM ActivityRelationshipView {where_clause} GROUP BY RelationshipType")
    counts = {row[0]: row[1] for row in cursor.fetchall()}
    conn.close()
    return jsonify(counts)

@app.route('/api/relationship-percentage-history')
def get_relationship_percentage_history():
    # This is dummy historical data, updated to reflect filtered data.
    # For simplicity, we are not applying filters to this dummy data as historical filtering would require
    # a more complex data structure and backend.
    history_data = {
        "labels": ["Mar 2019", "Aug 2019", "Dec 2019", "Apr 2020", "Aug 2020", "Dec 2020", "Apr 2021"],
        "data": [80, 81, 90, 70, 85, 94, 90]
    }
    return jsonify(history_data)

@app.route('/api/typical-non-fs0d')
def typical_non_fs0d():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    relationship_type = request.args.get('relationship_type')
    driving = request.args.get('driving')
    lag = request.args.get('lag')
    free_float = request.args.get('free_float')
    project_id = request.args.get('project_id')

    filters = [
        "Relationship_Status = 'Incomplete'",
        "(Lag IS NULL OR Lag != 0)"
    ]
    if relationship_type and relationship_type != 'All':
        filters.append(f"RelationshipType = '{relationship_type}'")
    else:
        filters.append("RelationshipType NOT IN ('PR_FS', 'PR_FS1')")
    if driving and driving != 'All':
        filters.append(f"Driving = '{driving}'")
    if lag and lag != 'All':
        filters.append(f"Lag = {lag}")
    if free_float and free_float != 'All':
        filters.append(f"FreeFloat = {free_float}")
    # Project filter
    if project_id and project_id != 'All':
        filters.append(f"Project_ID = '{project_id}'")
    where_clause = " AND ".join(filters)
    if where_clause:
        where_clause = "WHERE " + where_clause
    query = f'''
        SELECT 
            Activity_ID, Activity_ID2, Activity_Name, Activity_Name2, RelationshipType, Lag, Driving, FreeFloat, Lead, ExcessiveLag, Relationship_Status
        FROM ActivityRelationshipView
        {where_clause}
    '''
    cursor.execute(query)
    rows = cursor.fetchall()
    conn.close()
    data = [
        {
            "Pred. ID": row[0],
            "Succ. ID": row[1],
            "Pred. Name": row[2],
            "Succ. Name": row[3],
            "Relationship type": row[4],
            "Lag": row[5],
            "Driving": row[6],
            "FreeFloat": row[7],
            "Lead": row[8],
            "ExcessiveLag": row[9],
            "Relationship_Status": row[10]
        }
        for row in rows
    ]
    return jsonify(data)

@app.route('/api/nonfs-relationship-type-options')
def get_nonfs_relationship_type_options():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT RelationshipType FROM ActivityRelationshipView WHERE RelationshipType NOT IN ('PR_FS', 'PR_FS1') ORDER BY RelationshipType")
    types = [row[0] for row in cursor.fetchall()]
    conn.close()
    return jsonify(types)

@app.route('/api/nonfs-lag-options')
def get_nonfs_lag_options():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT Lag FROM ActivityRelationshipView WHERE RelationshipType NOT IN ('PR_FS', 'PR_FS1') AND (Lag IS NULL OR Lag != 0) ORDER BY CAST(Lag AS REAL)")
    lags = [row[0] for row in cursor.fetchall()]
    conn.close()
    return jsonify(lags)

@app.route('/api/nonfs-free-float-options')
def get_nonfs_free_float_options():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT FreeFloat FROM ActivityRelationshipView WHERE RelationshipType NOT IN ('PR_FS', 'PR_FS1') AND (Lag IS NULL OR Lag != 0) ORDER BY CAST(FreeFloat AS REAL)")
    free_floats = [row[0] for row in cursor.fetchall()]
    conn.close()
    return jsonify(free_floats)

@app.route('/api/nonfs-driving-options')
def get_nonfs_driving_options():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT Driving FROM ActivityRelationshipView WHERE RelationshipType NOT IN ('PR_FS', 'PR_FS1') AND (Lag IS NULL OR Lag != 0) ORDER BY Driving")
    drivings = [row[0] for row in cursor.fetchall()]
    conn.close()
    return jsonify(drivings)

@app.route('/api/non-fs0d-kpi')
def non_fs0d_kpi():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    relationship_type = request.args.get('relationship_type')
    driving = request.args.get('driving')
    lag = request.args.get('lag')
    free_float = request.args.get('free_float')
    project_id = request.args.get('project_id')

    try:
        # Build base filters for Non FS+0d page: ALL THREE FILTERS APPLIED CONSISTENTLY
        # 1. RelationshipType NOT IN ('PR_FS', 'PR_FS1')
        # 2. Lag IS NULL OR Lag != 0
        # 3. Relationship_Status = 'Incomplete'
        base_filters = [
            "Relationship_Status = 'Incomplete'",
            "(Lag IS NULL OR Lag != 0)"
        ]
        
        if relationship_type and relationship_type != 'All':
            base_filters.append(f"RelationshipType = '{relationship_type}'")
        else:
            base_filters.append("RelationshipType NOT IN ('PR_FS', 'PR_FS1')")
        
        if driving and driving != 'All':
            base_filters.append(f"Driving = '{driving}'")
        if lag and lag != 'All':
            base_filters.append(f"Lag = {lag}")
        if free_float and free_float != 'All':
            base_filters.append(f"FreeFloat = {free_float}")
        if project_id and project_id != 'All':
            base_filters.append(f"Project_ID = '{project_id}'")
        
        base_where_clause = " AND ".join(base_filters)
        if base_where_clause:
            base_where_clause = "WHERE " + base_where_clause

        # Total Relationships - relationships matching all three Non FS+0d filters
        cursor.execute(f'''
            SELECT COUNT(*) as Total_Relationship_Count
            FROM ActivityRelationshipView
            {base_where_clause}
        ''')
        total_relationships = cursor.fetchone()[0]

        # Remaining Relationships - same as Total since we're already filtering by 'Incomplete'
        remaining_relationships = total_relationships

        # Lag Count - incomplete relationships with actual lag issues (Lag != 0 AND Lag IS NOT NULL)
        lag_filters = base_filters.copy()
        lag_filters.append("Lag != 0")
        lag_filters.append("Lag IS NOT NULL")
        
        lag_where_clause = " AND ".join(lag_filters)
        if lag_where_clause:
            lag_where_clause = "WHERE " + lag_where_clause

        cursor.execute(f'''
            SELECT COUNT(*) as Lag_Count
            FROM ActivityRelationshipView
            {lag_where_clause}
        ''')
        lag_count = cursor.fetchone()[0]

        # Calculate lag percentage
        lag_percentage = (lag_count / remaining_relationships * 100) if remaining_relationships > 0 else 0

        conn.close()
        return jsonify({
            'Total_Relationship_Count': int(total_relationships),
            'Remaining_Relationship_Count': int(remaining_relationships), 
            'Lag_Count': int(lag_count),
            'Lag_Percentage': float(round(lag_percentage, 2))
        })
        
    except Exception as e:
        print(f"Error in non_fs0d_kpi: {e}")
        conn.close()
        return jsonify({
            'Total_Relationship_Count': 0,
            'Remaining_Relationship_Count': 0,
            'Lag_Count': 0,
            'Lag_Percentage': 0.0
        })

@app.route('/api/leads')
def leads():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    relationship_type = request.args.get('relationship_type')
    driving = request.args.get('driving')
    lag = request.args.get('lag')
    free_float = request.args.get('free_float')
    project_id = request.args.get('project_id')

    filters = [
        "Relationship_Status = 'Incomplete'",
        "Lag < 0"
    ]
    if relationship_type and relationship_type != 'All':
        filters.append(f"RelationshipType = '{relationship_type}'")
    if driving and driving != 'All':
        filters.append(f"Driving = '{driving}'")
    if lag and lag != 'All':
        filters.append(f"Lag = {lag}")
    if free_float and free_float != 'All':
        filters.append(f"FreeFloat = {free_float}")
    # Project filter
    if project_id and project_id != 'All':
        filters.append(f"Project_ID = '{project_id}'")
    where_clause = " AND ".join(filters)
    if where_clause:
        where_clause = "WHERE " + where_clause
    query = f'''
        SELECT 
            Activity_ID, Activity_ID2, Activity_Name, Activity_Name2, RelationshipType, Lag, Driving, FreeFloat, Lead, ExcessiveLag, Relationship_Status
        FROM ActivityRelationshipView
        {where_clause}
    '''
    cursor.execute(query)
    rows = cursor.fetchall()
    conn.close()
    data = [
        {
            "Pred. ID": row[0],
            "Succ. ID": row[1],
            "Pred. Name": row[2],
            "Succ. Name": row[3],
            "Relationship type": row[4],
            "Lag": row[5],
            "Driving": row[6],
            "FreeFloat": row[7],
            "Lead": row[8],
            "ExcessiveLag": row[9],
            "Relationship_Status": row[10]
        }
        for row in rows
    ]
    return jsonify(data)

@app.route('/api/leads-relationship-type-options')
def get_leads_relationship_type_options():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT RelationshipType FROM ActivityRelationshipView WHERE Relationship_Status = 'Incomplete' AND Lag < 0 ORDER BY RelationshipType")
    types = [row[0] for row in cursor.fetchall()]
    conn.close()
    return jsonify(types)

@app.route('/api/leads-lag-options')
def get_leads_lag_options():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT Lag FROM ActivityRelationshipView WHERE Relationship_Status = 'Incomplete' AND Lag < 0 ORDER BY CAST(Lag AS REAL)")
    lags = [row[0] for row in cursor.fetchall()]
    conn.close()
    return jsonify(lags)

@app.route('/api/leads-free-float-options')
def get_leads_free_float_options():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT FreeFloat FROM ActivityRelationshipView WHERE Relationship_Status = 'Incomplete' AND Lag < 0 ORDER BY CAST(FreeFloat AS REAL)")
    free_floats = [row[0] for row in cursor.fetchall()]
    conn.close()
    return jsonify(free_floats)

@app.route('/api/leads-driving-options')
def get_leads_driving_options():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT Driving FROM ActivityRelationshipView WHERE Relationship_Status = 'Incomplete' AND Lag < 0 ORDER BY Driving")
    drivings = [row[0] for row in cursor.fetchall()]
    conn.close()
    return jsonify(drivings)

@app.route('/api/leads-kpi')
def leads_kpi():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    relationship_type = request.args.get('relationship_type')
    driving = request.args.get('driving')
    lag = request.args.get('lag')
    free_float = request.args.get('free_float')
    project_id = request.args.get('project_id')

    try:
        # Always calculate from ActivityRelationshipView with proper Leads filters
        # Build filters for leads calculation (Lag < 0 and Relationship_Status = 'Incomplete')
        leads_filters = [
            "Relationship_Status = 'Incomplete'",
            "Lag < 0"
        ]
        if relationship_type and relationship_type != 'All':
            leads_filters.append(f"RelationshipType = '{relationship_type}'")
        if driving and driving != 'All':
            leads_filters.append(f"Driving = '{driving}'")
        if lag and lag != 'All':
            leads_filters.append(f"Lag = {lag}")
        if free_float and free_float != 'All':
            leads_filters.append(f"FreeFloat = {free_float}")
        if project_id and project_id != 'All':
            leads_filters.append(f"Project_ID = '{project_id}'")
        
        leads_where_clause = " AND ".join(leads_filters)
        if leads_where_clause:
            leads_where_clause = "WHERE " + leads_where_clause

        # Calculate leads count
        cursor.execute(f'''
            SELECT COUNT(*) as Leads_Count
            FROM ActivityRelationshipView
            {leads_where_clause}
        ''')
        leads_count = cursor.fetchone()[0]

        # Build filters for remaining relationships calculation (only Relationship_Status = 'Incomplete')
        remaining_filters = ["Relationship_Status = 'Incomplete'"]
        if relationship_type and relationship_type != 'All':
            remaining_filters.append(f"RelationshipType = '{relationship_type}'")
        if driving and driving != 'All':
            remaining_filters.append(f"Driving = '{driving}'")
        if lag and lag != 'All':
            remaining_filters.append(f"Lag = {lag}")
        if free_float and free_float != 'All':
            remaining_filters.append(f"FreeFloat = {free_float}")
        if project_id and project_id != 'All':
            remaining_filters.append(f"Project_ID = '{project_id}'")
        
        remaining_where_clause = " AND ".join(remaining_filters)
        if remaining_where_clause:
            remaining_where_clause = "WHERE " + remaining_where_clause

        # Calculate remaining relationships count
        cursor.execute(f'''
            SELECT COUNT(*) as Remaining_Relationship_Count
            FROM ActivityRelationshipView
            {remaining_where_clause}
        ''')
        remaining_count = cursor.fetchone()[0]

        # Calculate total relationships for the project (for percentage calculation)
        total_filters = []
        if project_id and project_id != 'All':
            total_filters.append(f"Project_ID = '{project_id}'")
        
        total_where_clause = ""
        if total_filters:
            total_where_clause = "WHERE " + " AND ".join(total_filters)

        cursor.execute(f'''
            SELECT COUNT(*) as Total_Relationship_Count
            FROM ActivityRelationshipView
            {total_where_clause}
        ''')
        total_count = cursor.fetchone()[0]

        # Calculate lead percentage
        lead_percentage = 0
        if remaining_count > 0:
            lead_percentage = round((leads_count * 100.0) / remaining_count, 2)

        kpi_data = {
            "Total_Relationship_Count": int(total_count) if total_count is not None else 0,
            "Remaining_Relationship_Count": int(remaining_count) if remaining_count is not None else 0,
            "Leads_Count": int(leads_count) if leads_count is not None else 0,
            "Lead_Percentage": float(lead_percentage) if lead_percentage is not None else 0.0
        }
    except Exception as e:
        print(f"Error in leads-kpi: {e}")
        kpi_data = {
            "Total_Relationship_Count": 0,
            "Remaining_Relationship_Count": 0,
            "Leads_Count": 0,
            "Lead_Percentage": 0
        }
    finally:
        conn.close()
    
    return jsonify(kpi_data)

@app.route('/api/leads-chart-data')
def leads_chart_data():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    relationship_type = request.args.get('relationship_type')
    driving = request.args.get('driving')
    lag = request.args.get('lag')
    free_float = request.args.get('free_float')
    project_id = request.args.get('project_id')

    filters = [
        "Relationship_Status = 'Incomplete'",
        "Lag < 0"
    ]
    if relationship_type and relationship_type != 'All':
        filters.append(f"RelationshipType = '{relationship_type}'")
    if driving and driving != 'All':
        filters.append(f"Driving = '{driving}'")
    if lag and lag != 'All':
        filters.append(f"Lag = {lag}")
    if free_float and free_float != 'All':
        filters.append(f"FreeFloat = {free_float}")
    # Project filter
    if project_id and project_id != 'All':
        filters.append(f"Project_ID = '{project_id}'")
    where_clause = " AND ".join(filters)
    if where_clause:
        where_clause = "WHERE " + where_clause

    # Get stacked column chart data (Lag vs Count by Relationship Type)
    cursor.execute(f'''
        SELECT 
            Lag,
            RelationshipType,
            COUNT(*) as Count
        FROM ActivityRelationshipView
        {where_clause}
        GROUP BY Lag, RelationshipType
        ORDER BY Lag, RelationshipType
    ''')
    
    chart_data = []
    for row in cursor.fetchall():
        chart_data.append({
            "lag": row[0],
            "relationship_type": row[1],
            "count": row[2]
        })
    
    conn.close()
    return jsonify(chart_data)

@app.route('/api/leads-percentage-history')
def leads_percentage_history():
    # This is dummy historical data for leads percentage
    # In a real implementation, this would query historical data from the database
    return jsonify([
        {"month": "Jan", "year": 2024, "percentage": 8.5},
        {"month": "Feb", "year": 2024, "percentage": 7.2},
        {"month": "Mar", "year": 2024, "percentage": 6.8},
        {"month": "Apr", "year": 2024, "percentage": 5.9},
        {"month": "May", "year": 2024, "percentage": 4.3},
        {"month": "Jun", "year": 2024, "percentage": 3.7}
    ])

# === LAGS METRIC ENDPOINTS ===

@app.route('/api/lags')
def lags():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    relationship_type = request.args.get('relationship_type')
    driving = request.args.get('driving')
    lag = request.args.get('lag')
    free_float = request.args.get('free_float')
    project_id = request.args.get('project_id')

    filters = []

    # Apply base filters for Lags metric
    filters.append("Relationship_Status = 'Incomplete'")
    filters.append("Lag != 0")  # Lag is not 0
    filters.append("Lag IS NOT NULL")  # Lag is not blank

    # Apply RelationshipType filter
    if relationship_type and relationship_type != 'All':
        filters.append(f"RelationshipType = '{relationship_type}'")

    # Apply Driving filter
    if driving and driving != 'All':
        filters.append(f"Driving = '{driving}'")

    # Apply Lag filter
    if lag and lag != 'All':
        filters.append(f"Lag = {lag}")

    # Apply FreeFloat filter
    if free_float and free_float != 'All':
        filters.append(f"FreeFloat = {free_float}")

    # Apply Project filter
    if project_id and project_id != 'All':
        filters.append(f"Project_ID = '{project_id}'")

    where_clause = " AND ".join(filters)
    if where_clause:
        where_clause = "WHERE " + where_clause

    query = f'''
        SELECT 
            Activity_ID, Activity_ID2, Activity_Name, Activity_Name2, RelationshipType, Lag, Driving, FreeFloat, Lead, ExcessiveLag, Relationship_Status
        FROM ActivityRelationshipView
        {where_clause}
    '''
    cursor.execute(query)
    rows = cursor.fetchall()
    conn.close()
    
    # Map to dicts for JSON
    data = [
        {
            "Pred. ID": row[0],
            "Succ. ID": row[1],
            "Pred. Name": row[2],
            "Succ. Name": row[3],
            "Relationship type": row[4],
            "Lag": row[5],
            "Driving": row[6],
            "FreeFloat": row[7],
            "Lead": row[8],
            "ExcessiveLag": row[9],
            "Relationship_Status": row[10]
        }
        for row in rows
    ]
    return jsonify(data)

@app.route('/api/lags-relationship-type-options')
def get_lags_relationship_type_options():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT RelationshipType FROM ActivityRelationshipView WHERE Relationship_Status = 'Incomplete' AND Lag != 0 AND Lag IS NOT NULL ORDER BY RelationshipType")
    relationship_types = [row[0] for row in cursor.fetchall()]
    conn.close()
    return jsonify(relationship_types)

@app.route('/api/lags-lag-options')
def get_lags_lag_options():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT Lag FROM ActivityRelationshipView WHERE Relationship_Status = 'Incomplete' AND Lag != 0 AND Lag IS NOT NULL ORDER BY CAST(Lag AS REAL)")
    lags = [row[0] for row in cursor.fetchall()]
    conn.close()
    return jsonify(lags)

@app.route('/api/lags-free-float-options')
def get_lags_free_float_options():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT FreeFloat FROM ActivityRelationshipView WHERE Relationship_Status = 'Incomplete' AND Lag != 0 AND Lag IS NOT NULL ORDER BY CAST(FreeFloat AS REAL)")
    free_floats = [row[0] for row in cursor.fetchall()]
    conn.close()
    return jsonify(free_floats)

@app.route('/api/lags-driving-options')
def get_lags_driving_options():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT Driving FROM ActivityRelationshipView WHERE Relationship_Status = 'Incomplete' AND Lag != 0 AND Lag IS NOT NULL ORDER BY Driving")
    driving_options = [row[0] for row in cursor.fetchall()]
    conn.close()
    return jsonify(driving_options)

@app.route('/api/lags-kpi')
def lags_kpi():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    relationship_type = request.args.get('relationship_type')
    driving = request.args.get('driving')
    lag = request.args.get('lag')
    free_float = request.args.get('free_float')
    project_id = request.args.get('project_id')

    try:
        # Always calculate from ActivityRelationshipView with proper Lags filters
        # Build filters for lags calculation (Lag != 0, Lag IS NOT NULL, and Relationship_Status = 'Incomplete')
        lags_filters = [
            "Relationship_Status = 'Incomplete'",
            "Lag != 0",
            "Lag IS NOT NULL"
        ]
        if relationship_type and relationship_type != 'All':
            lags_filters.append(f"RelationshipType = '{relationship_type}'")
        if driving and driving != 'All':
            lags_filters.append(f"Driving = '{driving}'")
        if lag and lag != 'All':
            lags_filters.append(f"Lag = {lag}")
        if free_float and free_float != 'All':
            lags_filters.append(f"FreeFloat = {free_float}")
        if project_id and project_id != 'All':
            lags_filters.append(f"Project_ID = '{project_id}'")
        
        lags_where_clause = " AND ".join(lags_filters)
        if lags_where_clause:
            lags_where_clause = "WHERE " + lags_where_clause

        # Calculate lags count
        cursor.execute(f'''
            SELECT COUNT(*) as Lag_Count
            FROM ActivityRelationshipView
            {lags_where_clause}
        ''')
        lag_count = cursor.fetchone()[0]

        # Build filters for remaining relationships calculation (only Relationship_Status = 'Incomplete')
        remaining_filters = ["Relationship_Status = 'Incomplete'"]
        if relationship_type and relationship_type != 'All':
            remaining_filters.append(f"RelationshipType = '{relationship_type}'")
        if driving and driving != 'All':
            remaining_filters.append(f"Driving = '{driving}'")
        if lag and lag != 'All':
            remaining_filters.append(f"Lag = {lag}")
        if free_float and free_float != 'All':
            remaining_filters.append(f"FreeFloat = {free_float}")
        if project_id and project_id != 'All':
            remaining_filters.append(f"Project_ID = '{project_id}'")
        
        remaining_where_clause = " AND ".join(remaining_filters)
        if remaining_where_clause:
            remaining_where_clause = "WHERE " + remaining_where_clause

        # Calculate remaining relationships count
        cursor.execute(f'''
            SELECT COUNT(*) as Remaining_Relationships
            FROM ActivityRelationshipView
            {remaining_where_clause}
        ''')
        remaining_relationships = cursor.fetchone()[0]

        # Calculate lag percentage
        lag_percentage = 0
        if remaining_relationships > 0:
            lag_percentage = round((lag_count * 100.0) / remaining_relationships, 1)

        kpi_data = {
            "Lag_Count": int(lag_count) if lag_count is not None else 0,
            "Remaining_Relationships": int(remaining_relationships) if remaining_relationships is not None else 0,
            "Lag_Percentage": float(lag_percentage) if lag_percentage is not None else 0.0
        }
    except Exception as e:
        print(f"Error in lags-kpi: {e}")
        kpi_data = {
            "Lag_Count": 0,
            "Remaining_Relationships": 0,
            "Lag_Percentage": 0.0
        }
    finally:
        conn.close()
    
    return jsonify(kpi_data)

@app.route('/api/lags-chart-data')
def lags_chart_data():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    relationship_type = request.args.get('relationship_type')
    driving = request.args.get('driving')
    lag = request.args.get('lag')
    free_float = request.args.get('free_float')
    project_id = request.args.get('project_id')

    filters = []
    filters.append("Relationship_Status = 'Incomplete'")
    filters.append("Lag != 0")
    filters.append("Lag IS NOT NULL")

    if relationship_type and relationship_type != 'All':
        filters.append(f"RelationshipType = '{relationship_type}'")
    if driving and driving != 'All':
        filters.append(f"Driving = '{driving}'")
    if lag and lag != 'All':
        filters.append(f"Lag = {lag}")
    if free_float and free_float != 'All':
        filters.append(f"FreeFloat = {free_float}")
    if project_id and project_id != 'All':
        filters.append(f"Project_ID = '{project_id}'")

    where_clause = " AND ".join(filters)
    if where_clause:
        where_clause = "WHERE " + where_clause

    query = f'''
        SELECT Lag, RelationshipType, COUNT(*) as count
        FROM ActivityRelationshipView
        {where_clause}
        GROUP BY Lag, RelationshipType
        ORDER BY CAST(Lag AS REAL), RelationshipType
    '''
    
    cursor.execute(query)
    rows = cursor.fetchall()
    conn.close()

    # Structure data for stacked column chart
    chart_data = {}
    for row in rows:
        lag_value = str(row[0])
        relationship_type = row[1]
        count = row[2]
        
        if lag_value not in chart_data:
            chart_data[lag_value] = {}
        chart_data[lag_value][relationship_type] = count

    return jsonify(chart_data)

@app.route('/api/lags-percentage-history')
def lags_percentage_history():
    # This is dummy historical data for lags percentage
    # In a real implementation, this would query historical data from the database
    return jsonify([
        {"month": "Jan", "year": 2024, "percentage": 12.3},
        {"month": "Feb", "year": 2024, "percentage": 11.8},
        {"month": "Mar", "year": 2024, "percentage": 10.5},
        {"month": "Apr", "year": 2024, "percentage": 9.7},
        {"month": "May", "year": 2024, "percentage": 8.9},
        {"month": "Jun", "year": 2024, "percentage": 8.2}
    ])

# === EXCESSIVE LAGS METRIC ENDPOINTS ===

@app.route('/api/excessive-lags')
def excessive_lags():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    relationship_type = request.args.get('relationship_type')
    driving = request.args.get('driving')
    lag = request.args.get('lag')
    free_float = request.args.get('free_float')
    project_id = request.args.get('project_id')

    filters = []

    # Apply base filters for Excessive Lags metric
    filters.append("Relationship_Status = 'Incomplete'")
    filters.append("ExcessiveLag = 'Excessive Lag'")  # Filter for excessive lag

    # Apply RelationshipType filter
    if relationship_type and relationship_type != 'All':
        filters.append(f"RelationshipType = '{relationship_type}'")

    # Apply Driving filter
    if driving and driving != 'All':
        filters.append(f"Driving = '{driving}'")

    # Apply Lag filter
    if lag and lag != 'All':
        filters.append(f"Lag = {lag}")

    # Apply FreeFloat filter
    if free_float and free_float != 'All':
        filters.append(f"FreeFloat = {free_float}")

    # Apply Project filter
    if project_id and project_id != 'All':
        filters.append(f"Project_ID = '{project_id}'")

    where_clause = " AND ".join(filters)
    if where_clause:
        where_clause = "WHERE " + where_clause

    query = f'''
        SELECT 
            Activity_ID, Activity_ID2, Activity_Name, Activity_Name2, RelationshipType, Lag, Driving, FreeFloat, Lead, ExcessiveLag, Relationship_Status
        FROM ActivityRelationshipView
        {where_clause}
    '''
    cursor.execute(query)
    rows = cursor.fetchall()
    conn.close()
    
    # Map to dicts for JSON
    data = [
        {
            "Pred. ID": row[0],
            "Succ. ID": row[1],
            "Pred. Name": row[2],
            "Succ. Name": row[3],
            "Relationship type": row[4],
            "Lag": row[5],
            "Driving": row[6],
            "FreeFloat": row[7],
            "Lead": row[8],
            "ExcessiveLag": row[9],
            "Relationship_Status": row[10]
        }
        for row in rows
    ]
    return jsonify(data)

@app.route('/api/excessive-lags-relationship-type-options')
def get_excessive_lags_relationship_type_options():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT RelationshipType FROM ActivityRelationshipView WHERE Relationship_Status = 'Incomplete' AND ExcessiveLag = 'Excessive Lag' ORDER BY RelationshipType")
    relationship_types = [row[0] for row in cursor.fetchall()]
    conn.close()
    return jsonify(relationship_types)

@app.route('/api/excessive-lags-lag-options')
def get_excessive_lags_lag_options():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT Lag FROM ActivityRelationshipView WHERE Relationship_Status = 'Incomplete' AND ExcessiveLag = 'Excessive Lag' ORDER BY CAST(Lag AS REAL)")
    lags = [row[0] for row in cursor.fetchall()]
    conn.close()
    return jsonify(lags)

@app.route('/api/excessive-lags-free-float-options')
def get_excessive_lags_free_float_options():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT FreeFloat FROM ActivityRelationshipView WHERE Relationship_Status = 'Incomplete' AND ExcessiveLag = 'Excessive Lag' ORDER BY CAST(FreeFloat AS REAL)")
    free_floats = [row[0] for row in cursor.fetchall()]
    conn.close()
    return jsonify(free_floats)

@app.route('/api/excessive-lags-driving-options')
def get_excessive_lags_driving_options():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT Driving FROM ActivityRelationshipView WHERE Relationship_Status = 'Incomplete' AND ExcessiveLag = 'Excessive Lag' ORDER BY Driving")
    driving_options = [row[0] for row in cursor.fetchall()]
    conn.close()
    return jsonify(driving_options)

@app.route('/api/excessive-lags-kpi')
def excessive_lags_kpi():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    relationship_type = request.args.get('relationship_type')
    driving = request.args.get('driving')
    lag = request.args.get('lag')
    free_float = request.args.get('free_float')
    project_id = request.args.get('project_id')

    # Always calculate from ActivityRelationshipView with proper filtering
    filters = []
    filters.append("Relationship_Status = 'Incomplete'")
    filters.append("ExcessiveLag = 'Excessive Lag'")

    if relationship_type and relationship_type != 'All':
        filters.append(f"RelationshipType = '{relationship_type}'")
    if driving and driving != 'All':
        filters.append(f"Driving = '{driving}'")
    if lag and lag != 'All':
        filters.append(f"Lag = {lag}")
    if free_float and free_float != 'All':
        filters.append(f"FreeFloat = {free_float}")
    if project_id and project_id != 'All':
        filters.append(f"Project_ID = '{project_id}'")

    where_clause = " AND ".join(filters)
    if where_clause:
        where_clause = "WHERE " + where_clause

    # Excessive Lag Count
    cursor.execute(f'SELECT COUNT(*) FROM ActivityRelationshipView {where_clause}')
    lag_count = cursor.fetchone()[0]

    # Total relationships for percentage calculation (remaining relationships with same filters except ExcessiveLag)
    total_filters = ["Relationship_Status = 'Incomplete'"]
    if relationship_type and relationship_type != 'All':
        total_filters.append(f"RelationshipType = '{relationship_type}'")
    if driving and driving != 'All':
        total_filters.append(f"Driving = '{driving}'")
    if free_float and free_float != 'All':
        total_filters.append(f"FreeFloat = {free_float}")
    if project_id and project_id != 'All':
        total_filters.append(f"Project_ID = '{project_id}'")

    total_where_clause = " AND ".join(total_filters)
    if total_where_clause:
        total_where_clause = "WHERE " + total_where_clause

    cursor.execute(f'SELECT COUNT(*) FROM ActivityRelationshipView {total_where_clause}')
    total_relationships = cursor.fetchone()[0]

    # Calculate percentage
    lag_percentage = (lag_count / total_relationships * 100) if total_relationships > 0 else 0

    conn.close()

    return jsonify({
        "Lag_Count": int(lag_count),
        "Remaining_Relationships": int(total_relationships),
        "Lag_Percentage": float(round(lag_percentage, 1))
    })

@app.route('/api/excessive-lags-chart-data')
def excessive_lags_chart_data():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    relationship_type = request.args.get('relationship_type')
    driving = request.args.get('driving')
    lag = request.args.get('lag')
    free_float = request.args.get('free_float')
    project_id = request.args.get('project_id')

    filters = []
    filters.append("Relationship_Status = 'Incomplete'")
    filters.append("ExcessiveLag = 'Excessive Lag'")

    if relationship_type and relationship_type != 'All':
        filters.append(f"RelationshipType = '{relationship_type}'")
    if driving and driving != 'All':
        filters.append(f"Driving = '{driving}'")
    if lag and lag != 'All':
        filters.append(f"Lag = {lag}")
    if free_float and free_float != 'All':
        filters.append(f"FreeFloat = {free_float}")
    if project_id and project_id != 'All':
        filters.append(f"Project_ID = '{project_id}'")

    where_clause = " AND ".join(filters)
    if where_clause:
        where_clause = "WHERE " + where_clause

    query = f'''
        SELECT Lag, RelationshipType, COUNT(*) as count
        FROM ActivityRelationshipView
        {where_clause}
        GROUP BY Lag, RelationshipType
        ORDER BY CAST(Lag AS REAL), RelationshipType
    '''
    
    cursor.execute(query)
    rows = cursor.fetchall()
    conn.close()

    # Structure data for stacked column chart
    chart_data = {}
    for row in rows:
        lag_value = str(row[0])
        relationship_type = row[1]
        count = row[2]
        
        if lag_value not in chart_data:
            chart_data[lag_value] = {}
        chart_data[lag_value][relationship_type] = count

    return jsonify(chart_data)

@app.route('/api/excessive-lags-percentage-history')
def excessive_lags_percentage_history():
    # This is dummy historical data for excessive lags percentage
    # In a real implementation, this would query historical data from the database
    return jsonify([
        {"month": "Jan", "year": 2024, "percentage": 15.2},
        {"month": "Feb", "year": 2024, "percentage": 14.6},
        {"month": "Mar", "year": 2024, "percentage": 13.1},
        {"month": "Apr", "year": 2024, "percentage": 12.4},
        {"month": "May", "year": 2024, "percentage": 11.7},
        {"month": "Jun", "year": 2024, "percentage": 10.9}
    ])

if __name__ == '__main__':
    app.run(debug=True, port=5000) 