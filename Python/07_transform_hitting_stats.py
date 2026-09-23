from pathlib import Path
import json

import pandas as pd


RAW_FILE_PATH = Path("Data/Raw/hitting_stats_2025.json")
PROCESSED_DATA_DIRECTORY = Path("Data/Processed")
OUTPUT_FILE_PATH = PROCESSED_DATA_DIRECTORY / "fact_batting_season_2025.csv"
SEASON = 2025


def load_raw_data(file_path: Path) -> dict:
    """Load a locally archived raw MLB API JSON response."""
    with file_path.open("r", encoding="utf-8") as input_file:
        return json.load(input_file)


def transform_hitting_data(raw_data: dict) -> pd.DataFrame:
    """Flatten MLB player hitting data into an analytics-ready fact table."""
    splits = raw_data["data"]["stats"][0]["splits"]

    records = []

    for split in splits:
        player = split.get("player", {})
        team = split.get("team", {})
        position = split.get("position", {})
        stat = split.get("stat", {})

        records.append(
            {
                "player_id": player.get("id"),
                "player_name": player.get("fullName"),
                "team_id": team.get("id"),
                "team_name": team.get("name"),
                "season": SEASON,
                "position_code": position.get("code"),
                "position_name": position.get("name"),
                "games_played": stat.get("gamesPlayed"),
                "plate_appearances": stat.get("plateAppearances"),
                "at_bats": stat.get("atBats"),
                "runs": stat.get("runs"),
                "hits": stat.get("hits"),
                "doubles": stat.get("doubles"),
                "triples": stat.get("triples"),
                "home_runs": stat.get("homeRuns"),
                "runs_batted_in": stat.get("rbi"),
                "stolen_bases": stat.get("stolenBases"),
                "caught_stealing": stat.get("caughtStealing"),
                "base_on_balls": stat.get("baseOnBalls"),
                "intentional_walks": stat.get("intentionalWalks"),
                "strikeouts": stat.get("strikeOuts"),
                "hit_by_pitch": stat.get("hitByPitch"),
                "sacrifice_flies": stat.get("sacFlies"),
                "sacrifice_bunts": stat.get("sacBunts"),
                "ground_into_double_play": stat.get("groundIntoDoublePlay"),
                "total_bases": stat.get("totalBases"),
                "left_on_base": stat.get("leftOnBase"),
                "batting_average": stat.get("avg"),
                "on_base_percentage": stat.get("obp"),
                "slugging_percentage": stat.get("slg"),
                "on_base_plus_slugging": stat.get("ops"),
            }
        )

    batting_data = pd.DataFrame(records)

    numeric_columns = [
        "player_id",
        "team_id",
        "season",
        "games_played",
        "plate_appearances",
        "at_bats",
        "runs",
        "hits",
        "doubles",
        "triples",
        "home_runs",
        "runs_batted_in",
        "stolen_bases",
        "caught_stealing",
        "base_on_balls",
        "intentional_walks",
        "strikeouts",
        "hit_by_pitch",
        "sacrifice_flies",
        "sacrifice_bunts",
        "ground_into_double_play",
        "total_bases",
        "left_on_base",
        "batting_average",
        "on_base_percentage",
        "slugging_percentage",
        "on_base_plus_slugging",
    ]

    for column in numeric_columns:
        batting_data[column] = pd.to_numeric(
            batting_data[column],
            errors="coerce",
        )

    batting_data = batting_data.sort_values(
        ["on_base_plus_slugging", "plate_appearances"],
        ascending=[False, False],
        na_position="last",
    ).reset_index(drop=True)

    return batting_data


def validate_hitting_data(batting_data: pd.DataFrame) -> None:
    """Apply basic quality checks before saving batting data."""
    if batting_data.empty:
        raise ValueError("Batting data transformation produced zero records.")

    if batting_data["player_id"].isna().any():
        raise ValueError("Batting data contains missing player IDs.")

    if batting_data["player_name"].isna().any():
        raise ValueError("Batting data contains missing player names.")

    if batting_data["team_id"].isna().any():
        raise ValueError("Batting data contains missing team IDs.")

    if (batting_data["plate_appearances"].fillna(0) < 0).any():
        raise ValueError("Batting data contains negative plate appearances.")

    if (batting_data["at_bats"].fillna(0) < 0).any():
        raise ValueError("Batting data contains negative at-bats.")

    if (batting_data["hits"].fillna(0) > batting_data["at_bats"].fillna(0)).any():
        raise ValueError("Batting data contains records where hits exceed at-bats.")

    duplicate_records = batting_data.duplicated(
        subset=["player_id", "team_id", "season"],
        keep=False,
    )

    if duplicate_records.any():
        duplicate_count = duplicate_records.sum()
        raise ValueError(
            "Batting data contains duplicate player-team-season records: "
            f"{duplicate_count} rows flagged."
        )


def save_processed_data(
    batting_data: pd.DataFrame,
    output_path: Path,
) -> None:
    """Save the analytics-ready batting fact as a CSV file."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    batting_data.to_csv(output_path, index=False)


def main() -> None:
    raw_data = load_raw_data(RAW_FILE_PATH)
    batting_data = transform_hitting_data(raw_data)

    validate_hitting_data(batting_data)
    save_processed_data(batting_data, OUTPUT_FILE_PATH)

    print(f"Successfully transformed {len(batting_data)} batting records.")
    print(f"Processed data saved to: {OUTPUT_FILE_PATH}")


if __name__ == "__main__":
    main()