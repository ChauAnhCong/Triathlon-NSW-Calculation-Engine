from numpy import floor
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
def ensure_directories():
    """Create directory structure if it doesn't exist"""
    for directory in [INPUT_DIR, OUTPUT_DIR, PROCESSED_DIR, 
                     CURRENT_SEASON_DIR, PAST_SEASON_DIR]:
        os.makedirs(directory, exist_ok=True)
def get_season_source_of_truth():
    """Get and validate season source of truth file"""
    source_path = os.path.join(INPUT_DIR, 'Triathlon Season.xlsx')
    current_source_path = os.path.join(CURRENT_SEASON_DIR, 'Triathlon Season.xlsx')
    
    if os.path.exists(source_path):
        # Validate source file structure
        try:
            with pd.ExcelFile(source_path) as xl:
                df = pd.read_excel(xl)
                df = normalize_column_names(df)
                required_columns = ['League Name', 'Round', 'Events or Rounds', 
                                  'Double Points', 'Per P & Part P', 'Part P', 'Clubs']
                missing_cols = [col for col in required_columns if col not in df.columns]
                if missing_cols:
                    print(f"Error: Missing required columns in source file: {missing_cols}")
                    return None
                    
                if os.path.exists(current_source_path):
                    # Compare and validate both files
                    with pd.ExcelFile(source_path) as new_xl, pd.ExcelFile(current_source_path) as current_xl:
                        new_source = pd.read_excel(new_xl)
                        current_source = pd.read_excel(current_xl)
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
def find_new_round_files():
    """Find new round files in input directory"""
    pattern = r'(.*?) Round (\d+) (.*?)\.xlsx'
    round_files = []
    
    for filename in os.listdir(INPUT_DIR):
        match = re.match(pattern, filename)
        if match:
            round_files.append({
                'filename': filename,
                'league': match.group(1),
                'round': int(match.group(2)),
                'name': match.group(3),
                'path': os.path.join(INPUT_DIR, filename)
            })
    
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
        'Per P': ['Per P', 'Performance points', 'Performance Points', 'Perf Points'],
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
def normalize_string(text):
    """Normalize a string by removing punctuation and extra spaces, and converting to lowercase."""
    if pd.isna(text):  # Handle NaN/None values
        return ''
    normalized = re.sub(r'[^\w\s]', '', str(text).lower())  # Convert to string first
    normalized = re.sub(r'\s+', ' ', normalized).strip()
    return normalized
def partial_match(str1, str2):
    """Check if one normalized string is completely contained in the other."""
    if pd.isna(str1) or pd.isna(str2):  # Handle NaN/None values
        return False
    norm1 = normalize_string(str1)
    norm2 = normalize_string(str2)
    return norm1 and norm2 and (norm1 in norm2 or norm2 in norm1)
def validate_race_type(race_name, league_info):
    """Validate if race type is allowed based on the race types listed in season source"""
    try:
        # Extract the race name after the round number (e.g., "Round 1 Sprint Distance" -> "Sprint Distance", "R10 Club Champs" -> "Club Champs")
        race_name = race_name.lower()
        match = re.search(r'(?:round\s*|r)\d+\s*(.*)', race_name, re.IGNORECASE)
        if match:
            race_name = match.group(1).strip()
        print(f"\nValidating race type: {race_name}")
        
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
        
        print(f"Allowed performance types: {perf_part_types}")
        print(f"Allowed participation types: {part_only_types}")
        
        # If no rules specified, default to eligible
        if not perf_part_types and not part_only_types:
            print("No race type rules found - defaulting to eligible")
            return {
                'performance_eligible': True,
                'participation_eligible': True,
                'double_points': str(league_info.get('Double Points', '')).lower() == 'yes'
            }
        
        # Special handling for club championships and similar events
        if any(term in race_name for term in ['club', 'champs', 'championship']):
            print("Club championship or similar event detected - automatically eligible")
            return {
                'performance_eligible': True,
                'participation_eligible': True,
                'double_points': str(league_info.get('Double Points', '')).lower() == 'yes'
            }
        
        
        # Define race type keywords with variations
        race_types = {
            'sprint aquabike': ['sprint aquabike'],
            'aquabike': ['aquabike', 'standard aquabike'],
            'aquabike 70.3': ['ironman 70.3 aquabike', '70.3 aquabike', 'challenge middle distance aquabike'],
            'aquathon': ['aquathlon', 'aquathon'],
            'long aqua': ['long aqua', 'long aquathlon'],
            'short aqua': ['short aqua'],
            'mini aqua': ['mini aqua'],
            'super sprint': ['super sprint', 'enitcer', 'tempta'],
            'sprint': ['sprint', 'sprint distance'],
            'standard': ['standard', 'olympic', 'standard distance'],
            'classic': ['classic'],
            'club': ['club'],
            'half club': ['half club'],
            'ironman 70.3': ['70.3', 'ironman 70.3', 'ultimate', 'enduro', 'challenge middle distance'],
            'ironman': ['ironman'],
            'ultra': ['ultra'],
            'teams': ['teams'],
            'duathlon': ['durathlon'],
            'super sprint duathlon': ['super sprint duathlon'],
            'sprint duathlon': ['sprint duathlon'],
            'standard durathlon': ['standard durathlon']
        }
        
        # Find all matching race types in the name
        found_types = set()
        for type_name, variations in race_types.items():
            if any(variation == race_name.strip() for variation in variations):  # fix to exact match
                found_types.add(type_name)
        
        if not found_types:
            print(f"Warning: Could not identify race type in: {race_name}")
            return {
                'performance_eligible': False,
                'participation_eligible': False,
                'double_points': False
            }
            
        print(f"Found race types: {found_types}")
        
        # Check eligibility using combination of found types
        def check_eligibility(allowed_types):
            # Split compound types (e.g., "club and aquabike" -> ["club", "aquabike"])
            expanded_allowed = set()
            for allowed in allowed_types:
                parts = [p.strip() for p in allowed.split(' and ')]
                expanded_allowed.update(parts)
            
            # Check if any found type matches any allowed type
            return any(
                any(found == allowed 
                    for allowed in expanded_allowed)
                for found in found_types
            )
        
        is_performance_eligible = check_eligibility(perf_part_types)
        is_participation_eligible = (
            is_performance_eligible or 
            check_eligibility(part_only_types)
        )
        
        result = {
            'performance_eligible': is_performance_eligible,
            'participation_eligible': is_participation_eligible,
            'double_points': str(league_info['Double Points']).lower() == 'yes'
        }
        
        print(f"Validation result: {result}")
        return result
        
    except Exception as e:
        print(f"Error in race validation: {str(e)}")
        print(f"Defaulting to eligible for: {race_name}")
        return {
            'performance_eligible': True,
            'participation_eligible': True,
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
    try:
        print("\n=== PERFORMANCE POINTS DEBUG ===")
        
        # Ensure numeric category places
        results_df['Category Finish Place'] = pd.to_numeric(
            results_df['Category Finish Place'], 
            errors='coerce'
        )
        
        # Points allocation
        place_points = {
            1: 10, 2: 9, 3: 8, 4: 7, 5: 6,
            6: 5, 7: 4, 8: 3, 9: 2, 10: 1
        }
        
        # Calculate points per result
        results_df['Points'] = results_df['Category Finish Place'].map(place_points).fillna(0)
        
        # Sum points by club
        club_points = results_df.groupby('Club Name')['Points'].sum()
        
        print("Performance points by club:")
        print(club_points)
        
        return club_points.to_dict()
        
    except Exception as e:
        print(f"Error calculating performance points: {e}")
        import traceback
        traceback.print_exc()
        return {}
def calculate_race_performance_points(results_df, icl_df, race_validation):
    """Calculate performance points for a single race (participation points are now handled at round level)"""
    try:
        # Normalize column names
        results_df = normalize_column_names(results_df)
        icl_df = normalize_column_names(icl_df)
        
        # Normalize club names in both DataFrames for robust matching
        results_df['Club Name Norm'] = results_df['Club Name'].apply(normalize_string)
        icl_df['Club Norm'] = icl_df['Club'].apply(normalize_string)
        
        print("\n=== RACE PERFORMANCE POINTS CALCULATION DEBUG ===")
        input_clubs = sorted([c for c in results_df['Club Name'].unique() if pd.notna(c)])
        icl_clubs = sorted([c for c in icl_df['Club'].unique() if pd.notna(c)])
        print(f"Input clubs: {input_clubs}")
        print(f"ICL clubs: {icl_clubs}")
        
        # Clean up ICL data - remove NaN rows
        icl_df = icl_df.dropna(subset=['Club'])
        
        # Create club mapping using normalized names
        club_mapping = {}
        for icl_norm, icl_club in zip(icl_df['Club Norm'], icl_df['Club']):
            for result_norm, result_club in zip(results_df['Club Name Norm'], results_df['Club Name']):
                # if partial_match(icl_norm, result_norm):
                if icl_norm == result_norm:     # use exact match instead as a priority
                    club_mapping[result_club] = icl_club
        
        print(f"Club mapping: {club_mapping}")
        
        # Map club names in results
        results_df['Club Name Mapped'] = results_df['Club Name'].map(club_mapping).fillna(results_df['Club Name'])
        
        # Initialize points DataFrame with all ICL clubs and filter out rows with empty club names
        points_df = icl_df.copy()
        points_df = points_df.dropna(subset=['Club'])  # Remove rows with no club name
        points_df = points_df[points_df['Club'].str.strip() != '']  # Remove rows with empty club names
        points_df['Participation Points'] = 0  # Will be calculated at round level
        points_df['Performance Points'] = 0
        
        # Calculate performance points if eligible
        if race_validation['performance_eligible']:
            # Use mapped club names for performance points
            mapped_results_df = results_df.copy()
            mapped_results_df['Club Name'] = mapped_results_df['Club Name Mapped']
            performance_points = calculate_performance_points(mapped_results_df)
            points_df['Performance Points'] = points_df['Club'].map(performance_points).fillna(0)
        
        # Apply double points if specified
        if race_validation['double_points']:
            points_df['Performance Points'] *= 2
        
        # Calculate total points (only performance for individual races)
        points_df['Total Points'] = points_df['Performance Points']
        
        print("\nRace performance points calculation:")
        print(points_df[['Club', 'Performance Points', 'Total Points']])
        return points_df
        
    except Exception as e:
        print(f"Error in race performance points calculation: {e}")
        import traceback
        traceback.print_exc()
        return None
    
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
    round_mvp = combined_results.groupby(['First Name', 'TA Number', 'Surname', 'Club Name'])['Individual Performance Points'].sum().reset_index()
    round_mvp['Full Name'] = round_mvp['First Name'] + ' ' + round_mvp['Surname']
    round_mvp = round_mvp.sort_values('Individual Performance Points', ascending=False)
    round_mvp = round_mvp[['Full Name', 'TA Number', 'Club Name', 'Individual Performance Points']].rename(columns={
        'Individual Performance Points': 'Round Performance Points'
    })
    
    # Create club MVP breakdown (top performer from each club)
    club_mvps = combined_results.groupby('Club Name').apply(
        lambda x: x.loc[x['Individual Performance Points'].idxmax()] if len(x) > 0 else None
    ).reset_index(drop=True)
    
    if not club_mvps.empty:
        club_mvps['Full Name'] = club_mvps['First Name'] + ' ' + club_mvps['Surname']
        club_mvps = club_mvps[['Club Name', 'TA Number', 'Full Name', 'Individual Performance Points']].rename(columns={
            'Individual Performance Points': 'Performance Points'
        })
        club_mvps = club_mvps.sort_values('Performance Points', ascending=False)
    
    return {
        'round_mvp': round_mvp,
        'club_mvps': club_mvps,
        'individual_results': combined_results
    }

def calculate_round_participation_points(all_results_dfs, icl_df, race_validations):
    """
    FIXED: Calculate participation points ONCE per round based on TOTAL finishers across all races
    This is the key fix - participation points should not be summed per race
    """
    print(f"\n=== CALCULATING ROUND PARTICIPATION POINTS ===")
    
    # Combine ALL race results for the round
    combined_results = pd.concat(all_results_dfs, ignore_index=True)
    print(f"Combined results shape: {combined_results.shape}")
    # Lowercase 'Club Name' in combined_results for consistency
    combined_results['Club Name'] = combined_results['Club Name'].str.lower()
    # Count TOTAL finishers per club across ALL races in the round
    club_total_finishers = combined_results['Club Name'].value_counts().to_dict()
    print(f"Total finishers per club across all races: {club_total_finishers}")
    
    # Initialize participation points DataFrame and filter out rows with empty club names
    participation_df = icl_df.copy()
    participation_df = participation_df.dropna(subset=['Club'])  # Remove rows with no club name
    participation_df = participation_df[participation_df['Club'].str.strip() != '']  # Remove rows with empty club names
    participation_df['Participation Points'] = 0
    participation_df['Total Finishers'] = 0
    
    # Apply participation thresholds ONCE based on total finishers
    for idx, row in participation_df.iterrows():
        club_name = row['Club']
        total_finishers = club_total_finishers.get(club_name.lower(), 0)
        participation_df.loc[idx, 'Total Finishers'] = total_finishers
        
        if total_finishers == 0:
            participation_points = 0
        # Apply thresholds
        elif total_finishers >= floor(row['45 PTS (20%)']):
            participation_points = 45
        elif total_finishers >= floor(row['30 PTS (10%)']):
            participation_points = 30
        elif total_finishers >= floor(row['15PTS (5%)']):
            participation_points = 15
        else:
            participation_points = 0
            
        participation_df.loc[idx, 'Participation Points'] = participation_points
        
        print(f"{club_name}: {total_finishers} finishers -> {participation_points} participation points")
    
    # if double points, multiply participation points by 2
    if any(validation.get('double_points', False) for validation in race_validations):
        participation_df['Participation Points'] *= 2

    print(participation_df)
    return participation_df

def generate_round_summary(all_points_dfs, all_results_dfs, icl_df, race_validations):
    """Generate round summary with participation and performance breakdowns"""
    
    print("\n=== ROUND SUMMARY CALCULATION DEBUG ===")
    
    # STEP 1: Calculate participation points ONCE for the entire round
    participation_df = calculate_round_participation_points(all_results_dfs, icl_df, race_validations)
    
    # STEP 2: Calculate performance points per race and sum them
    performance_points_by_race = []
    for i, (race_points_df, race_validation) in enumerate(zip(all_points_dfs, race_validations)):
        if race_validation['performance_eligible']:
            print(f"\nRace {i+1} performance points:")
            print(race_points_df[['Club', 'Performance Points']])
            performance_points_by_race.append(race_points_df[['Club', 'Performance Points']])
    
    # STEP 3: Sum performance points across all races
    if performance_points_by_race:
        combined_performance = pd.concat(performance_points_by_race, ignore_index=True)
        total_performance = combined_performance.groupby('Club')['Performance Points'].sum().reset_index()
    else:
        total_performance = pd.DataFrame(columns=['Club', 'Performance Points'])
    
    # STEP 4: Combine participation and performance points
    round_summary = participation_df.merge(total_performance, on='Club', how='left')
    round_summary['Performance Points'] = round_summary['Performance Points'].fillna(0)
    
    # STEP 5: Calculate total points
    round_summary['Total Points'] = round_summary['Participation Points'] + round_summary['Performance Points']
    
    print("\nRound summary after aggregation:")
    print(round_summary[['Club', 'Total Finishers', 'Participation Points', 'Performance Points', 'Total Points']])

    # STEP 6: Calculate adjusted scores (cap at 150 points, or 300 for double points)
    # Check if any race in the round has double points
    is_double_points_round = any(validation.get('double_points', False) for validation in race_validations)
    max_points = 300 if is_double_points_round else 150
    
    round_summary['Adjusted Total Points'] = round_summary['Total Points'].apply(
        lambda x: min(x, max_points)
    )
    
    # STEP 7: Select only the required columns for round ladder
    round_ladder_columns = ['Club', 'Participation Points', 'Performance Points', 'Total Points', 'Adjusted Total Points', 'ICL Eligible Number']
    round_summary = round_summary[round_ladder_columns]
        
    # STEP 8: Sort by total points descending
    round_summary = round_summary.sort_values('Total Points', ascending=False)
    

    return round_summary
    
def generate_season_ladder(round_summary, season_ladder_path):
    """Generate cumulative season ladder"""
    try:
        # Read existing season history
        if os.path.exists(season_ladder_path):
            with pd.ExcelFile(season_ladder_path) as xl:
                existing_ladder = pd.read_excel(xl)
        else:
            existing_ladder = pd.DataFrame()
        
        # Combine with new round
        season_ladder = pd.concat([existing_ladder, round_summary], ignore_index=True)
        
        # Group by club and sum points
        season_ladder = season_ladder.groupby('Club').agg({
            'Participation Points': 'sum',
            'Performance Points': 'sum',
            'Total Points': 'sum',
            'Adjusted Total Points': 'sum',
            'ICL Eligible Number': 'first'
        }).reset_index()
        
        # Sort by total points descending
        season_ladder = season_ladder.sort_values('Total Points', ascending=False)
        # Save the updated season ladder for next round
        season_ladder.to_excel(season_ladder_path, index=False)

        race_season_ladder = season_ladder[season_ladder['Club'].isin(round_summary['Club'])]
        return race_season_ladder
        
    except Exception as e:
        print(f"Error generating season ladder: {e}")
        return pd.DataFrame()
def generate_season_mvp_ladder(round_mvp_data):
    """Generate cumulative season MVP ladder"""
    try:
        season_mvp_path = os.path.join(CURRENT_SEASON_DIR, 'Season_MVP.xlsx')
        
        if os.path.exists(season_mvp_path):
            # Read existing season MVP data
            with pd.ExcelFile(season_mvp_path) as xl:
                season_mvp = pd.read_excel(xl)
                season_mvp = season_mvp.rename(columns={'Season Performance Points': 'Round Performance Points'})
            
            
            # Combine with new round data
            combined_mvp = pd.concat([season_mvp, round_mvp_data['round_mvp']], ignore_index=True)
            
            # Group by individual and sum points
            season_mvp = combined_mvp.groupby(['Full Name', 'TA Number', 'Club Name'])['Round Performance Points'].sum().reset_index()
            season_mvp = season_mvp.rename(columns={'Round Performance Points': 'Season Performance Points'})
            season_mvp = season_mvp.sort_values('Season Performance Points', ascending=False)
        else:
            # First round of the season
            season_mvp = round_mvp_data['round_mvp'].copy()
            season_mvp = season_mvp.rename(columns={'Round Performance Points': 'Season Performance Points'})
            
        # Save updated season MVP data
        season_mvp.to_excel(season_mvp_path, index=False)
        
        league_season_mvp = season_mvp[season_mvp['Club Name'].isin(round_mvp_data['round_mvp']['Club Name'])]

        return league_season_mvp
        
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
            club_mvp_sheet = club_mvp[['Full Name','TA Number','Category', 'Individual Performance Points']].rename(columns={
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
    
    # Define the columns we want to keep in the history
    desired_columns = [
        'First Name', 'Surname', 'TA Number', 'Category', 'Category Finish Place',
        'Club Name', 'Performance points Participation points or both',
        'Race_Type'
    ]
    
    if os.path.exists(history_path):
        with pd.ExcelFile(history_path) as xl:
            history_df = pd.read_excel(xl)
    else:
        history_df = pd.DataFrame()
    
    return_df = results_df[desired_columns]
    # Add round information to results
    return_df['League'] = round_info['league']
    return_df['Round'] = round_info['round']
    return_df['Event'] = round_info['name']
    
    # # Select only the desired columns from results_df
    # available_columns = [col for col in desired_columns if col in results_df.columns]
    # results_df = results_df[available_columns]
    
    # Check for duplicates - remove existing entries for this league/round combination
    if not history_df.empty:
        # Remove any existing entries for this league and round
        history_df = history_df[
            ~((history_df['League'] == round_info['league']) & 
              (history_df['Round'] == round_info['round']))
        ]
        print(f"DEBUG: Removed existing entries for {round_info['league']} Round {round_info['round']}")
    
    # Combine with history
    updated_history = pd.concat([history_df, return_df], ignore_index=True)
    
    # Save updated history
    updated_history.to_excel(history_path, index=False)
def process_round_file(round_info, season_source):
    """Process a single round file with multiple race sheets"""
    try:
        # Skip temporary Excel files
        if round_info['filename'].startswith('~$'):
            print(f"Skipping temporary file: {round_info['filename']}")
            return
            
        # Skip if filename doesn't match expected pattern
        if not re.match(r'^[^~].*Round \d+.*\.xlsx$', round_info['filename']):
            print(f"Skipping invalid filename format: {round_info['filename']}")
            return
        season_source = normalize_column_names(season_source)
        # Get league info from season source
        league_matches = season_source[
            (season_source['League Name'].str.lower() == round_info['league'].lower()) & 
            (season_source['Round'] == round_info['round'])
        ]
        
        if league_matches.empty:
            print(f"Error: No matching league/round found for {round_info['league']} Round {round_info['round']}")
            return
            
        league_info = league_matches.iloc[0]
        
        # Read Excel file with proper context management
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
                
            all_results = []
            all_points = []
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
                    print(f"\n=== PROCESSING RACE: {sheet_name} ===")
                    
                    # Read race results
                    race_df = xl.parse(sheet_name)
                    print(f"Raw data shape: {race_df.shape}")
                    print(f"Raw columns: {list(race_df.columns)}")
                    
                    race_df = normalize_column_names(race_df)
                    print(f"After normalize columns: {list(race_df.columns)}")
                    
                    # Standardize column names
                    race_df = validate_and_standardize_columns(race_df, sheet_name)
                    if race_df is None:
                        print(f"ERROR: validate_and_standardize_columns returned None for {sheet_name}")
                        continue
                    
                    print(f"After standardize columns: {list(race_df.columns)}")
                    print(f"Sample club names in race_df: {race_df['Club Name'].unique()}")
                    
                    # Clean data
                    race_df = race_df.dropna(subset=['Club Name'])
                    print(f"After dropna shape: {race_df.shape}")
                    race_df['Race_Type'] = sheet_name
                    
                    # Calculate points
                    if icl_df is not None:
                        print(f"ICL clubs before points calculation: {list(icl_df['Club'].values)}")
                        print(f"Race validation: {race_validation}")
                        
                        # Calculate performance points for this race
                        points_df = calculate_race_performance_points(race_df, icl_df.copy(), race_validation)
                        
                        print(f"Race performance points calculation returned:")
                        print(f"Shape: {points_df.shape}")
                        print(f"Columns: {list(points_df.columns)}")
                        print(f"Performance Points column values: {points_df['Performance Points'].tolist()}")
                        
                        points_df['Race_Type'] = sheet_name
                        
                        print(f"Before appending to all_points:")
                        print(points_df[['Club', 'Performance Points', 'Total Points']])
                        
                        all_points.append(points_df)
                        
                        print(f"Current all_points length: {len(all_points)}")
                    else:
                        print(f"ERROR: icl_df is None for {sheet_name}")
                    
                    all_results.append(race_df)
                    race_validations.append(race_validation)
                    
                    print(f"Successfully processed {sheet_name}")
                    
                except Exception as e:
                    print(f"Error processing sheet {sheet_name}: {e}")
                    import traceback
                    traceback.print_exc()
                    continue
            
            if not all_results:
                print("No valid race results found to process")
                return
                
            # Generate round summary
            round_summary = generate_round_summary(all_points, all_results, icl_df, race_validations)
            
            # Generate season ladder
            season_ladder_path = os.path.join(CURRENT_SEASON_DIR, 'Season_Ladder.xlsx')
            season_ladder = generate_season_ladder(round_summary, season_ladder_path)
            
            # Generate MVP data
            mvp_data = generate_individual_mvp_data(all_results, race_validations)
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
                
                # e) Individual club MVP sheets
                for sheet_name, club_mvp_df in club_mvp_sheets.items():
                    if not club_mvp_df.empty:
                        club_mvp_df.to_excel(writer, sheet_name=sheet_name, index=False)
                
                # Individual race results with points breakdowns
                for race_df, race_points in zip(all_results, all_points):
                    race_type = race_df['Race_Type'].iloc[0] if 'Race_Type' in race_df.columns else 'Unknown Race'
                    
                    # Combine race results with club points for this race
                    race_summary = race_points[['Club', 'Participation Points', 'Performance Points', 'Total Points']]
                    race_summary.to_excel(writer, sheet_name=f'{race_type} Points', index=False)
            
        # Update season history
        update_season_history(pd.concat(all_results), round_info)
        
        # Move processed file
        processed_path = os.path.join(PROCESSED_DIR, round_info['filename'])
        try:
            shutil.move(round_info['path'], processed_path)
            print(f"File moved successfully: {round_info['filename']}")
        except Exception as e:
            print(f"Warning: Could not move file {round_info['filename']}: {e}")
        
        print(f"Successfully processed {round_info['filename']} -> {output_filename}")
        
    except Exception as e:
        print(f"  {e}")
def main():
    """Main function to process triathlon results"""
    ensure_directories()
    
    # Get and validate season source
    season_source_path = get_season_source_of_truth()
    if not season_source_path:
        print("Error: No valid season source file found")
        return
        
    try:
        with pd.ExcelFile(season_source_path) as xl:
            season_source = pd.read_excel(xl)
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