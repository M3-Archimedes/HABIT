import os
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point
import math
import random
import copy
import uuid

def read_ais_locations(file_path, col_ts='TIMESTAMP', sep=','):
    """Creates a DataFrame from the AIS locations in lon/lat coordinates contained in the given CSV file. 

    Args:
        file_path (string): The path to the input CSV file.
        col_ts (string): The name of the column with the timestamps (in date/time format).
        sep (string): The character used as separator in the CSV file. 
                
    Returns:
        A DataFrame with the locations chronologically ordered by UNIX epochs (in seconds).
    """
    
    df = pd.read_csv(file_path, sep=sep).drop_duplicates()

    # Check timestamps
    if df[col_ts].astype(str).str.isnumeric().all(): # Numeric timestamps
        df[col_ts] = df[col_ts].astype(int)
        df['epoch'] = df[col_ts]
    else: # Turn timestamps into UNIX epochs (seconds) in an extra column
        df[col_ts] = pd.to_datetime(df[col_ts])
        df['epoch'] = df[col_ts].apply(lambda x: x.timestamp()).astype(int)

    return df


def trajectory2trips(df_trajectory, MIN_GAP_SIZE=3600):
    """Split the trajectory of a moving vessel given in the GeoDataFrame into trips between stops (e.g., ports). 

    Args:
        df_trajectory (DataFrame): A DataFrame containing the (chronologically ordered) locations of a SINGLE trajectory (i.e., the same moving object).
        MIN_GAP_SIZE (int): The maximum allowed interval (in seconds) with no positional report; if no signal is relayed for a period longer than this threshold, a new trip will be assigned.
        
    Returns:
        A DataFrame with the movement of the vessel separated in trips (i.e., movements between stops). Each trip is assigned a unique identifier based on its MMSI and the respective time interval (min and max timestamp in UNIX epochs).
    """

    # Variables
    stopped = False
    t_stop_start = None
    gap = False
    t_gap_start = None
    trip_id = str(uuid.uuid1().int>>64)   # First trip

    # Copy all trajectory information to a new DataFrame with an extra column for the trip ID
    df_trips = df_trajectory.copy()
    df_trips['TRIP'] = pd.Series(dtype='object')  # Create column for trip ID

    # Chronologically iterate over the locations of a given trajectory
    for index, row in df_trips.iterrows():
        if 'STOP_START' in row['ANNOTATION']:
            t_stop_start = row['epoch']
            stopped = True
        if stopped and ('STOP_END' in row['ANNOTATION']):
            trip_id = str(uuid.uuid1().int>>64)  # A new trip will start after the STOP
            stopped = False
        if gap and 'GAP_END' in row['ANNOTATION']:     
            if row['epoch'] - t_gap_start > MIN_GAP_SIZE:  # GAP is longer than the MIN_GAP_SIZE, so make it another trip
                trip_id = uuid.uuid1().int>>64  # A new trip will start after the GAP
            t_gap_start = None
            gap = False
        if not stopped and 'GAP_START' in row['ANNOTATION']:
            t_gap_start = row['epoch']
            gap = True

        #Assign a temporary trip ID 
        df_trips.loc[index,'TRIP'] = trip_id

    # Get min and max timestamp per trip
    df_trip_bounds = df_trips.groupby('TRIP').agg({'MMSI':['min'], 'epoch': ['min', 'max']})
    df_trip_bounds = df_trip_bounds.sort_values(by=('epoch', 'min'), ascending=True).reset_index()
    df_trip_bounds.columns = ['_'.join(col).strip() for col in df_trip_bounds.columns.values]
    # Create a composite TRIP_ID: MMSI + min_timestamp + max_timestamp
    df_trip_bounds['NEW_TRIP_ID'] = df_trip_bounds.apply(lambda row: str(row['MMSI_min']) + '_' + str(row['epoch_min']) + '_' + str(row['epoch_max']), axis=1)
    trip_dict = dict(zip(df_trip_bounds['TRIP_'], df_trip_bounds['NEW_TRIP_ID']))
    # Apply the composite TRIP_ID
    df_trips['TRIP'] = df_trips['TRIP'].map(trip_dict)

    # Put the trip ID as the first column in the table
    col_trip_id = df_trips.pop('TRIP')
    df_trips.insert(0, 'TRIP', col_trip_id)
    
    return df_trips

def dataset2trips(raw_ais_file, annotated_ais_file, MIN_GAP_SIZE=3600, col_mmsi_raw='MMSI', col_ts_raw='# Timestamp', sep_raw=',', col_mmsi_anno='MMSI', col_ts_anno='TIMESTAMP', col_anno='ANNOTATION', sep_anno=','):
    """Split the trajectories of vessels into trips between stops (e.g., ports) or gaps (when communication is lost for some time).. 

    Args:
        raw_ais_file (string): Path to the CSV file containing the raw AIS data concerning multiple vessels.
        annotated_ais_file (string): Path to the CSV file containing the same AIS data, but with possible ANNOTATIONS per row to indicate important mobility events (e.g., STOP, TURN, GAP, etc.)
        MIN_GAP_SIZE (int): The maximum allowed interval (in seconds) with no positional report; if no signal is relayed for a period longer than this threshold, a new trip will be assigned.
        
    Returns:
        A DataFrame with the movement of each vessel separated in trips (i.e., movements between stops or gaps). Each trip is assigned a unique identifier.
    """

    # Read RAW data for all vessels
    df_raw_ais = read_ais_locations(RAW_FILE, col_ts=col_ts_raw, sep=sep_raw)

    # Read ANNOTATED data for the same vessels
    df_annotated_ais = pd.read_csv(annotated_ais_file, sep=sep_anno)

    # Get the unique MMSI of all vessels
    vessels = df_annotated_ais[col_mmsi_anno].unique()
    # Iterate over all vessels and segment the trajectory of each one separately into trips
    df_all_trips = None
    for mmsi in vessels:
        # Extract the ANNOTATED trajectory of a vessel given its MMSI
        df_anno_trajectory = df_annotated_ais[df_annotated_ais[col_mmsi_anno].isin([int(mmsi)])].drop_duplicates().sort_values(col_ts_anno, ascending=True)
        df_anno_trajectory[col_anno] = df_anno_trajectory[col_anno].fillna('')  # Remove NaN values from annotation
        # Annotations per timestamp for this vessel
        mmsi_anno_dict = dict(zip(df_anno_trajectory[col_ts_anno], df_anno_trajectory[col_anno]))
    
        # Extract the RAW trajectory of a vessel given its MMSI
        df_trajectory = df_raw_ais[df_raw_ais[col_mmsi_raw].isin([mmsi])].drop_duplicates().sort_values('epoch', ascending=True)

        # STEP #1: Associate annotations to the RAW trajectory
        tags = []
        for i, row in df_trajectory.iterrows():
            ts = int(row['epoch'])
            tag = mmsi_anno_dict[ts] if ts in mmsi_anno_dict else ''
            tags.append(tag)         
        df_trajectory[col_anno] = tags
    
        # STEP #2: Segment this trajectory into trips between stops or gaps
        # Only gaps lasting longer than the specified MIN_GAP_SIZE (in seconds) will be considered
        df_tripped_trajectory = trajectory2trips(df_trajectory, MIN_GAP_SIZE=MIN_GAP_SIZE)
        print(mmsi)
    
        # Concatenate with the rest
        if df_all_trips is None:
            df_all_trips = df_tripped_trajectory
        else:
            df_all_trips = pd.concat([df_all_trips, df_tripped_trajectory])

    return df_all_trips
