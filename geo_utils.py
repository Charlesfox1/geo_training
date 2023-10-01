import geopandas as gpd
from shapely.geometry import Point
import os
import time
import json
import requests
from datetime import datetime
from loguru import logger
import uuid

def tt_isochrone(p,
                 travel_time_mins,
                 creds, 
                 mode = 'driving',
                 _id_ = None, 
                 departure = None,
                 endpoint = "https://api.traveltimeapp.com/v4/time-map"):

    # Rate limit - https://docs.traveltime.com/api/overview/usage-limits
    time.sleep(13) # max 60 HPM
    
    # Append Accept header to creds dictionary
    creds['Accept'] =  'application/geo+json'

    # Departure time (relevant for public transit especially)
    if not departure:
        departure = datetime.now().date().isoformat()+'T'+datetime.now().time().isoformat()
        
    # Log request
    logger.info(f"Requesting {travel_time_mins} minute {mode} isochrone for (x: {p.x}, y:{p.y}), departure {departure}")
    
    # Generate ID if no id
    if not _id_:
        _id_ = str(uuid.uuid4())

    # Populate parameter dictionary for all modes
    param_dict = {
        'driving' : {
          "departure_searches": [
            {
              "id": _id_,
              "coords": {
                  "lat": p.y, 
                  "lng": p.x
              },
              "departure_time": departure,
              "travel_time": (travel_time_mins * 60),
              "transportation": {
                "type": "driving"
              }
            }
          ]
        },
        'public_transport' : {
          "departure_searches": [
            {
              "id": _id_,
              "coords": {
                  "lat": p.y, 
                  "lng": p.x
              },
              "departure_time": departure,
              "travel_time": (travel_time_mins * 60),
              "transportation": {
                "type": "public_transport",
                "walking_time": (travel_time_mins * 60), # Up to full travel time
                "cycling_time_to_station":int(max((travel_time_mins * 60 / 6), 300)), # 6th of travel time or as low as 5 mins
                "parking_time": 30, # 30 seconds standard
                "boarding_time": 0, # ferries only
                "driving_time_to_station": (travel_time_mins * 60 / 2), # Up to half of travel time
                "pt_change_delay": 60, # 60 seconds for boarding at platforms
                "disable_border_crossing": False
              }
            }
          ]
        },
        'driving+train' : {
          "departure_searches": [
            {
              "id": _id_,
              "coords": {
                  "lat": p.y, 
                  "lng": p.x
              },
              "departure_time": departure,
              "travel_time": (travel_time_mins * 60),
              "transportation": {
                "type": "driving+train",
                "walking_time": (travel_time_mins * 60),
                "cycling_time_to_station": int(max((travel_time_mins * 60 / 6), 300)),
                "parking_time": 30, # 30 seconds standard
                "boarding_time": 0, # ferries only
                "driving_time_to_station": (travel_time_mins * 60),
                "pt_change_delay": 60,
                "disable_border_crossing": False
              },
            }
          ]
        }
    }

    # Make POST Request
    r = requests.post(url = endpoint, 
                      json = param_dict[mode],
                      headers = creds)

    # Handling
    if r.status_code == 200:
        logger.success("Isochrone Successfully Generated")
        js = r.json()
        gdf = gpd.GeoDataFrame.from_features(js, crs = 4326).set_index('search_id')
        return gdf
    else:
        logger.error(f"Failed with error code: {r.status_code}")
        return r, param_dict[mode]