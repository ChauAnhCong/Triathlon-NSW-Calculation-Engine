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
    return league_df #[['Club', 'Finishers', 'Participation Points']]

def main():
    # Read Excel sheets
    xl = pd.ExcelFile('Example Interclub for Cameron.xlsx')
    results_df = xl.parse('Results')
    league_df = xl.parse('League one', header=1)  # Header is on row 2 (index 1)

    # Clean up column names if needed
    league_df.columns = [col.strip() for col in league_df.columns]
    results_df.columns = [col.strip() for col in results_df.columns]
    league_df.dropna(subset=['Club'], inplace=True)
    results_df.dropna(subset=['Triathlon Club'], inplace=True)
    # Calculate points
    points_df = calculate_participation_points(results_df, league_df)
    print(points_df)


    premier_league_df = xl.parse('Premier League')  # Header is on row 2 (index 1)
    premier_league_df.columns = [col.strip() for col in premier_league_df.columns]
    premier_league_df.dropna(subset=['Club'], inplace=True)
    # Calculate points
    points_df = calculate_participation_points(results_df, premier_league_df)
    print(points_df)



    # Save results to Excel
    with pd.ExcelWriter('Participation_Points_Calculation.xlsx') as writer:
        points_df.to_excel(writer, sheet_name='League Points', index=False)
        premier_league_df.to_excel(writer, sheet_name='Premier League Points', index=False)     



if __name__ == "__main__":
    main()