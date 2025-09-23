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
    - Removing leading/trailing spaces
    - Replacing multiple spaces with single space
    - Preserving case
    """
    df.columns = [
        re.sub(r'\s+', ' ', col.strip()) 
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
    Read multiple ICL tables from Excel file, separated by blank rows
    Returns a dictionary of league names to their ICL DataFrames
    """
    try:
        # Read the entire ICL sheet
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
            # Check if row is entirely empty or NaN
            if row.isna().all():
                if current_league and current_data:
                    # Create DataFrame for current league
                    df = pd.DataFrame(current_data, columns=header_row)
                    df = normalize_column_names(df)
                    # Remove the summary row if it exists (row with just numbers)
                    df = df[df['Club'].notna()]
                    icl_tables[current_league] = df
                    
                # Reset for next table
                current_data = []
                current_league = None
                header_row = None
                continue
            
            # Convert row to list and check if it's not empty
            row_data = row.dropna().tolist()
            if not row_data:
                continue
                
            # Check if this is a league header row
            if isinstance(row_data[0], str) and 'League' in row_data[0]:
                current_league = row_data[0]
                # Next row should be headers
                header_row = raw_data.iloc[idx + 1].tolist()
                continue
                
            # Skip the header row itself as we've already captured it
            if header_row and row_data == header_row:
                continue
                
            # Add data row
            if header_row and current_league:
                # Ensure row is same length as header
                padded_row = row.tolist()[:len(header_row)]
                while len(padded_row) < len(header_row):
                    padded_row.append(None)
                current_data.append(padded_row)
        
        # Handle last table if exists
        if current_league and current_data:
            df = pd.DataFrame(current_data, columns=header_row)
            df = normalize_column_names(df)
            df = df[df['Club'].notna()]
            icl_tables[current_league] = df
        
        # Print summary of found tables
        print("\nFound ICL tables:")
        for league, df in icl_tables.items():
            print(f"{league}: {len(df)} clubs")
            print("Clubs:", df['Club'].tolist())
            print("-" * 80)
        
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
    """Find new round files in input directory with optional league/event names"""
    # Updated pattern to capture "Round" as the key separator
    pattern = r'(?:([^R]+?)(?=Round)|)?Round (\d+)(?: (.*))?\.xlsx'
    round_files = []
    
    # Get season source for league inference
    season_source_path = os.path.join(CURRENT_SEASON_DIR, 'Triathalon Season.xlsx')
    try:
        season_source = pd.read_excel(season_source_path)
        season_source = normalize_column_names(season_source)
    except Exception as e:
        print(f"Warning: Could not load season source for league inference: {e}")
        season_source = None
    
    for filename in os.listdir(INPUT_DIR):
        if filename.startswith('~$'):
            continue
            
        match = re.match(pattern, filename)
        if match:
            filepath = os.path.join(INPUT_DIR, filename)
            event_name = match.group(3) if match.group(3) else match.group(1)
            
            # Infer league from clubs if available
            league_name = None
            if season_source is not None:
                league_name = infer_league_from_clubs(filepath, season_source)
            
            if not league_name:
                print(f"Warning: Could not determine league for {filename}")
                continue
            
            round_info = {
                'filename': filename,
                'league': league_name,
                'round': int(match.group(2)),
                'name': event_name.strip() if event_name else None,
                'path': filepath
            }
            
            print(f"\nFound round file: {filename}")
            print(f"- League: {round_info['league']}")
            print(f"- Round: {round_info['round']}")
            print(f"- Event: {round_info['name']}")
            
            round_files.append(round_info)
    
    return round_files
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
    """Validate required columns and standardize column names"""
    required_columns = {
        'First Name',
        'Surname',
        'TA Number',
        'Category',
        'Category Finish Place',
        'Club Name'
    }
    
    # Get mapping of actual column names
    column_mapping = get_column_mapping(race_df)
    
    # Check for missing required columns
    missing_cols = required_columns - set(column_mapping.keys())
    if missing_cols:
        print(f"Warning: Sheet {sheet_name} missing required columns: {missing_cols}")
        return None
        
    # Rename columns to standard names
    race_df = race_df.rename(columns={v: k for k, v in column_mapping.items()})
    
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

def validate_race_type(race_name, league_info):
    """Validate if race type is allowed based on the race types listed in season source"""
    try:
        race_name = race_name.lower()
        
        # Get performance & participation race types
        perf_part_types = set()
        if pd.notna(league_info['Per P & Part P']):
            perf_part_types = {
                race_type.strip().lower() 
                for race_type in str(league_info['Per P & Part P']).split(',')
            }
            
        # Get participation only race types
        part_only_types = set()
        if pd.notna(league_info['Part P']) and str(league_info['Part P']).lower() != 'n/a':
            part_only_types = {
                race_type.strip().lower() 
                for race_type in str(league_info['Part P']).split(',')
            }
        
        # Extract race type from sheet name using common keywords
        race_keywords = {'sprint', 'standard', 'aquabike', 'classic', 'ultimate', 'ultra', 'super'}
        race_words = set(race_name.split())
        found_types = race_words.intersection(race_keywords)
        
        if not found_types:
            print(f"Warning: Could not identify race type in sheet name: {race_name}")
            return {
                'performance_eligible': False,
                'participation_eligible': False,
                'double_points': False
            }
        
        # Check eligibility by matching any race type keywords
        is_performance_eligible = any(
            any(race_type.lower() in allowed_type.lower() for race_type in found_types)
            for allowed_type in perf_part_types
        )
        
        is_participation_eligible = (
            is_performance_eligible or 
            any(any(race_type.lower() in allowed_type.lower() for race_type in found_types)
                for allowed_type in part_only_types)
        )
        
        result = {
            'performance_eligible': is_performance_eligible,
            'participation_eligible': is_participation_eligible,
            'double_points': str(league_info['Double Points']).lower() == 'yes'
        }
        
        return result
        
    except Exception as e:
        print(f"Error in race validation: {str(e)}")
        return {
            'performance_eligible': False,
            'participation_eligible': False,
            'double_points': False
        }

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

def process_round_file(round_info, season_source):
    """
    FIXED: Process a single round file with corrected participation points logic
    """
    try:
        season_source = normalize_column_names(season_source)
                # Read ICL tables
        icl_tables = read_icl_tables(round_info['path'])
        if not icl_tables:
            print("Cannot proceed without ICL tables")
            return
        

        # Process each league's results separately
        for league_name, icl_df in icl_tables.items():
            print(f"\nProcessing results for {league_name}")
            # Get league info from season source
            league_matches = season_source[
                (season_source['League Name'].str.lower() == round_info['league'].lower()) & 
                (season_source['Round'] == round_info['round'])
            ]
            
            if league_matches.empty:
                print(f"Error: No matching league/round found for {round_info['league']} Round {round_info['round']}")
                return
                
            league_info = league_matches.iloc[0]
            
            # Read Excel file and ensure it's properly closed
            with pd.ExcelFile(round_info['path']) as xl:
                # First read ICL eligible numbers
                try:
                    icl_df = xl.parse('Current ICL Eligible Number')
                    icl_df = normalize_column_names(icl_df)
                    if 'ICL Eligible Number' not in icl_df.columns:
                        print("Warning: ICL sheet missing required column 'ICL Eligible Number'")
                except Exception as e:
                    print(f"Warning: Could not read ICL sheet: {e}")
                    icl_df = None
                    
                if icl_df is None:
                    print("Cannot proceed without ICL eligible numbers")
                    return
                    
                all_results = []
                race_validations = []
                
                # Process each race sheet
                for sheet_name in xl.sheet_names:
                    # Skip non-race and summary sheets
                    if any(x in sheet_name.lower() for x in ['icl', 'summary', 'points', 'eligible', 'manual', 'calculations']):
                        continue
                        
                    print(f"Processing race sheet: {sheet_name}")
                    
                    # Validate race type
                    race_validation = validate_race_type(sheet_name, league_info)
                    if not (race_validation['performance_eligible'] or race_validation['participation_eligible']):
                        print(f"Warning: Sheet {sheet_name} not listed in allowed race types")
                        continue
                    
                    try:
                        # Read race results
                        race_df = xl.parse(sheet_name)
                        race_df = normalize_column_names(race_df)
                        
                        # Standardize column names
                        race_df = validate_and_standardize_columns(race_df, sheet_name)
                        if race_df is None:
                            continue
                        
                        # Clean data
                        race_df = race_df.dropna(subset=['Club Name'])
                        race_df['Race_Type'] = sheet_name
                        
                        all_results.append(race_df)
                        race_validations.append(race_validation)
                        
                        print(f"Successfully processed {sheet_name}: {len(race_df)} participants")
                        
                    except Exception as e:
                        print(f"Error processing sheet {sheet_name}: {e}")
                        continue
            
            if not all_results:
                print("No valid race results found to process")
                return
            
            # FIXED: Calculate participation points ONCE for the entire round
            icl_with_participation = calculate_round_participation_points(all_results, icl_df, race_validations)
            
            # Calculate performance points across all races
            icl_with_performance = calculate_round_performance_points(all_results, icl_df, race_validations)
            
            # Generate round summary
            round_summary = generate_round_summary(icl_with_participation, icl_with_performance)
            
            # Generate season ladder
            season_ladder_path = os.path.join(CURRENT_SEASON_DIR, 'Season_Ladder.xlsx')
            season_ladder = generate_season_ladder(round_summary, season_ladder_path)
            
            # Generate MVP data (filter results to eligible clubs first)
            filtered_results_for_mvp = []
            for race_results in all_results:
                filtered_results = filter_eligible_clubs_only(race_results, icl_df)
                filtered_results_for_mvp.append(filtered_results)
            
            mvp_data = generate_individual_mvp_data(filtered_results_for_mvp, race_validations)
            season_mvp = generate_season_mvp_ladder(mvp_data) if mvp_data else pd.DataFrame()
            
            # Generate club individual MVP sheets
            club_mvp_sheets = generate_club_individual_mvp_sheets(mvp_data)
            
            # Save all outputs
            output_filename = f"{round_info['league']}_R{round_info['round']}_{datetime.now().strftime('%Y%m%d')}.xlsx"
            output_path = os.path.join(OUTPUT_DIR, output_filename)
            
            with pd.ExcelWriter(output_path) as writer:
                # a) Round ladder with breakdown
                round_summary.to_excel(writer, sheet_name='Round Ladder', index=False)
                
                # b) Cumulative season ladder with breakdown
                season_ladder.to_excel(writer, sheet_name='Season Ladder', index=False)
                
                # c) Round MVP ladder
                if mvp_data and not mvp_data['round_mvp'].empty:
                    mvp_data['round_mvp'].to_excel(writer, sheet_name='Round MVP', index=False)
                
                # d) Cumulative season MVP ladder
                if not season_mvp.empty:
                    season_mvp.to_excel(writer, sheet_name='Season MVP', index=False)
                
                # e) Individual club MVP sheets (only for eligible clubs)
                for sheet_name, club_mvp_df in club_mvp_sheets.items():
                    if not club_mvp_df.empty:
                        club_mvp_df.to_excel(writer, sheet_name=sheet_name, index=False)
            
            # Update season history
            combined_results = pd.concat(filtered_results_for_mvp)
            update_season_history(combined_results, round_info)
        
        # Copy file to processed directory instead of moving to avoid file lock issues
        processed_path = os.path.join(PROCESSED_DIR, round_info['filename'])
        try:
            shutil.copy2(round_info['path'], processed_path)
            print(f"File copied to processed directory: {processed_path}")
            
            # Try to delete original file, but don't fail if it's locked
            try:
                os.remove(round_info['path'])
                print(f"Original file deleted: {round_info['path']}")
            except PermissionError:
                print(f"Warning: Could not delete original file (file may be open in another application): {round_info['path']}")
                print("Please manually delete or move this file after closing any applications that may have it open.")
        except Exception as e:
            print(f"Warning: Could not copy file to processed directory: {e}")
        
        print(f"Successfully processed {round_info['filename']} -> {output_filename}")
        
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