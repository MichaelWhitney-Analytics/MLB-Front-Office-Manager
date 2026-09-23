from pathlib import Path
import json

import pandas as pd


RAW_FILE_PATH = Path("Data/Raw/team_pitching_stats_2025.json")
PROCESSED_DATA_DIRECTORY = Path("Data/Processed")
OUTPUT_FILE_PATH = (
    PROCESSED_DATA_DIRECTORY / "fact_pitching_player_team_season_2025.csv"
)
SEASON = 2025


def load_raw_data(file_path: Path) -> dict:
    """Load locally archived team-level MLB pitching responses."""
    with file_path.open("r", encoding="utf-8") as input_file:
        return json.load(input_file)


def parse_innings_pitched(innings_pitched: object) -> float | None:
    """
    Convert baseball innings notation to decimal innings.

    MLB reports partial innings as tenths:
    5.1 means 5 innings and 1 out, or 5.333 decimal innings.
    5.2 means 5 innings and 2 outs, or 5.667 decimal innings.
    """
    if innings_pitched is None or pd.isna(innings_pitched):
        return None

    innings_text = str(innings_pitched).strip()

    if not innings_text:
        return None

    try:
        whole_innings, outs_text = innings_text.split(".", maxsplit=1)
        whole_innings = int(whole_innings)
        outs = int(outs_text)

        if outs not in {0, 1, 2}:
            raise ValueError(
                f"Invalid baseball innings notation: {innings_pitched}"
            )

        return whole_innings + (outs / 3)
    except ValueError as error:
        raise ValueError(
            f"Unable to parse innings pitched value: {innings_pitched}"
        ) from error


def safe_divide(
    numerator: pd.Series,
    denominator: pd.Series,
) -> pd.Series:
    """Safely divide two numeric Series and return null where denominator is zero."""
    return (numerator / denominator).where(denominator > 0)


def transform_team_pitching_data(raw_data: dict) -> pd.DataFrame:
    """Create one record per player-team-season from team-specific pitching data."""
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
                    "games_pitched": stat.get("gamesPitched"),
                    "games_started": stat.get("gamesStarted"),
                    "games_finished": stat.get("gamesFinished"),
                    "complete_games": stat.get("completeGames"),
                    "shutouts": stat.get("shutouts"),
                    "wins": stat.get("wins"),
                    "losses": stat.get("losses"),
                    "saves": stat.get("saves"),
                    "save_opportunities": stat.get("saveOpportunities"),
                    "holds": stat.get("holds"),
                    "blown_saves": stat.get("blownSaves"),
                    "innings_pitched_baseball": stat.get("inningsPitched"),
                    "hits_allowed": stat.get("hits"),
                    "runs_allowed": stat.get("runs"),
                    "earned_runs": stat.get("earnedRuns"),
                    "home_runs_allowed": stat.get("homeRuns"),
                    "base_on_balls": stat.get("baseOnBalls"),
                    "intentional_walks": stat.get("intentionalWalks"),
                    "strikeouts": stat.get("strikeOuts"),
                    "hit_batters": stat.get("hitByPitch"),
                    "batters_faced": stat.get("battersFaced"),
                    "wild_pitches": stat.get("wildPitches"),
                    "balks": stat.get("balks"),
                    "ground_outs": stat.get("groundOuts"),
                    "air_outs": stat.get("airOuts"),
                    "ground_into_double_play": stat.get("groundIntoDoublePlay"),
                    "inherited_runners": stat.get("inheritedRunners"),
                    "inherited_runners_scored": stat.get("inheritedRunnersScored"),
                }
            )

    pitching_data = pd.DataFrame(records)

    integer_columns = [
        "player_id",
        "team_id",
        "source_team_id",
        "season",
        "games_pitched",
        "games_started",
        "games_finished",
        "complete_games",
        "shutouts",
        "wins",
        "losses",
        "saves",
        "save_opportunities",
        "holds",
        "blown_saves",
        "hits_allowed",
        "runs_allowed",
        "earned_runs",
        "home_runs_allowed",
        "base_on_balls",
        "intentional_walks",
        "strikeouts",
        "hit_batters",
        "batters_faced",
        "wild_pitches",
        "balks",
        "ground_outs",
        "air_outs",
        "ground_into_double_play",
        "inherited_runners",
        "inherited_runners_scored",
    ]

    for column in integer_columns:
        pitching_data[column] = pd.to_numeric(
            pitching_data[column],
            errors="coerce",
        )

    pitching_data["innings_pitched"] = pitching_data[
        "innings_pitched_baseball"
    ].apply(parse_innings_pitched)

    pitching_data["earned_run_average"] = (
        9 * pitching_data["earned_runs"] / pitching_data["innings_pitched"]
    ).where(pitching_data["innings_pitched"] > 0)

    pitching_data["walks_and_hits_per_inning_pitched"] = safe_divide(
        pitching_data["base_on_balls"] + pitching_data["hits_allowed"],
        pitching_data["innings_pitched"],
    )

    pitching_data["strikeouts_per_nine"] = (
        9 * pitching_data["strikeouts"] / pitching_data["innings_pitched"]
    ).where(pitching_data["innings_pitched"] > 0)

    pitching_data["walks_per_nine"] = (
        9 * pitching_data["base_on_balls"] / pitching_data["innings_pitched"]
    ).where(pitching_data["innings_pitched"] > 0)

    pitching_data["home_runs_per_nine"] = (
        9 * pitching_data["home_runs_allowed"] / pitching_data["innings_pitched"]
    ).where(pitching_data["innings_pitched"] > 0)

    pitching_data["strikeout_to_walk_ratio"] = safe_divide(
        pitching_data["strikeouts"],
        pitching_data["base_on_balls"],
    )

    pitching_data["starter_appearance_percentage"] = safe_divide(
        pitching_data["games_started"],
        pitching_data["games_pitched"],
    )

    pitching_data["pitching_role"] = "Relief"
    pitching_data.loc[
        pitching_data["games_started"] > 0,
        "pitching_role",
    ] = "Starter"
    pitching_data.loc[
        (pitching_data["games_started"] > 0)
        & (pitching_data["games_started"] < pitching_data["games_pitched"]),
        "pitching_role",
    ] = "Swing"

    teams_played_for_count = (
        pitching_data.groupby(["player_id", "season"])["team_id"]
        .transform("nunique")
    )

    pitching_data["teams_played_for_count"] = teams_played_for_count
    pitching_data["multiple_teams_flag"] = (
        pitching_data["teams_played_for_count"] > 1
    ).map({True: "Yes", False: "No"})
    pitching_data["roster_movement_flag"] = pitching_data[
        "multiple_teams_flag"
    ]
    pitching_data["record_scope"] = "Player Team Season"

    pitching_data = pitching_data.sort_values(
        ["earned_run_average", "innings_pitched"],
        ascending=[True, False],
        na_position="last",
    ).reset_index(drop=True)

    return pitching_data


def validate_team_pitching_data(pitching_data: pd.DataFrame) -> None:
    """Validate team-specific player pitching records before saving."""
    if pitching_data.empty:
        raise ValueError("Team pitching data transformation produced zero records.")

    required_columns = [
        "player_id",
        "player_name",
        "team_id",
        "team_name",
        "season",
    ]

    for column in required_columns:
        if pitching_data[column].isna().any():
            raise ValueError(
                f"Team pitching data contains missing values in {column}."
            )

    non_negative_columns = [
        "games_pitched",
        "games_started",
        "games_finished",
        "innings_pitched",
        "hits_allowed",
        "runs_allowed",
        "earned_runs",
        "home_runs_allowed",
        "base_on_balls",
        "strikeouts",
    ]

    for column in non_negative_columns:
        if (pitching_data[column].fillna(0) < 0).any():
            raise ValueError(
                f"Team pitching data contains negative values in {column}."
            )

    if (
        pitching_data["games_started"].fillna(0)
        > pitching_data["games_pitched"].fillna(0)
    ).any():
        raise ValueError(
            "Team pitching data contains records where games started "
            "exceeds games pitched."
        )

    if (
        pitching_data["earned_runs"].fillna(0)
        > pitching_data["runs_allowed"].fillna(0)
    ).any():
        raise ValueError(
            "Team pitching data contains records where earned runs "
            "exceeds total runs allowed."
        )

    duplicate_records = pitching_data.duplicated(
        subset=["player_id", "team_id", "season"],
        keep=False,
    )

    if duplicate_records.any():
        duplicate_count = duplicate_records.sum()
        raise ValueError(
            "Team pitching data contains duplicate player-team-season records: "
            f"{duplicate_count} rows flagged."
        )

    mismatched_team_context = pitching_data[
        pitching_data["team_id"] != pitching_data["source_team_id"]
    ]

    if not mismatched_team_context.empty:
        raise ValueError(
            "Team response context does not match the source team on one or "
            "more pitcher records."
        )


def save_processed_data(
    pitching_data: pd.DataFrame,
    output_path: Path,
) -> None:
    """Save the analytics-ready player-team-season pitching fact as CSV."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    pitching_data.to_csv(output_path, index=False)


def main() -> None:
    raw_data = load_raw_data(RAW_FILE_PATH)
    pitching_data = transform_team_pitching_data(raw_data)

    validate_team_pitching_data(pitching_data)
    save_processed_data(pitching_data, OUTPUT_FILE_PATH)

    multi_team_player_count = (
        pitching_data.loc[
            pitching_data["multiple_teams_flag"] == "Yes",
            "player_id",
        ]
        .nunique()
    )

    print(
        f"Successfully transformed {len(pitching_data)} "
        "player-team-season pitching records."
    )
    print(
        f"Players appearing for multiple teams: "
        f"{multi_team_player_count}."
    )
    print(f"Processed data saved to: {OUTPUT_FILE_PATH}")


if __name__ == "__main__":
    main()