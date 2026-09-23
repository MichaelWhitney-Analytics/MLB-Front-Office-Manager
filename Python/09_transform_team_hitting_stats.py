from pathlib import Path
import json

import pandas as pd


RAW_FILE_PATH = Path("Data/Raw/team_hitting_stats_2025.json")
PROCESSED_DATA_DIRECTORY = Path("Data/Processed")
OUTPUT_FILE_PATH = (
    PROCESSED_DATA_DIRECTORY / "fact_batting_player_team_season_2025.csv"
)
SEASON = 2025


def load_raw_data(file_path: Path) -> dict:
    """Load locally archived team-level MLB hitting responses."""
    with file_path.open("r", encoding="utf-8") as input_file:
        return json.load(input_file)


def transform_team_hitting_data(raw_data: dict) -> pd.DataFrame:
    """Create one record per player-team-season from team-specific responses."""
    records = []

    for team_response in raw_data["data"]["teams"]:
        requested_team_id = team_response["team_id"]
        requested_team_name = team_response["team_name"]

        splits = team_response["stats"].get("stats", [{}])[0].get("splits", [])

        for split in splits:
            player = split.get("player", {})
            player_team = split.get("team", {})
            position = split.get("position", {})
            stat = split.get("stat", {})

            records.append(
                {
                    "player_id": player.get("id"),
                    "player_name": player.get("fullName"),
                    "team_id": requested_team_id,
                    "team_name": requested_team_name,
                    "source_team_id": player_team.get("id"),
                    "source_team_name": player_team.get("name"),
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
                }
            )

    batting_data = pd.DataFrame(records)

    numeric_columns = [
        "player_id",
        "team_id",
        "source_team_id",
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

    teams_played_for_count = (
        batting_data.groupby(["player_id", "season"])["team_id"]
        .transform("nunique")
    )

    batting_data["teams_played_for_count"] = teams_played_for_count
    batting_data["multiple_teams_flag"] = (
        batting_data["teams_played_for_count"] > 1
    ).map({True: "Yes", False: "No"})
    batting_data["roster_movement_flag"] = batting_data[
        "multiple_teams_flag"
    ]
    batting_data["record_scope"] = "Player Team Season"

    batting_data = batting_data.sort_values(
        ["on_base_plus_slugging", "plate_appearances"],
        ascending=[False, False],
        na_position="last",
    ).reset_index(drop=True)

    return batting_data


def validate_team_hitting_data(batting_data: pd.DataFrame) -> None:
    """Validate team-specific player batting records before saving."""
    if batting_data.empty:
        raise ValueError("Team hitting data transformation produced zero records.")

    required_columns = [
        "player_id",
        "player_name",
        "team_id",
        "team_name",
        "season",
    ]

    for column in required_columns:
        if batting_data[column].isna().any():
            raise ValueError(f"Team hitting data contains missing values in {column}.")

    if (batting_data["plate_appearances"].fillna(0) < 0).any():
        raise ValueError("Team hitting data contains negative plate appearances.")

    if (batting_data["at_bats"].fillna(0) < 0).any():
        raise ValueError("Team hitting data contains negative at-bats.")

    if (batting_data["hits"].fillna(0) > batting_data["at_bats"].fillna(0)).any():
        raise ValueError("Team hitting data contains records where hits exceed at-bats.")

    duplicate_records = batting_data.duplicated(
        subset=["player_id", "team_id", "season"],
        keep=False,
    )

    if duplicate_records.any():
        duplicate_count = duplicate_records.sum()
        raise ValueError(
            "Team hitting data contains duplicate player-team-season records: "
            f"{duplicate_count} rows flagged."
        )

    mismatched_team_context = batting_data[
        batting_data["team_id"] != batting_data["source_team_id"]
    ]

    if not mismatched_team_context.empty:
        raise ValueError(
            "Team response context does not match the source team on one or "
            "more player records."
        )


def save_processed_data(
    batting_data: pd.DataFrame,
    output_path: Path,
) -> None:
    """Save the analytics-ready player-team-season batting fact as CSV."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    batting_data.to_csv(output_path, index=False)


def main() -> None:
    raw_data = load_raw_data(RAW_FILE_PATH)
    batting_data = transform_team_hitting_data(raw_data)

    validate_team_hitting_data(batting_data)
    save_processed_data(batting_data, OUTPUT_FILE_PATH)

    multi_team_player_count = (
        batting_data.loc[
            batting_data["multiple_teams_flag"] == "Yes",
            "player_id",
        ]
        .nunique()
    )

    print(
        f"Successfully transformed {len(batting_data)} "
        "player-team-season batting records."
    )
    print(
        f"Players appearing for multiple teams: "
        f"{multi_team_player_count}."
    )
    print(f"Processed data saved to: {OUTPUT_FILE_PATH}")


if __name__ == "__main__":
    main()