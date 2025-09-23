import streamlit as st
import pandas as pd
import numpy as np
import altair as alt

st.title("📈 Club Performance Over Time")

# Simulate event results over 6 months
months = pd.date_range(start="2025-01-01", periods=6, freq='M')
clubs = ['Northern Tide', 'Coastal Flyers', 'Urban Pulse', 'Desert Storm', 'Valley Racers']
club_sizes = {'Northern Tide': 25, 'Coastal Flyers': 64, 'Urban Pulse': 120, 'Desert Storm': 18, 'Valley Racers': 80}

# Generate streamed athlete performances (random)
np.random.seed(42)
stream_data = []
for month in months:
    for club in clubs:
        entries = np.random.randint(3, 20)  # number of athletes
        double_ups = np.random.randint(0, 3)
        placements = np.random.choice(range(1, 11), size=np.random.randint(1, entries), replace=True)
        stream_data.append({
            'Club': club,
            'Date': month,
            'Participants': entries,
            'Double-Ups': double_ups,
            'Placements': placements
        })

df_stream = pd.DataFrame(stream_data)

# Adjust club sizes
df_stream['Adjusted Size'] = df_stream['Club'].map(lambda x: max(club_sizes[x], 20))
df_stream['Total Participants'] = df_stream['Participants'] + df_stream['Double-Ups']

# Participation logic
def calc_participation_points(row):
    thresholds = {0.05: 15, 0.10: 30, 0.20: 45}
    pts = 0
    for perc, val in thresholds.items():
        req = round(row['Adjusted Size'] * perc)
        if row['Adjusted Size'] == 20 and req == 1 and perc == 0.10:
            req += 1
        if row['Total Participants'] >= req:
            pts = val
    return pts

df_stream['Participation Points'] = df_stream.apply(calc_participation_points, axis=1)
df_stream['Performance Points'] = df_stream['Placements'].apply(lambda x: sum([11 - p for p in x]))
df_stream['Total Points'] = df_stream[['Participation Points', 'Performance Points']].sum(axis=1)
df_stream['Total Points'] = df_stream['Total Points'].clip(upper=150)

# Monthly aggregation
df_monthly = df_stream.groupby(['Date', 'Club'])[['Participation Points', 'Performance Points', 'Total Points']].sum().reset_index()

# 📊 Chart
chart = alt.Chart(df_monthly).transform_fold(
    ['Participation Points', 'Performance Points', 'Total Points'],
    as_=['Type', 'Points']
).mark_line(point=True).encode(
    x='Date:T',
    y='Points:Q',
    color='Club:N',
    strokeDash='Type:N'
).properties(title="Monthly Club Points Trend")

st.altair_chart(chart, use_container_width=True)

# 📋 Table view
st.markdown("### Monthly Point Totals")
st.dataframe(df_monthly)