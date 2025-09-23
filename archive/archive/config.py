# config.py
import os

# Base directory for the application
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Data directories
DATA_DIR = os.path.join(BASE_DIR, 'data')
INPUT_DIR = os.path.join(DATA_DIR, 'input')
OUTPUT_DIR = os.path.join(DATA_DIR, 'output')
PROCESSED_DIR = os.path.join(DATA_DIR, 'processed')

# Season-specific directories
CURRENT_SEASON_DIR = os.path.join(DATA_DIR, 'season', 'current_season')
PAST_SEASON_DIR = os.path.join(DATA_DIR, 'season', 'past_season')