# Project Metrics Dashboard

A comprehensive web-based dashboard for analyzing project metrics from Primavera XER files. This application provides interactive visualizations and filtering capabilities for relationship analysis, lag tracking, and project health monitoring.

## Features

### 📊 **Five Key Metrics Dashboards:**
1. **FS+0d Lag** - Traditional Finish-to-Start relationships with zero lag
2. **Non FS+0d Lag** - All other relationship types 
3. **Leads** - Negative lag analysis (Lead ≠ 0)
4. **Lags** - Positive lag analysis (Lag ≠ 0)
5. **Excessive Lags** - Critical lag analysis (ExcessiveLag = 'Excessive Lag')

### 🎯 **Key Features:**
- **Interactive Filtering**: Each metric has independent filters for relationship type, driving status, lag values, and free float
- **Real-time Charts**: Stacked column charts and trend line visualizations using Chart.js
- **Data Tables**: Sortable tables with CSV export functionality 
- **KPI Cards**: Key performance indicators including counts and percentages
- **Responsive Design**: Modern, professional UI with WCAG 2.1 accessibility compliance
- **XER File Support**: Direct parsing of Primavera P6 XER files into SQLite database

## Project Structure

```
metrics-dashboard/
│
├── metrics_api.py              # Flask backend API
├── metrics_dashboard.html      # Frontend dashboard
├── xer_to_sqlite.py           # XER file parser
├── requirements.txt           # Python dependencies
├── README.md                  # Project documentation
└── mydata.db                  # SQLite database (generated)
```

## Setup Instructions

### Prerequisites
- Python 3.7+
- Flask
- Pandas
- SQLite3

### Installation

1. **Clone the repository:**
   ```bash
   git clone <your-repo-url>
   cd metrics-dashboard
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Prepare your data:**
   - Place your XER files in a folder (e.g., `Xer/`)
   - Update the path in `xer_to_sqlite.py` if needed:
     ```python
     xer_folder = r'C:\path\to\your\Xer'
     db_path = r'C:\path\to\your\mydata.db'
     ```

4. **Parse XER files to database:**
   ```bash
   python xer_to_sqlite.py
   ```

5. **Update database path in API:**
   - Edit `metrics_api.py` and update the `DB_PATH` variable:
     ```python
     DB_PATH = r'C:\path\to\your\mydata.db'
     ```

6. **Run the application:**
   ```bash
   python metrics_api.py
   ```

7. **Access the dashboard:**
   Open your browser and navigate to: `http://127.0.0.1:5000`

## Usage

### Dashboard Navigation
- **Sidebar**: Select metrics to display (single selection mode)
- **Filter Bar**: Apply filters specific to each metric
- **Charts**: Interactive visualizations with hover details
- **Data Cards**: Key performance indicators
- **Tables**: Detailed data with sorting and export capabilities

### Filter Options
Each metric supports independent filtering:
- **Relationship Type**: PR_FS, PR_FF, PR_SF, PR_SS, etc.
- **Driving**: Yes/No status
- **Lag Values**: Specific lag values from your data
- **Free Float**: Free float values from your data

### Data Export
- Click "Export CSV" on any table to download data
- Charts can be saved as images (right-click context menu)

## Database Schema

The application expects these key tables/views:
- **ActivityRelationshipView**: Main relationship data
- **FinalActivityKPIView**: KPI calculations (optional, with fallback)

### Key Columns:
- `Activity_ID`, `Activity_ID2`: Predecessor/Successor IDs
- `Activity_Name`, `Activity_Name2`: Activity names
- `RelationshipType`: Relationship type (PR_FS, etc.)
- `Lag`: Lag values
- `Driving`: Driving status
- `FreeFloat`: Free float values
- `Lead`: Lead values
- `ExcessiveLag`: Excessive lag classification
- `Relationship_Status`: Incomplete/Complete status

## Technical Details

### Backend (Flask API)
- **Framework**: Flask with SQLite
- **Endpoints**: RESTful API with 30+ endpoints
- **Filtering**: Dynamic SQL generation based on user selections
- **Error Handling**: Graceful fallbacks for missing data

### Frontend (HTML/JavaScript)
- **Charts**: Chart.js with professional styling
- **Responsiveness**: CSS Grid and Flexbox layouts
- **Accessibility**: WCAG 2.1 compliant design
- **Interactivity**: Real-time updates without page refresh

### Data Processing
- **XER Parser**: Custom parser for Primavera XER format
- **Database**: SQLite for lightweight, portable storage
- **Performance**: Optimized queries with proper indexing

## Troubleshooting

### Common Issues:

1. **"No such table: ActivityRelationshipView"**
   - Ensure XER files are parsed correctly
   - Check database path in both parser and API

2. **Empty data or charts**
   - Verify your XER files contain relationship data
   - Check filter settings aren't too restrictive

3. **Port already in use**
   - Change the port in `metrics_api.py`:
     ```python
     app.run(debug=True, port=5001)
     ```

### PowerShell Commands (Windows)
```powershell
# Navigate and run (PowerShell syntax)
cd C:\path\to\project; python metrics_api.py

# Check files
Get-ChildItem *.py, *.html
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

This project is provided as-is for project management and analysis purposes.

## Screenshots

### Dashboard Overview
The main dashboard provides a clean, professional interface with:
- Sidebar navigation for metric selection
- Filter controls for each metric
- Interactive charts and KPI cards
- Detailed data tables with export functionality

### Key Metrics
- **FS+0d Lag**: Traditional precedence relationships
- **Leads/Lags**: Schedule compression and extension analysis  
- **Excessive Lags**: Critical path impact analysis

---

**Author**: Created for project schedule analysis and reporting
**Last Updated**: June 2025 