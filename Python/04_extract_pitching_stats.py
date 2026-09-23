from datetime import datetime, timezone
from pathlib import Path
import json

import requests


API_BASE_URL = "https://statsapi.mlb.com/api/v1"
RAW_DATA_DIRECTORY = Path("Data/Raw")
SEASON = 2025


def get_pitching_stats(season: int) -> dict:
    """Retrieve MLB regular-season individual pitching statistics."""
    response = requests.get(
        f"{API_BASE_URL}/stats",
        params={
            "stats": "season",
            "group": "pitching",
            "season": season,
            "sportIds": 1,
            "playerPool": "ALL",
            "gameType": "R",
            "limit": 5000,
        },
        timeout=60,
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
            "season": SEASON,
            "statistical_group": "pitching",
            "game_type": "R",
            "player_pool": "ALL",
        },
        "data": data,
    }

    output_path = RAW_DATA_DIRECTORY / file_name

    with output_path.open("w", encoding="utf-8") as output_file:
        json.dump(output, output_file, indent=2)

    return output_path


def main() -> None:
    pitching_data = get_pitching_stats(SEASON)
    output_file = save_json(pitching_data, f"pitching_stats_{SEASON}.json")

    splits = pitching_data.get("stats", [{}])[0].get("splits", [])
    player_count = len(splits)

    print(f"Successfully extracted pitching statistics for {player_count} players.")
    print(f"Raw data saved to: {output_file}")


if __name__ == "__main__":
    main()