import pandas
import numpy as np


def calc_participation_points(row):
    thresholds = {0.05: 15, 0.10: 30, 0.20: 45}
    pts = 0
    for perc, val in thresholds.items():
        if row['Adjusted Size'] == 20 and perc == 0.10:
            req = round(row['Adjusted Size'] * perc)
        if row['Adjusted Size'] == 20 and req == 1 and perc == 0.10:
            req += 1
        if row['ICL Eligible Number'] >= req:
            pts = val
    return pts

def main():
    df = pandas.read_excel('Example Interclub for Cameron.xlsx', sheet_name=None, header=0, index_col=None)
    print(df.keys())
    df = df[df.keys()[0]]



if __name__ == "__main__":
    main()
