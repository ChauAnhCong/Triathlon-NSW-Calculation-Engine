# main.py
import pandas as pd
from datetime import datetime
import traceback

# Import modules
import config
import file_handler
import data_formatter
import calculations

def process_round_file(round_info, season_source):
    """Orchestrate the processing of a single round file."""
    try:
        print(f"\nProcessing {round_info['filename']}...")
        
        # 1. Read ICL tables to identify leagues in the file
        icl_tables = data_formatter.read_icl_tables(round_info['path'])
        if not icl_tables:
            print(f"Error: No ICL tables found in {round_info['filename']}. Skipping.")
            return

        # 2. Infer league for this file
        league_name = data_formatter.infer_league_from_clubs(round_info['path'], season_source)
        if not league_name:
            print(f"Error: Could not determine league for {round_info['filename']}. Skipping.")
            return
        round_info['league'] = league_name

        # 3. Get the correct ICL table and league info for this round
        icl_df = icl_tables.get(league_name)
        if icl_df is None:
            print(f"Error: No ICL data found for inferred league '{league_name}'.")
            return

        league_info = season_source[
            (season_source['League Name'].str.lower() == league_name.lower()) & 
            (season_source['Round'] == round_info['round'])
        ].iloc[0]

        # 4. Read all race sheets from the Excel file
        all_results, race_validations = [], []
        with pd.ExcelFile(round_info['path']) as xl:
            for sheet_name in xl.sheet_names:
                if any(x in sheet_name.lower() for x in ['icl', 'summary', 'points', 'eligible']):
                    continue
                
                validation = calculations.validate_race_type(sheet_name, league_info)
                if not validation['participation_eligible']:
                    print(f"Skipping sheet '{sheet_name}': not an eligible race type.")
                    continue

                race_df = xl.parse(sheet_name)
                race_df = data_formatter.normalize_column_names(race_df)
                race_df = data_formatter.validate_and_standardize_columns(race_df, sheet_name)
                if race_df is not None:
                    all_results.append(race_df.dropna(subset=['Club Name']))
                    race_validations.append(validation)
        
        if not all_results:
            print("No valid race results found to process.")
            return
            
        # 5. Perform all calculations
        icl_with_participation = calculations.calculate_round_participation_points(all_results, icl_df)
        icl_with_performance = calculations.calculate_round_performance_points(all_results, icl_df, race_validations)
        round_summary = calculations.generate_round_summary(icl_with_participation, icl_with_performance)
        
        season_ladder = calculations.generate_season_ladder(round_summary)
        
        filtered_results_for_mvp = [data_formatter.filter_eligible_clubs_only(df, icl_df) for df in all_results]
        mvp_data = calculations.generate_individual_mvp_data(filtered_results_for_mvp, race_validations)
        
        season_mvp = calculations.generate_season_mvp_ladder(mvp_data) if mvp_data else pd.DataFrame()
        club_mvp_sheets = calculations.generate_club_individual_mvp_sheets(mvp_data)
        
        # 6. Save all outputs to a single Excel file
        output_filename = f"{league_name}_R{round_info['round']}_{datetime.now().strftime('%Y%m%d')}.xlsx"
        output_path = config.OUTPUT_DIR + '/' + output_filename
        
        with pd.ExcelWriter(output_path) as writer:
            round_summary.to_excel(writer, sheet_name='Round Ladder', index=False)
            season_ladder.to_excel(writer, sheet_name='Season Ladder', index=False)
            if mvp_data:
                mvp_data['round_mvp'].to_excel(writer, sheet_name='Round MVP', index=False)
            if not season_mvp.empty:
                season_mvp.to_excel(writer, sheet_name='Season MVP', index=False)
            for sheet_name, df in club_mvp_sheets.items():
                df.to_excel(writer, sheet_name=sheet_name, index=False)

        print(f"Successfully generated output: {output_filename}")

        # 7. Update history and archive the processed file
        combined_results = pd.concat(filtered_results_for_mvp, ignore_index=True)
        file_handler.update_season_history(combined_results, round_info)
        file_handler.archive_processed_file(round_info)

    except Exception as e:
        print(f"An unexpected error occurred processing {round_info['filename']}: {e}")
        traceback.print_exc()

def main():
    """Main function to run the triathlon results processing."""
    print("Starting triathlon results processing...")
    file_handler.ensure_directories()
    
    season_source_path = file_handler.get_season_source_of_truth()
    if not season_source_path:
        print("Error: No valid season source file found. Exiting.")
        return
        
    try:
        season_source = pd.read_excel(season_source_path)
        season_source = data_formatter.normalize_column_names(season_source)
    except Exception as e:
        print(f"Error reading season source file: {e}. Exiting.")
        return
    
    new_files = file_handler.find_new_round_files()
    if not new_files:
        print("No new round files to process.")
    else:
        for round_info in new_files:
            process_round_file(round_info, season_source)
    
    print("\nProcessing complete!")

if __name__ == "__main__":
    main()