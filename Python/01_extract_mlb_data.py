from datetime import datetime, timezone
from pathlib import Path
import json

import requests


API_BASE_URL = "https://statsapi.mlb.com/api/v1"
RAW_DATA_DIRECTORY = Path("Data/Raw")
SEASON = 2025


def get_teams(season: int) -> dict:
    """Retrieve Major League Baseball team reference data for a season."""
    response = requests.get(
        f"{API_BASE_URL}/teams",
        params={"sportId": 1, "season": season},
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
    teams_data = get_teams(SEASON)
    output_file = save_json(teams_data, f"teams_{SEASON}.json")

    team_count = len(teams_data.get("teams", []))

    print(f"Successfully extracted {team_count} teams.")
    print(f"Raw data saved to: {output_file}")


if __name__ == "__main__":
    main()