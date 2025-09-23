import pandas as pd
import re


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

def calculate_individual_points(results_df):
    """Calculate points for each individual participant"""
    # Initialize points for top 10 places
    place_points = {
        1: 10, 2: 9, 3: 8, 4: 7, 5: 6,
        6: 5, 7: 4, 8: 3, 9: 2, 10: 1
    }
    
    # Calculate performance points for each participant
    results_df['Individual Points'] = results_df.apply(
        lambda row: place_points.get(row['FINISH_CAT_PLACE'], 0) 
        if pd.notnull(row['FINISH_CAT_PLACE']) else 0, 
        axis=1
    )
    
    # Create MVP dataframe
    mvp_df = results_df[['SURNAME', 'FORENAME', 'Triathlon Club', 'CATGY', 'Individual Points']]
    mvp_df['Full Name'] = mvp_df['FORENAME'] + ' ' + mvp_df['SURNAME']
    
    # Group by club and get top scorer
    club_mvps = mvp_df.sort_values('Individual Points', ascending=False).groupby('Triathlon Club').first()
    
    # Reset index and reorder columns
    club_mvps = club_mvps.reset_index()
    club_mvps = club_mvps[['Triathlon Club', 'Full Name', 'CATGY', 'Individual Points']]
    club_mvps = club_mvps.rename(columns={
        'Triathlon Club': 'Club',
        'CATGY': 'Category',
        'Individual Points': 'Points'
    })
    
    return club_mvps
def calculate_performance_points(results_df):
    """Calculate performance points based on category finish positions"""
    # Initialize points for top 3 places
    place_points = {
        1: 10,  # 1st place
        2: 9,   # 2nd place
        3: 8,   # 3rd place
        4: 7,   # 4th place
        5: 6,   # 5th place
        6: 5,   # 6th place
        7: 4,   # 7th place
        8: 3,   # 8th place
        9: 2,   # 9th place
        10: 1   # 10th place
    }
    
    # Create mask for top 3 finishers in each category
    results_df['Performance Points'] = results_df.apply(
        lambda row: place_points.get(row['FINISH_CAT_PLACE'], 0) 
        if pd.notnull(row['FINISH_CAT_PLACE']) else 0, 
        axis=1
    )
    
    # Group by club and sum performance points
    return results_df.groupby('Triathlon Club')['Performance Points'].sum().to_dict()
def calculate_participation_points(results_df, league_df):

    # Standardize club names to lowercase and strip whitespace for matching
    # results_df['Triathlon Club'] = results_df['Triathlon Club'].fillna('')
    # league_df['Club'] = league_df['Club'].fillna('')
    result = []
    # Create a mapping for club names based on partial matches
    for comp_name in league_df['Club'].values:
        for club_name in results_df['Triathlon Club'].values:
            if partial_match(comp_name,club_name):
                result.append({club_name :comp_name})
    # result = set(result)
    result = {k: v for d in result for k, v in d.items()}
    results_df['Triathlon Club'] =  results_df['Triathlon Club'].replace(result)
    # league_df['Club'] =  league_df['Club'].replace(result) #league_df.loc[league_df['Club'] == comp_name, 'Club'] = club_name


    # Count finishers per club
    club_counts = results_df['Triathlon Club'].value_counts().to_dict()
    league_df['Finishers'] = league_df['Club'].map(club_counts).fillna(0).astype(int)
    league_df['45 PTS (20%)'] = league_df['45 PTS (20%)'].astype(int)
    league_df['30 PTS (10%)'] = league_df['30 PTS (10%)'].astype(int)
    league_df['15PTS (5%)'] = league_df['15PTS (5%)'].astype(int)
    # Calculate points
    def get_points(row):
        if row['Finishers'] >= row['45 PTS (20%)']:
            return 45
        elif row['Finishers'] >= row['30 PTS (10%)']:
            return 30
        elif row['Finishers'] >= row['15PTS (5%)']:
            return 15
        else:
            return 0

    league_df['Participation Points'] = league_df.apply(get_points, axis=1)
    performance_points = calculate_performance_points(results_df)
    league_df['Performance Points'] = league_df['Club'].map(performance_points).fillna(0).astype(int)
    
    # Calculate total points
    league_df['Total Points'] = league_df['Participation Points'] + league_df['Performance Points']
    
    return league_df

def main():
    # Read Excel sheets
    xl = pd.ExcelFile('Example Interclub for Cameron.xlsx')
    results_df = xl.parse('Results')
    return_results_df = results_df.copy()
    league_df = xl.parse('League one', header=1)  # Header is on row 2 (index 1)

    # Clean up column names if needed
    league_df.columns = [col.strip() for col in league_df.columns]
    results_df.columns = [col.strip() for col in results_df.columns]
    league_df.dropna(subset=['Club'], inplace=True)
    results_df.dropna(subset=['Triathlon Club'], inplace=True)



    premier_league_df = xl.parse('Premier League')  # Header is on row 2 (index 1)
    premier_league_df.columns = [col.strip() for col in premier_league_df.columns]
    premier_league_df.dropna(subset=['Club'], inplace=True)
    # Calculate points
    
    print(premier_points_df)



    # Calculate MVP data
    premier_points_df = calculate_participation_points(results_df, premier_league_df)
    points_df = calculate_participation_points(results_df, league_df)
    mvp_df = calculate_individual_points(results_df)

    # Save results to Excel with MVP sheet
    with pd.ExcelWriter('Participation_Points_Calculation.xlsx') as writer:
        columns_order = ['Club', 'ICL Eligible Number','45 PTS (20%)','30 PTS (10%)','15PTS (5%)', 'Finishers', 
                        'Participation Points', 'Performance Points', 'Total Points']
        
        league_points = points_df[columns_order]
        premier_points = premier_points_df[columns_order]

        return_results_df.to_excel(writer, sheet_name='Results', index=False)
        league_points.to_excel(writer, sheet_name='League Points', index=False)
        premier_points.to_excel(writer, sheet_name='Premier League Points', index=False)
        mvp_df.to_excel(writer, sheet_name='Club MVPs', index=False)    



if __name__ == "__main__":
    main()