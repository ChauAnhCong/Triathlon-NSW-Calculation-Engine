import pandas as pd
import re
import pandas as pd
import os
import shutil
from datetime import datetime
import re
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
    updated_history = pd.concat([history_df, results_df])
    
    # Save updated history
    updated_history.to_excel(history_path, index=False)
def generate_round_summary(all_points_dfs, all_results_dfs):
    """Generate round summary with participation and performance breakdowns"""
    # Combine all race points
    round_points = pd.concat(all_points_dfs)
    
    # Group by club and sum points
    round_summary = round_points.groupby('Club').agg({
        'Participation Points': 'sum',
        'Performance Points': 'sum',
        'Total Points': 'sum',
        'ICL Eligible Number': 'first'
    }).reset_index()
    
    # Sort by total points descending
    round_summary = round_summary.sort_values('Total Points', ascending=False)
    
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
        season_ladder = pd.concat([season_history, round_summary])
        
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

def generate_mvp_ladders(results_df, round_info):
    """Generate MVP ladders for the round and season"""
    try:
        # Calculate individual points for this round
        results_df['MVP Points'] = results_df.apply(
            lambda row: calculate_individual_points(row), 
            axis=1
        )
        
        # Round MVP ladder
        round_mvp = results_df.groupby(['First Name', 'Surname', 'Club Name'])['MVP Points'].sum().reset_index()
        round_mvp['Full Name'] = round_mvp['First Name'] + ' ' + round_mvp['Surname']
        round_mvp = round_mvp.sort_values('MVP Points', ascending=False)
        
        # Club MVPs
        club_mvps = round_mvp.groupby('Club Name').first().reset_index()
        
        # Season MVP ladder
        season_mvp_path = os.path.join(CURRENT_SEASON_DIR, 'Season_MVP.xlsx')
        if os.path.exists(season_mvp_path):
            season_mvp = pd.read_excel(season_mvp_path)
            season_mvp = pd.concat([season_mvp, round_mvp])
            season_mvp = season_mvp.groupby(['Full Name', 'Club Name'])['MVP Points'].sum().reset_index()
            season_mvp = season_mvp.sort_values('MVP Points', ascending=False)
        else:
            season_mvp = round_mvp
            
        # Save season MVP data
        season_mvp.to_excel(season_mvp_path, index=False)
        
        return {
            'round_mvp': round_mvp,
            'club_mvps': club_mvps,
            'season_mvp': season_mvp
        }
        
    except Exception as e:
        print(f"Error generating MVP ladders: {e}")
        return None


def normalize_column_names(df):
    """
    Normalize column names by:
    - Removing leading/trailing spaces
    - Replacing multiple spaces with single space
    - Preserving case
    
    Args:
        df: pandas DataFrame
    Returns:
        DataFrame with normalized column names
    """
    df.columns = [
        re.sub(r'\s+', ' ', col.strip()) 
        for col in df.columns
    ]
    return df

# Update get_column_mapping to use normalized column names
def get_column_mapping(df):
    """Map various possible column names to standardized names"""
    # First normalize the column names
    df = normalize_column_names(df)
    
    column_mappings = {
        'First Name': ['First Name', 'FORENAME', 'FirstName', 'Given Name'],
        'Surname': ['Surname', 'SURNAME', 'LastName', 'Family Name'],
        'TA Number': ['TA Number', 'TANumber', 'TA_Number', 'Membership'],
        'Category': ['Category', 'CATGY', 'Race Category', 'Division'],
        'Category Finish Place': ['Category Finish Place', 'FINISH_CAT_PLACE', 'Cat Place', 'Division Place'],
        'Club Name': ['Club Name', 'Triathlon Club', 'Club', 'CLUB'],
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
            if 'ICL Eligible Number' not in icl_df.columns:
                print("Warning: ICL sheet missing required column 'ICL Eligible Number'")
        except Exception as e:
            print(f"Warning: Could not read ICL sheet: {e}")
            icl_df = None
            
        all_results = []
        all_points = []
        
        # Process each race sheet
        for sheet_name in xl.sheet_names:
            # Skip non-race and summary sheets
            if any(x in sheet_name.lower() for x in ['icl', 'summary', 'points', 'eligible']):
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
                
                # Calculate points
                if icl_df is not None:
                    race_df = race_df.merge(
                        icl_df[['Club', 'ICL Eligible Number']], 
                        left_on='Club Name',
                        right_on='Club',
                        how='left'
                    )
                
                points_df = calculate_participation_points(race_df, icl_df, race_validation)
                
                # Add metadata
                points_df['Race_Type'] = sheet_name
                all_points.append(points_df)
                all_results.append(race_df)
                
            except Exception as e:
                print(f"Error processing sheet {sheet_name}: {e}")
                continue
        
        if not all_results:
            print("No valid race results found to process")
            return
            
        # Generate round summary
        round_summary = generate_round_summary(all_points, all_results)
        
        # Generate season ladder
        season_ladder = generate_season_ladder(
            round_summary,
            os.path.join(CURRENT_SEASON_DIR, 'Season_Ladder.xlsx')
        )
        
        # Generate MVP ladders
        mvp_data = generate_mvp_ladders(pd.concat(all_results), round_info)
        
        # Save all outputs
        output_filename = f"{round_info['league']}_R{round_info['round']}_{datetime.now().strftime('%Y%m%d')}.xlsx"
        output_path = os.path.join(OUTPUT_DIR, output_filename)
        
        with pd.ExcelWriter(output_path) as writer:
            # Round results
            round_summary.to_excel(writer, sheet_name='Round Ladder', index=False)
            season_ladder.to_excel(writer, sheet_name='Season Ladder', index=False)
            
            if mvp_data:
                mvp_data['round_mvp'].to_excel(writer, sheet_name='Round MVP', index=False)
                mvp_data['club_mvps'].to_excel(writer, sheet_name='Club MVPs', index=False)
                mvp_data['season_mvp'].to_excel(writer, sheet_name='Season MVP', index=False)
            
            # Individual race results
            for race_type, race_points in pd.concat(all_points).groupby('Race_Type'):
                race_points.to_excel(writer, sheet_name=f'{race_type} Points', index=False)
        
        # Update season history
        update_season_history(pd.concat(all_results), round_info)
        
        # Move processed file
        processed_path = os.path.join(PROCESSED_DIR, round_info['filename'])
        shutil.move(round_info['path'], processed_path)
        
    except Exception as e:
        print(f"Error processing round file: {e}")

def normalize_string(text):
    """
    Normalize a string by removing punctuation and extra spaces,
    and converting to lowercase.
    """
    # Remove punctuation and convert to lowercase
    normalized = re.sub(r'[^\w\s]', '', text.lower())
    # Replace multiple spaces with single space and strip
    normalized = re.sub(r'\s+', ' ', normalized).strip()
    return normalized

def partial_match(str1, str2):
    """
    Check if one normalized string is completely contained in the other.
    
    Args:
        str1, str2: Strings to compare
    
    Returns:
        bool: True if one string is contained in the other
    """
    norm1 = normalize_string(str1)
    norm2 = normalize_string(str2)
    
    return norm1 in norm2
def validate_race_type(race_name, league_info):
    """
    Validate if race type is allowed based on the race types listed in season source
    
    Args:
        race_name: Name of the race sheet
        league_info: Row from season source of truth for this league/round
    """
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
        
        # Debug output
        print(f"\nRace validation for {race_name}:")
        print(f"Identified race types: {found_types}")
        print(f"Allowed race types:")
        print(f"- Performance & Participation: {perf_part_types}")
        print(f"- Participation only: {part_only_types}")
        print(f"Results:")
        print(f"- Performance eligible: {result['performance_eligible']}")
        print(f"- Participation eligible: {result['participation_eligible']}")
        print(f"- Double points: {result['double_points']}")
        
        return result
        
    except Exception as e:
        print(f"Error in race validation: {str(e)}")
        return {
            'performance_eligible': False,
            'participation_eligible': False,
            'double_points': False
        }

def validate_club(club_name, allowed_clubs):
    """Check if club is listed in season source of truth"""
    return any(partial_match(club_name, allowed_club) for allowed_club in allowed_clubs)

# Update calculate_individual_points to use standardized column names
def calculate_individual_points(results_df):
    """Calculate points for each individual participant"""
    # Initialize points for top 10 places
    place_points = {
        1: 10, 2: 9, 3: 8, 4: 7, 5: 6,
        6: 5, 7: 4, 8: 3, 9: 2, 10: 1
    }
    
    results_df['Individual Points'] = results_df.apply(
        lambda row: place_points.get(row['Category Finish Place'], 0) 
        if pd.notnull(row['Category Finish Place']) else 0, 
        axis=1
    )
    
    mvp_df = results_df[['Surname', 'First Name', 'Club Name', 'Category', 'Individual Points']]
    mvp_df['Full Name'] = mvp_df['First Name'] + ' ' + mvp_df['Surname']
    
    club_mvps = mvp_df.sort_values('Individual Points', ascending=False).groupby('Club Name').first()
    
    club_mvps = club_mvps.reset_index()
    club_mvps = club_mvps[['Club Name', 'Full Name', 'Category', 'Individual Points']]
    club_mvps = club_mvps.rename(columns={
        'Club Name': 'Club',
        'Individual Points': 'Points'
    })
    
    return club_mvps



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
    
    # Debug print
    print("\nPerformance Points Calculation:")
    print("Sample of results before grouping:")
    print(results_df[['Club Name', 'Category', 'Category Finish Place', 'Performance Points']].head())
    
    # Group by club and sum performance points
    club_points = results_df.groupby('Club Name')['Performance Points'].sum()
    
    print("\nPerformance points by club:")
    print(club_points)
    
    return club_points.to_dict()


def calculate_participation_points(results_df, league_df, race_validation=None):
    """Calculate participation and performance points with race type validation"""
    # Normalize column names
    results_df = normalize_column_names(results_df)
    league_df = normalize_column_names(league_df)
    
    if race_validation is None:
        race_validation = {
            'performance_eligible': True,
            'participation_eligible': True,
            'double_points': False
        }

    # Standardize club names using partial matching
    club_mapping = {}
    for league_club in league_df['Club'].values:
        for result_club in results_df['Club Name'].unique():
            if partial_match(league_club, result_club):
                club_mapping[result_club] = league_club
    
    # Apply club name standardization
    results_df['Club Name'] = results_df['Club Name'].map(club_mapping).fillna(results_df['Club Name'])
    
    # Debug print
    print("\nClub name mapping:")
    print(club_mapping)
    
    # Count finishers per club
    club_counts = results_df['Club Name'].value_counts().to_dict()
    league_df['Finishers'] = league_df['Club'].map(club_counts).fillna(0).astype(int)
    
    # Calculate participation points
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

    league_df['Participation Points'] = league_df.apply(get_participation_points, axis=1)

    # Calculate performance points if eligible
    if race_validation['performance_eligible']:
        performance_points = calculate_performance_points(results_df)
        league_df['Performance Points'] = league_df['Club'].map(performance_points).fillna(0)
    else:
        league_df['Performance Points'] = 0

    # Apply double points if specified
    if race_validation['double_points']:
        league_df['Performance Points'] *= 2
        league_df['Participation Points'] *= 2

    # Calculate total points
    league_df['Total Points'] = league_df['Participation Points'] + league_df['Performance Points']
    
    # Debug print
    print("\nFinal points calculation:")
    print(league_df[['Club', 'Participation Points', 'Performance Points', 'Total Points']])
    
    return league_df
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
        print(f"\nProcessing {round_info['league']}...")
        print(f"\nProcessing {round_info['round']}...")
        print(f"\nProcessing {round_info['name']}...")
        process_round_file(round_info, season_source)
    
    print("\nProcessing complete!")


if __name__ == "__main__":
    main()