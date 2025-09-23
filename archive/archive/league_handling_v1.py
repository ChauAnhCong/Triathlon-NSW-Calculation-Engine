import pandas as pd
import numpy as np

# --- 1. Create a Club-to-League Mapping ---
# Load the original season template to get the club-league association
season_template_df = pd.read_csv('Triathalon Season template AW UPDATED 28AUG25.xlsx - Interclub League season 1.csv')
season_template_df.columns = season_template_df.columns.str.strip()
season_template_df['League Name'] = season_template_df['League Name'].ffill()

# Drop rows where 'Clubs' is NaN and create the mapping
club_to_league = season_template_df.dropna(subset=['Clubs'])
club_to_league['Clubs'] = club_to_league['Clubs'].str.strip()
club_league_mapping = club_to_league.set_index('Clubs')['League Name'].to_dict()

# --- 2. Create an Event-to-Leagues Mapping ---
season_summary = pd.read_csv('triathlon_season_summary.csv')
season_summary['Events or Rounds'] = season_summary['Events or RoundI''s'].str.strip()
event_to_leagues = season_summary.groupby('Events or Rounds')['League Name'].apply(list).to_dict()

# --- 3. Reprocess Event Data with New Logic ---
event_files = {
    'IRONMAN 70.3 and Sprint Round 1': [
        'IRONMAN 70.3 and Sprint Round 1.xlsx - Sydney Round 1 70.3.csv',
        'IRONMAN 70.3 and Sprint Round 1.xlsx - Sydney Round 1 Sprint.csv'
    ],
    'Club Champs Round 2': [
        'Club Champs Round 2.xlsx - Club Distance.csv',
        'Club Champs Round 2.xlsx - Club Aquabike.csv',
        'Club Champs Round 2.xlsx - Half Club Distance.csv'
    ]
}

event_mapping = {
    'IRONMAN 70.3 and Sprint Round 1': 'IRONMAN Western Sydney 70.3',
    'Club Champs Round 2': 'NSW Triathlon Club Champs'
}

all_event_data_with_leagues = []

for event_name, files in event_files.items():
    # Read and concatenate data for the event
    event_df = pd.concat([pd.read_csv(f) for f in files], ignore_index=True)
    
    # Standardize 'Club Name' column
    club_column = [col for col in event_df.columns if 'club' in col.strip().lower()][0]
    event_df.rename(columns={club_column: 'Club Name'}, inplace=True)
    event_df['Club Name'] = event_df['Club Name'].str.strip()

    participating_clubs = event_df['Club Name'].unique()
    
    summary_event_name = event_mapping.get(event_name)
    if summary_event_name:
        eligible_leagues_for_event = event_to_leagues.get(summary_event_name, [])
        event_info = season_summary[season_summary['Events or Rounds'] == summary_event_name]
        
        # We might have multiple rows if the event is in multiple leagues. 
        # The eligible races should be the same, so we take the first row's info.
        if not event_info.empty:
            perf_points = event_info['Performance and Participation Points'].iloc[0]
            part_points = event_info['Participation Points Only'].iloc[0]

            for club in participating_clubs:
                club_league = "Unknown"
                # Find the league for the club, trying to match variations
                for map_club, league in club_league_mapping.items():
                    if club.lower() in map_club.lower() or map_club.lower() in club.lower():
                        club_league = league
                        break

                eligibility_status = "Ineligible"
                if club_league in eligible_leagues_for_event:
                    eligibility_status = "Eligible"
                
                # Special case for visiting members
                if "visiting" in club.lower():
                    eligibility_status = "Ineligible (Visiting)"
                
                all_event_data_with_leagues.append({
                    'Event': event_name,
                    'Club': club,
                    'League': club_league,
                    'Eligibility Status': eligibility_status,
                    'Eligible for Performance Points': perf_points if eligibility_status == "Eligible" else "N/A",
                    'Eligible for Participation Points': part_points if pd.notna(part_points) and eligibility_status == "Eligible" else "N/A"
                })

# --- 4. Display Final Results ---
if all_event_data_with_leagues:
    results_df_with_leagues = pd.DataFrame(all_event_data_with_leagues)
    
    print("--- Eligible Races by Club, League, and Event ---\n")
    for event, group in results_df_with_leagues.groupby('Event'):
        print(f"## Event: {event}\n")
        print(group[['Club', 'League', 'Eligibility Status', 'Eligible for Performance Points', 'Eligible for Participation Points']].to_markdown(index=False))
        print("\n" + "="*50 + "\n")
else:
    print("No matching event data could be processed with the new logic.")