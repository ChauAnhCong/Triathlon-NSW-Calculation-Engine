import streamlit as st
import pandas as pd
import numpy as np
import altair as alt
from datetime import datetime, timedelta

st.title("📆 Regional Interclub Points Explorer")

# 📌 Sidebar rules
st.sidebar.header("📋 Point Calculation Settings")

threshold_5 = st.sidebar.slider("5% Threshold Points", 10, 20, 15)
threshold_10 = st.sidebar.slider("10% Threshold Points", 20, 40, 30)
threshold_20 = st.sidebar.slider("20% Threshold Points", 30, 60, 45)
event_cap = st.sidebar.slider("Max Total Points per Event", 100, 200, 150)
normalize_small_clubs = st.sidebar.checkbox("Normalize clubs < 20 to 20 members", value=True)

# Time series parameters
st.sidebar.header("📅 Time Series Settings")
start_date = st.sidebar.date_input("Start Date", value=datetime(2025, 1, 1))
end_date = st.sidebar.date_input("End Date", value=datetime(2025, 6, 30))
event_frequency = st.sidebar.selectbox("Event Frequency", ["Weekly", "Bi-weekly", "Monthly"], index=0)

# 📅 Define clubs
clubs = pd.DataFrame({
    'Club': ['Northern Tide', 'Coastal Flyers', 'Urban Pulse', 'Desert Storm', 'Valley Racers'],
    'Members': [25, 64, 120, 18, 80]
})
if normalize_small_clubs:
    clubs['Adjusted Members'] = clubs['Members'].apply(lambda x: max(x, 20))
else:
    clubs['Adjusted Members'] = clubs['Members']

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

# 📊 Generate time series data
@st.cache_data
def generate_time_series(start_date, end_date, frequency, clubs_df, seed=42):
    np.random.seed(seed)
    
    # Create date range based on frequency
    if frequency == "Weekly":
        dates = pd.date_range(start=start_date, end=end_date, freq='W')
    elif frequency == "Bi-weekly":
        dates = pd.date_range(start=start_date, end=end_date, freq='2W')
    else:  # Monthly
        dates = pd.date_range(start=start_date, end=end_date, freq='M')
    
    time_series_data = []
    
    for date in dates:
        for _, club_row in clubs_df.iterrows():
            # Simulate seasonal variation and club-specific patterns
            base_participation = club_row['Adjusted Members'] * 0.15
            seasonal_factor = 1 + 0.3 * np.sin(2 * np.pi * date.dayofyear / 365)
            club_factor = np.random.uniform(0.8, 1.2)
            
            expected_participants = int(base_participation * seasonal_factor * club_factor)
            participants = max(1, np.random.poisson(expected_participants))
            double_ups = np.random.poisson(participants * 0.1)
            
            # Generate individual placements
            max_placements = min(participants + double_ups, 15)
            num_placements = np.random.randint(1, max_placements + 1) if max_placements > 1 else 1
            placements = np.random.choice(range(1, 21), size=num_placements, replace=True)
            
            # Calculate points
            total_participants = participants + double_ups
            participation_points = get_participation_points(club_row['Adjusted Members'], total_participants)
            performance_points = sum([max(0, 21 - p) for p in placements])  # 20 points for 1st, 19 for 2nd, etc.
            total_points = min(participation_points + performance_points, event_cap)
            
            time_series_data.append({
                'Date': date,
                'Club': club_row['Club'],
                'Members': club_row['Members'],
                'Adjusted_Members': club_row['Adjusted Members'],
                'Participants': participants,
                'Double_Ups': double_ups,
                'Total_Participants': total_participants,
                'Participation_Points': participation_points,
                'Performance_Points': performance_points,
                'Total_Points': total_points,
                'Placements': placements.tolist(),
                'Num_Placements': len(placements)
            })
    
    return pd.DataFrame(time_series_data)

# Generate the time series
ts_df = generate_time_series(start_date, end_date, event_frequency, clubs)

# 📊 Time series visualization
st.subheader("📈 Points Over Time")

# Create line chart
line_chart = alt.Chart(ts_df).mark_line(point=True).encode(
    x='Date:T',
    y='Total_Points:Q',
    color='Club:N',
    tooltip=['Date:T', 'Club:N', 'Total_Points:Q', 'Participants:Q', 'Performance_Points:Q']
).properties(height=400)

st.altair_chart(line_chart, use_container_width=True)

# 📊 Cumulative points chart
st.subheader("📈 Cumulative Points")
ts_df_sorted = ts_df.sort_values(['Club', 'Date'])
ts_df_sorted['Cumulative_Points'] = ts_df_sorted.groupby('Club')['Total_Points'].cumsum()

cumulative_chart = alt.Chart(ts_df_sorted).mark_line(point=True).encode(
    x='Date:T',
    y='Cumulative_Points:Q',
    color='Club:N',
    tooltip=['Date:T', 'Club:N', 'Cumulative_Points:Q']
).properties(height=400)

st.altair_chart(cumulative_chart, use_container_width=True)

# 📊 Recent performance table
st.subheader("📋 Recent Events (Last 5)")
recent_data = ts_df.sort_values('Date', ascending=False).head(25)  # 5 most recent events × 5 clubs
display_columns = ['Date', 'Club', 'Participants', 'Double_Ups', 'Participation_Points', 'Performance_Points', 'Total_Points']
st.dataframe(recent_data[display_columns])

# 📥 CSV Export Section
st.subheader("📥 Export Time Series Data")

col1, col2 = st.columns(2)

with col1:
    # Export complete time series
    ts_export = ts_df.copy()
    ts_export['Placements_String'] = ts_export['Placements'].apply(lambda x: ','.join(map(str, x)))
    ts_export_clean = ts_export.drop(['Placements'], axis=1)
    
    ts_csv = ts_export_clean.to_csv(index=False)
    st.download_button(
        label="📄 Download Complete Time Series",
        data=ts_csv,
        file_name=f"time_series_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}.csv",
        mime="text/csv"
    )

with col2:
    # Export cumulative summary
    cumulative_summary = ts_df_sorted[['Date', 'Club', 'Total_Points', 'Cumulative_Points']].copy()
    cumulative_csv = cumulative_summary.to_csv(index=False)
    st.download_button(
        label="📄 Download Cumulative Points",
        data=cumulative_csv,
        file_name=f"cumulative_points_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}.csv",
        mime="text/csv"
    )

# 📊 Detailed individual placements export
st.subheader("📊 Individual Placements Time Series")
if st.checkbox("Generate detailed placements time series"):
    detailed_ts = []
    for _, row in ts_df.iterrows():
        for i, placement in enumerate(row['Placements']):
            detailed_ts.append({
                'Date': row['Date'],
                'Club': row['Club'],
                'Event_Participant_ID': f"{row['Club']}_{row['Date'].strftime('%Y%m%d')}_{i+1}",
                'Placement': placement,
                'Points_Earned': max(0, 21 - placement)
            })
    
    detailed_ts_df = pd.DataFrame(detailed_ts)
    
    # Show sample
    st.dataframe(detailed_ts_df.head(20))
    
    # Export detailed placements
    detailed_csv = detailed_ts_df.to_csv(index=False)
    st.download_button(
        label="📄 Download Individual Placements Time Series",
        data=detailed_csv,
        file_name=f"individual_placements_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}.csv",
        mime="text/csv"
    )

# 📊 Monthly/Weekly aggregations
st.subheader("📊 Aggregated Time Series")

aggregation_period = st.selectbox("Aggregation Period", ["Monthly", "Weekly"], index=0)

if aggregation_period == "Monthly":
    freq = 'M'
    format_str = '%Y-%m'
else:
    freq = 'W'
    format_str = '%Y-%U'

ts_df['Period'] = ts_df['Date'].dt.to_period(freq)
aggregated = ts_df.groupby(['Club', 'Period']).agg({
    'Total_Points': 'sum',
    'Participation_Points': 'sum',
    'Performance_Points': 'sum',
    'Participants': 'sum',
    'Total_Participants': 'sum',
    'Date': 'count'  # Number of events
}).rename(columns={'Date': 'Number_of_Events'}).reset_index()

aggregated['Period_String'] = aggregated['Period'].astype(str)
st.dataframe(aggregated)

# Export aggregated data
agg_csv = aggregated.to_csv(index=False)
st.download_button(
    label=f"📄 Download {aggregation_period} Aggregated Data",
    data=agg_csv,
    file_name=f"{aggregation_period.lower()}_aggregated_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}.csv",
    mime="text/csv"
)

# 📊 Data Summary
with st.expander("📊 Time Series Data Summary"):
    st.write(f"**Generated {len(ts_df)} data points** ({len(ts_df['Date'].unique())} events × {len(clubs)} clubs)")
    st.write(f"**Date Range**: {start_date} to {end_date}")
    st.write(f"**Event Frequency**: {event_frequency}")
    st.write("**Available CSV exports:**")
    st.write("- **Complete Time Series**: All event-level data with individual club performance")
    st.write("- **Cumulative Points**: Running totals over time")
    st.write("- **Individual Placements**: Granular placement data for each participant")
    st.write(f"- **{aggregation_period} Aggregated**: Summarized by time period")
    
    st.write("**Time Series Columns:**")
    st.write("- Date, Club, Members, Participants, Points (various types)")
    st.write("- Individual placement arrays and performance metrics")
    st.write("- Seasonal and club-specific variation patterns")