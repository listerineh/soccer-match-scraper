import json
import os
import pandas as pd
import sys


def load_city_mappings(filepath: str) -> dict:
    """Helper function to load the city-based JSON mapping file."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"[Error] Mapping file not found at: {filepath}", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError:
        print(f"[Error] Failed to decode JSON from: {filepath}", file=sys.stderr)
        sys.exit(1)


def build_reverse_team_map(city_mappings: dict) -> dict:
    """Inverts the city map to create a fast team-lookup map."""
    team_lookup = {}
    malformed_cities = []

    for city, data in city_mappings.items():
        try:
            altitude = data["altitude"]
            teams = data["teams"]
            if not isinstance(teams, list):
                malformed_cities.append(f"{city} (la llave 'teams' no es una lista)")
                continue
            for team in teams:
                team_lookup[team] = {"city": city, "altitude": altitude}
        except KeyError:
            malformed_cities.append(f"{city} (faltan llaves 'altitude' o 'teams')")
        except Exception as e:
            malformed_cities.append(f"{city} (error: {e})")

    if malformed_cities:
        print(
            "\n[Warning] Se encontraron ciudades con formato incorrecto en 'city_mappings.json':"
        )
        for city_error in malformed_cities:
            print(f"  - {city_error}")

    return team_lookup


def process_data(raw_json_path: str, city_map_path: str, output_csv_path: str):
    """
    Reads raw match data and the single mapping file to create the final
    processed CSV with altitude calculations.
    """
    city_mappings = load_city_mappings(city_map_path)

    try:
        with open(raw_json_path, "r", encoding="utf-8") as f:
            matches = json.load(f)
    except FileNotFoundError:
        print(f"[Error] Raw data file not found: {raw_json_path}", file=sys.stderr)
        return

    if not city_mappings:
        print("[Error] Aborting due to missing city mapping file.", file=sys.stderr)
        return

    team_lookup = build_reverse_team_map(city_mappings)
    print(f"Loaded {len(matches)} raw matches.")
    print(
        f"Loaded {len(city_mappings)} cities and created lookup map for {len(team_lookup)} teams."
    )

    processed_data = []
    missing_teams = set()

    for match in matches:
        home_team = match.get("home_team")
        away_team = match.get("away_team")
        if not home_team or not away_team:
            continue

        home_mapping = team_lookup.get(home_team)
        away_mapping = team_lookup.get(away_team)

        if not home_mapping:
            missing_teams.add(home_team)
        if not away_mapping:
            missing_teams.add(away_team)
        if not home_mapping or not away_mapping:
            continue

        home_city = home_mapping["city"]
        home_altitude = home_mapping["altitude"]
        away_city = away_mapping["city"]
        away_altitude = away_mapping["altitude"]
        altitude_difference = home_altitude - away_altitude

        processed_data.append(
            {
                "year": match.get("year"),
                "phase": match.get("phase"),
                "date": match.get("date"),
                "home_team": home_team,
                "home_city": home_city,
                "home_altitude_meters": home_altitude,
                "away_team": away_team,
                "away_city": away_city,
                "away_altitude_meters": away_altitude,
                "altitude_difference": altitude_difference,
                "home_goals": match.get("home_goals"),
                "away_goals": match.get("away_goals"),
                "score_raw": match.get("score"),
                "stadium": match.get("stadium"),
            }
        )

    if missing_teams:
        print(
            f"\n[Warning] {len(missing_teams)} teams are missing from your 'city_mappings.json' file:"
        )
        for i, team in enumerate(list(missing_teams)):
            if i >= 10:
                print(f"  ... and {len(missing_teams) - 10} more.")
                break
            print(f"  - {team}")

    if not processed_data:
        print(
            "\n[Error] No data was processed. Check your mapping file.", file=sys.stderr
        )
        return

    df = pd.DataFrame(processed_data)

    try:
        os.makedirs(os.path.dirname(output_csv_path), exist_ok=True)
        df.to_csv(output_csv_path, index=False, encoding="utf-8-sig")

        print(f"\n--- Altitude Processing Finished ---")
        print(f"Successfully processed {len(df)} matches.")
        print(f"Final analysis CSV saved to: {output_csv_path}")

    except IOError as e:
        print(f"Error writing to {output_csv_path}: {e}", file=sys.stderr)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Error: Missing tournament name argument.", file=sys.stderr)
        print(
            "Usage: python3 process_altitude.py [sudamericana|libertadores]",
            file=sys.stderr,
        )
        sys.exit(1)

    tournament_name = sys.argv[1].lower()
    RAW_DIR = os.path.join("data", "raw")
    PROCESSED_DIR = os.path.join("data", "processed")
    CITY_MAP_PATH = os.path.join("data", "mappings", "city_mappings.json")

    if tournament_name == "sudamericana":
        RAW_JSON_PATH = os.path.join(RAW_DIR, "sudamericana_matches.json")
        OUTPUT_CSV_PATH = os.path.join(PROCESSED_DIR, "sudamericana_analysis.csv")
    elif tournament_name == "libertadores":
        RAW_JSON_PATH = os.path.join(RAW_DIR, "libertadores_matches.json")
        OUTPUT_CSV_PATH = os.path.join(PROCESSED_DIR, "libertadores_analysis.csv")
    else:
        print(f"Error: Unknown tournament '{tournament_name}'.", file=sys.stderr)
        sys.exit(1)

    process_data(RAW_JSON_PATH, CITY_MAP_PATH, OUTPUT_CSV_PATH)
