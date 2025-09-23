# data_formatter.py
import pandas as pd
import re

def normalize_column_names(df):
    """Normalize column names by cleaning spaces."""
    df.columns = [re.sub(r'\s+', ' ', col.strip()) for col in df.columns]
    return df

def normalize_club_name(club_name):
    """Normalize club name for consistent comparison."""
    if pd.isna(club_name):
        return ""
    normalized = str(club_name).lower().strip()
    normalized = re.sub(r'\s+', ' ', normalized)
    normalized = normalized.replace('triathlon club', 'tc')
    normalized = normalized.replace(' club', '')
    normalized = re.sub(r'[^\w\s]', '', normalized)
    return normalized

def get_column_mapping(df):
    """Map various possible column names to standardized names."""
    column_mappings = {
        'First Name': ['First Name', 'FORENAME', 'FirstName', 'Given Name'],
        'Surname': ['Surname', 'SURNAME', 'LastName', 'Family Name', 'Surname '],
        'TA Number': ['TA Number', 'TANumber', 'TA_Number', 'Membership'],
        'Category': ['Category', 'CATGY', 'Race Category', 'Division', 'Category '],
        'Category Finish Place': ['Category Finish Place', 'FINISH_CAT_PLACE', 'Cat Place', 'Division Place', 'Category Finish Place '],
        'Club Name': ['Club Name', 'Triathlon Club', 'Club', 'CLUB', 'Club Name '],
    }
    actual_columns = {
        std_name: next((col for col in df.columns if col in possible_names), None)
        for std_name, possible_names in column_mappings.items()
    }
    return {k: v for k, v in actual_columns.items() if v}

def validate_and_standardize_columns(race_df, sheet_name):
    """Validate required columns and rename them to standard names."""
    required = {'First Name', 'Surname', 'TA Number', 'Category', 'Category Finish Place', 'Club Name'}
    mapping = get_column_mapping(race_df)
    
    if not required.issubset(mapping.keys()):
        print(f"Warning: Sheet {sheet_name} missing required columns: {required - set(mapping.keys())}")
        return None
        
    return race_df.rename(columns={v: k for k, v in mapping.items()})

def create_club_mapping(results_df, icl_df):
    """Create a mapping from result club names to official ICL club names."""
    eligible_clubs = set(icl_df['Club'].values)
    result_clubs = set(results_df['Club Name'].dropna().unique())
    
    club_mapping = {}
    for result_club in result_clubs:
        result_normalized = normalize_club_name(result_club)
        for eligible_club in eligible_clubs:
            if result_normalized == normalize_club_name(eligible_club):
                club_mapping[result_club] = eligible_club
                break
    return club_mapping

def filter_eligible_clubs_only(results_df, icl_df):
    """Filter results to only include ICL-eligible clubs and standardize names."""
    club_mapping = create_club_mapping(results_df, icl_df)
    filtered_df = results_df[results_df['Club Name'].isin(club_mapping.keys())].copy()
    filtered_df['Club Name'] = filtered_df['Club Name'].map(club_mapping)
    return filtered_df

def infer_league_from_clubs(filepath, season_source):
    """Infer the most likely league based on participating clubs in a results file."""
    try:
        with pd.ExcelFile(filepath) as xl:
            if 'Current ICL Eligible Number' in xl.sheet_names:
                icl_df = xl.parse('Current ICL Eligible Number')
                participating_clubs = {normalize_club_name(c) for c in icl_df['Club'].dropna()}
                
                league_matches = {}
                for _, row in season_source.iterrows():
                    league_name = row['League Name']
                    if pd.notna(row['Clubs']):
                        league_clubs = {normalize_club_name(c) for c in str(row['Clubs']).split(',')}
                        matching = participating_clubs.intersection(league_clubs)
                        if matching:
                            league_matches[league_name] = len(matching) / len(league_clubs)
                
                if league_matches:
                    return max(league_matches, key=league_matches.get)
    except Exception as e:
        print(f"Warning: Could not infer league from clubs: {e}")
    return None

def read_icl_tables(filepath):
    """Read multiple ICL tables from an Excel sheet, separated by blank rows."""
    try:
        with pd.ExcelFile(filepath) as xl:
            if 'Current ICL Eligible Number' not in xl.sheet_names:
                return None
            raw_data = xl.parse('Current ICL Eligible Number', header=None)
            
        icl_tables, current_data, current_league, header_row = {}, [], None, None
        
        for idx, row in raw_data.iterrows():
            if row.isna().all():
                if current_league and current_data:
                    df = pd.DataFrame(current_data, columns=header_row)
                    df = normalize_column_names(df)
                    icl_tables[current_league] = df[df['Club'].notna()]
                current_data, current_league, header_row = [], None, None
                continue

            row_data = row.dropna().tolist()
            if not row_data: continue

            if isinstance(row_data[0], str) and 'League' in row_data[0]:
                current_league = row_data[0]
                header_row = raw_data.iloc[idx + 1].tolist()
                continue
            
            if header_row and current_league and row.tolist()[:len(header_row)] != header_row:
                current_data.append(row.tolist()[:len(header_row)])

        if current_league and current_data:
            df = pd.DataFrame(current_data, columns=header_row)
            df = normalize_column_names(df)
            icl_tables[current_league] = df[df['Club'].notna()]
            
        return icl_tables
    except Exception as e:
        print(f"Error reading ICL tables: {e}")
        return None