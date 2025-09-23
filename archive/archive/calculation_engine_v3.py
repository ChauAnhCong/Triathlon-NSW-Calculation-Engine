import pandas as pd
import re
import os
import shutil
from datetime import datetime

# Add new constants for directory structure
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')
INPUT_DIR = os.path.join(DATA_DIR, 'input')
OUTPUT_DIR = os.path.join(DATA_DIR, 'output')
PROCESSED_DIR = os.path.join(DATA_DIR, 'processed')
CURRENT_SEASON_DIR = os.path.join(DATA_DIR, 'season', 'current_season')
PAST_SEASON_DIR = os.path.join(DATA_DIR, 'season', 'past_season')

def normalize_column_names(df):
    """
    Normalize column names by:
    - Converting to string
    - Removing leading/trailing spaces
    - Replacing multiple spaces with single space
    - Preserving case
    """
    df.columns = [
        re.sub(r'\s+', ' ', str(col).strip()) 
        for col in df.columns
    ]
    return df

def normalize_club_name(club_name):
    """Normalize club name for comparison"""
    if pd.isna(club_name):
        return ""
    
    normalized = str(club_name).lower().strip()
    # Remove common variations
    normalized = re.sub(r'\s+', ' ', normalized)  # Multiple spaces to single
    normalized = normalized.replace('triathlon club', 'tc')
    normalized = normalized.replace(' club', '')
    normalized = re.sub(r'[^\w\s]', '', normalized)  # Remove punctuation
    
    return normalized

def ensure_directories():
    """Create directory structure if it doesn't exist"""
    for directory in [INPUT_DIR, OUTPUT_DIR, PROCESSED_DIR, 
                     CURRENT_SEASON_DIR, PAST_SEASON_DIR]:
        os.makedirs(directory, exist_ok=True)

def get_season_source_of_truth():
    """Get and validate season source of truth file"""
    source_path = os.path.join(INPUT_DIR, 'Triathalon Season.xlsx')
    current_source_path = os.path.join(CURRENT_SEASON_DIR, 'Triathalon Season.xlsx')
    
    if os.path.exists(source_path):
        # Validate source file structure
        try:
            df = pd.read_excel(source_path)
            df = normalize_column_names(df)
            required_columns = ['League Name', 'Round', 'Events or Rounds', 
                              'Double Points', 'Per P & Part P', 'Part P', 'Clubs']
            missing_cols = [col for col in required_columns if col not in df.columns]
            if missing_cols:
                print(f"Error: Missing required columns in source file: {missing_cols}")
                return None
                
            if os.path.exists(current_source_path):
                # Compare and validate both files
                new_source = pd.read_excel(source_path)
                current_source = pd.read_excel(current_source_path)
                if not new_source.equals(current_source):
                    # Backup current source before updating
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    backup_path = os.path.join(CURRENT_SEASON_DIR, f'Triathlon_Season_backup_{timestamp}.xlsx')
                    shutil.copy2(current_source_path, backup_path)
                    shutil.move(source_path, current_source_path)
            else:
                shutil.move(source_path, current_source_path)
                
        except Exception as e:
            print(f"Error reading source file: {e}")
            return None
    
    return current_source_path if os.path.exists(current_source_path) else None

def read_icl_tables(filepath):
    """
    Read multiple ICL tables from Excel file, handling both league-prefixed and direct club tables.
    Returns a dictionary of league names to their ICL DataFrames.
    """
    try:
        with pd.ExcelFile(filepath) as xl:
            if 'Current ICL Eligible Number' not in xl.sheet_names:
                print("Warning: No ICL sheet found")
                return None
                
            raw_data = xl.parse('Current ICL Eligible Number', header=None)
            
        # Initialize variables
        icl_tables = {}
        current_data = []
        current_league = None
        header_row = None
        
        # Process each row
        for idx, row in raw_data.iterrows():
            # Check if row is entirely empty (separator between tables)
            if row.isna().all():
                if current_data and header_row:
                    try:
                        # Create DataFrame for current table
                        df = pd.DataFrame(current_data, columns=header_row)
                        df = normalize_column_names(df)
                        
                        # Remove summary rows (rows with just numbers)
                        df = df[df['Club'].notna()]
                        
                        if not df.empty:
                            # If no league name was found, use default
                            if not current_league:
                                print("No league name found, inferring from data...")
                                # Try to infer league from first row if it contains 'League'
                                first_row = str(raw_data.iloc[0][0])
                                if 'League' in first_row:
                                    current_league = first_row.strip()
                                else:
                                    current_league = "Default League"
                                print(f"Using league name: {current_league}")
                                
                            icl_tables[current_league] = df
                    except Exception as e:
                        print(f"Error processing table: {e}")
                    
                # Reset for next table
                current_data = []
                current_league = None
                header_row = None
                continue
            
            # Convert row to list and check if it's not empty
            row_data = row.dropna().tolist()
            if not row_data:
                continue
                
            # Check if this is a league header or column header row
            if isinstance(row_data[0], str):
                if 'League' in row_data[0]:
                    current_league = str(row_data[0]).strip()
                    # Next row should be headers
                    header_row = [str(x).strip() if pd.notnull(x) else '' 
                                for x in raw_data.iloc[idx + 1]]
                    continue
                elif row_data[0].lower() == 'club':
                    # Direct club table without league header
                    header_row = [str(x).strip() if pd.notnull(x) else '' 
                                for x in row_data]
                    continue
            
            # Add data row if we have headers
            if header_row:
                # Ensure row data is properly formatted
                padded_row = row.tolist()[:len(header_row)]
                while len(padded_row) < len(header_row):
                    padded_row.append(None)
                current_data.append(padded_row)
        
        # Handle last table if exists
        if current_data and header_row:
            try:
                df = pd.DataFrame(current_data, columns=header_row)
                df = normalize_column_names(df)
                df = df[df['Club'].notna()]
                if not df.empty:
                    if not current_league:
                        current_league = "Default League"
                    icl_tables[current_league] = df
            except Exception as e:
                print(f"Error processing final table: {e}")
        
        # Print summary of found tables
        if icl_tables:
            print("\nFound ICL tables:")
            for league, df in icl_tables.items():
                print(f"\n{league}:")
                print(f"Number of clubs: {len(df)}")
                print("Clubs:", df['Club'].tolist())
                print("-" * 80)
        else:
            print("No valid ICL tables found in file")
        
        return icl_tables
        
    except Exception as e:
        print(f"Error reading ICL tables: {e}")
        import traceback
        traceback.print_exc()
        return None
def infer_league_from_clubs(filepath, season_source):
    """
    Infer league based on participating clubs in the results.
    Returns all possible leagues based on club matches.
    """
    try:
        # Read the ICL sheet first
        icl_df = None
        with pd.ExcelFile(filepath) as xl:
            if 'Current ICL Eligible Number' in xl.sheet_names:
                icl_df = xl.parse('Current ICL Eligible Number')
                icl_df = normalize_column_names(icl_df)
                participating_clubs = set(icl_df['Club'].str.lower())
                
                print(f"\nParticipating clubs found: {participating_clubs}")
                
                # Group season source by league and get club sets
                league_matches = {}
                for _, league_row in season_source.iterrows():
                    league_name = league_row['League Name']
                    if pd.notna(league_row['Clubs']):
                        league_clubs = {
                            club.strip().lower() 
                            for club in str(league_row['Clubs']).split(',')
                        }
                        # Count matching clubs
                        matching_clubs = participating_clubs.intersection(league_clubs)
                        if matching_clubs:
                            league_matches[league_name] = {
                                'matching_clubs': matching_clubs,
                                'match_count': len(matching_clubs),
                                'total_clubs': len(league_clubs)
                            }
                
                if league_matches:
                    print("\nLeague matches found:")
                    for league, stats in league_matches.items():
                        print(f"{league}:")
                        print(f"- Matching clubs: {stats['match_count']}/{stats['total_clubs']}")
                        print(f"- Clubs: {stats['matching_clubs']}")
                    
                    # Return league with highest proportion of matching clubs
                    best_match = max(
                        league_matches.items(),
                        key=lambda x: x[1]['match_count'] / x[1]['total_clubs']
                    )
                    
                    print(f"\nBest matching league: {best_match[0]}")
                    return best_match[0]
                    
    except Exception as e:
        print(f"Warning: Could not infer league from clubs: {e}")
    
    return None

def find_new_round_files():
    """Find new round files in input directory"""
    try:
        # Get season source for league inference
        season_source_path = os.path.join(CURRENT_SEASON_DIR, 'Triathalon Season.xlsx')
        season_source = None
        
        try:
            season_source = pd.read_excel(season_source_path)
            season_source = normalize_column_names(season_source)
            print("\nAvailable leagues in season source:")
            print(season_source['League Name'].tolist())
        except Exception as e:
            print(f"Warning: Could not load season source: {e}")
        
        patterns = [
            r'(?:([^R]+?) )?Round (\d+)(?: (.*))?\.xlsx',
        ]
        round_files = []
        
        for filename in os.listdir(INPUT_DIR):
            if filename.startswith('~$'):
                continue
                
            for pattern in patterns:
                match = re.match(pattern, filename)
                if match:
                    filepath = os.path.join(INPUT_DIR, filename)
                    
                    # Read ICL tables with season source for league inference
                    icl_tables = read_icl_tables(filepath, season_source)
                    if not icl_tables:
                        print(f"Warning: No ICL tables found in {filename}")
                        continue
                    
                    # Create round info for each participating league
                    for league_name, icl_df in icl_tables.items():
                        # Try to match league name with season source
                        if season_source is not None:
                            matching_leagues = season_source[
                                season_source['League Name'].str.contains(
                                    league_name, 
                                    case=False, 
                                    na=False,
                                    regex=False
                                )
                            ]
                            if not matching_leagues.empty:
                                league_name = matching_leagues.iloc[0]['League Name']
                        
                        round_info = {
                            'filename': filename,
                            'league': league_name,
                            'round': int(match.group(2)),
                            'name': match.group(3) or match.group(1),
                            'path': filepath,
                            'icl_data': icl_df
                        }
                        
                        round_files.append(round_info)
                    break
        
        return round_files
        
    except Exception as e:
        print(f"Error finding round files: {e}")
        return []
def get_column_mapping(df):
    """Map various possible column names to standardized names"""
    # First normalize the column names
    df = normalize_column_names(df)
    
    column_mappings = {
        'First Name': ['First Name', 'FORENAME', 'FirstName', 'Given Name'],
        'Surname': ['Surname', 'SURNAME', 'LastName', 'Family Name', 'Surname '],
        'TA Number': ['TA Number', 'TANumber', 'TA_Number', 'Membership'],
        'Category': ['Category', 'CATGY', 'Race Category', 'Division', 'Category '],
        'Category Finish Place': ['Category Finish Place', 'FINISH_CAT_PLACE', 'Cat Place', 'Division Place', 'Category Finish Place '],
        'Club Name': ['Club Name', 'Triathlon Club', 'Club', 'CLUB', 'Club Name '],
        'Per P': ['Per P', 'Performance points', 'Performance Points', 'Perf Points', 'Performance points Participation points or both'],
    }

    actual_columns = {}
    for std_name, possible_names in column_mappings.items():
        found_col = next((col for col in df.columns if col in possible_names), None)
        if found_col:
            actual_columns[std_name] = found_col
    
    return actual_columns

def validate_and_standardize_columns(race_df, sheet_name):
    """Validate and standardize column names"""
    # Standard column mappings
    standard_mappings = {
        'First Name': ['First Name', 'FirstName', 'FIRST NAME', 'Given Name'],
        'Surname': ['Surname', 'LastName', 'SURNAME', 'Family Name'],
        'TA Number': ['TA Number', 'TA_Number', 'TANumber', 'Membership'],
        'Category': ['Category', 'Age Group', 'Division', 'Race Category'],
        'Category Finish Place': ['Category Finish Place', 'Category Place', 'Division Place'],
        'Club Name': ['Club Name', 'Club', 'Team', 'Triathlon Club']
    }
    
    # Try to match columns
    new_columns = {}
    current_cols = race_df.columns
    
    for standard_name, variations in standard_mappings.items():
        matched_col = next(
            (col for col in current_cols if any(var.lower() == col.lower() for var in variations)),
            None
        )
        if matched_col:
            new_columns[matched_col] = standard_name
    
    # Check if we found all required columns
    missing = set(standard_mappings.keys()) - set(new_columns.values())
    if missing:
        print(f"\nMissing required columns in {sheet_name}:")
        print(f"- Missing: {missing}")
        print(f"- Available: {current_cols.tolist()}")
        return None
    
    # Rename columns to standard names
    race_df = race_df.rename(columns=new_columns)
    
    return race_df

def create_club_mapping(results_df, icl_df):
    """
    ENHANCED: Create robust club mapping between race results and ICL eligible clubs
    """
    eligible_clubs = set(icl_df['Club'].values)
    result_clubs = set(results_df['Club Name'].unique())
    
    print(f"Eligible ICL clubs: {sorted(eligible_clubs)}")
    print(f"Clubs in race results: {sorted(result_clubs)}")
    
    club_mapping = {}
    excluded_clubs = []
    
    for result_club in result_clubs:
        matched = False
        result_normalized = normalize_club_name(result_club)
        
        for eligible_club in eligible_clubs:
            eligible_normalized = normalize_club_name(eligible_club)
            
            if result_normalized == eligible_normalized:
                club_mapping[result_club] = eligible_club
                matched = True
                print(f"MATCHED: '{result_club}' -> '{eligible_club}'")
                break
        
        if not matched:
            excluded_clubs.append(result_club)
    
    if excluded_clubs:
        print(f"EXCLUDED (not ICL eligible): {excluded_clubs}")
    
    return club_mapping, excluded_clubs

def filter_eligible_clubs_only(results_df, icl_df):
    """
    ENHANCED: Filter results to only include ICL-eligible clubs with better logging and mapping
    """
    print(f"\n=== FILTERING ELIGIBLE CLUBS ===")
    print(f"Input results shape: {results_df.shape}")
    
    # Create robust club mapping
    club_mapping, excluded_clubs = create_club_mapping(results_df, icl_df)
    
    # Filter to only eligible clubs
    original_count = len(results_df)
    results_df = results_df[results_df['Club Name'].isin(club_mapping.keys())].copy()
    
    # Apply standardized club names
    results_df['Club Name'] = results_df['Club Name'].map(club_mapping)
    
    print(f"Filtered results: {original_count} -> {len(results_df)} participants")
    print(f"Clubs included: {sorted(results_df['Club Name'].unique())}")
    
    return results_df
def infer_league_from_clubs_list(clubs_list, season_source):
    """Infer league name based on matching clubs from season source"""
    if not isinstance(clubs_list, (list, set)):
        return None
        
    clubs_set = {str(club).lower().strip() for club in clubs_list}
    best_match = None
    best_match_count = 0
    
    for _, row in season_source.iterrows():
        if pd.notna(row['Clubs']):
            league_clubs = {
                club.strip().lower() 
                for club in str(row['Clubs']).split(',')
            }
            matches = len(clubs_set.intersection(league_clubs))
            if matches > best_match_count:
                best_match_count = matches
                best_match = row['League Name']
    
    if best_match:
        print(f"Inferred league '{best_match}' from {best_match_count} matching clubs")
    return best_match
def read_icl_tables(filepath, season_source=None):
    """Read multiple ICL tables from Excel file"""
    try:
        # Define standard ICL column names
        STANDARD_COLUMNS = [
            'Club',
            'ICL Eligible Number',
            '15PTS (5%)',
            '30 PTS (10%)',
            '45 PTS (20%)'
        ]

        with pd.ExcelFile(filepath) as xl:
            if 'Current ICL Eligible Number' not in xl.sheet_names:
                print("Warning: No ICL sheet found")
                return None
                
            # Read the ICL sheet without headers
            ICL_DF = pd.read_excel(filepath, sheet_name='Current ICL Eligible Number', header=None)
            
            # Find the empty row that separates tables
            nan_rows = ICL_DF[ICL_DF.isnull().all(axis=1)].index
            if len(nan_rows) == 0:
                print("No table separator found")
                return None
            
            nan_row_index = nan_rows[0]
            
            # Split into two DataFrames
            df1 = ICL_DF.iloc[:nan_row_index]
            df2 = ICL_DF.iloc[nan_row_index + 1:]
            
            icl_tables = {}
            
            # Process first table
            if not df1.empty:
                league_name = str(df1.iloc[0, 0])  # Get league name from first row
                df1 = df1.iloc[1:]  # Skip league name row
                df1.columns = STANDARD_COLUMNS
                df1 = df1[df1['Club'].notna()]  # Remove rows without club names
                if not df1.empty:
                    icl_tables[league_name] = df1
                    print(f"\nProcessed table for {league_name}:")
                    print(f"Number of clubs: {len(df1)}")
                    print("Clubs:", df1['Club'].tolist())
                    
            # Process second table
            if not df2.empty:
                league_name = str(df2.iloc[0, 0])  # Get league name from first row
                df2 = df2.iloc[1:]  # Skip league name row
                df2.columns = STANDARD_COLUMNS
                df2 = df2[df2['Club'].notna()]  # Remove rows without club names
                if not df2.empty:
                    icl_tables[league_name] = df2
                    print(f"\nProcessed table for {league_name}:")
                    print(f"Number of clubs: {len(df2)}")
                    print("Clubs:", df2['Club'].tolist())
            
            return icl_tables
            
    except Exception as e:
        print(f"Error reading ICL tables: {e}")
        import traceback
        traceback.print_exc()
        return None
# def read_icl_tables(filepath, season_source=None):
#     """
#     Read multiple ICL tables from Excel file using empty row detection.
#     Returns a dictionary of league names to their ICL DataFrames.
#     """
#     try:
#         # Define standard ICL column names and their possible variations
#         STANDARD_COLUMNS = {
#             'Club': ['Club', 'Club Name', 'Triathlon Club'],
#             'ICL Eligible Number': ['ICL Eligible Number', 'ICL Number', 'Eligible Number', 'ICL Eligible'],
#             '15PTS (5%)': ['15PTS (5%)', '15 PTS', '5%', '15pts'],
#             '30 PTS (10%)': ['30 PTS (10%)', '30 PTS', '10%', '30pts'],
#             '45 PTS (20%)': ['45 PTS (20%)', '45 PTS', '20%', '45pts']
#         }

#         with pd.ExcelFile(filepath) as xl:
#             if 'Current ICL Eligible Number' not in xl.sheet_names:
#                 print("Warning: No ICL sheet found")
#                 return None
                
#             # Read the ICL sheet
#             ICL_DF = pd.read_excel(filepath, sheet_name='Current ICL Eligible Number')
            
#             # Find the empty rows that separate tables
#             nan_rows = ICL_DF[ICL_DF.isnull().all(axis=1)].index
#             tables = []
            
#             if len(nan_rows) == 0:
#                 tables = [ICL_DF]
#             else:
#                 start_idx = 0
#                 for idx in nan_rows:
#                     if idx > start_idx:
#                         tables.append(ICL_DF.iloc[start_idx:idx])
#                     start_idx = idx + 1
#                 if start_idx < len(ICL_DF):
#                     tables.append(ICL_DF.iloc[start_idx:])
            
#             icl_tables = {}
            
#             for table in tables:
#                 if table.empty:
#                     continue
                
#                 # Initialize league_name
#                 league_name = None
#                 header_found = False
                
#                 # Look for league name and column headers
#                 for idx, row in table.iterrows():
#                     row_values = row.dropna().tolist()
#                     if not row_values:
#                         continue
                        
#                     first_cell = str(row_values[0])
                    
#                     if 'League' in first_cell:
#                         # Found league header
#                         league_name = first_cell.strip()
#                         continue
                        
#                     # Skip summary row (contains only numbers)
#                     if all(isinstance(x, (int, float)) for x in row_values):
#                         continue
                        
#                     # Found header row
#                     header_row = row
#                     data_start_idx = idx + 1
#                     header_found = True
#                     break
                
#                 if not header_found:
#                     print(f"No valid header row found in table")
#                     continue
                
#                 # Process data rows
#                 data_rows = table.iloc[data_start_idx:]
#                 new_table = pd.DataFrame(data_rows.values, columns=header_row)
                
#                 # Map columns to standard names
#                 column_mapping = {}
#                 for col in new_table.columns:
#                     if pd.isna(col):
#                         continue
#                     col_str = str(col).strip()
#                     for std_name, variations in STANDARD_COLUMNS.items():
#                         if any(var.lower() == col_str.lower() for var in variations):
#                             column_mapping[col] = std_name
#                             break
                
#                 print(f"\nProcessing table with columns: {list(new_table.columns)}")
#                 print(f"Column mapping: {column_mapping}")
                
#                 # Rename columns using mapping
#                 new_table = new_table.rename(columns=column_mapping)
                
#                 # Convert numeric columns safely
#                 for col in new_table.columns:
#                     try:
#                         new_table[col] = pd.to_numeric(new_table[col], errors='coerce')
#                     except:
#                         pass
                
#                 # Ensure all required columns exist
#                 for std_name in STANDARD_COLUMNS.keys():
#                     if std_name not in new_table.columns:
#                         new_table[std_name] = None
                
#                 # Remove rows without club names
#                 new_table = new_table[new_table['Club'].notna()]
                
#                 if new_table.empty:
#                     continue
                
#                 # If no league name, try to infer from clubs
#                 if not league_name and season_source is not None:
#                     league_name = infer_league_from_clubs_list(
#                         new_table['Club'].tolist(), 
#                         season_source
#                     )
                
#                 if not league_name:
#                     league_name = "Default League"
                
#                 # Keep only standard columns
#                 new_table = new_table[list(STANDARD_COLUMNS.keys())]
                
#                 # Store processed table
#                 icl_tables[league_name] = new_table
#                 print(f"\nProcessed table for {league_name}:")
#                 print(f"Number of clubs: {len(new_table)}")
#                 print(f"Columns: {new_table.columns.tolist()}")
#                 print("Clubs:", new_table['Club'].tolist())
#                 print("-" * 80)
            
#             return icl_tables
            
#     except Exception as e:
#         print(f"Error reading ICL tables: {e}")
#         import traceback
#         traceback.print_exc()
#         return None
def calculate_individual_performance_points(place):
    """Calculate individual performance points based on category finish place"""
    place_points = {
        1: 10, 2: 9, 3: 8, 4: 7, 5: 6,
        6: 5, 7: 4, 8: 3, 9: 2, 10: 1
    }
    return place_points.get(place, 0) if pd.notnull(place) else 0

def calculate_performance_points(results_df):
    """Calculate performance points based on category finish positions"""
    # Initialize points for top 10 places
    place_points = {
        1: 10, 2: 9, 3: 8, 4: 7, 5: 6,
        6: 5, 7: 4, 8: 3, 9: 2, 10: 1
    }
    
    # Convert Category Finish Place to numeric, handling any non-numeric values
    results_df['Category Finish Place'] = pd.to_numeric(
        results_df['Category Finish Place'], 
        errors='coerce'
    )
    
    # Calculate points for each participant
    results_df['Performance Points'] = results_df['Category Finish Place'].map(
        place_points
    ).fillna(0)
    
    # Group by club and sum performance points
    club_points = results_df.groupby('Club Name')['Performance Points'].sum()
    
    print(f"Performance points by club: {club_points.to_dict()}")
    
    return club_points.to_dict()

def calculate_round_participation_points(all_race_results, icl_df, race_validations):
    """
    FIXED: Calculate participation points ONCE per round based on TOTAL finishers across all races
    This is the key fix - participation points should not be summed per race
    """
    print(f"\n=== CALCULATING ROUND PARTICIPATION POINTS ===")
    
    # Filter each race to only eligible clubs and combine
    filtered_race_results = []
    for race_results in all_race_results:
        filtered_results = filter_eligible_clubs_only(race_results, icl_df)
        filtered_race_results.append(filtered_results)
    
    # Combine ALL race results for the round
    combined_results = pd.concat(filtered_race_results, ignore_index=True)
    print(f"Combined results shape: {combined_results.shape}")
    
    # Count TOTAL finishers per club across ALL races in the round
    club_total_finishers = combined_results['Club Name'].value_counts().to_dict()
    print(f"Total finishers per club across all races: {club_total_finishers}")
    
    # Initialize participation points
    icl_df = icl_df.copy()
    icl_df['Participation Points'] = 0
    icl_df['Total Finishers'] = 0
    
    # Apply participation thresholds ONCE based on total finishers
    for idx, row in icl_df.iterrows():
        club_name = row['Club']
        total_finishers = club_total_finishers.get(club_name, 0)
        icl_df.loc[idx, 'Total Finishers'] = total_finishers
        
        # Apply thresholds
        if total_finishers >= row['45 PTS (20%)']:
            participation_points = 45
        elif total_finishers >= row['30 PTS (10%)']:
            participation_points = 30
        elif total_finishers >= row['15PTS (5%)']:
            participation_points = 15
        else:
            participation_points = 0
            
        icl_df.loc[idx, 'Participation Points'] = participation_points
        
        print(f"{club_name}: {total_finishers} finishers -> {participation_points} participation points")
    
    return icl_df

def calculate_round_performance_points(all_race_results, icl_df, race_validations):
    """Calculate performance points across all races in the round"""
    print(f"\n=== CALCULATING ROUND PERFORMANCE POINTS ===")
    
    # Initialize performance points
    icl_df = icl_df.copy()
    icl_df['Performance Points'] = 0
    
    # Calculate performance points for each race and sum
    total_performance_points = {}
    
    for race_results, race_validation in zip(all_race_results, race_validations):
        if race_validation['performance_eligible']:
            # Filter to eligible clubs only
            filtered_results = filter_eligible_clubs_only(race_results, icl_df)
            
            # Calculate performance points for this race
            race_performance_points = calculate_performance_points(filtered_results)
            
            # Apply double points if specified
            if race_validation['double_points']:
                race_performance_points = {k: v * 2 for k, v in race_performance_points.items()}
            
            # Sum into total
            for club, points in race_performance_points.items():
                total_performance_points[club] = total_performance_points.get(club, 0) + points
    
    # Map performance points to ICL dataframe
    for idx, row in icl_df.iterrows():
        club_name = row['Club']
        perf_points = total_performance_points.get(club_name, 0)
        icl_df.loc[idx, 'Performance Points'] = perf_points
        print(f"{club_name}: {perf_points} performance points")
    
    return icl_df

def generate_round_summary(icl_with_participation, icl_with_performance):
    """
    ENHANCED: Generate round summary with proper finisher count tracking
    """
    print(f"\n=== GENERATING ROUND SUMMARY ===")
    
    # Merge participation and performance points
    round_summary = icl_with_participation[['Club', 'ICL Eligible Number', 'Participation Points', 'Total Finishers']].copy()
    
    # Add performance points
    perf_points_map = dict(zip(icl_with_performance['Club'], icl_with_performance['Performance Points']))
    round_summary['Performance Points'] = round_summary['Club'].map(perf_points_map).fillna(0)
    
    # Calculate total points
    round_summary['Total Points'] = round_summary['Participation Points'] + round_summary['Performance Points']
    
    # Sort by total points descending
    round_summary = round_summary.sort_values('Total Points', ascending=False)
    
    print(f"FINAL ROUND SUMMARY:")
    print("-" * 80)
    for _, row in round_summary.iterrows():
        print(f"{row['Club']:25} | Finishers: {int(row['Total Finishers']):2d} | Part: {int(row['Participation Points']):2d} | Perf: {int(row['Performance Points']):3d} | Total: {int(row['Total Points']):3d}")
    print("-" * 80)
    
    return round_summary
def generate_individual_mvp_data(all_results_dfs, race_validations):
    """Generate individual MVP data for round and season"""
    all_individual_results = []
    
    for results_df, race_validation in zip(all_results_dfs, race_validations):
        if race_validation['performance_eligible']:
            # Calculate individual performance points
            individual_df = results_df.copy()
            individual_df['Individual Performance Points'] = individual_df['Category Finish Place'].apply(
                calculate_individual_performance_points
            )
            
            # Apply double points if specified
            if race_validation['double_points']:
                individual_df['Individual Performance Points'] *= 2
                
            all_individual_results.append(individual_df)
    
    if not all_individual_results:
        return None
    
    # Combine all individual results
    combined_results = pd.concat(all_individual_results, ignore_index=True)
    
    # Create round MVP ladder
    round_mvp = combined_results.groupby(['First Name', 'Surname', 'Club Name'])['Individual Performance Points'].sum().reset_index()
    round_mvp['Full Name'] = round_mvp['First Name'] + ' ' + round_mvp['Surname']
    round_mvp = round_mvp.sort_values('Individual Performance Points', ascending=False)
    round_mvp = round_mvp[['Full Name', 'Club Name', 'Individual Performance Points']].rename(columns={
        'Individual Performance Points': 'Round Performance Points'
    })
    
    # Create club MVP breakdown (top performer from each club) - Fixed for older pandas
    club_mvps_list = []
    for club_name, club_data in combined_results.groupby('Club Name'):
        if len(club_data) > 0:
            top_performer = club_data.loc[club_data['Individual Performance Points'].idxmax()]
            club_mvps_list.append(top_performer)
    
    if club_mvps_list:
        club_mvps = pd.DataFrame(club_mvps_list)
    
    if not club_mvps.empty:
        club_mvps['Full Name'] = club_mvps['First Name'] + ' ' + club_mvps['Surname']
        club_mvps = club_mvps[['Club Name', 'Full Name', 'Individual Performance Points']].rename(columns={
            'Individual Performance Points': 'Performance Points'
        })
        club_mvps = club_mvps.sort_values('Performance Points', ascending=False)
    
    return {
        'round_mvp': round_mvp,
        'club_mvps': club_mvps,
        'individual_results': combined_results
    }
def generate_season_ladder(round_summary, season_history_path):
    """Generate cumulative season ladder"""
    try:
        # Read existing season history
        if os.path.exists(season_history_path):
            season_history = pd.read_excel(season_history_path)
        else:
            season_history = pd.DataFrame()
        
        # Combine with new round
        season_ladder = pd.concat([season_history, round_summary], ignore_index=True)
        
        # Group by club and sum points
        season_ladder = season_ladder.groupby('Club').agg({
            'Participation Points': 'sum',
            'Performance Points': 'sum',
            'Total Points': 'sum',
            'ICL Eligible Number': 'first'
        }).reset_index()
        
        # Sort by total points descending
        season_ladder = season_ladder.sort_values('Total Points', ascending=False)
        
        return season_ladder
        
    except Exception as e:
        print(f"Error generating season ladder: {e}")
        return pd.DataFrame()

def generate_season_mvp_ladder(round_mvp_data):
    """Generate cumulative season MVP ladder"""
    try:
        season_mvp_path = os.path.join(CURRENT_SEASON_DIR, 'Season_MVP.xlsx')
        
        if os.path.exists(season_mvp_path):
            # Read existing season MVP data
            season_mvp = pd.read_excel(season_mvp_path)
            
            # Combine with new round data
            combined_mvp = pd.concat([season_mvp, round_mvp_data['round_mvp']], ignore_index=True)
            
            # Group by individual and sum points
            season_mvp = combined_mvp.groupby(['Full Name', 'Club Name'])['Round Performance Points'].sum().reset_index()
            season_mvp = season_mvp.rename(columns={'Round Performance Points': 'Season Performance Points'})
            season_mvp = season_mvp.sort_values('Season Performance Points', ascending=False)
        else:
            # First round of the season
            season_mvp = round_mvp_data['round_mvp'].copy()
            season_mvp = season_mvp.rename(columns={'Round Performance Points': 'Season Performance Points'})
            
        # Save updated season MVP data
        season_mvp.to_excel(season_mvp_path, index=False)
        
        return season_mvp
        
    except Exception as e:
        print(f"Error generating season MVP ladder: {e}")
        return pd.DataFrame()

def generate_club_individual_mvp_sheets(round_mvp_data):
    """Generate individual MVP sheets for each club"""
    try:
        if round_mvp_data is None or 'individual_results' not in round_mvp_data:
            return {}
            
        club_individual_sheets = {}
        individual_results = round_mvp_data['individual_results']
        
        # Group by club
        for club_name, club_data in individual_results.groupby('Club Name'):
            # Create individual performance breakdown for this club
            club_mvp = club_data.copy()
            club_mvp['Full Name'] = club_mvp['First Name'] + ' ' + club_mvp['Surname']
            
            # Sort by performance points descending
            club_mvp = club_mvp.sort_values('Individual Performance Points', ascending=False)
            
            # Select relevant columns
            club_mvp_sheet = club_mvp[['Full Name', 'Category', 'Individual Performance Points']].rename(columns={
                'Individual Performance Points': 'Performance Points'
            })
            
            club_individual_sheets[f"{club_name} MVP"] = club_mvp_sheet
            
        return club_individual_sheets
        
    except Exception as e:
        print(f"Error generating club individual MVP sheets: {e}")
        return {}

def update_season_history(results_df, round_info):
    """Update season history with new round results"""
    history_path = os.path.join(CURRENT_SEASON_DIR, 'Season_History.xlsx')
    
    if os.path.exists(history_path):
        with pd.ExcelFile(history_path) as xls:
            history_df = pd.read_excel(xls)
    else:
        history_df = pd.DataFrame()
    
    # Add round information to results
    results_df['League'] = round_info['league']
    results_df['Round'] = round_info['round']
    results_df['Event'] = round_info['name']
    
    # Combine with history
    updated_history = pd.concat([history_df, results_df], ignore_index=True)
    
    # Save updated history
    updated_history.to_excel(history_path, index=False)
def validate_required_columns(race_df):
    """
    Validate that race sheet has required columns based on valid_race_column_names
    """
    required_columns = [
        "First Name", "Surname", "TA Number", "Category", 
        "Category Finish Place", "Club Name"
    ]
    
    # Get current columns after normalization
    current_columns = set(race_df.columns)
    
    # Check for missing required columns
    missing_columns = [col for col in required_columns if col not in current_columns]
    
    if missing_columns:
        print(f"Missing required columns: {missing_columns}")
        print(f"Available columns: {sorted(current_columns)}")
        return False
    
    return True

def validate_race_type(sheet_name, league_info):
    """Validate race type against league rules"""
    try:
        sheet_name = sheet_name.lower()
        
        # Race type keywords with standardized variations
        race_types = {
            'sprint': ['sprint', 'half club distance'],
            'standard': ['standard', 'olympic', 'club distance', '70.3'],
            'aquabike': ['aquabike', 'club aquabike'],
            'classic': ['classic'],
            'ultimate': ['ultimate']
        }
        
        # Find race type in sheet name
        found_type = None
        for race_type, keywords in race_types.items():
            if any(keyword in sheet_name for keyword in keywords):
                found_type = race_type
                break
        
        if not found_type:
            print(f"Could not identify race type in: {sheet_name}")
            return {
                'performance_eligible': False,
                'participation_eligible': False,
                'double_points': False
            }
        
        # Get allowed race types, handling empty/None values
        perf_part_types = []
        part_only_types = []
        
        if pd.notna(league_info.get('Per P & Part P')):
            perf_part_types = [
                type_str.strip().lower() 
                for type_str in str(league_info['Per P & Part P']).split(',')
            ]
        
        if pd.notna(league_info.get('Part P')):
            part_only_types = [
                type_str.strip().lower() 
                for type_str in str(league_info['Part P']).split(',')
            ]
        
        print(f"\nValidating race type '{found_type}' against:")
        print(f"Performance & Participation types: {perf_part_types}")
        print(f"Participation only types: {part_only_types}")
        
        # Check eligibility using more flexible matching
        performance_eligible = any(
            found_type in type_str or type_str in found_type
            for type_str in perf_part_types
        )
        
        participation_eligible = (
            performance_eligible or 
            any(found_type in type_str or type_str in found_type 
                for type_str in part_only_types)
        )
        
        # If no rules specified, default to eligible
        if not perf_part_types and not part_only_types:
            print("No race type rules found - defaulting to eligible")
            performance_eligible = True
            participation_eligible = True
        
        result = {
            'performance_eligible': performance_eligible,
            'participation_eligible': participation_eligible,
            'double_points': str(league_info.get('Double Points', 'No')).lower() == 'yes'
        }
        
        print(f"\nRace validation for {sheet_name}:")
        print(f"- Found type: {found_type}")
        print(f"- Result: {result}")
        
        return result
        
    except Exception as e:
        print(f"Error in race validation: {e}")
        print("Defaulting to eligible")
        return {
            'performance_eligible': True,
            'participation_eligible': True,
            'double_points': False
        }

def calculate_participation_points(results_df, icl_df, race_validation=None):
    """
    Calculate participation points based on number of finishers and ICL thresholds
    """
    if race_validation is None:
        race_validation = {
            'participation_eligible': True,
            'performance_eligible': True,
            'double_points': False
        }
    
    # Count finishers per club
    club_finishers = results_df['Club Name'].value_counts()
    
    # Initialize points DataFrame
    points_df = icl_df.copy()
    points_df['Total Finishers'] = points_df['Club'].map(club_finishers).fillna(0)
    points_df['Participation Points'] = 0
    points_df['Performance Points'] = 0
    
    # Calculate participation points if eligible
    if race_validation['participation_eligible']:
        for idx, row in points_df.iterrows():
            finishers = row['Total Finishers']
            if finishers >= row['45 PTS (20%)']:
                points_df.loc[idx, 'Participation Points'] = 45
            elif finishers >= row['30 PTS (10%)']:
                points_df.loc[idx, 'Participation Points'] = 30
            elif finishers >= row['15PTS (5%)']:
                points_df.loc[idx, 'Participation Points'] = 15
    
    # Calculate performance points if eligible
    if race_validation['performance_eligible']:
        performance_points = calculate_performance_points(results_df)
        points_df['Performance Points'] = points_df['Club'].map(performance_points).fillna(0)
    
    # Apply double points if specified
    if race_validation['double_points']:
        points_df['Participation Points'] *= 2
        points_df['Performance Points'] *= 2
    
    # Calculate total points
    points_df['Total Points'] = points_df['Participation Points'] + points_df['Performance Points']
    
    return points_df

def calculate_individual_performance_points(place):
    """Calculate individual performance points based on category finish place"""
    place_points = {
        1: 10, 2: 9, 3: 8, 4: 7, 5: 6,
        6: 5, 7: 4, 8: 3, 9: 2, 10: 1
    }
    return place_points.get(place, 0) if pd.notnull(place) else 0

def generate_individual_mvp_data(all_results_dfs, race_validations):
    """Generate individual MVP data for round and season"""
    all_individual_results = []
    
    for results_df, race_validation in zip(all_results_dfs, race_validations):
        if race_validation['performance_eligible']:
            # Calculate individual performance points
            individual_df = results_df.copy()
            individual_df['Individual Performance Points'] = individual_df['Category Finish Place'].apply(
                calculate_individual_performance_points
            )
            
            # Apply double points if specified
            if race_validation['double_points']:
                individual_df['Individual Performance Points'] *= 2
                
            all_individual_results.append(individual_df)
    
    if not all_individual_results:
        return None
    
    # Combine all individual results
    combined_results = pd.concat(all_individual_results, ignore_index=True)
    
    # Create round MVP ladder
    round_mvp = combined_results.groupby(
        ['First Name', 'Surname', 'Club Name']
    )['Individual Performance Points'].sum().reset_index()
    round_mvp['Full Name'] = round_mvp['First Name'] + ' ' + round_mvp['Surname']
    round_mvp = round_mvp.sort_values('Individual Performance Points', ascending=False)
    
    # Create club MVP breakdown
    club_mvps = (combined_results.groupby('Club Name')
                 .apply(lambda x: x.nlargest(1, 'Individual Performance Points'))
                 .reset_index(drop=True))
    club_mvps['Full Name'] = club_mvps['First Name'] + ' ' + club_mvps['Surname']
    
    return {
        'round_mvp': round_mvp,
        'club_mvps': club_mvps,
        'individual_results': combined_results
    }

def generate_season_mvp_ladder(mvp_data):
    """Generate cumulative season MVP ladder"""
    try:
        season_mvp_path = os.path.join(CURRENT_SEASON_DIR, 'Season_MVP.xlsx')
        
        if os.path.exists(season_mvp_path):
            # Read existing season MVP data
            season_mvp = pd.read_excel(season_mvp_path)
            
            # Combine with new round data
            combined_mvp = pd.concat(
                [season_mvp, mvp_data['round_mvp']], 
                ignore_index=True
            )
            
            # Group by individual and sum points
            season_mvp = (combined_mvp.groupby(['Full Name', 'Club Name'])
                         ['Individual Performance Points'].sum()
                         .reset_index()
                         .sort_values('Individual Performance Points', ascending=False))
        else:
            # First round of the season
            season_mvp = mvp_data['round_mvp'].copy()
        
        # Save updated season MVP data
        season_mvp.to_excel(season_mvp_path, index=False)
        
        return season_mvp
        
    except Exception as e:
        print(f"Error generating season MVP ladder: {e}")
        return pd.DataFrame()

def generate_club_individual_mvp_sheets(mvp_data):
    """Generate individual MVP sheets for each club"""
    try:
        club_sheets = {}
        
        for club_name, club_data in mvp_data['individual_results'].groupby('Club Name'):
            # Create individual performance breakdown
            club_mvp = club_data.copy()
            club_mvp['Full Name'] = club_mvp['First Name'] + ' ' + club_mvp['Surname']
            
            # Sort by points and select relevant columns
            club_sheet = (club_mvp.sort_values('Individual Performance Points', ascending=False)
                         [['Full Name', 'Category', 'Individual Performance Points']])
            
            club_sheets[f"{club_name} MVP"] = club_sheet
        
        return club_sheets
        
    except Exception as e:
        print(f"Error generating club MVP sheets: {e}")
        return {}
    
def generate_mvp_ladders(all_race_results, round_info):
    """
    Generate MVP ladders for:
    - Round MVP (top performers in this round)
    - Season MVP (cumulative performance)
    - Club MVPs (top performer from each club)
    """
    try:
        print("\n=== Generating MVP Ladders ===")
        
        # Calculate individual points for all races
        mvp_data = generate_individual_mvp_data(all_race_results, round_info)
        if not mvp_data:
            print("No MVP data to process")
            return None
        
        # Generate season MVP ladder
        season_mvp = generate_season_mvp_ladder(mvp_data)
        
        # Generate club-specific MVP sheets
        club_mvp_sheets = generate_club_individual_mvp_sheets(mvp_data)
        
        # Add sheets to mvp_data
        mvp_data['season_mvp'] = season_mvp
        mvp_data['club_mvp_sheets'] = club_mvp_sheets
        
        print("\nMVP Ladders Generated:")
        print(f"- Round MVP: {len(mvp_data['round_mvp'])} entries")
        print(f"- Club MVPs: {len(mvp_data['club_mvps'])} clubs")
        print(f"- Season MVP: {len(mvp_data['season_mvp'])} entries")
        print(f"- Individual Club Sheets: {len(club_mvp_sheets)} clubs")
        
        return mvp_data
        
    except Exception as e:
        print(f"Error generating MVP ladders: {e}")
        import traceback
        traceback.print_exc()
        return None
def process_round_file(round_info, season_source):
    """Process round file for a specific league"""
    try:
        print(f"\nProcessing {round_info['league']} - {round_info['name']}")
        
        # Get league info from season source with better error handling
        matching_leagues = season_source[
            season_source['League Name'].str.contains(
                round_info['league'], 
                case=False, 
                na=False,
                regex=False
            )
        ]
        
        if matching_leagues.empty:
            print(f"No matching league found in season source for: {round_info['league']}")
            print("Available leagues:", season_source['League Name'].tolist())
            return
            
        league_info = matching_leagues.iloc[0]
        
        print(f"\nLeague info found:")
        print(f"League name: {league_info['League Name']}")
        print(f"- Performance types: {league_info.get('Per P & Part P', 'None')}")
        print(f"- Participation types: {league_info.get('Part P', 'None')}")
        print(f"- Double points: {league_info.get('Double Points', 'No')}")
        
        # Read race sheets
        xl = pd.ExcelFile(round_info['path'])
        all_points = []
        all_results = []
        race_validations = []
        
        for sheet_name in xl.sheet_names:
            if sheet_name == 'Current ICL Eligible Number':
                continue
                
            try:
                print(f"\nProcessing sheet: {sheet_name}")
                
                # Read sheet with first row as header - FIXED
                race_df = pd.read_excel(
                    round_info['path'],
                    sheet_name=sheet_name,
                    header=0  # Use first row as header
                )
                
                # Normalize and validate columns
                race_df = normalize_column_names(race_df)
                race_df = validate_and_standardize_columns(race_df, sheet_name)
                
                if race_df is None:
                    continue
                    
                # Filter to valid clubs
                race_df = filter_eligible_clubs_only(race_df, round_info['icl_data'])
                
                if race_df.empty:
                    print(f"No results for {round_info['league']} clubs")
                    continue
                
                # Validate race type with proper league info
                race_validation = validate_race_type(sheet_name, league_info)
                
                if not (race_validation['performance_eligible'] or 
                       race_validation['participation_eligible']):
                    print(f"Race type not eligible")
                    continue
                
                # Calculate points
                points_df = calculate_participation_points(
                    race_df,
                    round_info['icl_data'],
                    race_validation
                )
                
                if not points_df.empty:
                    points_df['Race_Type'] = sheet_name
                    all_points.append(points_df)
                    all_results.append(race_df)
                    race_validations.append(race_validation)
                    
            except Exception as e:
                print(f"Error processing sheet {sheet_name}: {e}")
                continue
        
        if not all_results:
            print(f"No valid results found for {round_info['league']}")
            return
            
        # Generate outputs for this league
        output_filename = f"{round_info['league']}_R{round_info['round']}_{datetime.now().strftime('%Y%m%d')}.xlsx"
        output_path = os.path.join(OUTPUT_DIR, output_filename)
        
        with pd.ExcelWriter(output_path) as writer:
            # Generate and save all rankings
            generate_round_summary(all_points, all_results).to_excel(
                writer, sheet_name='Round Ladder', index=False
            )
            
            generate_season_ladder(
                all_points, round_info
            ).to_excel(writer, sheet_name='Season Ladder', index=False)
            
            mvp_data = generate_mvp_ladders(
                pd.concat(all_results), round_info
            )
            
            if mvp_data:
                mvp_data['round_mvp'].to_excel(
                    writer, sheet_name='Round MVP', index=False
                )
                mvp_data['club_mvps'].to_excel(
                    writer, sheet_name='Club MVPs', index=False
                )
                mvp_data['season_mvp'].to_excel(
                    writer, sheet_name='Season MVP', index=False
                )
        
        print(f"Generated output file: {output_filename}")
        
    except Exception as e:
        print(f"Error processing round file: {e}")
        import traceback
        traceback.print_exc()

def main():
    """Main function to process triathlon results"""
    ensure_directories()
    
    # Get and validate season source
    season_source_path = get_season_source_of_truth()
    if not season_source_path:
        print("Error: No valid season source file found")
        return
        
    try:
        season_source = pd.read_excel(season_source_path)
    except Exception as e:
        print(f"Error reading season source file: {e}")
        return
    
    # Find new round files
    round_files = find_new_round_files()
    if not round_files:
        print("No new round files to process")
        return

    for round_info in round_files:
        print(f"\nProcessing {round_info['filename']}...")
        process_round_file(round_info, season_source)
    
    print("\nProcessing complete!")

if __name__ == "__main__":
    main()