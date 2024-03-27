import teslapy
from teslapy import Vehicle
import json
import os


file_path = "sanjay.json"

with teslapy.Tesla(os.getenv("tesla_email")) as tesla:
    vehicles: list[Vehicle] = tesla.vehicle_list()
    vehicle = vehicles[2]
    vehicle.sync_wake_up()
    vehicle.get_vehicle_data()
    print(vehicle.decode_vin())

    # Open the file in write mode and save the dictionary as JSON
    with open(file_path, "w+") as json_file:
        json.dump(dict(vehicle), json_file, indent=4)

