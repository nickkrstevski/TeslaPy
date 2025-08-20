#!/usr/bin/env python3
import argparse
import sys
from typing import Optional

import teslapy


def prompt_for_redirected_url(authorization_url: str) -> str:
    print("Use your browser to log in. A 'Page Not Found' will be shown on success.")
    print("Open this URL:")
    print(authorization_url)
    print()
    redirected_url = input("Paste the full URL you were redirected to: ").strip()
    if not redirected_url:
        print("No redirected URL provided. Exiting.")
        sys.exit(1)
    return redirected_url


def find_vehicles(email: str, timeout: Optional[int]) -> int:
    with teslapy.Tesla(email, timeout=timeout) as tesla:
        if not tesla.authorized:
            auth_url = tesla.authorization_url()
            redirected_url = prompt_for_redirected_url(auth_url)
            tesla.fetch_token(authorization_response=redirected_url)

        vehicles = tesla.vehicle_list()
        if not vehicles:
            print("No vehicles found for this account.")
            return 2

        print(f"Found {len(vehicles)} vehicle(s):")
        for index, vehicle in enumerate(vehicles, start=1):
            display_name = vehicle.get("display_name") or "(unnamed)"
            vin = vehicle.get("vin") or "unknown VIN"
            state = vehicle.get("state") or "unknown"
            identifier = vehicle.get("id_s") or "unknown id"
            print(
                f"  {index}. {display_name} | VIN: {vin} | State: {state} | ID: {identifier}"
            )

        sanjay = next(
            (
                vehicle
                for vehicle in vehicles
                if vehicle.get("display_name") == "Sanjay"
            ),
            None,
        )
        if sanjay is None:
            print("No vehicle found with the name 'Sanjay'.")
            return 2

        print()
        print("Identified Sanjay:")
        print(f"  Name: {sanjay.get('display_name')}")
        print(f"  VIN: {sanjay.get('vin')}")
        print(f"  ID: {sanjay.get('id_s')}")
        print(f"  State: {sanjay.get('state')}")
        print(sanjay.decode_vin())
        return 0


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Authenticate with Tesla SSO and list vehicles for the account."
    )
    parser.add_argument(
        "-e", "--email", required=True, help="Tesla account email address"
    )
    parser.add_argument(
        "-t",
        "--timeout",
        type=int,
        default=10,
        help="Connect/read timeout in seconds (default: 10)",
    )
    args = parser.parse_args()

    exit_code = find_vehicles(email=args.email, timeout=args.timeout)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
