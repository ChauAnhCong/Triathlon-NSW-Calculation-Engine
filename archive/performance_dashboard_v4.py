import streamlit as st
import pandas as pd
import numpy as np
import altair as alt
from io import StringIO

st.title("📆 Regional Interclub Points Explorer")

# 📌 Sidebar rules
st.sidebar.header("📋 Point Calculation Settings")

threshold_5 = st.sidebar.slider("5% Threshold Points", 10, 20, 15)
threshold_10 = st.sidebar.slider("10% Threshold Points", 20, 40, 30)
threshold_20 = st.sidebar.slider("20% Threshold Points", 30, 60, 45)
event_cap = st.sidebar.slider("Max Total Points per Event", 100, 200, 150)
normalize_small_clubs = st.sidebar.checkbox("Normalize clubs < 20 to 20 members", value=True)

# 📅 Define clubs & May 31 snapshot
clubs = pd.DataFrame({
    'Club': ['Northern Tide', 'Coastal Flyers', 'Urban Pulse', 'Desert Storm', 'Valley Racers'],
    'Members': [25, 64, 120, 18, 80]
})
if normalize_small_clubs:
    clubs['Adjusted Members'] = clubs['Members'].apply(lambda x: max(x, 20))
else:
    clubs['Adjusted Members'] = clubs['Members']

# 🚦 May 31 snapshot data
snapshot = pd.DataFrame({
    'Club': clubs['Club'],
    'Participants': [3, 8, 30, 2, 10],
    'Double-Ups': [1, 2, 5, 1, 3]
})
snapshot['Total Participants'] = snapshot['Participants'] + snapshot['Double-Ups']
snapshot = snapshot.merge(clubs[['Club', 'Adjusted Members']], on='Club')

# 🧠 Participation logic
def get_participation_points(size, count):
    thresholds = {
        0.05: threshold_5,
        0.10: threshold_10,
        0.20: threshold_20,
    }
    pts = 0
    for perc, val in thresholds.items():
        req = round(size * perc)
        if size == 20 and req == 1 and perc == 0.10:
            req += 1
        if count >= req:
            pts = val
    return pts

snapshot['Participation Points'] = snapshot.apply(
    lambda row: get_participation_points(row['Adjusted Members'], row['Total Participants']), axis=1)

# 📈 Bar chart for May 31
st.subheader("📊 May 31 Club Participation Summary")
bar_may = alt.Chart(snapshot).mark_bar().encode(
    x='Club:N',
    y='Participation Points:Q',
    color='Club:N'
).properties(height=400)

st.altair_chart(bar_may, use_container_width=True)

# 📆 Simulate one more month of streaming data
month = pd.Timestamp("2025-06-30")
stream_data = []
np.random.seed(42)
for i, row in clubs.iterrows():
    entries = np.random.randint(4, 25)
    double_ups = np.random.randint(0, 3)
    placements = np.random.choice(range(1, 11), size=np.random.randint(1, entries), replace=True)
    stream_data.append({
        'Club': row['Club'],
        'Date': month,
        'Participants': entries,
        'Double-Ups': double_ups,
        'Placements': placements,
        'Adjusted Members': row['Adjusted Members']
    })

stream_df = pd.DataFrame(stream_data)
stream_df['Total Participants'] = stream_df['Participants'] + stream_df['Double-Ups']
stream_df['Participation Points'] = stream_df.apply(
    lambda row: get_participation_points(row['Adjusted Members'], row['Total Participants']), axis=1)
stream_df['Performance Points'] = stream_df['Placements'].apply(lambda x: sum([11 - p for p in x]))
stream_df['Total Points'] = stream_df['Participation Points'] + stream_df['Performance Points']
stream_df['Total Points'] = stream_df['Total Points'].clip(upper=event_cap)

# 📊 Bar chart for streaming month
st.subheader("📊 June Club Performance (Streamed Data)")
bar_june = alt.Chart(stream_df).transform_fold(
    ['Participation Points', 'Performance Points', 'Total Points'],
    as_=['Point Type', 'Points']
).mark_bar().encode(
    x='Club:N',
    y='Points:Q',
    color='Point Type:N',
    column='Point Type:N'
).properties(height=400)

st.altair_chart(bar_june, use_container_width=True)

# 📋 Monthly Table
st.subheader("📋 June Points Table")
st.dataframe(stream_df[['Club', 'Participation Points', 'Performance Points', 'Total Points']])

# 📥 CSV Export Section
st.subheader("📥 Export Data to CSV")

# Create columns for export buttons
col1, col2, col3 = st.columns(3)

with col1:
    # Export May 31 snapshot data
    may_csv = snapshot.to_csv(index=False)
    st.download_button(
        label="📄 Download May 31 Data",
        data=may_csv,
        file_name="may_31_snapshot.csv",
        mime="text/csv"
    )

with col2:
    # Export June streaming data (summary)
    june_summary = stream_df[['Club', 'Date', 'Participants', 'Double-Ups', 'Total Participants', 
                              'Participation Points', 'Performance Points', 'Total Points']].copy()
    june_csv = june_summary.to_csv(index=False)
    st.download_button(
        label="📄 Download June Summary",
        data=june_csv,
        file_name="june_performance_summary.csv",
        mime="text/csv"
    )

with col3:
    # Export club configuration data
    clubs_csv = clubs.to_csv(index=False)
    st.download_button(
        label="📄 Download Club Config",
        data=clubs_csv,
        file_name="club_configuration.csv",
        mime="text/csv"
    )

# 📊 Detailed placements export (optional)
st.subheader("📊 Detailed Placements Data")
if st.checkbox("Show detailed placements data"):
    # Create detailed placements dataframe
    detailed_placements = []
    for _, row in stream_df.iterrows():
        for placement in row['Placements']:
            detailed_placements.append({
                'Club': row['Club'],
                'Date': row['Date'],
                'Placement': placement,
                'Points_Earned': 11 - placement
            })
    
    placements_df = pd.DataFrame(detailed_placements)
    st.dataframe(placements_df)
    
    # Export detailed placements
    placements_csv = placements_df.to_csv(index=False)
    st.download_button(
        label="📄 Download Detailed Placements",
        data=placements_csv,
        file_name="detailed_placements.csv",
        mime="text/csv"
    )

# 📋 Export all data as one combined file
st.subheader("📋 Combined Export")
if st.button("🔄 Generate Combined Export"):
    # Create a combined dataset with all information
    combined_data = []
    
    # Add May data
    for _, row in snapshot.iterrows():
        combined_data.append({
            'Month': 'May',
            'Club': row['Club'],
            'Members': clubs[clubs['Club'] == row['Club']]['Members'].iloc[0],
            'Adjusted_Members': row['Adjusted Members'],
            'Participants': row['Participants'],
            'Double_Ups': row['Double-Ups'],
            'Total_Participants': row['Total Participants'],
            'Participation_Points': row['Participation Points'],
            'Performance_Points': 0,  # No performance data for May
            'Total_Points': row['Participation Points']
        })
    
    # Add June data
    for _, row in stream_df.iterrows():
        combined_data.append({
            'Month': 'June',
            'Club': row['Club'],
            'Members': clubs[clubs['Club'] == row['Club']]['Members'].iloc[0],
            'Adjusted_Members': row['Adjusted Members'],
            'Participants': row['Participants'],
            'Double_Ups': row['Double-Ups'],
            'Total_Participants': row['Total Participants'],
            'Participation_Points': row['Participation Points'],
            'Performance_Points': row['Performance Points'],
            'Total_Points': row['Total Points']
        })
    
    combined_df = pd.DataFrame(combined_data)
    combined_csv = combined_df.to_csv(index=False)
    
    st.download_button(
        label="📄 Download Combined Data (May + June)",
        data=combined_csv,
        file_name="combined_performance_data.csv",
        mime="text/csv"
    )
    
    st.success("✅ Combined export generated! Click the download button above to save the file.")

# 📊 Data Summary
with st.expander("📊 Data Summary"):
    st.write("**Available CSV exports:**")
    st.write("- **May 31 Data**: Club participation snapshot for May")
    st.write("- **June Summary**: Complete June performance data")
    st.write("- **Club Config**: Club membership configuration")
    st.write("- **Detailed Placements**: Individual placement records (optional)")
    st.write("- **Combined Data**: All months combined in one file")
    
    st.write("**Current Settings:**")
    st.write(f"- 5% Threshold: {threshold_5} points")
    st.write(f"- 10% Threshold: {threshold_10} points")
    st.write(f"- 20% Threshold: {threshold_20} points")
    st.write(f"- Event Cap: {event_cap} points")
    st.write(f"- Normalize Small Clubs: {normalize_small_clubs}")