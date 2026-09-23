from pathlib import Path
import json

import pandas as pd


RAW_FILE_PATH = Path("Data/Raw/teams_2025.json")
PROCESSED_DATA_DIRECTORY = Path("Data/Processed")
OUTPUT_FILE_PATH = PROCESSED_DATA_DIRECTORY / "dim_team_2025.csv"


def load_raw_data(file_path: Path) -> dict:
    """Load a locally archived raw MLB API JSON response."""
    with file_path.open("r", encoding="utf-8") as input_file:
        return json.load(input_file)


def transform_team_data(raw_data: dict) -> pd.DataFrame:
    """Flatten MLB team reference data into an analytics-ready dimension."""
    teams = raw_data["data"]["teams"]

    records = []

    for team in teams:
        records.append(
            {
                "team_id": team.get("id"),
                "team_name": team.get("name"),
                "team_abbreviation": team.get("abbreviation"),
                "team_code": team.get("teamCode"),
                "file_code": team.get("fileCode"),
                "location_name": team.get("locationName"),
                "franchise_name": team.get("franchiseName"),
                "club_name": team.get("clubName"),
                "first_year_of_play": team.get("firstYearOfPlay"),
                "active": team.get("active"),
                "league_id": team.get("league", {}).get("id"),
                "league_name": team.get("league", {}).get("name"),
                "division_id": team.get("division", {}).get("id"),
                "division_name": team.get("division", {}).get("name"),
                "venue_id": team.get("venue", {}).get("id"),
                "venue_name": team.get("venue", {}).get("name"),
                "season": team.get("season"),
            }
        )

    team_data = pd.DataFrame(records)

    team_data = team_data.sort_values("team_name").reset_index(drop=True)

    return team_data


def validate_team_data(team_data: pd.DataFrame) -> None:
    """Apply basic data-quality checks before saving the dataset."""
    expected_team_count = 30

    if len(team_data) != expected_team_count:
        raise ValueError(
            f"Expected {expected_team_count} MLB teams, found {len(team_data)}."
        )

    if team_data["team_id"].isna().any():
        raise ValueError("Team data contains missing team IDs.")

    if team_data["team_id"].duplicated().any():
        raise ValueError("Team data contains duplicate team IDs.")

    if team_data["team_name"].isna().any():
        raise ValueError("Team data contains missing team names.")


def save_processed_data(team_data: pd.DataFrame, output_path: Path) -> None:
    """Save the analytics-ready team dimension as a CSV file."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    team_data.to_csv(output_path, index=False)


def main() -> None:
    raw_data = load_raw_data(RAW_FILE_PATH)
    team_data = transform_team_data(raw_data)

    validate_team_data(team_data)
    save_processed_data(team_data, OUTPUT_FILE_PATH)

    print(f"Successfully transformed {len(team_data)} team records.")
    print(f"Processed data saved to: {OUTPUT_FILE_PATH}")


if __name__ == "__main__":
    main()