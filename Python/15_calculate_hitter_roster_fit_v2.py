from pathlib import Path

import pandas as pd


PLAYER_SEASON_FILE = Path("Data/Processed/fact_batting_season_2025.csv")
PLAYER_TEAM_SEASON_FILE = Path(
    "Data/Processed/fact_batting_player_team_season_2025.csv"
)
TEAM_NEEDS_FILE = Path("Data/Processed/fact_team_needs_2025.csv")
POSITION_NEEDS_FILE = Path(
    "Data/Processed/fact_team_position_needs_2025.csv"
)
OUTPUT_FILE = Path("Data/Processed/fact_hitter_roster_fit_v2_2025.csv")

MINIMUM_CANDIDATE_PLATE_APPEARANCES = 100

PLAYER_PERFORMANCE_WEIGHT = 0.45
TEAM_OFFENSIVE_NEED_WEIGHT = 0.25
POSITION_NEED_WEIGHT = 0.20
PLAYING_TIME_WEIGHT = 0.10

NEUTRAL_POSITION_NEED_SCORE = 50.0


def load_data() -> tuple[
    pd.DataFrame,
    pd.DataFrame,
    pd.DataFrame,
    pd.DataFrame,
]:
    """Load the processed datasets required for position-aware hitter fit."""
    player_season = pd.read_csv(PLAYER_SEASON_FILE)
    player_team_season = pd.read_csv(PLAYER_TEAM_SEASON_FILE)
    team_needs = pd.read_csv(TEAM_NEEDS_FILE)
    position_needs = pd.read_csv(POSITION_NEEDS_FILE)

    return player_season, player_team_season, team_needs, position_needs


def validate_required_columns(
    data: pd.DataFrame,
    required_columns: list[str],
    dataset_name: str,
) -> None:
    """Raise a clear error if a source dataset lacks a required field."""
    missing_columns = [
        column for column in required_columns if column not in data.columns
    ]

    if missing_columns:
        raise ValueError(
            f"{dataset_name} is missing required columns: {missing_columns}"
        )


def min_max_scale(values: pd.Series) -> pd.Series:
    """Scale numeric values to a 0-100 range."""
    numeric_values = pd.to_numeric(values, errors="coerce")

    minimum = numeric_values.min()
    maximum = numeric_values.max()

    if pd.isna(minimum) or pd.isna(maximum) or minimum == maximum:
        return pd.Series(50.0, index=values.index)

    scaled_values = 100 * (
        (numeric_values - minimum) / (maximum - minimum)
    )

    return scaled_values.clip(lower=0, upper=100)


def standardize_position(position_name: object) -> str | None:
    """Map source primary-position text into roster-fit position groups."""
    if pd.isna(position_name):
        return None

    position_text = str(position_name).strip().lower()

    position_mapping = {
        "catcher": "Catcher",
        "first base": "First Base",
        "second base": "Second Base",
        "third base": "Third Base",
        "shortstop": "Shortstop",
        "left field": "Outfield",
        "center field": "Outfield",
        "right field": "Outfield",
        "outfield": "Outfield",
        "designated hitter": "Designated Hitter",
    }

    return position_mapping.get(position_text)


def prepare_candidates(player_season: pd.DataFrame) -> pd.DataFrame:
    """Prepare eligible hitters with performance and playing-time scores."""
    validate_required_columns(
        player_season,
        [
            "player_id",
            "player_name",
            "season",
            "source_team_id",
            "source_team_name",
            "position_code",
            "position_name",
            "plate_appearances",
            "on_base_plus_slugging",
            "batting_average",
            "on_base_percentage",
            "slugging_percentage",
            "home_runs",
            "runs_batted_in",
        ],
        "Player-season batting data",
    )

    numeric_columns = [
        "player_id",
        "season",
        "source_team_id",
        "plate_appearances",
        "on_base_plus_slugging",
        "batting_average",
        "on_base_percentage",
        "slugging_percentage",
        "home_runs",
        "runs_batted_in",
    ]

    candidates = player_season.copy()

    for column in numeric_columns:
        candidates[column] = pd.to_numeric(
            candidates[column],
            errors="coerce",
        )

    candidates = candidates[
        (candidates["plate_appearances"] >= MINIMUM_CANDIDATE_PLATE_APPEARANCES)
        & candidates["on_base_plus_slugging"].notna()
    ].copy()

    candidates["position_group"] = candidates["position_name"].apply(
        standardize_position
    )

    candidates["player_performance_score"] = min_max_scale(
        candidates["on_base_plus_slugging"]
    )

    candidates["playing_time_score"] = min_max_scale(
        candidates["plate_appearances"]
    )

    candidates = candidates.rename(
        columns={
            "source_team_id": "player_source_team_id",
            "source_team_name": "player_source_team_name",
            "position_code": "player_position_code",
            "position_name": "player_position_name",
            "plate_appearances": "player_plate_appearances",
            "batting_average": "player_batting_average",
            "on_base_percentage": "player_on_base_percentage",
            "slugging_percentage": "player_slugging_percentage",
            "on_base_plus_slugging": "player_ops",
            "home_runs": "player_home_runs",
            "runs_batted_in": "player_runs_batted_in",
        }
    )

    return candidates[
        [
            "player_id",
            "player_name",
            "season",
            "player_source_team_id",
            "player_source_team_name",
            "player_position_code",
            "player_position_name",
            "position_group",
            "player_plate_appearances",
            "player_batting_average",
            "player_on_base_percentage",
            "player_slugging_percentage",
            "player_ops",
            "player_home_runs",
            "player_runs_batted_in",
            "player_performance_score",
            "playing_time_score",
        ]
    ]


def prepare_team_needs(team_needs: pd.DataFrame) -> pd.DataFrame:
    """Prepare target-team overall and offensive need metrics."""
    validate_required_columns(
        team_needs,
        [
            "team_id",
            "team_name",
            "team_abbreviation",
            "league_name",
            "division_name",
            "offensive_need_score",
            "offensive_need_level",
            "overall_need_score",
            "overall_need_level",
            "primary_need",
        ],
        "Team-needs data",
    )

    numeric_columns = [
        "team_id",
        "offensive_need_score",
        "overall_need_score",
    ]

    target_teams = team_needs.copy()

    for column in numeric_columns:
        target_teams[column] = pd.to_numeric(
            target_teams[column],
            errors="coerce",
        )

    if target_teams["team_id"].duplicated().any():
        raise ValueError("Team-needs data contains duplicate team IDs.")

    if target_teams["offensive_need_score"].isna().any():
        raise ValueError("Team-needs data contains missing offensive need scores.")

    return target_teams.rename(
        columns={
            "team_id": "target_team_id",
            "team_name": "target_team_name",
            "team_abbreviation": "target_team_abbreviation",
            "league_name": "target_league_name",
            "division_name": "target_division_name",
            "offensive_need_score": "target_offensive_need_score",
            "offensive_need_level": "target_offensive_need_level",
            "overall_need_score": "target_overall_need_score",
            "overall_need_level": "target_overall_need_level",
            "primary_need": "target_primary_need",
        }
    )[
        [
            "target_team_id",
            "target_team_name",
            "target_team_abbreviation",
            "target_league_name",
            "target_division_name",
            "target_offensive_need_score",
            "target_offensive_need_level",
            "target_overall_need_score",
            "target_overall_need_level",
            "target_primary_need",
        ]
    ]


def prepare_position_needs(position_needs: pd.DataFrame) -> pd.DataFrame:
    """Prepare target team-position need scores for roster-fit matching."""
    validate_required_columns(
        position_needs,
        [
            "team_id",
            "position_group",
            "position_need_score",
            "position_need_level",
            "season",
        ],
        "Team-position needs data",
    )

    prepared_position_needs = position_needs.copy()

    prepared_position_needs["team_id"] = pd.to_numeric(
        prepared_position_needs["team_id"],
        errors="coerce",
    )
    prepared_position_needs["season"] = pd.to_numeric(
        prepared_position_needs["season"],
        errors="coerce",
    )
    prepared_position_needs["position_need_score"] = pd.to_numeric(
        prepared_position_needs["position_need_score"],
        errors="coerce",
    )

    duplicate_records = prepared_position_needs.duplicated(
        subset=["team_id", "position_group", "season"],
        keep=False,
    )

    if duplicate_records.any():
        raise ValueError(
            "Team-position needs data contains duplicate team-position-season "
            "records."
        )

    return prepared_position_needs.rename(
        columns={
            "team_id": "target_team_id",
            "position_need_score": "target_position_need_score",
            "position_need_level": "target_position_need_level",
        }
    )[
        [
            "target_team_id",
            "position_group",
            "season",
            "target_position_need_score",
            "target_position_need_level",
        ]
    ]


def prepare_player_team_history(
    player_team_season: pd.DataFrame,
) -> pd.DataFrame:
    """Prepare player-team records used to exclude players from their 2025 team."""
    validate_required_columns(
        player_team_season,
        [
            "player_id",
            "team_id",
            "season",
        ],
        "Player-team-season batting data",
    )

    history = player_team_season[
        [
            "player_id",
            "team_id",
            "season",
        ]
    ].copy()

    history["player_id"] = pd.to_numeric(
        history["player_id"],
        errors="coerce",
    )
    history["team_id"] = pd.to_numeric(
        history["team_id"],
        errors="coerce",
    )
    history["season"] = pd.to_numeric(
        history["season"],
        errors="coerce",
    )

    return history.rename(
        columns={
            "team_id": "target_team_id",
        }
    ).drop_duplicates()


def build_roster_fit(
    candidates: pd.DataFrame,
    target_teams: pd.DataFrame,
    position_needs: pd.DataFrame,
    player_team_history: pd.DataFrame,
) -> pd.DataFrame:
    """Score external hitter candidates against target-team and position needs."""
    candidates_with_key = candidates.copy()
    target_teams_with_key = target_teams.copy()

    candidates_with_key["_join_key"] = 1
    target_teams_with_key["_join_key"] = 1

    roster_fit = candidates_with_key.merge(
        target_teams_with_key,
        on="_join_key",
        how="inner",
    ).drop(columns="_join_key")

    roster_fit = roster_fit.merge(
        position_needs,
        on=["target_team_id", "position_group", "season"],
        how="left",
    )

    roster_fit["target_position_need_score"] = roster_fit[
        "target_position_need_score"
    ].fillna(NEUTRAL_POSITION_NEED_SCORE)

    roster_fit["target_position_need_level"] = roster_fit[
        "target_position_need_level"
    ].fillna("Neutral / Unmapped Position")

    roster_fit = roster_fit.merge(
        player_team_history.assign(player_on_target_team=True),
        on=["player_id", "target_team_id", "season"],
        how="left",
    )

    roster_fit = roster_fit[
        roster_fit["player_on_target_team"].isna()
    ].copy()

    roster_fit["roster_fit_score"] = (
        PLAYER_PERFORMANCE_WEIGHT
        * roster_fit["player_performance_score"]
        + TEAM_OFFENSIVE_NEED_WEIGHT
        * roster_fit["target_offensive_need_score"]
        + POSITION_NEED_WEIGHT
        * roster_fit["target_position_need_score"]
        + PLAYING_TIME_WEIGHT
        * roster_fit["playing_time_score"]
    ).clip(lower=0, upper=100)

    roster_fit["fit_tier"] = pd.cut(
        roster_fit["roster_fit_score"],
        bins=[-1, 25, 50, 75, 100],
        labels=[
            "Low Fit",
            "Moderate Fit",
            "Strong Fit",
            "Excellent Fit",
        ],
    )

    roster_fit["position_alignment_status"] = "Mapped"
    roster_fit.loc[
        roster_fit["position_group"].isna(),
        "position_alignment_status",
    ] = "Neutral - Unmapped Position"

    roster_fit["fit_explanation"] = (
        "Player OPS: "
        + roster_fit["player_ops"].round(3).astype(str)
        + "; performance score: "
        + roster_fit["player_performance_score"].round(1).astype(str)
        + "; target offensive need: "
        + roster_fit["target_offensive_need_score"].round(1).astype(str)
        + "; target position need: "
        + roster_fit["target_position_need_score"].round(1).astype(str)
        + "; playing-time score: "
        + roster_fit["playing_time_score"].round(1).astype(str)
        + "."
    )

    roster_fit["season"] = roster_fit["season"].astype(int)
    roster_fit["minimum_candidate_plate_appearances"] = (
        MINIMUM_CANDIDATE_PLATE_APPEARANCES
    )
    roster_fit["player_performance_weight"] = PLAYER_PERFORMANCE_WEIGHT
    roster_fit["team_offensive_need_weight"] = TEAM_OFFENSIVE_NEED_WEIGHT
    roster_fit["position_need_weight"] = POSITION_NEED_WEIGHT
    roster_fit["playing_time_weight"] = PLAYING_TIME_WEIGHT

    roster_fit = roster_fit.sort_values(
        ["target_team_name", "roster_fit_score"],
        ascending=[True, False],
    ).reset_index(drop=True)

    return roster_fit


def validate_roster_fit(roster_fit: pd.DataFrame) -> None:
    """Validate the position-aware hitter roster-fit output."""
    if roster_fit.empty:
        raise ValueError("Roster-fit scoring produced zero candidate records.")

    required_columns = [
        "player_id",
        "player_name",
        "target_team_id",
        "target_team_name",
        "season",
        "roster_fit_score",
        "target_position_need_score",
    ]

    for column in required_columns:
        if roster_fit[column].isna().any():
            raise ValueError(
                f"Roster-fit output contains missing values in {column}."
            )

    invalid_scores = roster_fit[
        (roster_fit["roster_fit_score"] < 0)
        | (roster_fit["roster_fit_score"] > 100)
    ]

    if not invalid_scores.empty:
        raise ValueError("Roster-fit output contains scores outside 0-100.")

    invalid_position_scores = roster_fit[
        (roster_fit["target_position_need_score"] < 0)
        | (roster_fit["target_position_need_score"] > 100)
    ]

    if not invalid_position_scores.empty:
        raise ValueError(
            "Roster-fit output contains invalid target position need scores."
        )

    candidates_on_target_team = roster_fit[
        roster_fit["player_on_target_team"].notna()
    ]

    if not candidates_on_target_team.empty:
        raise ValueError(
            "Roster-fit output includes players already associated with "
            "the target team."
        )


def save_data(roster_fit: pd.DataFrame) -> None:
    """Save the final position-aware hitter roster-fit candidate output."""
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    roster_fit.to_csv(OUTPUT_FILE, index=False)


def main() -> None:
    (
        player_season,
        player_team_season,
        team_needs,
        position_needs,
    ) = load_data()

    candidates = prepare_candidates(player_season)
    target_teams = prepare_team_needs(team_needs)
    prepared_position_needs = prepare_position_needs(position_needs)
    player_team_history = prepare_player_team_history(player_team_season)

    roster_fit = build_roster_fit(
        candidates,
        target_teams,
        prepared_position_needs,
        player_team_history,
    )

    validate_roster_fit(roster_fit)
    save_data(roster_fit)

    candidate_count = candidates["player_id"].nunique()
    output_record_count = len(roster_fit)

    print(f"Eligible hitter candidates: {candidate_count}.")
    print(f"Position-aware roster-fit records created: {output_record_count}.")
    print(f"Processed data saved to: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()