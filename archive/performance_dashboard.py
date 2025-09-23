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

# 🚦 May 31 snapshot data
snapshot = pd.DataFrame({
    'Club': clubs['Club'],
    'Participants': [3, 8, 30, 2, 10],
    'Event-Weekends': [1, 2, 5, 1, 3]
})
snapshot['Total Participants'] = snapshot['Participants'] + snapshot['Event-Weekends']
snapshot = snapshot.merge(clubs[['Club', 'Members', 'Adjusted Members']], on='Club')
snapshot['Participation Points'] = snapshot.apply(
    lambda row: get_participation_points(row['Adjusted Members'], row['Total Participants']), axis=1)

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
            Event_Weekends = np.random.poisson(participants * 0.1)
            
            # Generate individual placements
            max_placements = min(participants + Event_Weekends, 15)
            num_placements = np.random.randint(1, max_placements + 1) if max_placements > 1 else 1
            placements = np.random.choice(range(1, 21), size=num_placements, replace=True)
            
            # Calculate points
            total_participants = participants + Event_Weekends
            participation_points = get_participation_points(club_row['Adjusted Members'], total_participants)
            performance_points = sum([max(0, 21 - p) for p in placements])  # 20 points for 1st, 19 for 2nd, etc.
            total_points = min(participation_points + performance_points, event_cap)
            
            time_series_data.append({
                'Date': date,
                'Club': club_row['Club'],
                'Members': club_row['Members'],
                'Adjusted_Members': club_row['Adjusted Members'],
                'Participants': participants,
                'Event_Weekends': Event_Weekends,
                'Total_Participants': total_participants,
                'Participation_Points': participation_points,
                'Performance_Points': performance_points,
                'Total_Points': total_points,
                'Placements': placements.tolist(),
                'Num_Placements': len(placements)
            })
    
    return pd.DataFrame(time_series_data)

# Create tabs
tab1, tab2 = st.tabs(["📊 May 31 Snapshot", "📈 Time Series Analysis"])

# ============ TAB 1: MAY 31 SNAPSHOT ============
with tab1:
    st.header("📊 May 31 Cutoff Analysis")
    st.write("This shows the aggregated data as it stood on May 31st, 2024")
    
    # Club overview metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Clubs", len(clubs))
    with col2:
        st.metric("Total Members", clubs['Members'].sum())
    with col3:
        st.metric("Active Participants", snapshot['Total Participants'].sum())
    with col4:
        st.metric("Total Points Awarded", snapshot['Participation Points'].sum())
    
    # 📈 Participation Points Bar Chart
    st.subheader("🏆 Club Participation Points (May 31)")
    
    bar_participation = alt.Chart(snapshot).mark_bar(color='steelblue').encode(
        x=alt.X('Club:N', sort='-y'),
        y='Participation Points:Q',
        tooltip=['Club:N', 'Participation Points:Q', 'Total Participants:Q', 'Members:Q']
    ).properties(height=400, title="Participation Points by Club")
    
    st.altair_chart(bar_participation, use_container_width=True)
    
    # 📊 Participation vs Members Scatter
    st.subheader("📊 Participation Rate Analysis")
    
    snapshot['Participation_Rate'] = (snapshot['Total Participants'] / snapshot['Adjusted Members']) * 100
    
    scatter_participation = alt.Chart(snapshot).mark_circle(size=200).encode(
        x=alt.X('Adjusted Members:Q', title='Club Size (Adjusted Members)'),
        y=alt.Y('Participation_Rate:Q', title='Participation Rate (%)'),
        color=alt.Color('Club:N', legend=alt.Legend(title="Club")),
        size=alt.Size('Participation Points:Q', title='Points Earned'),
        tooltip=['Club:N', 'Members:Q', 'Adjusted Members:Q', 'Total Participants:Q', 
                'Participation_Rate:Q', 'Participation Points:Q']
    ).properties(height=400, title="Club Size vs Participation Rate")
    
    st.altair_chart(scatter_participation, use_container_width=True)
    
    # 📋 Club breakdown table
    st.subheader("📋 Detailed Club Breakdown (May 31)")
    
    display_snapshot = snapshot.copy()
    display_snapshot['Participation_Rate'] = display_snapshot['Participation_Rate'].round(1)
    display_columns = ['Club', 'Members', 'Adjusted Members', 'Participants', 'Event-Weekends', 
                      'Total Participants', 'Participation_Rate', 'Participation Points']
    
    st.dataframe(
        display_snapshot[display_columns].rename(columns={
            'Participation_Rate': 'Participation Rate (%)',
            'Participation Points': 'Points Earned'
        }), 
        use_container_width=True
    )
    
    # 📊 Points threshold visualization
    st.subheader("🎯 Points Threshold Analysis")
    
    # Calculate what each club would need for different thresholds
    threshold_analysis = []
    for _, row in clubs.iterrows():
        club_data = {'Club': row['Club'], 'Current_Members': row['Adjusted Members']}
        for perc, points in [(0.05, threshold_5), (0.10, threshold_10), (0.20, threshold_20)]:
            req = round(row['Adjusted Members'] * perc)
            if row['Adjusted Members'] == 20 and req == 1 and perc == 0.10:
                req += 1
            club_data[f'{int(perc*100)}%_Required'] = req
            club_data[f'{int(perc*100)}%_Points'] = points
        threshold_analysis.append(club_data)
    
    threshold_df = pd.DataFrame(threshold_analysis)
    
    # Melt for visualization
    threshold_melted = threshold_df.melt(
        id_vars=['Club', 'Current_Members'], 
        value_vars=['5%_Required', '10%_Required', '20%_Required'],
        var_name='Threshold', value_name='Required_Participants'
    )
    threshold_melted['Threshold'] = threshold_melted['Threshold'].str.replace('_Required', ' Threshold')
    
    threshold_chart = alt.Chart(threshold_melted).mark_bar().encode(
        x='Club:N',
        y='Required_Participants:Q',
        color='Threshold:N',
        column='Threshold:N',
        tooltip=['Club:N', 'Required_Participants:Q', 'Current_Members:Q']
    ).properties(height=300, title="Participation Requirements by Threshold")
    
    st.altair_chart(threshold_chart, use_container_width=True)
    
    # Export May 31 data
    st.subheader("📥 Export May 31 Data")
    
    col1, col2 = st.columns(2)
    
    with col1:
        may_csv = snapshot.to_csv(index=False)
        st.download_button(
            label="📄 Download May 31 Snapshot",
            data=may_csv,
            file_name="may_31_snapshot.csv",
            mime="text/csv"
        )
    
    with col2:
        threshold_csv = threshold_df.to_csv(index=False)
        st.download_button(
            label="📄 Download Threshold Analysis",
            data=threshold_csv,
            file_name="threshold_requirements.csv",
            mime="text/csv"
        )

# ============ TAB 2: TIME SERIES ANALYSIS ============
with tab2:
    st.header("📈 Time Series Analysis")
    st.write("Live data ingestion and temporal analysis")
    
    # Time series parameters
    col1, col2, col3 = st.columns(3)
    
    with col1:
        start_date = st.date_input("Start Date", value=datetime(2025, 6, 1))
    with col2:
        end_date = st.date_input("End Date", value=datetime(2025, 12, 31))
    with col3:
        event_frequency = st.selectbox("Event Frequency", ["Weekly", "Bi-weekly", "Monthly"], index=0)
    
    # Generate the time series
    ts_df = generate_time_series(start_date, end_date, event_frequency, clubs)
    
    # Time series metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Events", len(ts_df['Date'].unique()))
    with col2:
        st.metric("Data Points", len(ts_df))
    with col3:
        st.metric("Avg Points/Event", f"{ts_df['Total_Points'].mean():.1f}")
    with col4:
        st.metric("Total Points Awarded", ts_df['Total_Points'].sum())
    
    # 📊 Time series visualization
    st.subheader("📈 Points Over Time")
    
    line_chart = alt.Chart(ts_df).mark_line(point=True).encode(
        x=alt.X('Date:T', title='Event Date'),
        y=alt.Y('Total_Points:Q', title='Total Points'),
        color=alt.Color('Club:N', legend=alt.Legend(title="Club")),
        tooltip=['Date:T', 'Club:N', 'Total_Points:Q', 'Participants:Q', 'Performance_Points:Q']
    ).properties(height=400, title="Club Performance Over Time")
    
    st.altair_chart(line_chart, use_container_width=True)
    
    # 📊 Cumulative points chart
    st.subheader("📈 Cumulative Points Standings")
    
    ts_df_sorted = ts_df.sort_values(['Club', 'Date'])
    ts_df_sorted['Cumulative_Points'] = ts_df_sorted.groupby('Club')['Total_Points'].cumsum()
    
    cumulative_chart = alt.Chart(ts_df_sorted).mark_line(point=True, strokeWidth=3).encode(
        x=alt.X('Date:T', title='Event Date'),
        y=alt.Y('Cumulative_Points:Q', title='Cumulative Points'),
        color=alt.Color('Club:N', legend=alt.Legend(title="Club")),
        tooltip=['Date:T', 'Club:N', 'Cumulative_Points:Q', 'Total_Points:Q']
    ).properties(height=400, title="Season Standings (Cumulative Points)")
    
    st.altair_chart(cumulative_chart, use_container_width=True)
    
    # 📊 Performance vs Participation breakdown
    st.subheader("📊 Points Composition Analysis")
    
    # Create stacked bar chart
    ts_melted = ts_df.melt(
        id_vars=['Date', 'Club'], 
        value_vars=['Participation_Points', 'Performance_Points'],
        var_name='Point_Type', value_name='Points'
    )
    ts_melted['Point_Type'] = ts_melted['Point_Type'].str.replace('_', ' ')
    
    stacked_chart = alt.Chart(ts_melted).mark_bar().encode(
        x=alt.X('Date:T', title='Event Date'),
        y=alt.Y('Points:Q', title='Points'),
        color=alt.Color('Point_Type:N', title='Point Type'),
        column=alt.Column('Club:N', title='Club'),
        tooltip=['Date:T', 'Club:N', 'Point_Type:N', 'Points:Q']
    ).properties(height=300, width=150, title="Points Breakdown by Club")
    
    st.altair_chart(stacked_chart, use_container_width=True)
    
    # 📊 Participation trends
    st.subheader("📊 Participation Trends")
    
    participation_chart = alt.Chart(ts_df).mark_area(opacity=0.7).encode(
        x=alt.X('Date:T', title='Event Date'),
        y=alt.Y('Total_Participants:Q', title='Total Participants'),
        color=alt.Color('Club:N', legend=alt.Legend(title="Club")),
        tooltip=['Date:T', 'Club:N', 'Total_Participants:Q', 'Participants:Q', 'Event_Weekends:Q']
    ).properties(height=400, title="Participation Levels Over Time")
    
    st.altair_chart(participation_chart, use_container_width=True)
    
    # 📋 Recent performance table
    st.subheader("📋 Recent Events (Last 10)")
    recent_data = ts_df.sort_values('Date', ascending=False).head(50)  # 10 most recent events
    display_columns = ['Date', 'Club', 'Participants', 'Event_Weekends', 'Participation_Points', 'Performance_Points', 'Total_Points']
    st.dataframe(recent_data[display_columns], use_container_width=True)
    
    # 📥 CSV Export Section
    st.subheader("📥 Export Time Series Data")
    
    col1, col2, col3 = st.columns(3)
    
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
    
    with col3:
        # Export participation trends
        participation_export = ts_df[['Date', 'Club', 'Participants', 'Event_Weekends', 'Total_Participants']].copy()
        participation_csv = participation_export.to_csv(index=False)
        st.download_button(
            label="📄 Download Participation Data",
            data=participation_csv,
            file_name=f"participation_trends_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )
    
    # 📊 Advanced exports
    with st.expander("📊 Advanced Data Exports"):
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Individual placements time series
            if st.button("🔄 Generate Individual Placements Export"):
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
                detailed_csv = detailed_ts_df.to_csv(index=False)
                st.download_button(
                    label="📄 Download Individual Placements",
                    data=detailed_csv,
                    file_name=f"individual_placements_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}.csv",
                    mime="text/csv"
                )
        
        with col2:
            # Aggregated summary
            aggregation_period = st.selectbox("Aggregation Period", ["Monthly", "Weekly"], index=0)
            
            if aggregation_period == "Monthly":
                freq = 'M'
            else:
                freq = 'W'
            
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
            agg_csv = aggregated.to_csv(index=False)
            st.download_button(
                label=f"📄 Download {aggregation_period} Aggregated",
                data=agg_csv,
                file_name=f"{aggregation_period.lower()}_aggregated_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )

# 📊 Overall Data Summary
with st.expander("📊 Dashboard Summary"):
    st.write("**Tab 1 - May 31 Snapshot:**")
    st.write("- Historical aggregated data as of May 31st cutoff")
    st.write("- Club participation analysis and threshold requirements")
    st.write("- Static point-in-time analysis")
    
    st.write("**Tab 2 - Time Series Analysis:**")
    st.write("- Live/streaming data with configurable frequency")
    st.write("- Temporal trends and cumulative standings")
    st.write("- Performance composition and participation patterns")
    
    st.write("**Current Settings:**")
    st.write(f"- 5% Threshold: {threshold_5} points")
    st.write(f"- 10% Threshold: {threshold_10} points") 
    st.write(f"- 20% Threshold: {threshold_20} points")
    st.write(f"- Event Cap: {event_cap} points")
    st.write(f"- Normalize Small Clubs: {normalize_small_clubs}")