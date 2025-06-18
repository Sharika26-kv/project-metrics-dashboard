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
        # !!! IMPORTANT: Replace 'ProjectID' with the actual column name for projects in your DB
        cursor.execute("SELECT DISTINCT ProjectID FROM ActivityRelationshipView ORDER BY ProjectID")
        projects = [row[0] for row in cursor.fetchall()]
    except sqlite3.OperationalError as e:
        print(f"Error fetching ProjectID options: {e}. Please ensure 'ProjectID' is the correct column name.")
        projects = [] # Return empty list if column not found
    conn.close()
    return jsonify(projects)

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

    # ProjectID filter - Placeholder for now, not applied to SQL query
    # if project_id and project_id != 'All':
    #     filters.append(f"ProjectID = '{project_id}'") 

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

    # Filters for Total_Relationship_Count and Remaining_Relationship_Count
    base_kpi_filters = []
    base_kpi_filters.append("Relationship_Status = 'Incomplete'") # Fixed condition for KPI
    # Removed hardcoded Lag = 0, now dynamic filter is applied below

    if relationship_type and relationship_type != 'All':
        base_kpi_filters.append(f"RelationshipType = '{relationship_type}'")
    else:
        base_kpi_filters.append("RelationshipType IN ('PR_FS', 'PR_FS1')")

    if driving and driving != 'All':
        base_kpi_filters.append(f"Driving = '{driving}'")

    if lag and lag != 'All':
        base_kpi_filters.append(f"Lag = {lag}")

    if free_float and free_float != 'All':
        base_kpi_filters.append(f"FreeFloat = {free_float}")

    # ProjectID filter - Placeholder for now, not applied to SQL query
    # if project_id and project_id != 'All':
    #     base_kpi_filters.append(f"ProjectID = '{project_id}'")

    base_kpi_where_clause = " AND ".join(base_kpi_filters)
    if base_kpi_where_clause:
        base_kpi_where_clause = "WHERE " + base_kpi_where_clause

    # Total Relationships (filtered)
    cursor.execute(f'SELECT COUNT(*) FROM ActivityRelationshipView {base_kpi_where_clause}')
    total_relationships = cursor.fetchone()[0]

    # Remaining Relationships (using the same base filter)
    cursor.execute(f'SELECT COUNT(*) FROM ActivityRelationshipView {base_kpi_where_clause}')
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

    # ProjectID filter - Placeholder for now, not applied to SQL query
    # if project_id and project_id != 'All':
    #     lag_count_filters.append(f"ProjectID = '{project_id}'")

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

    # ProjectID filter - Placeholder for now, not applied to SQL query
    # if project_id and project_id != 'All':
    #     filters.append(f"ProjectID = '{project_id}'")

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
        "Lag IS NOT NULL AND Lag != 0 AND Lag != ''"
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
    # ProjectID filter - Placeholder for now
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
    cursor.execute("SELECT DISTINCT Lag FROM ActivityRelationshipView WHERE RelationshipType NOT IN ('PR_FS', 'PR_FS1') AND Lag IS NOT NULL AND Lag != 0 AND Lag != '' ORDER BY CAST(Lag AS REAL)")
    lags = [row[0] for row in cursor.fetchall()]
    conn.close()
    return jsonify(lags)

@app.route('/api/nonfs-free-float-options')
def get_nonfs_free_float_options():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT FreeFloat FROM ActivityRelationshipView WHERE RelationshipType NOT IN ('PR_FS', 'PR_FS1') AND Lag IS NOT NULL AND Lag != 0 AND Lag != '' ORDER BY CAST(FreeFloat AS REAL)")
    free_floats = [row[0] for row in cursor.fetchall()]
    conn.close()
    return jsonify(free_floats)

@app.route('/api/nonfs-driving-options')
def get_nonfs_driving_options():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT Driving FROM ActivityRelationshipView WHERE RelationshipType NOT IN ('PR_FS', 'PR_FS1') AND Lag IS NOT NULL AND Lag != 0 AND Lag != '' ORDER BY Driving")
    drivings = [row[0] for row in cursor.fetchall()]
    conn.close()
    return jsonify(drivings)

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
    # ProjectID filter - Placeholder for now
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
        # Try different possible names for the FinalActivityKPIView
        view_found = False
        kpi_data = None
        
        for view_name in ['FinalActivityKPIView', 'finalactivityKPIview', 'FinalActivityKPI', 'finalactivitykpi']:
            try:
                cursor.execute(f"SELECT * FROM {view_name} LIMIT 1")
                row = cursor.fetchone()
                if row:
                    # Get column names
                    cursor.execute(f"PRAGMA table_info({view_name})")
                    columns = [col[1] for col in cursor.fetchall()]
                    
                    # Map the data based on available columns
                    leads_count = 0
                    lead_percentage = 0
                    
                    # Look for leads count column
                    for i, col in enumerate(columns):
                        if 'leads' in col.lower() and 'count' in col.lower():
                            leads_count = row[i] if row[i] else 0
                        elif 'lead' in col.lower() and 'percentage' in col.lower():
                            lead_percentage = row[i] if row[i] else 0
                    
                    kpi_data = {
                        "Total_Relationship_Count": leads_count,
                        "Remaining_Relationship_Count": leads_count,
                        "Leads_Count": leads_count,
                        "Lead_Percentage": lead_percentage
                    }
                    view_found = True
                    break
            except:
                continue
        
        if not view_found:
            # FinalActivityKPIView doesn't exist, calculate from ActivityRelationshipView
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
            
            where_clause = " AND ".join(filters)
            if where_clause:
                where_clause = "WHERE " + where_clause

            cursor.execute(f'''
                SELECT 
                    COUNT(*) as Total_Relationship_Count,
                    COUNT(*) as Remaining_Relationship_Count,
                    COUNT(*) as Leads_Count,
                    ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM ActivityRelationshipView WHERE Relationship_Status = 'Incomplete'), 2) as Lead_Percentage
                FROM ActivityRelationshipView
                {where_clause}
            ''')
            
            row = cursor.fetchone()
            kpi_data = {
                "Total_Relationship_Count": row[0] if row else 0,
                "Remaining_Relationship_Count": row[1] if row else 0,
                "Leads_Count": row[2] if row else 0,
                "Lead_Percentage": row[3] if row else 0
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
    # ProjectID filter - Placeholder for now
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
        # Try to get data from FinalActivityKPIView first
        cursor.execute("SELECT Lag_Count, Lag_Percentage FROM FinalActivityKPIView LIMIT 1")
        kpi_data = cursor.fetchone()
        
        if kpi_data:
            lag_count = kpi_data[0] if kpi_data[0] is not None else 0
            lag_percentage = kpi_data[1] if kpi_data[1] is not None else 0
        else:
            raise Exception("No data in FinalActivityKPIView")
            
    except Exception as e:
        print(f"FinalActivityKPIView not accessible: {e}. Using fallback calculations.")
        
        # Fallback calculations
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

        where_clause = " AND ".join(filters)
        if where_clause:
            where_clause = "WHERE " + where_clause

        # Lag Count
        cursor.execute(f'SELECT COUNT(*) FROM ActivityRelationshipView {where_clause}')
        lag_count = cursor.fetchone()[0]

        # Total relationships for percentage calculation
        total_filters = ["Relationship_Status = 'Incomplete'"]
        if relationship_type and relationship_type != 'All':
            total_filters.append(f"RelationshipType = '{relationship_type}'")
        if driving and driving != 'All':
            total_filters.append(f"Driving = '{driving}'")
        if free_float and free_float != 'All':
            total_filters.append(f"FreeFloat = {free_float}")

        total_where_clause = " AND ".join(total_filters)
        if total_where_clause:
            total_where_clause = "WHERE " + total_where_clause

        cursor.execute(f'SELECT COUNT(*) FROM ActivityRelationshipView {total_where_clause}')
        total_relationships = cursor.fetchone()[0]

        # Calculate percentage
        lag_percentage = (lag_count / total_relationships * 100) if total_relationships > 0 else 0

    # Remaining relationships calculation
    remaining_filters = ["Relationship_Status = 'Incomplete'"]
    if relationship_type and relationship_type != 'All':
        remaining_filters.append(f"RelationshipType = '{relationship_type}'")
    if driving and driving != 'All':
        remaining_filters.append(f"Driving = '{driving}'")
    if free_float and free_float != 'All':
        remaining_filters.append(f"FreeFloat = {free_float}")

    remaining_where_clause = " AND ".join(remaining_filters)
    if remaining_where_clause:
        remaining_where_clause = "WHERE " + remaining_where_clause

    cursor.execute(f'SELECT COUNT(*) FROM ActivityRelationshipView {remaining_where_clause}')
    remaining_relationships = cursor.fetchone()[0]

    conn.close()

    return jsonify({
        "Lag_Count": lag_count,
        "Remaining_Relationships": remaining_relationships,
        "Lag_Percentage": round(lag_percentage, 1)
    })

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

    try:
        # Try to get data from FinalActivityKPIView first
        cursor.execute("SELECT Lag_Count, Lag_Percentage FROM FinalActivityKPIView LIMIT 1")
        kpi_data = cursor.fetchone()
        
        if kpi_data:
            lag_count = kpi_data[0] if kpi_data[0] is not None else 0
            lag_percentage = kpi_data[1] if kpi_data[1] is not None else 0
        else:
            raise Exception("No data in FinalActivityKPIView")
            
    except Exception as e:
        print(f"FinalActivityKPIView not accessible: {e}. Using fallback calculations.")
        
        # Fallback calculations
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

        where_clause = " AND ".join(filters)
        if where_clause:
            where_clause = "WHERE " + where_clause

        # Excessive Lag Count
        cursor.execute(f'SELECT COUNT(*) FROM ActivityRelationshipView {where_clause}')
        lag_count = cursor.fetchone()[0]

        # Total relationships for percentage calculation
        total_filters = ["Relationship_Status = 'Incomplete'"]
        if relationship_type and relationship_type != 'All':
            total_filters.append(f"RelationshipType = '{relationship_type}'")
        if driving and driving != 'All':
            total_filters.append(f"Driving = '{driving}'")
        if free_float and free_float != 'All':
            total_filters.append(f"FreeFloat = {free_float}")

        total_where_clause = " AND ".join(total_filters)
        if total_where_clause:
            total_where_clause = "WHERE " + total_where_clause

        cursor.execute(f'SELECT COUNT(*) FROM ActivityRelationshipView {total_where_clause}')
        total_relationships = cursor.fetchone()[0]

        # Calculate percentage
        lag_percentage = (lag_count / total_relationships * 100) if total_relationships > 0 else 0

    # Remaining relationships calculation
    remaining_filters = ["Relationship_Status = 'Incomplete'"]
    if relationship_type and relationship_type != 'All':
        remaining_filters.append(f"RelationshipType = '{relationship_type}'")
    if driving and driving != 'All':
        remaining_filters.append(f"Driving = '{driving}'")
    if free_float and free_float != 'All':
        remaining_filters.append(f"FreeFloat = {free_float}")

    remaining_where_clause = " AND ".join(remaining_filters)
    if remaining_where_clause:
        remaining_where_clause = "WHERE " + remaining_where_clause

    cursor.execute(f'SELECT COUNT(*) FROM ActivityRelationshipView {remaining_where_clause}')
    remaining_relationships = cursor.fetchone()[0]

    conn.close()

    return jsonify({
        "Lag_Count": lag_count,
        "Remaining_Relationships": remaining_relationships,
        "Lag_Percentage": round(lag_percentage, 1)
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