# file_handler.py
import os
import shutil
import re
import pandas as pd
from datetime import datetime

# Import constants from the config file
import config

def ensure_directories():
    """Create directory structure if it doesn't exist"""
    for directory in [config.INPUT_DIR, config.OUTPUT_DIR, config.PROCESSED_DIR, 
                     config.CURRENT_SEASON_DIR, config.PAST_SEASON_DIR]:
        os.makedirs(directory, exist_ok=True)

def get_season_source_of_truth():
    """Get and validate season source of truth file, moving it if necessary."""
    source_path = os.path.join(config.INPUT_DIR, 'Triathalon Season.xlsx')
    current_source_path = os.path.join(config.CURRENT_SEASON_DIR, 'Triathalon Season.xlsx')
    
    if os.path.exists(source_path):
        try:
            # Validate the new source file before moving
            df = pd.read_excel(source_path)
            required_columns = ['League Name', 'Round', 'Events or Rounds', 
                              'Double Points', 'Per P & Part P', 'Part P', 'Clubs']
            missing_cols = [col for col in required_columns if col not in df.columns]
            if missing_cols:
                print(f"Error: Missing required columns in new source file: {missing_cols}")
                return None
                
            if os.path.exists(current_source_path):
                new_source = pd.read_excel(source_path)
                current_source = pd.read_excel(current_source_path)
                if not new_source.equals(current_source):
                    # Backup current source before updating
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    backup_path = os.path.join(config.CURRENT_SEASON_DIR, f'Triathlon_Season_backup_{timestamp}.xlsx')
                    shutil.copy2(current_source_path, backup_path)
                    shutil.move(source_path, current_source_path)
            else:
                shutil.move(source_path, current_source_path)
        except Exception as e:
            print(f"Error validating or moving source file: {e}")
            return None
    
    return current_source_path if os.path.exists(current_source_path) else None

def find_new_round_files():
    """Find new round files in input directory."""
    pattern = r'(?:([^R]+?)(?=Round)|)?Round (\d+)(?: (.*))?\.xlsx'
    round_files = []
    
    for filename in os.listdir(config.INPUT_DIR):
        if filename.startswith('~$') or not filename.endswith('.xlsx'):
            continue
            
        match = re.match(pattern, filename)
        if match:
            event_name = match.group(3) if match.group(3) else match.group(1)
            round_info = {
                'filename': filename,
                'round': int(match.group(2)),
                'name': event_name.strip() if event_name else None,
                'path': os.path.join(config.INPUT_DIR, filename)
            }
            round_files.append(round_info)
            
    return round_files
    
def update_season_history(results_df, round_info):
    """Update season history Excel file with new round results."""
    history_path = os.path.join(config.CURRENT_SEASON_DIR, 'Season_History.xlsx')
    
    try:
        history_df = pd.read_excel(history_path) if os.path.exists(history_path) else pd.DataFrame()
        
        results_df['League'] = round_info['league']
        results_df['Round'] = round_info['round']
        results_df['Event'] = round_info['name']
        
        updated_history = pd.concat([history_df, results_df], ignore_index=True)
        updated_history.to_excel(history_path, index=False)
    except Exception as e:
        print(f"Error updating season history: {e}")

def archive_processed_file(round_info):
    """Copy processed file to the processed directory and remove original."""
    processed_path = os.path.join(config.PROCESSED_DIR, round_info['filename'])
    try:
        shutil.copy2(round_info['path'], processed_path)
        print(f"File copied to processed directory: {processed_path}")
        
        try:
            os.remove(round_info['path'])
            print(f"Original file deleted: {round_info['path']}")
        except PermissionError:
            print(f"Warning: Could not delete original file (may be open): {round_info['path']}")
    except Exception as e:
        print(f"Warning: Could not archive processed file: {e}")