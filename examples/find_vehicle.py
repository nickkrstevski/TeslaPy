#!/usr/bin/env python3
import argparse
import sys
import json
from pathlib import Path
from typing import Optional, List, Tuple, Any, Iterable
from datetime import datetime, timezone

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


def _parse_datetime_flexible(value: Any) -> Optional[datetime]:
    if value is None:
        return None
    # Epoch seconds or milliseconds
    if isinstance(value, (int, float)):
        try:
            if value > 1_000_000_000_000:  # ms
                return datetime.fromtimestamp(value / 1000.0, tz=timezone.utc)
            return datetime.fromtimestamp(value, tz=timezone.utc)
        except Exception:
            return None
    # ISO-like strings
    if isinstance(value, str):
        v = value.strip()
        if not v:
            return None
        try:
            # Handle trailing Z
            if v.endswith("Z"):
                v = v[:-1] + "+00:00"
            return datetime.fromisoformat(v)
        except Exception:
            # Try date only
            try:
                return datetime.strptime(v, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            except Exception:
                return None
    return None


def _extract_points_kwh_from_list(items: List[dict]) -> List[Tuple[datetime, float]]:
    time_keys = (
        "timestamp",
        "time",
        "date",
        "start_date",
        "start_time",
        "charging_start_time",
        "session_date",
        "end_time",
    )
    energy_keys = (
        "charge_energy_added",
        "energy_added",
        "kwh",
        "energy",
        "charged_kwh",
        "energy_kWh",
        "charger_energy",
        "total_energy_wh",
        "total_energy_Wh",
    )

    points: List[Tuple[datetime, float]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        when = None
        for tk in time_keys:
            if tk in item:
                when = _parse_datetime_flexible(item.get(tk))
                if when is not None:
                    break
        if when is None:
            continue

        energy_kwh = None
        for ek in energy_keys:
            if ek in item:
                val = item.get(ek)
                try:
                    if isinstance(val, str):
                        val = float(val)
                    if ek.lower().endswith("wh") and isinstance(val, (int, float)):
                        val = float(val) / 1000.0
                    energy_kwh = float(val)
                except Exception:
                    energy_kwh = None
                break
        if energy_kwh is None:
            continue
        points.append((when, energy_kwh))

    points.sort(key=lambda p: p[0])
    return points


def _iter_nested_lists(obj: Any) -> Iterable[List[dict]]:
    if isinstance(obj, list) and all(isinstance(x, dict) for x in obj):
        yield obj
    elif isinstance(obj, dict):
        for value in obj.values():
            yield from _iter_nested_lists(value)
    elif isinstance(obj, list):
        for value in obj:
            yield from _iter_nested_lists(value)


def _extract_points_kwh(history: Any) -> List[Tuple[datetime, float]]:
    if history is None:
        return []
    if isinstance(history, dict):
        for key in (
            "data_points",
            "data",
            "points",
            "items",
            "history",
            "charging_sessions",
        ):
            if key in history and isinstance(history[key], list):
                pts = _extract_points_kwh_from_list(history[key])
                if pts:
                    return pts
    for candidate in _iter_nested_lists(history):
        pts = _extract_points_kwh_from_list(candidate)
        if pts:
            return pts
    return []


def find_vehicles(email: str, timeout: Optional[int], debug: bool = False) -> int:
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
        # Fetch history (v2 preferred if available)
        try:
            charge_history2 = sanjay.get_charge_history_v2()
        except Exception:
            charge_history2 = None
        try:
            charge_history = sanjay.get_charge_history()
        except Exception:
            charge_history = None

        if debug:
            out_dir = Path(".")
            if charge_history is not None:
                (out_dir / "charge_history_raw.json").write_text(
                    json.dumps(charge_history, indent=2, default=str)
                )
                print("Wrote charge_history_raw.json")
            if charge_history2 is not None:
                (out_dir / "charge_history_v2_raw.json").write_text(
                    json.dumps(charge_history2, indent=2, default=str)
                )
                print("Wrote charge_history_v2_raw.json")

        points = _extract_points_kwh(charge_history2)
        if not points:
            points = _extract_points_kwh(charge_history)

        if not points:
            print("No parsable charge history points found.")
            print(
                "Hints: ensure Data Sharing is enabled, you are primary owner, and car software >= 2021.44.25."
            )
            print(
                "Run with --debug to write raw responses to JSON files for inspection."
            )
            return 0

        # Plot using matplotlib when available
        try:
            import matplotlib.pyplot as plt  # type: ignore
        except Exception:
            print(
                "matplotlib is required to plot. Install: python3 -m pip install matplotlib"
            )
            return 0

        xs = [dt for dt, _ in points]
        ys = [kwh for _, kwh in points]

        fig, ax = plt.subplots(figsize=(10, 5))
        ax.plot(xs, ys, marker="o", linewidth=1.5)
        ax.set_title("Charging History (kWh)")
        ax.set_xlabel("Time")
        ax.set_ylabel("Energy Added (kWh)")
        ax.grid(True, linestyle="--", alpha=0.4)
        fig.autofmt_xdate()
        output_path = "charge_history.png"
        plt.tight_layout()
        fig.savefig(output_path, dpi=160)
        print(f"Saved plot to {output_path}")
        return sanjay


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
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Write raw charge history responses to JSON files",
    )
    args = parser.parse_args()

    exit_code = find_vehicles(email=args.email, timeout=args.timeout, debug=args.debug)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
