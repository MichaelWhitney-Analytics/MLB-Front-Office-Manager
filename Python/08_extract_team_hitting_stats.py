from datetime import datetime, timezone
from pathlib import Path
import json
import time

import requests


API_BASE_URL = "https://statsapi.mlb.com/api/v1"
RAW_DATA_DIRECTORY = Path("Data/Raw")
SEASON = 2025
SPORT_ID = 1
REQUEST_PAUSE_SECONDS = 0.25


def get_mlb_teams(season: int) -> list[dict]:
    """Retrieve MLB team reference records for a specified season."""
    response = requests.get(
        f"{API_BASE_URL}/teams",
        params={
            "sportId": SPORT_ID,
            "season": season,
        },
        timeout=30,
    )
    response.raise_for_status()
    return response.json().get("teams", [])


def get_team_hitting_stats(team_id: int, season: int) -> dict:
    """Retrieve regular-season hitter statistics for one MLB team."""
    response = requests.get(
        f"{API_BASE_URL}/stats",
        params={
            "stats": "season",
            "group": "hitting",
            "season": season,
            "sportIds": SPORT_ID,
            "teamId": team_id,
            "playerPool": "ALL",
            "gameType": "R",
            "limit": 5000,
        },
        timeout=60,
    )
    response.raise_for_status()
    return response.json()


def save_json(data: dict, file_name: str) -> Path:
    """Save raw source data locally with extraction metadata."""
    RAW_DATA_DIRECTORY.mkdir(parents=True, exist_ok=True)

    output = {
        "metadata": {
            "source": "MLB Stats API",
            "extracted_at_utc": datetime.now(timezone.utc).isoformat(),
            "season": SEASON,
            "statistical_group": "hitting",
            "game_type": "R",
            "player_pool": "ALL",
            "extraction_grain": "team_player_season",
        },
        "data": data,
    }

    output_path = RAW_DATA_DIRECTORY / file_name

    with output_path.open("w", encoding="utf-8") as output_file:
        json.dump(output, output_file, indent=2)

    return output_path


def main() -> None:
    teams = get_mlb_teams(SEASON)
    team_hitting_data = []
    failed_teams = []

    for index, team in enumerate(teams, start=1):
        team_id = team["id"]
        team_name = team["name"]

        try:
            stats_data = get_team_hitting_stats(team_id, SEASON)
            splits = stats_data.get("stats", [{}])[0].get("splits", [])

            team_hitting_data.append(
                {
                    "team_id": team_id,
                    "team_name": team_name,
                    "stats": stats_data,
                }
            )

            print(
                f"[{index:02d}/{len(teams)}] "
                f"Retrieved {len(splits)} hitter records for {team_name}."
            )
        except requests.RequestException as error:
            failed_teams.append(
                {
                    "team_id": team_id,
                    "team_name": team_name,
                    "error": str(error),
                }
            )
            print(
                f"[{index:02d}/{len(teams)}] "
                f"FAILED for {team_name}: {error}"
            )

        time.sleep(REQUEST_PAUSE_SECONDS)

    output_data = {
        "teams": team_hitting_data,
        "failed_teams": failed_teams,
    }

    output_file = save_json(
        output_data,
        f"team_hitting_stats_{SEASON}.json",
    )

    total_hitter_records = sum(
        len(team_data["stats"].get("stats", [{}])[0].get("splits", []))
        for team_data in team_hitting_data
    )

    print()
    print(f"Successfully retrieved data for {len(team_hitting_data)} teams.")
    print(f"Failed team requests: {len(failed_teams)}.")
    print(f"Total player-team hitting records: {total_hitter_records}.")
    print(f"Raw data saved to: {output_file}")


if __name__ == "__main__":
    main()