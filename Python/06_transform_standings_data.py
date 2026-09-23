from pathlib import Path
import json

import pandas as pd


RAW_FILE_PATH = Path("Data/Raw/standings_2025.json")
PROCESSED_DATA_DIRECTORY = Path("Data/Processed")
OUTPUT_FILE_PATH = PROCESSED_DATA_DIRECTORY / "fact_team_season_2025.csv"
SEASON = 2025


def load_raw_data(file_path: Path) -> dict:
    """Load a locally archived raw MLB API JSON response."""
    with file_path.open("r", encoding="utf-8") as input_file:
        return json.load(input_file)


def transform_standings_data(raw_data: dict) -> pd.DataFrame:
    """Flatten MLB standings data into an analytics-ready team-season fact."""
    division_records = raw_data["data"]["records"]

    records = []

    for division in division_records:
        league = division.get("league", {})
        division_info = division.get("division", {})

        for team_record in division.get("teamRecords", []):
            team = team_record.get("team", {})
            records.append(
                {
                    "team_id": team.get("id"),
                    "team_name": team.get("name"),
                    "season": SEASON,
                    "league_id": league.get("id"),
                    "league_name": league.get("name"),
                    "division_id": division_info.get("id"),
                    "division_name": division_info.get("name"),
                    "games_played": team_record.get("gamesPlayed"),
                    "wins": team_record.get("wins"),
                    "losses": team_record.get("losses"),
                    "winning_percentage": team_record.get("winningPercentage"),
                    "games_back": team_record.get("gamesBack"),
                    "division_rank": team_record.get("divisionRank"),
                    "division_champ": team_record.get("divisionChamp"),
                    "division_leader": team_record.get("divisionLeader"),
                    "wild_card_rank": team_record.get("wildCardRank"),
                    "wild_card_games_back": team_record.get("wildCardGamesBack"),
                    "runs_scored": team_record.get("runsScored"),
                    "runs_allowed": team_record.get("runsAllowed"),
                    "run_differential": team_record.get("runDifferential"),
                    "elimination_number": team_record.get("eliminationNumber"),
                    "wild_card_elimination_number": team_record.get(
                        "wildCardEliminationNumber"
                    ),
                    "clinched": team_record.get("clinched"),
                    "clinch_indicator": team_record.get("clinchIndicator"),
                }
            )

    standings_data = pd.DataFrame(records)

    numeric_columns = [
        "team_id",
        "season",
        "league_id",
        "division_id",
        "games_played",
        "wins",
        "losses",
        "winning_percentage",
        "games_back",
        "division_rank",
        "wild_card_rank",
        "wild_card_games_back",
        "runs_scored",
        "runs_allowed",
        "run_differential",
        "elimination_number",
        "wild_card_elimination_number",
    ]

    for column in numeric_columns:
        standings_data[column] = pd.to_numeric(
            standings_data[column],
            errors="coerce",
        )

    standings_data = standings_data.sort_values(
        ["league_name", "division_name", "division_rank"]
    ).reset_index(drop=True)

    return standings_data


def validate_standings_data(standings_data: pd.DataFrame) -> None:
    """Apply basic quality checks before saving the team-season fact."""
    expected_team_count = 30

    if len(standings_data) != expected_team_count:
        raise ValueError(
            f"Expected {expected_team_count} team-season records, "
            f"found {len(standings_data)}."
        )

    if standings_data["team_id"].isna().any():
        raise ValueError("Standings data contains missing team IDs.")

    if standings_data["team_id"].duplicated().any():
        raise ValueError("Standings data contains duplicate team IDs.")

    if standings_data["wins"].isna().any():
        raise ValueError("Standings data contains missing win totals.")

    if standings_data["losses"].isna().any():
        raise ValueError("Standings data contains missing loss totals.")

    invalid_game_totals = standings_data[
        standings_data["wins"] + standings_data["losses"]
        != standings_data["games_played"]
    ]

    if not invalid_game_totals.empty:
        raise ValueError(
            "Standings data contains records where wins plus losses "
            "does not equal games played."
        )

    if standings_data["run_differential"].notna().any():
        invalid_run_differentials = standings_data[
            standings_data["run_differential"]
            != standings_data["runs_scored"] - standings_data["runs_allowed"]
        ]

        if not invalid_run_differentials.empty:
            raise ValueError(
                "Standings data contains records where run differential "
                "does not equal runs scored minus runs allowed."
            )


def save_processed_data(
    standings_data: pd.DataFrame,
    output_path: Path,
) -> None:
    """Save the analytics-ready team-season fact as a CSV file."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    standings_data.to_csv(output_path, index=False)


def main() -> None:
    raw_data = load_raw_data(RAW_FILE_PATH)
    standings_data = transform_standings_data(raw_data)

    validate_standings_data(standings_data)
    save_processed_data(standings_data, OUTPUT_FILE_PATH)

    print(
        f"Successfully transformed {len(standings_data)} "
        "team-season records."
    )
    print(f"Processed data saved to: {OUTPUT_FILE_PATH}")


if __name__ == "__main__":
    main()