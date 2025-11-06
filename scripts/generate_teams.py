import json
import os
import sys


def generate_unique_teams(raw_json_path: str, output_txt_path: str):
    """
    Reads a raw JSON file and creates a text file
    containing a unique list of all team names.
    """
    try:
        with open(raw_json_path, "r", encoding="utf-8") as f:
            matches = json.load(f)
    except FileNotFoundError:
        print(f"[Error] Raw data file not found at: {raw_json_path}", file=sys.stderr)
        return
    except json.JSONDecodeError:
        print(f"[Error] Failed to decode JSON from: {raw_json_path}", file=sys.stderr)
        return

    team_names = set()
    for match in matches:
        if match.get("home_team"):
            team_names.add(match["home_team"].strip())
        if match.get("away_team"):
            team_names.add(match["away_team"].strip())

    if not team_names:
        print("[Warning] No teams were found in the JSON file.")
        return

    sorted_teams = sorted(list(team_names))

    try:
        with open(output_txt_path, "w", encoding="utf-8") as f:
            for team in sorted_teams:
                f.write(f"{team}\n")

        print(f"--- Unique Team List Generation Finished ---")
        print(f"Found {len(sorted_teams)} unique teams.")
        print(f"List saved to: {output_txt_path}")
    except IOError as e:
        print(f"Error writing to {output_txt_path}: {e}", file=sys.stderr)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Error: Missing tournament name argument.", file=sys.stderr)
        print(
            "Usage: python3 generate_teams.py [sudamericana|libertadores]",
            file=sys.stderr,
        )
        sys.exit(1)

    tournament_name = sys.argv[1].lower()
    RAW_DIR = os.path.join("data", "raw")

    if tournament_name == "sudamericana":
        RAW_JSON_PATH = os.path.join(RAW_DIR, "sudamericana_matches.json")
        OUTPUT_TXT_PATH = os.path.join(RAW_DIR, "unique_teams_sudamericana.txt")
    elif tournament_name == "libertadores":
        RAW_JSON_PATH = os.path.join(RAW_DIR, "libertadores_matches.json")
        OUTPUT_TXT_PATH = os.path.join(RAW_DIR, "unique_teams_libertadores.txt")
    else:
        print(f"Error: Unknown tournament '{tournament_name}'.", file=sys.stderr)
        sys.exit(1)

    generate_unique_teams(RAW_JSON_PATH, OUTPUT_TXT_PATH)
