# Triathlon NSW Calculation Engine

A Python application that processes triathlon race results and calculates performance points, participation points, and generates league ladders and MVP rankings for Triathlon NSW.

## Overview

This program automatically processes triathlon race results from Excel files, calculates club points based on performance and participation, and generates comprehensive reports including:

- Round ladders with point breakdowns
- Cumulative season ladders
- Individual MVP rankings (round and season)
- Club-specific MVP breakdowns

## Features

- **Automatic Processing**: Processes all new round files in the `data/input` directory
- **Point Calculations**:
  - Performance points (top 10 finishers per category: 10, 9, 8, 7, 6, 5, 4, 3, 2, 1)
  - Participation points (based on finisher thresholds: 5%, 10%, 20% of ICL eligible numbers)
- **Double Points Support**: Automatically applies double points for designated events
- **Season Tracking**: Maintains cumulative season statistics and history

## Directory Structure

```
Triathlon NSW Calculation Engine/
├── calculation_engine.py      # Main program file
├── calculation_engine.exe     # Compiled executable (after building)
├── build.bat                  # Build script to create executable
├── requirements.txt           # Python dependencies
├── data/
│   ├── input/                 # Place input files here
│   ├── output/                # Generated reports appear here
│   ├── processed/             # Processed files are moved here
│   └── season/
│       └── current_season/    # Season tracking files
└── venv/                      # Python virtual environment
```

## Setup and Installation

### Prerequisites

- Python 3.x installed (Python 3.7 or higher recommended)
- pip (Python package installer)

### Creating a Virtual Environment

1. **Open Command Prompt** in the project directory

2. **Create a virtual environment**:
   ```cmd
   python -m venv venv
   ```
   This creates a `venv` folder in your project directory.

3. **Activate the virtual environment**:
   ```cmd
   venv\Scripts\activate
   ```
   You should see `(venv)` at the beginning of your command prompt, indicating the virtual environment is active.

4. **Install required packages**:
   ```cmd
   pip install -r requirements.txt
   ```
   This installs all necessary dependencies (pandas, numpy, openpyxl, pyinstaller).

5. **Verify installation**:
   ```cmd
   pip list
   ```
   You should see pandas, numpy, openpyxl, and pyinstaller in the list.


**Note**: Always create the virtual environment before running the program or building the executable.

## Building the Executable

### Prerequisites

- Python 3.x installed
- Virtual environment created and activated (see Setup section above)
- Required packages installed via `requirements.txt`

### Steps to Build

**Important**: Make sure you have completed the [Setup and Installation](#setup-and-installation) steps first.

1. **Open Command Prompt** in the project directory
2. **Run the build script**:

   ```cmd
   build.bat
   ```

   Or simply **double-click** `build.bat` in Windows Explorer

   The script will automatically:
   - Activate the virtual environment
   - Clean old build files
   - Build the executable using PyInstaller
   - Create `calculation_engine.exe` in the main directory
3. **Wait for completion**: The build process may take a few minutes
4. **Verify**: You should see "BUILD SUCCESSFUL!" message and `calculation_engine.exe` in the directory

### Troubleshooting Build Issues

- **Build fails**: Check that all dependencies are installed in the virtual environment

## Running the Program

### Method 1: Using the Executable (Recommended)

1. **Double-click** `calculation_engine.exe`

   - The program will run in a console window
   - Follow the on-screen prompts
2. **Or run from Command Prompt**:

   ```cmd
   calculation_engine.exe
   ```

### Method 2: Using Python Script

**Note**: Make sure you have completed the [Setup and Installation](#setup-and-installation) steps first.

1. **Activate virtual environment**:

   ```cmd
   venv\Scripts\activate
   ```
   You should see `(venv)` at the beginning of your command prompt.

2. **Run the script**:

   ```cmd
   python calculation_engine.py
   ```

## Preparing Input Data

### Required Files

#### 1. Season Configuration File

- **Filename**: `Triathlon Season.xlsx`
- **Location**: `data/input/` directory
- **Required Columns**:
  - `League Name`
  - `Round`
  - `Events or Rounds`
  - `Double Points` (Yes/No)
  - `Per P & Part P` (comma-separated race types)
  - `Part P` (comma-separated race types)
  - `Clubs`

#### 2. Round Result Files

- **Filename Format**: `[League Name] Round [Number] [Event Name].xlsx`
  - Example: `Sydney Premier League Round 1 IRONMAN 70.3 and Sprint.xlsx` or ``Sydney Premier League Round 1.xlsx``
- **Location**: `data/input/` directory

### Excel File Structure

Each round file must contain:

#### Sheet 1: "Current ICL Eligible Number"

Required columns:

- `Club` - Club name (must match exactly with race results)
- `ICL Eligible Number` - Number of eligible members
- `15PTS (5%)` - 5% threshold for 15 points
- `30 PTS (10%)` - 10% threshold for 30 points
- `45 PTS (20%)` - 20% threshold for 45 points

#### Additional Sheets: Race Results

Each race type gets its own sheet (e.g., "Round 1 Sprint Distance", "Round 1 IRONMAN 70.3")

**Required Columns** (column names are flexible - the program recognizes variations):

- `First Name` (or: FORENAME, FirstName, Given Name)
- `Surname` (or: SURNAME, LastName, Family Name)
- `TA Number` (or: TANumber, TA_Number, Membership)
- `Category` (or: CATGY, Race Category, Division)
- `Category Finish Place` (or: FINISH_CAT_PLACE, Cat Place, Division Place)
- `Club Name` (or: Triathlon Club, Club, CLUB)

**Optional Columns**:

- `Per P` (or: Performance points, Performance Points, Perf Points)

### Example File Structure

```
Sydney Premier League Round 1 IRONMAN 70.3 and Sprint.xlsx
├── Sheet: "Current ICL Eligible Number"
│   └── Columns: Club | ICL Eligible Number | 15PTS (5%) | 30 PTS (10%) | 45 PTS (20%)
├── Sheet: "Round 1 Sprint Distance"
│   └── Columns: First Name | Surname | TA Number | Category | Category Finish Place | Club Name
└── Sheet: "Round 1 IRONMAN 70.3"
    └── Columns: First Name | Surname | TA Number | Category | Category Finish Place | Club Name
```

## How to Use the Program

### Step-by-Step Process

1. **Prepare your input files**:

   - Ensure `Triathlon Season.xlsx` is in `data/input/`
   - Place your round result files in `data/input/` with proper naming
2. **Run the program**:

   - Double-click `calculation_engine.exe` (or run from command line)
3. **Monitor the output**:

   - The console will show processing progress
   - Watch for any warnings or errors
4. **Check the results**:

   - Output files are created in `data/output/`
   - Filename format: `[League Name]_R[Round]_[YYYYMMDD].xlsx`
   - Processed input files are moved to `data/processed/`

### Output File Contents

Each output file contains multiple sheets:

1. **Round Ladder**: Current round standings with point breakdown

   - Columns: Club, Participation Points, Performance Points, Total Points, Adjusted Total Points, ICL Eligible Number
2. **Season Ladder**: Cumulative season standings

   - Same structure as Round Ladder, but cumulative across all rounds
3. **Round MVP**: Top individual performers for the round

   - Columns: Full Name, TA Number, Club Name, Round Performance Points
4. **Season MVP**: Cumulative individual MVP rankings

   - Columns: Full Name, TA Number, Club Name, Season Performance Points
5. **Individual Club MVP Sheets**: One sheet per club showing top performers

   - Columns: Full Name, TA Number, Category, Performance Points
6. **Race Points Sheets**: One sheet per race showing club points breakdown

   - Columns: Club, Total That Raced, Performance Points

## Point Calculation Rules

### Performance Points

- Awarded to top 10 finishers in each category:
  - 1st place: 10 points
  - 2nd place: 9 points
  - 3rd place: 8 points
  - ...continuing to 10th place: 1 point
- Points are summed across all races in the round
- Double points events multiply all performance points by 2

### Participation Points

- Calculated once per round based on total finishers across all races
- Thresholds based on ICL Eligible Number:
  - 5% threshold: 15 points
  - 10% threshold: 30 points
  - 20% threshold: 45 points
- Double points events multiply participation points by 2

### Total Points Cap

- Normal rounds: Maximum 150 points per club
- Double points rounds: Maximum 300 points per club

## Troubleshooting

### Common Issues

**"No new round files to process"**

- Check that files are in `data/input/` directory
- Verify filename format: `[League Name] Round [Number] [Event Name].xlsx`
- Ensure files are not already processed (check `data/processed/`)

**"Missing required columns"**

- Verify all required columns are present in race result sheets
- Check column name variations are recognized (see column mapping above)

**"No matching league/round found"**

- Ensure `Triathlon Season.xlsx` contains matching League Name and Round number
- Check for exact spelling matches (case-insensitive)

**"Could not read ICL sheet"**

- Verify sheet is named exactly: "Current ICL Eligible Number"
- Check that required ICL columns are present

**Club names not matching**

- Club names must match exactly between ICL sheet and race results
- Check for extra spaces or spelling differences
- The program normalizes names but exact matches are preferred

### Getting Help

If you encounter errors:

1. Check the console output for specific error messages
2. Verify all input files meet the required format
3. Ensure `Triathlon Season.xlsx` is properly configured
4. Check that processed files haven't been re-added to input directory

## Technical Details

### Dependencies

All dependencies are listed in `requirements.txt`. Install them using:
```cmd
pip install -r requirements.txt
```

Required packages:
- Python 3.x (3.7 or higher recommended)
- pandas (>=1.5.0) - Data manipulation and Excel file reading
- openpyxl (>=3.0.0) - Excel file handling
- numpy (>=1.20.0) - Numerical operations
- PyInstaller (>=5.0.0) - For building executable

### File Processing Flow

1. Program scans `data/input/` for new round files
2. Validates file format and required sheets/columns
3. Reads season configuration from `Triathlon Season.xlsx`
4. Processes each race sheet in the round file
5. Calculates performance and participation points
6. Generates round and season ladders
7. Creates MVP rankings
8. Saves output to `data/output/`
9. Moves processed file to `data/processed/`

## Notes

- The program automatically creates required directories if they don't exist
- Season tracking files are maintained in `data/season/current_season/`
- Processed files are automatically moved to prevent reprocessing
- The program supports multiple races per round (multiple sheets per file)
- Race type validation ensures only eligible race types are processed
