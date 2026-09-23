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
    """
    Flatten player-season hitting statistics into an analytics-ready fact.

    Source grain: one row per MLB player for the specified season.
    The team attached by the source is retained as reference context only;
    it must not be used for team-specific performance analysis.
    """
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
                "season": SEASON,
                "source_team_id": team.get("id"),
                "source_team_name": team.get("name"),
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
            }
        )

    batting_data = pd.DataFrame(records)

    numeric_columns = [
        "player_id",
        "season",
        "source_team_id",
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
    ]

    for column in numeric_columns:
        batting_data[column] = pd.to_numeric(
            batting_data[column],
            errors="coerce",
        )

    batting_data["batting_average"] = (
        batting_data["hits"] / batting_data["at_bats"]
    ).where(batting_data["at_bats"] > 0)

    on_base_denominator = (
        batting_data["at_bats"]
        + batting_data["base_on_balls"]
        + batting_data["hit_by_pitch"]
        + batting_data["sacrifice_flies"]
    )

    batting_data["on_base_percentage"] = (
        (
            batting_data["hits"]
            + batting_data["base_on_balls"]
            + batting_data["hit_by_pitch"]
        )
        / on_base_denominator
    ).where(on_base_denominator > 0)

    batting_data["slugging_percentage"] = (
        batting_data["total_bases"] / batting_data["at_bats"]
    ).where(batting_data["at_bats"] > 0)

    batting_data["on_base_plus_slugging"] = (
        batting_data["on_base_percentage"]
        + batting_data["slugging_percentage"]
    )

    batting_data["record_scope"] = "Player Season Total"
    batting_data["team_context_note"] = (
        "Source team is reference context only; player totals may include "
        "statistics from multiple teams."
    )

    batting_data = batting_data.sort_values(
        ["on_base_plus_slugging", "plate_appearances"],
        ascending=[False, False],
        na_position="last",
    ).reset_index(drop=True)

    return batting_data


def validate_hitting_data(batting_data: pd.DataFrame) -> None:
    """Apply data-quality checks before saving player-season batting data."""
    if batting_data.empty:
        raise ValueError("Batting data transformation produced zero records.")

    expected_record_count = 765

    if len(batting_data) != expected_record_count:
        raise ValueError(
            f"Expected {expected_record_count} player-season records, "
            f"found {len(batting_data)}."
        )

    required_columns = [
        "player_id",
        "player_name",
        "season",
        "record_scope",
    ]

    for column in required_columns:
        if batting_data[column].isna().any():
            raise ValueError(f"Batting data contains missing values in {column}.")

    if batting_data["player_id"].duplicated().any():
        raise ValueError(
            "Player-season source contains duplicate player IDs. "
            "Expected one record per player for the selected season."
        )

    if (batting_data["plate_appearances"].fillna(0) < 0).any():
        raise ValueError("Batting data contains negative plate appearances.")

    if (batting_data["at_bats"].fillna(0) < 0).any():
        raise ValueError("Batting data contains negative at-bats.")

    if (batting_data["hits"].fillna(0) > batting_data["at_bats"].fillna(0)).any():
        raise ValueError("Batting data contains records where hits exceed at-bats.")

    invalid_ops = batting_data[
        batting_data["on_base_plus_slugging"].notna()
        & (
            (
                batting_data["on_base_plus_slugging"]
                - (
                    batting_data["on_base_percentage"]
                    + batting_data["slugging_percentage"]
                )
            ).abs()
            > 0.000001
        )
    ]

    if not invalid_ops.empty:
        raise ValueError("OPS validation failed for one or more player records.")


def save_processed_data(
    batting_data: pd.DataFrame,
    output_path: Path,
) -> None:
    """Save the analytics-ready player-season batting fact as a CSV file."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    batting_data.to_csv(output_path, index=False)


def main() -> None:
    raw_data = load_raw_data(RAW_FILE_PATH)
    batting_data = transform_hitting_data(raw_data)

    validate_hitting_data(batting_data)
    save_processed_data(batting_data, OUTPUT_FILE_PATH)

    print(
        f"Successfully transformed {len(batting_data)} "
        "player-season batting records."
    )
    print(f"Processed data saved to: {OUTPUT_FILE_PATH}")


if __name__ == "__main__":
    main()