# calculations.py
import pandas as pd
import os

from data_formatter import filter_eligible_clubs_only
import config

def validate_race_type(race_name, league_info):
    """Determine if a race is eligible for performance and/or participation points."""
    race_name = race_name.lower()
    perf_part_types = {t.strip().lower() for t in str(league_info['Per P & Part P']).split(',')}
    part_only_types = {t.strip().lower() for t in str(league_info['Part P']).split(',')}
    
    race_keywords = {'sprint', 'standard', 'aquabike', 'classic', 'ultimate', 'ultra', 'super'}
    found_types = set(race_name.split()).intersection(race_keywords)

    if not found_types:
        return {'performance_eligible': False, 'participation_eligible': False, 'double_points': False}

    is_perf = any(any(ft in at for ft in found_types) for at in perf_part_types)
    is_part = is_perf or any(any(ft in at for ft in found_types) for at in part_only_types)
    
    return {
        'performance_eligible': is_perf,
        'participation_eligible': is_part,
        'double_points': str(league_info['Double Points']).lower() == 'yes'
    }

def calculate_individual_performance_points(place):
    """Calculate points for an individual based on their category finish place."""
    points = {1: 10, 2: 9, 3: 8, 4: 7, 5: 6, 6: 5, 7: 4, 8: 3, 9: 2, 10: 1}
    return points.get(place, 0) if pd.notna(place) else 0

def calculate_round_participation_points(all_race_results, icl_df):
    """Calculate participation points once per round based on total finishers."""
    filtered_results = [filter_eligible_clubs_only(df, icl_df) for df in all_race_results]
    combined = pd.concat(filtered_results, ignore_index=True)
    
    finishers = combined['Club Name'].value_counts()
    icl_df['Total Finishers'] = icl_df['Club'].map(finishers).fillna(0)
    
    def get_points(row):
        if row['Total Finishers'] >= row['45 PTS (20%)']: return 45
        if row['Total Finishers'] >= row['30 PTS (10%)']: return 30
        if row['Total Finishers'] >= row['15PTS (5%)']: return 15
        return 0
        
    icl_df['Participation Points'] = icl_df.apply(get_points, axis=1)
    return icl_df

def calculate_round_performance_points(all_race_results, icl_df, race_validations):
    """Calculate total performance points across all eligible races in a round."""
    total_perf_points = pd.Series(0, index=icl_df['Club'].unique(), name='Performance Points')

    for race_df, validation in zip(all_race_results, race_validations):
        if not validation['performance_eligible']:
            continue
        
        filtered_df = filter_eligible_clubs_only(race_df, icl_df)
        filtered_df['Category Finish Place'] = pd.to_numeric(filtered_df['Category Finish Place'], errors='coerce')
        filtered_df['Points'] = filtered_df['Category Finish Place'].apply(calculate_individual_performance_points)
        
        if validation['double_points']:
            filtered_df['Points'] *= 2
            
        race_points = filtered_df.groupby('Club Name')['Points'].sum()
        total_perf_points = total_perf_points.add(race_points, fill_value=0)
        
    icl_df['Performance Points'] = icl_df['Club'].map(total_perf_points).fillna(0)
    return icl_df

def generate_round_summary(icl_with_participation, icl_with_performance):
    """Combine participation and performance points for a final round summary."""
    summary = icl_with_participation[['Club', 'ICL Eligible Number', 'Participation Points', 'Total Finishers']].copy()
    summary['Performance Points'] = summary['Club'].map(icl_with_performance['Performance Points']).fillna(0)
    summary['Total Points'] = summary['Participation Points'] + summary['Performance Points']
    return summary.sort_values('Total Points', ascending=False)

def generate_individual_mvp_data(all_results, race_validations):
    """Generate individual MVP data for the round."""
    eligible_results = []
    for df, validation in zip(all_results, race_validations):
        if validation['performance_eligible']:
            df_copy = df.copy()
            df_copy['Individual Performance Points'] = df_copy['Category Finish Place'].apply(calculate_individual_performance_points)
            if validation['double_points']:
                df_copy['Individual Performance Points'] *= 2
            eligible_results.append(df_copy)
    
    if not eligible_results: return None
    
    combined = pd.concat(eligible_results, ignore_index=True)
    
    round_mvp = combined.groupby(['First Name', 'Surname', 'Club Name'])['Individual Performance Points'].sum().reset_index()
    round_mvp['Full Name'] = round_mvp['First Name'] + ' ' + round_mvp['Surname']
    round_mvp = round_mvp.sort_values('Individual Performance Points', ascending=False).rename(
        columns={'Individual Performance Points': 'Round Performance Points'}
    )[['Full Name', 'Club Name', 'Round Performance Points']]
    
    club_mvps = combined.loc[combined.groupby('Club Name')['Individual Performance Points'].idxmax()]
    club_mvps['Full Name'] = club_mvps['First Name'] + ' ' + club_mvps['Surname']
    club_mvps = club_mvps.sort_values('Individual Performance Points', ascending=False).rename(
        columns={'Individual Performance Points': 'Performance Points'}
    )[['Club Name', 'Full Name', 'Performance Points']]
    
    return {'round_mvp': round_mvp, 'club_mvps': club_mvps, 'individual_results': combined}

def generate_season_ladder(round_summary):
    """Generate a cumulative season ladder by combining history with the current round."""
    history_path = os.path.join(config.CURRENT_SEASON_DIR, 'Season_Ladder.xlsx')
    history = pd.read_excel(history_path) if os.path.exists(history_path) else pd.DataFrame()
    
    combined = pd.concat([history, round_summary], ignore_index=True)
    season_ladder = combined.groupby('Club').agg({
        'Participation Points': 'sum',
        'Performance Points': 'sum',
        'Total Points': 'sum',
        'ICL Eligible Number': 'first'
    }).reset_index().sort_values('Total Points', ascending=False)
    
    season_ladder.to_excel(history_path, index=False)
    return season_ladder

def generate_season_mvp_ladder(round_mvp_data):
    """Generate and save the cumulative season MVP ladder."""
    season_mvp_path = os.path.join(config.CURRENT_SEASON_DIR, 'Season_MVP.xlsx')
    season_mvp = pd.read_excel(season_mvp_path) if os.path.exists(season_mvp_path) else pd.DataFrame()
    
    combined = pd.concat([season_mvp, round_mvp_data['round_mvp']], ignore_index=True)
    
    season_mvp = combined.groupby(['Full Name', 'Club Name'])['Round Performance Points'].sum().reset_index()
    season_mvp = season_mvp.rename(columns={'Round Performance Points': 'Season Performance Points'})
    season_mvp = season_mvp.sort_values('Season Performance Points', ascending=False)
            
    season_mvp.to_excel(season_mvp_path, index=False)
    return season_mvp

def generate_club_individual_mvp_sheets(mvp_data):
    """Generate a dictionary of DataFrames, one for each club's MVP breakdown."""
    if not mvp_data or 'individual_results' not in mvp_data: return {}
    
    sheets = {}
    for club, data in mvp_data['individual_results'].groupby('Club Name'):
        data = data.copy()
        data['Full Name'] = data['First Name'] + ' ' + data['Surname']
        sheet = data.sort_values('Individual Performance Points', ascending=False)
        sheets[f"{club} MVP"] = sheet[['Full Name', 'Category', 'Individual Performance Points']].rename(
            columns={'Individual Performance Points': 'Performance Points'}
        )
    return sheets