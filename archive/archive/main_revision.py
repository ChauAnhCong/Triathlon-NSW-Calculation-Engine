import pandas as pd
import numpy as np



#retrieve these from folder
file_names = {'IRONMAN 70.3 and Sprint Round 1.xlsx':[],
              'Club Champs Round 2.xlsx': []}


ICL_Sheetname = 'Current ICL Eligible Number'


valid_race_column_names = ["First Name","Surname", "TA Number","Category", "Category Finish Place", "Per P", "Club Name", "Performance points Participation points or both"]

valid_icl_column_names = ['icl', 'summary', 'points', 'eligible', 'manual', 'calculations']

all_event_data_with_leagues = []



def main():
    for event_name, files in file_names.items():

        # Read and concatenate data for the event
        sheet_name = pd.ExcelFile(event_name).sheet_names

        ICL_DF = pd.concat([pd.read_excel(event_name, sheet_name = ICL_Sheetname)], ignore_index=True)


        print(sheet_name)

        # Find ICL Tables
        nan_row_index = ICL_DF[ICL_DF.isnull().all(axis=1)].index[0]

        # Split the DataFrame
        df1 = ICL_DF.iloc[:nan_row_index]
        df2 = ICL_DF.iloc[nan_row_index + 1:]

        print(df1)
        column_names = list(df2.iloc[0])
        df2 = df2[1:]
        df2.columns = column_names
        print(df2)

        #filter out ICL numers without Clubs
        first_column = df1.columns[0]
        df1 = df1[df1[first_column].notna()]

        print(df1)
        first_column = df2.columns[0]
        df2 = df2[df2[first_column].notna()]

        print(df2)


        for sheet_name_entry in sheet_name:
            sheet = pd.concat([pd.read_excel(event_name, sheet_name = sheet_name_entry)], ignore_index=True)
            valid_sheet_names_check = [col for col in sheet.columns if col in valid_race_column_names]
            if len(valid_sheet_names_check) == len(sheet.columns):
                print("inside the valid sheet check")
                

    

if __name__ == "__main__":
    main()