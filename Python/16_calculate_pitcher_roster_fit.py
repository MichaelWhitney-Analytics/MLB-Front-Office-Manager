from pathlib import Path

import pandas as pd


PITCHING_FILE = Path(
    "Data/Processed/fact_pitching_player_team_season_2025.csv"
)
TEAM_NEEDS_FILE = Path("Data/Processed/fact_team_needs_2025.csv")
OUTPUT_FILE = Path("Data/Processed/fact_pitcher_roster_fit_2025.csv")

MINIMUM_CANDIDATE_INNINGS_PITCHED = 25

PITCHER_PERFORMANCE_WEIGHT = 0.55
ROLE_ALIGNED_TEAM_NEED_WEIGHT = 0.30
WORKLOAD_CONTEXT_WEIGHT = 0.15

ERA_PERFORMANCE_WEIGHT = 0.45
WHIP_PERFORMANCE_WEIGHT = 0.35
STRIKEOUT_RATE_PERFORMANCE_WEIGHT = 0.20


def load_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Load pitching and team-needs datasets."""
    pitching = pd.read_csv(PITCHING_FILE)
    team_needs = pd.read_csv(TEAM_NEEDS_FILE)

    return pitching, team_needs


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


def min_max_scale(
    values: pd.Series,
    higher_value_means_higher_score: bool,
) -> pd.Series:
    """Scale numeric values to 0-100 and optionally reverse a metric."""
    numeric_values = pd.to_numeric(values, errors="coerce")

    minimum = numeric_values.min()
    maximum = numeric_values.max()

    if pd.isna(minimum) or pd.isna(maximum) or minimum == maximum:
        return pd.Series(50.0, index=values.index)

    scaled_values = 100 * (
        (numeric_values - minimum) / (maximum - minimum)
    )

    if not higher_value_means_higher_score:
        scaled_values = 100 - scaled_values

    return scaled_values.clip(lower=0, upper=100)


def prepare_pitcher_candidates(pitching: pd.DataFrame) -> pd.DataFrame:
    """Prepare eligible pitcher candidates and performance component scores."""
    validate_required_columns(
        pitching,
        [
            "player_id",
            "player_name",
            "team_id",
            "team_name",
            "season",
            "pitching_role",
            "innings_pitched",
            "earned_run_average",
            "walks_and_hits_per_inning_pitched",
            "strikeouts_per_nine",
            "games_pitched",
            "games_started",
            "saves",
            "holds",
        ],
        "Player-team pitching data",
    )

    numeric_columns = [
        "player_id",
        "team_id",
        "season",
        "innings_pitched",
        "earned_run_average",
        "walks_and_hits_per_inning_pitched",
        "strikeouts_per_nine",
        "games_pitched",
        "games_started",
        "saves",
        "holds",
    ]

    candidates = pitching.copy()

    for column in numeric_columns:
        candidates[column] = pd.to_numeric(
            candidates[column],
            errors="coerce",
        )

    candidates = candidates[
        (candidates["innings_pitched"] >= MINIMUM_CANDIDATE_INNINGS_PITCHED)
        & candidates["earned_run_average"].notna()
        & candidates["walks_and_hits_per_inning_pitched"].notna()
        & candidates["strikeouts_per_nine"].notna()
    ].copy()

    candidates["era_performance_score"] = min_max_scale(
        candidates["earned_run_average"],
        higher_value_means_higher_score=False,
    )

    candidates["whip_performance_score"] = min_max_scale(
        candidates["walks_and_hits_per_inning_pitched"],
        higher_value_means_higher_score=False,
    )

    candidates["strikeout_rate_performance_score"] = min_max_scale(
        candidates["strikeouts_per_nine"],
        higher_value_means_higher_score=True,
    )

    candidates["pitcher_performance_score"] = (
        ERA_PERFORMANCE_WEIGHT * candidates["era_performance_score"]
        + WHIP_PERFORMANCE_WEIGHT * candidates["whip_performance_score"]
        + STRIKEOUT_RATE_PERFORMANCE_WEIGHT
        * candidates["strikeout_rate_performance_score"]
    ).clip(lower=0, upper=100)

    candidates["workload_context_score"] = min_max_scale(
        candidates["innings_pitched"],
        higher_value_means_higher_score=True,
    )

    candidates = candidates.rename(
        columns={
            "team_id": "player_source_team_id",
            "team_name": "player_source_team_name",
            "pitching_role": "candidate_pitching_role",
            "innings_pitched": "candidate_innings_pitched",
            "earned_run_average": "candidate_era",
            "walks_and_hits_per_inning_pitched": "candidate_whip",
            "strikeouts_per_nine": "candidate_k_per_nine",
            "games_pitched": "candidate_games_pitched",
            "games_started": "candidate_games_started",
            "saves": "candidate_saves",
            "holds": "candidate_holds",
        }
    )

    return candidates[
        [
            "player_id",
            "player_name",
            "season",
            "player_source_team_id",
            "player_source_team_name",
            "candidate_pitching_role",
            "candidate_innings_pitched",
            "candidate_era",
            "candidate_whip",
            "candidate_k_per_nine",
            "candidate_games_pitched",
            "candidate_games_started",
            "candidate_saves",
            "candidate_holds",
            "era_performance_score",
            "whip_performance_score",
            "strikeout_rate_performance_score",
            "pitcher_performance_score",
            "workload_context_score",
        ]
    ]


def prepare_team_needs(team_needs: pd.DataFrame) -> pd.DataFrame:
    """Prepare role-aligned target-team need scores."""
    validate_required_columns(
        team_needs,
        [
            "team_id",
            "team_name",
            "team_abbreviation",
            "league_name",
            "division_name",
            "starting_pitching_need_score",
            "starting_pitching_need_level",
            "bullpen_need_score",
            "bullpen_need_level",
            "overall_need_score",
            "overall_need_level",
            "primary_need",
        ],
        "Team-needs data",
    )

    numeric_columns = [
        "team_id",
        "starting_pitching_need_score",
        "bullpen_need_score",
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

    required_score_columns = [
        "starting_pitching_need_score",
        "bullpen_need_score",
    ]

    for column in required_score_columns:
        if target_teams[column].isna().any():
            raise ValueError(
                f"Team-needs data contains missing values in {column}."
            )

    return target_teams.rename(
        columns={
            "team_id": "target_team_id",
            "team_name": "target_team_name",
            "team_abbreviation": "target_team_abbreviation",
            "league_name": "target_league_name",
            "division_name": "target_division_name",
            "starting_pitching_need_score": (
                "target_starting_pitching_need_score"
            ),
            "starting_pitching_need_level": (
                "target_starting_pitching_need_level"
            ),
            "bullpen_need_score": "target_bullpen_need_score",
            "bullpen_need_level": "target_bullpen_need_level",
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
            "target_starting_pitching_need_score",
            "target_starting_pitching_need_level",
            "target_bullpen_need_score",
            "target_bullpen_need_level",
            "target_overall_need_score",
            "target_overall_need_level",
            "target_primary_need",
        ]
    ]


def prepare_pitcher_team_history(pitching: pd.DataFrame) -> pd.DataFrame:
    """Prepare player-team records used to exclude pitchers from current teams."""
    history = pitching[
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


def assign_role_aligned_team_need(roster_fit: pd.DataFrame) -> pd.DataFrame:
    """Assign the proper target need based on each candidate's pitching role."""
    roster_fit["role_aligned_need_score"] = roster_fit[
        "target_bullpen_need_score"
    ]

    roster_fit["role_aligned_need_level"] = roster_fit[
        "target_bullpen_need_level"
    ]

    starter_mask = roster_fit["candidate_pitching_role"] == "Starter"

    roster_fit.loc[
        starter_mask,
        "role_aligned_need_score",
    ] = roster_fit.loc[
        starter_mask,
        "target_starting_pitching_need_score",
    ]

    roster_fit.loc[
        starter_mask,
        "role_aligned_need_level",
    ] = roster_fit.loc[
        starter_mask,
        "target_starting_pitching_need_level",
    ]

    swing_mask = roster_fit["candidate_pitching_role"] == "Swing"

    starter_need_is_higher = (
        roster_fit["target_starting_pitching_need_score"]
        >= roster_fit["target_bullpen_need_score"]
    )

    swing_starter_mask = swing_mask & starter_need_is_higher
    swing_bullpen_mask = swing_mask & ~starter_need_is_higher

    roster_fit.loc[
        swing_starter_mask,
        "role_aligned_need_score",
    ] = roster_fit.loc[
        swing_starter_mask,
        "target_starting_pitching_need_score",
    ]

    roster_fit.loc[
        swing_starter_mask,
        "role_aligned_need_level",
    ] = roster_fit.loc[
        swing_starter_mask,
        "target_starting_pitching_need_level",
    ]

    roster_fit.loc[
        swing_bullpen_mask,
        "role_aligned_need_score",
    ] = roster_fit.loc[
        swing_bullpen_mask,
        "target_bullpen_need_score",
    ]

    roster_fit.loc[
        swing_bullpen_mask,
        "role_aligned_need_level",
    ] = roster_fit.loc[
        swing_bullpen_mask,
        "target_bullpen_need_level",
    ]

    return roster_fit


def build_roster_fit(
    candidates: pd.DataFrame,
    target_teams: pd.DataFrame,
    pitcher_team_history: pd.DataFrame,
) -> pd.DataFrame:
    """Score eligible external pitcher candidates for all target teams."""
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
        pitcher_team_history.assign(player_on_target_team=True),
        on=["player_id", "target_team_id", "season"],
        how="left",
    )

    roster_fit = roster_fit[
        roster_fit["player_on_target_team"].isna()
    ].copy()

    roster_fit = assign_role_aligned_team_need(roster_fit)

    roster_fit["pitcher_roster_fit_score"] = (
        PITCHER_PERFORMANCE_WEIGHT
        * roster_fit["pitcher_performance_score"]
        + ROLE_ALIGNED_TEAM_NEED_WEIGHT
        * roster_fit["role_aligned_need_score"]
        + WORKLOAD_CONTEXT_WEIGHT
        * roster_fit["workload_context_score"]
    ).clip(lower=0, upper=100)

    roster_fit["fit_tier"] = pd.cut(
        roster_fit["pitcher_roster_fit_score"],
        bins=[-1, 25, 50, 75, 100],
        labels=[
            "Low Fit",
            "Moderate Fit",
            "Strong Fit",
            "Excellent Fit",
        ],
    )

    roster_fit["fit_explanation"] = (
        "Role: "
        + roster_fit["candidate_pitching_role"].astype(str)
        + "; ERA: "
        + roster_fit["candidate_era"].round(2).astype(str)
        + "; WHIP: "
        + roster_fit["candidate_whip"].round(3).astype(str)
        + "; K/9: "
        + roster_fit["candidate_k_per_nine"].round(2).astype(str)
        + "; performance score: "
        + roster_fit["pitcher_performance_score"].round(1).astype(str)
        + "; role-aligned team need: "
        + roster_fit["role_aligned_need_score"].round(1).astype(str)
        + "; workload score: "
        + roster_fit["workload_context_score"].round(1).astype(str)
        + "."
    )

    roster_fit["season"] = roster_fit["season"].astype(int)
    roster_fit["minimum_candidate_innings_pitched"] = (
        MINIMUM_CANDIDATE_INNINGS_PITCHED
    )
    roster_fit["pitcher_performance_weight"] = PITCHER_PERFORMANCE_WEIGHT
    roster_fit["role_aligned_team_need_weight"] = (
        ROLE_ALIGNED_TEAM_NEED_WEIGHT
    )
    roster_fit["workload_context_weight"] = WORKLOAD_CONTEXT_WEIGHT
    roster_fit["era_performance_weight"] = ERA_PERFORMANCE_WEIGHT
    roster_fit["whip_performance_weight"] = WHIP_PERFORMANCE_WEIGHT
    roster_fit["strikeout_rate_performance_weight"] = (
        STRIKEOUT_RATE_PERFORMANCE_WEIGHT
    )

    roster_fit = roster_fit.sort_values(
        ["target_team_name", "pitcher_roster_fit_score"],
        ascending=[True, False],
    ).reset_index(drop=True)

    return roster_fit


def validate_roster_fit(roster_fit: pd.DataFrame) -> None:
    """Validate pitcher roster-fit output before saving."""
    if roster_fit.empty:
        raise ValueError("Pitcher roster-fit scoring produced zero records.")

    required_columns = [
        "player_id",
        "player_name",
        "target_team_id",
        "target_team_name",
        "season",
        "candidate_pitching_role",
        "pitcher_roster_fit_score",
        "role_aligned_need_score",
    ]

    for column in required_columns:
        if roster_fit[column].isna().any():
            raise ValueError(
                f"Pitcher roster-fit output contains missing values in {column}."
            )

    score_columns = [
        "pitcher_roster_fit_score",
        "pitcher_performance_score",
        "workload_context_score",
        "role_aligned_need_score",
    ]

    for column in score_columns:
        invalid_scores = roster_fit[
            roster_fit[column].isna()
            | (roster_fit[column] < 0)
            | (roster_fit[column] > 100)
        ]

        if not invalid_scores.empty:
            raise ValueError(
                f"Pitcher roster-fit output contains invalid values in {column}."
            )

    candidates_on_target_team = roster_fit[
        roster_fit["player_on_target_team"].notna()
    ]

    if not candidates_on_target_team.empty:
        raise ValueError(
            "Pitcher roster-fit output includes pitchers already associated "
            "with the target team."
        )


def save_data(roster_fit: pd.DataFrame) -> None:
    """Save the final pitcher roster-fit candidate output."""
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    roster_fit.to_csv(OUTPUT_FILE, index=False)


def main() -> None:
    pitching, team_needs = load_data()

    candidates = prepare_pitcher_candidates(pitching)
    target_teams = prepare_team_needs(team_needs)
    pitcher_team_history = prepare_pitcher_team_history(pitching)

    roster_fit = build_roster_fit(
        candidates,
        target_teams,
        pitcher_team_history,
    )

    validate_roster_fit(roster_fit)
    save_data(roster_fit)

    candidate_count = candidates["player_id"].nunique()
    output_record_count = len(roster_fit)

    print(f"Eligible pitcher candidates: {candidate_count}.")
    print(f"Pitcher roster-fit candidate records created: {output_record_count}.")
    print(f"Processed data saved to: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()