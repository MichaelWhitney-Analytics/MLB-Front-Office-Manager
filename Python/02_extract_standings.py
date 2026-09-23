from datetime import datetime, timezone
from pathlib import Path
import json

import requests


API_BASE_URL = "https://statsapi.mlb.com/api/v1"
RAW_DATA_DIRECTORY = Path("Data/Raw")
SEASON = 2025


def get_standings(season: int) -> dict:
    """Retrieve MLB regular-season standings for a specified season."""
    response = requests.get(
        f"{API_BASE_URL}/standings",
        params={
            "leagueId": "103,104",
            "season": season,
            "standingsTypes": "regularSeason",
        },
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


def save_json(data: dict, file_name: str) -> Path:
    """Save API data locally along with extraction metadata."""
    RAW_DATA_DIRECTORY.mkdir(parents=True, exist_ok=True)

    output = {
        "metadata": {
            "source": "MLB Stats API",
            "extracted_at_utc": datetime.now(timezone.utc).isoformat(),
        },
        "data": data,
    }

    output_path = RAW_DATA_DIRECTORY / file_name

    with output_path.open("w", encoding="utf-8") as output_file:
        json.dump(output, output_file, indent=2)

    return output_path


def main() -> None:
    standings_data = get_standings(SEASON)
    output_file = save_json(standings_data, f"standings_{SEASON}.json")

    division_count = len(standings_data.get("records", []))
    team_count = sum(
        len(division.get("teamRecords", []))
        for division in standings_data.get("records", [])
    )

    print(f"Successfully extracted standings for {team_count} teams.")
    print(f"Division records returned: {division_count}.")
    print(f"Raw data saved to: {output_file}")


if __name__ == "__main__":
    main()