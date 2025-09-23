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
            df = pd.read_excel(source_path)
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

def normalize_string(text):
    """Normalize a string by removing punctuation and extra spaces, and converting to lowercase."""
    normalized = re.sub(r'[^\w\s]', '', text.lower())
    normalized = re.sub(r'\s+', ' ', normalized).strip()
    return normalized

def partial_match(str1, str2):
    """Check if one normalized string is completely contained in the other."""
    norm1 = normalize_string(str1)
    norm2 = normalize_string(str2)
    return norm1 in norm2

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

def calculate_performance_points(results_df, race_validation):
    """Calculate performance points based on category finish positions"""
    if not race_validation['performance_eligible']:
        return {}
    
    # Convert Category Finish Place to numeric, handling any non-numeric values
    results_df['Category Finish Place'] = pd.to_numeric(
        results_df['Category Finish Place'], 
        errors='coerce'
    )
    
    # Calculate points for each participant
    results_df['Performance Points'] = results_df['Category Finish Place'].apply(
        calculate_individual_performance_points
    )
    
    # Apply double points if specified
    if race_validation['double_points']:
        results_df['Performance Points'] *= 2
    
    # Group by club and sum performance points
    club_points = results_df.groupby('Club Name')['Performance Points'].sum()
    
    return club_points.to_dict()

def calculate_participation_points(results_df, icl_df, race_validation):
    """Calculate participation and performance points with race type validation"""
    # Normalize column names
    results_df = normalize_column_names(results_df)
    icl_df = normalize_column_names(icl_df)
    
    if race_validation is None:
        race_validation = {
            'performance_eligible': True,
            'participation_eligible': True,
            'double_points': False
        }

    # Standardize club names using partial matching
    club_mapping = {}
    for icl_club in icl_df['Club'].values:
        for result_club in results_df['Club Name'].unique():
            if partial_match(icl_club, result_club):
                club_mapping[result_club] = icl_club
    
    # Apply club name standardization
    results_df['Club Name'] = results_df['Club Name'].map(club_mapping).fillna(results_df['Club Name'])
    
    # Count finishers per club FOR THIS SPECIFIC RACE
    club_counts = results_df['Club Name'].value_counts().to_dict()
    icl_df['Finishers'] = icl_df['Club'].map(club_counts).fillna(0).astype(int)
    
    # Calculate participation points FOR THIS SPECIFIC RACE
    def get_participation_points(row):
        if not race_validation['participation_eligible']:
            return 0
        if row['Finishers'] >= row['45 PTS (20%)']:
            return 45
        elif row['Finishers'] >= row['30 PTS (10%)']:
            return 30
        elif row['Finishers'] >= row['15PTS (5%)']:
            return 15
        return 0

    icl_df['Participation Points'] = icl_df.apply(get_participation_points, axis=1)

    # CRITICAL FIX: Calculate performance points FOR THIS SPECIFIC RACE
    if race_validation['performance_eligible']:
        # Calculate individual performance points
        results_df['Individual Performance Points'] = results_df['Category Finish Place'].apply(
            lambda place: calculate_individual_performance_points(place)
        )
        
        # Apply double points if specified
        if race_validation['double_points']:
            results_df['Individual Performance Points'] *= 2
        
        # Sum by club for this race
        club_performance = results_df.groupby('Club Name')['Individual Performance Points'].sum()
        icl_df['Performance Points'] = icl_df['Club'].map(club_performance).fillna(0)
    else:
        icl_df['Performance Points'] = 0

    # Apply double points to participation if specified
    if race_validation['double_points']:
        icl_df['Participation Points'] *= 2

    # Calculate total points for this race
    icl_df['Total Points'] = icl_df['Participation Points'] + icl_df['Performance Points']
    
    return icl_df

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
    
    # Create club MVP breakdown (top performer from each club)
    club_mvps = combined_results.groupby('Club Name').apply(
        lambda x: x.loc[x['Individual Performance Points'].idxmax()] if len(x) > 0 else None
    ).reset_index(drop=True)
    
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

def generate_round_summary(all_points_dfs, all_results_dfs, race_validations):
    """Generate round summary with participation and performance breakdowns"""
    
    # STEP 1: Calculate participation points (from existing race point calculations)
    round_points = pd.concat(all_points_dfs, ignore_index=True)
    participation_summary = round_points.groupby('Club').agg({
        'Participation Points': 'sum',
        'ICL Eligible Number': 'first'
    }).reset_index()
    
    # STEP 2: Calculate performance points by aggregating individual results
    club_performance_points = {}
    
    for results_df, race_validation in zip(all_results_dfs, race_validations):
        if race_validation['performance_eligible']:
            # Calculate individual performance points for this race
            results_df_copy = results_df.copy()
            results_df_copy['Individual Performance Points'] = results_df_copy['Category Finish Place'].apply(
                lambda place: calculate_individual_performance_points(place)
            )
            
            # Apply double points if specified
            if race_validation['double_points']:
                results_df_copy['Individual Performance Points'] *= 2
            
            # Sum by club for this race
            race_club_performance = results_df_copy.groupby('Club Name')['Individual Performance Points'].sum()
            
            # Add to total club performance points
            for club, points in race_club_performance.items():
                club_performance_points[club] = club_performance_points.get(club, 0) + points
    
    # STEP 3: Merge participation and performance points
    participation_summary['Performance Points'] = participation_summary['Club'].map(club_performance_points).fillna(0)
    participation_summary['Total Points'] = participation_summary['Participation Points'] + participation_summary['Performance Points']
    
    # Sort by total points descending
    round_summary = participation_summary.sort_values('Total Points', ascending=False)
    
    return round_summary

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
            
            club_individual_sheets[f"{club_name} Round MVP"] = club_mvp_sheet
            
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
    """Process a single round file with multiple race sheets"""
    try:
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
        
        # Read Excel file
        xl = pd.ExcelFile(round_info['path'])
        
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
                
                # Calculate points FOR THIS SPECIFIC RACE
                if icl_df is not None:
                    points_df = calculate_participation_points(race_df, icl_df.copy(), race_validation)
                    points_df['Race_Type'] = sheet_name
                    all_points.append(points_df)
                
                all_results.append(race_df)
                race_validations.append(race_validation)
                
            except Exception as e:
                print(f"Error processing sheet {sheet_name}: {e}")
                continue
        
        if not all_results:
            print("No valid race results found to process")
            return
            
        # CRITICAL FIX: Generate MVP data first
        mvp_data = generate_individual_mvp_data(all_results, race_validations)
        
        # Generate round summary using MVP data for performance points aggregation
        round_summary = generate_round_summary(all_points, all_results, race_validations)
        
        # Generate season ladder
        season_ladder_path = os.path.join(CURRENT_SEASON_DIR, 'Season_Ladder.xlsx')
        season_ladder = generate_season_ladder(round_summary, season_ladder_path)
        
        # Generate season MVP
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
            
            # Individual race results with CORRECTED points breakdowns
            for race_points in all_points:
                race_type = race_points['Race_Type'].iloc[0] if 'Race_Type' in race_points.columns else 'Unknown Race'
                race_summary = race_points[['Club', 'Participation Points', 'Performance Points', 'Total Points', 'Finishers']]
                race_summary.to_excel(writer, sheet_name=f'{race_type} Points', index=False)
        
        # Update season history
        update_season_history(pd.concat(all_results), round_info)
        
        # Move processed file
        processed_path = os.path.join(PROCESSED_DIR, round_info['filename'])
        shutil.move(round_info['path'], processed_path)
        
        print(f"Successfully processed {round_info['filename']} -> {output_filename}")
        
    except Exception as e:
        print(f"Error processing round file: {e}")

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