from pathlib import Path

import pandas as pd


TEAM_DIMENSION_FILE = Path("Data/Processed/dim_team_2025.csv")
TEAM_SEASON_FILE = Path("Data/Processed/fact_team_season_2025.csv")
BATTING_FILE = Path(
    "Data/Processed/fact_batting_player_team_season_2025.csv"
)
PITCHING_FILE = Path(
    "Data/Processed/fact_pitching_player_team_season_2025.csv"
)
OUTPUT_FILE = Path("Data/Processed/fact_team_needs_2025.csv")

MINIMUM_BATTING_PLATE_APPEARANCES = 50
MINIMUM_STARTER_GAMES_STARTED = 10
MINIMUM_STARTER_INNINGS_PITCHED = 50
MINIMUM_RELIEVER_INNINGS_PITCHED = 20

OFFENSIVE_NEED_WEIGHT = 0.40
STARTING_PITCHING_NEED_WEIGHT = 0.35
BULLPEN_NEED_WEIGHT = 0.25


def load_data() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Load all processed inputs required for team-needs scoring."""
    teams = pd.read_csv(TEAM_DIMENSION_FILE)
    team_season = pd.read_csv(TEAM_SEASON_FILE)
    batting = pd.read_csv(BATTING_FILE)
    pitching = pd.read_csv(PITCHING_FILE)

    return teams, team_season, batting, pitching


def validate_required_columns(
    data: pd.DataFrame,
    required_columns: list[str],
    dataset_name: str,
) -> None:
    """Raise a clear error if an input dataset is missing required fields."""
    missing_columns = [
        column for column in required_columns if column not in data.columns
    ]

    if missing_columns:
        raise ValueError(
            f"{dataset_name} is missing required columns: {missing_columns}"
        )


def convert_to_numeric(
    data: pd.DataFrame,
    columns: list[str],
) -> pd.DataFrame:
    """Convert selected fields to numeric values without changing other columns."""
    converted_data = data.copy()

    for column in columns:
        converted_data[column] = pd.to_numeric(
            converted_data[column],
            errors="coerce",
        )

    return converted_data


def min_max_scale(
    values: pd.Series,
    higher_value_means_higher_need: bool,
) -> pd.Series:
    """Scale values to 0-100, optionally reversing a performance metric."""
    numeric_values = pd.to_numeric(values, errors="coerce")

    minimum = numeric_values.min()
    maximum = numeric_values.max()

    if pd.isna(minimum) or pd.isna(maximum) or minimum == maximum:
        return pd.Series(50.0, index=values.index)

    scaled_values = 100 * (
        (numeric_values - minimum) / (maximum - minimum)
    )

    if not higher_value_means_higher_need:
        scaled_values = 100 - scaled_values

    return scaled_values.clip(lower=0, upper=100)


def calculate_offensive_metrics(
    batting: pd.DataFrame,
    team_season: pd.DataFrame,
) -> pd.DataFrame:
    """Calculate team offense using qualified hitter statistics and scoring context."""
    validate_required_columns(
        batting,
        [
            "team_id",
            "team_name",
            "plate_appearances",
            "at_bats",
            "hits",
            "base_on_balls",
            "hit_by_pitch",
            "sacrifice_flies",
            "total_bases",
        ],
        "Batting data",
    )

    validate_required_columns(
        team_season,
        [
            "team_id",
            "games_played",
            "runs_scored",
            "run_differential",
        ],
        "Team season data",
    )

    batting = convert_to_numeric(
        batting,
        [
            "team_id",
            "plate_appearances",
            "at_bats",
            "hits",
            "base_on_balls",
            "hit_by_pitch",
            "sacrifice_flies",
            "total_bases",
        ],
    )

    team_season = convert_to_numeric(
        team_season,
        [
            "team_id",
            "games_played",
            "runs_scored",
            "run_differential",
        ],
    )

    qualified_batting = batting[
        batting["plate_appearances"] >= MINIMUM_BATTING_PLATE_APPEARANCES
    ].copy()

    team_batting = (
        qualified_batting.groupby(["team_id", "team_name"], as_index=False)
        .agg(
            total_at_bats=("at_bats", "sum"),
            total_hits=("hits", "sum"),
            total_walks=("base_on_balls", "sum"),
            total_hit_by_pitch=("hit_by_pitch", "sum"),
            total_sacrifice_flies=("sacrifice_flies", "sum"),
            total_bases=("total_bases", "sum"),
        )
    )

    on_base_denominator = (
        team_batting["total_at_bats"]
        + team_batting["total_walks"]
        + team_batting["total_hit_by_pitch"]
        + team_batting["total_sacrifice_flies"]
    )

    team_batting["team_obp"] = (
        (
            team_batting["total_hits"]
            + team_batting["total_walks"]
            + team_batting["total_hit_by_pitch"]
        )
        / on_base_denominator
    ).where(on_base_denominator > 0)

    team_batting["team_slg"] = (
        team_batting["total_bases"] / team_batting["total_at_bats"]
    ).where(team_batting["total_at_bats"] > 0)

    team_batting["team_ops"] = (
        team_batting["team_obp"] + team_batting["team_slg"]
    )

    offensive_metrics = team_batting.merge(
        team_season[
            [
                "team_id",
                "games_played",
                "runs_scored",
                "run_differential",
            ]
        ],
        on="team_id",
        how="left",
    )

    offensive_metrics["runs_scored_per_game"] = (
        offensive_metrics["runs_scored"] / offensive_metrics["games_played"]
    ).where(offensive_metrics["games_played"] > 0)

    offensive_metrics["ops_need_component"] = min_max_scale(
        offensive_metrics["team_ops"],
        higher_value_means_higher_need=False,
    )

    offensive_metrics["runs_per_game_need_component"] = min_max_scale(
        offensive_metrics["runs_scored_per_game"],
        higher_value_means_higher_need=False,
    )

    offensive_metrics["offensive_need_score"] = (
        0.70 * offensive_metrics["ops_need_component"]
        + 0.30 * offensive_metrics["runs_per_game_need_component"]
    ).clip(lower=0, upper=100)

    return offensive_metrics[
        [
            "team_id",
            "team_ops",
            "runs_scored_per_game",
            "offensive_need_score",
        ]
    ]


def calculate_starting_pitching_metrics(
    pitching: pd.DataFrame,
) -> pd.DataFrame:
    """Calculate team starting-pitching need from starter-level statistics."""
    validate_required_columns(
        pitching,
        [
            "team_id",
            "team_name",
            "games_started",
            "innings_pitched",
            "earned_runs",
            "hits_allowed",
            "base_on_balls",
            "strikeouts",
        ],
        "Pitching data",
    )

    pitching = convert_to_numeric(
        pitching,
        [
            "team_id",
            "games_started",
            "innings_pitched",
            "earned_runs",
            "hits_allowed",
            "base_on_balls",
            "strikeouts",
        ],
    )

    starters = pitching[
        (pitching["games_started"] >= MINIMUM_STARTER_GAMES_STARTED)
        & (pitching["innings_pitched"] >= MINIMUM_STARTER_INNINGS_PITCHED)
    ].copy()

    team_starters = (
        starters.groupby(["team_id", "team_name"], as_index=False)
        .agg(
            starter_innings_pitched=("innings_pitched", "sum"),
            starter_earned_runs=("earned_runs", "sum"),
            starter_hits_allowed=("hits_allowed", "sum"),
            starter_walks=("base_on_balls", "sum"),
            starter_strikeouts=("strikeouts", "sum"),
        )
    )

    team_starters["starter_era"] = (
        9
        * team_starters["starter_earned_runs"]
        / team_starters["starter_innings_pitched"]
    ).where(team_starters["starter_innings_pitched"] > 0)

    team_starters["starter_whip"] = (
        (
            team_starters["starter_hits_allowed"]
            + team_starters["starter_walks"]
        )
        / team_starters["starter_innings_pitched"]
    ).where(team_starters["starter_innings_pitched"] > 0)

    team_starters["starter_k_per_nine"] = (
        9
        * team_starters["starter_strikeouts"]
        / team_starters["starter_innings_pitched"]
    ).where(team_starters["starter_innings_pitched"] > 0)

    team_starters["starter_era_need_component"] = min_max_scale(
        team_starters["starter_era"],
        higher_value_means_higher_need=True,
    )

    team_starters["starter_whip_need_component"] = min_max_scale(
        team_starters["starter_whip"],
        higher_value_means_higher_need=True,
    )

    team_starters["starter_k_per_nine_need_component"] = min_max_scale(
        team_starters["starter_k_per_nine"],
        higher_value_means_higher_need=False,
    )

    team_starters["starting_pitching_need_score"] = (
        0.50 * team_starters["starter_era_need_component"]
        + 0.30 * team_starters["starter_whip_need_component"]
        + 0.20 * team_starters["starter_k_per_nine_need_component"]
    ).clip(lower=0, upper=100)

    return team_starters[
        [
            "team_id",
            "starter_innings_pitched",
            "starter_era",
            "starter_whip",
            "starter_k_per_nine",
            "starting_pitching_need_score",
        ]
    ]


def calculate_bullpen_metrics(pitching: pd.DataFrame) -> pd.DataFrame:
    """Calculate team bullpen need from reliever-level statistics."""
    validate_required_columns(
        pitching,
        [
            "team_id",
            "team_name",
            "games_started",
            "innings_pitched",
            "earned_runs",
            "hits_allowed",
            "base_on_balls",
            "strikeouts",
        ],
        "Pitching data",
    )

    pitching = convert_to_numeric(
        pitching,
        [
            "team_id",
            "games_started",
            "innings_pitched",
            "earned_runs",
            "hits_allowed",
            "base_on_balls",
            "strikeouts",
        ],
    )

    relievers = pitching[
        (pitching["games_started"] < MINIMUM_STARTER_GAMES_STARTED)
        & (pitching["innings_pitched"] >= MINIMUM_RELIEVER_INNINGS_PITCHED)
    ].copy()

    team_relievers = (
        relievers.groupby(["team_id", "team_name"], as_index=False)
        .agg(
            bullpen_innings_pitched=("innings_pitched", "sum"),
            bullpen_earned_runs=("earned_runs", "sum"),
            bullpen_hits_allowed=("hits_allowed", "sum"),
            bullpen_walks=("base_on_balls", "sum"),
            bullpen_strikeouts=("strikeouts", "sum"),
        )
    )

    team_relievers["bullpen_era"] = (
        9
        * team_relievers["bullpen_earned_runs"]
        / team_relievers["bullpen_innings_pitched"]
    ).where(team_relievers["bullpen_innings_pitched"] > 0)

    team_relievers["bullpen_whip"] = (
        (
            team_relievers["bullpen_hits_allowed"]
            + team_relievers["bullpen_walks"]
        )
        / team_relievers["bullpen_innings_pitched"]
    ).where(team_relievers["bullpen_innings_pitched"] > 0)

    team_relievers["bullpen_k_per_nine"] = (
        9
        * team_relievers["bullpen_strikeouts"]
        / team_relievers["bullpen_innings_pitched"]
    ).where(team_relievers["bullpen_innings_pitched"] > 0)

    team_relievers["bullpen_era_need_component"] = min_max_scale(
        team_relievers["bullpen_era"],
        higher_value_means_higher_need=True,
    )

    team_relievers["bullpen_whip_need_component"] = min_max_scale(
        team_relievers["bullpen_whip"],
        higher_value_means_higher_need=True,
    )

    team_relievers["bullpen_need_score"] = (
        0.60 * team_relievers["bullpen_era_need_component"]
        + 0.40 * team_relievers["bullpen_whip_need_component"]
    ).clip(lower=0, upper=100)

    return team_relievers[
        [
            "team_id",
            "bullpen_innings_pitched",
            "bullpen_era",
            "bullpen_whip",
            "bullpen_k_per_nine",
            "bullpen_need_score",
        ]
    ]


def assign_need_level(score: float) -> str:
    """Translate a 0-100 need score into a readable category."""
    if pd.isna(score):
        return "Insufficient Data"
    if score >= 75:
        return "High Need"
    if score >= 50:
        return "Moderate Need"
    if score >= 25:
        return "Low Need"
    return "Relative Strength"


def calculate_team_needs(
    teams: pd.DataFrame,
    team_season: pd.DataFrame,
    batting: pd.DataFrame,
    pitching: pd.DataFrame,
) -> pd.DataFrame:
    """Build the complete team-needs profile."""
    validate_required_columns(
        teams,
        [
            "team_id",
            "team_name",
            "team_abbreviation",
            "league_name",
            "division_name",
        ],
        "Team dimension data",
    )

    validate_required_columns(
        team_season,
        [
            "team_id",
            "wins",
            "losses",
            "winning_percentage",
            "run_differential",
        ],
        "Team season data",
    )

    teams = convert_to_numeric(teams, ["team_id"])
    team_season = convert_to_numeric(
        team_season,
        [
            "team_id",
            "wins",
            "losses",
            "winning_percentage",
            "run_differential",
        ],
    )

    offense = calculate_offensive_metrics(batting, team_season)
    starters = calculate_starting_pitching_metrics(pitching)
    bullpen = calculate_bullpen_metrics(pitching)

    team_needs = teams[
        [
            "team_id",
            "team_name",
            "team_abbreviation",
            "league_name",
            "division_name",
        ]
    ].merge(
        team_season[
            [
                "team_id",
                "wins",
                "losses",
                "winning_percentage",
                "run_differential",
            ]
        ],
        on="team_id",
        how="left",
    )

    team_needs = team_needs.merge(offense, on="team_id", how="left")
    team_needs = team_needs.merge(starters, on="team_id", how="left")
    team_needs = team_needs.merge(bullpen, on="team_id", how="left")

    team_needs["offensive_need_score"] = team_needs[
        "offensive_need_score"
    ].fillna(50).clip(lower=0, upper=100)

    team_needs["starting_pitching_need_score"] = team_needs[
        "starting_pitching_need_score"
    ].fillna(50).clip(lower=0, upper=100)

    team_needs["bullpen_need_score"] = team_needs[
        "bullpen_need_score"
    ].fillna(50).clip(lower=0, upper=100)

    team_needs["overall_need_score"] = (
        OFFENSIVE_NEED_WEIGHT * team_needs["offensive_need_score"]
        + STARTING_PITCHING_NEED_WEIGHT
        * team_needs["starting_pitching_need_score"]
        + BULLPEN_NEED_WEIGHT * team_needs["bullpen_need_score"]
    ).clip(lower=0, upper=100)

    need_columns = [
        "offensive_need_score",
        "starting_pitching_need_score",
        "bullpen_need_score",
    ]

    team_needs["primary_need"] = (
        team_needs[need_columns]
        .idxmax(axis=1)
        .str.replace("_need_score", "", regex=False)
        .str.replace("_", " ", regex=False)
        .str.title()
    )

    team_needs["offensive_need_level"] = team_needs[
        "offensive_need_score"
    ].apply(assign_need_level)

    team_needs["starting_pitching_need_level"] = team_needs[
        "starting_pitching_need_score"
    ].apply(assign_need_level)

    team_needs["bullpen_need_level"] = team_needs[
        "bullpen_need_score"
    ].apply(assign_need_level)

    team_needs["overall_need_level"] = team_needs[
        "overall_need_score"
    ].apply(assign_need_level)

    team_needs["season"] = 2025
    team_needs["minimum_batting_plate_appearances"] = (
        MINIMUM_BATTING_PLATE_APPEARANCES
    )
    team_needs["minimum_starter_games_started"] = (
        MINIMUM_STARTER_GAMES_STARTED
    )
    team_needs["minimum_starter_innings_pitched"] = (
        MINIMUM_STARTER_INNINGS_PITCHED
    )
    team_needs["minimum_reliever_innings_pitched"] = (
        MINIMUM_RELIEVER_INNINGS_PITCHED
    )
    team_needs["offensive_need_weight"] = OFFENSIVE_NEED_WEIGHT
    team_needs["starting_pitching_need_weight"] = (
        STARTING_PITCHING_NEED_WEIGHT
    )
    team_needs["bullpen_need_weight"] = BULLPEN_NEED_WEIGHT

    team_needs = team_needs.sort_values(
        "overall_need_score",
        ascending=False,
    ).reset_index(drop=True)

    return team_needs


def validate_team_needs(team_needs: pd.DataFrame) -> None:
    """Validate the team-needs output before saving."""
    expected_team_count = 30

    if len(team_needs) != expected_team_count:
        raise ValueError(
            f"Expected {expected_team_count} team need records, "
            f"found {len(team_needs)}."
        )

    if team_needs["team_id"].isna().any():
        raise ValueError("Team needs output contains missing team IDs.")

    if team_needs["team_id"].duplicated().any():
        raise ValueError("Team needs output contains duplicate team IDs.")

    score_columns = [
        "offensive_need_score",
        "starting_pitching_need_score",
        "bullpen_need_score",
        "overall_need_score",
    ]

    for column in score_columns:
        invalid_scores = team_needs[
            team_needs[column].isna()
            | (team_needs[column] < 0)
            | (team_needs[column] > 100)
        ]

        if not invalid_scores.empty:
            issue_details = invalid_scores[
                ["team_name", column]
            ].to_dict("records")

            raise ValueError(
                f"Team needs output contains invalid values in {column}: "
                f"{issue_details}"
            )


def save_data(team_needs: pd.DataFrame) -> None:
    """Save the final team-needs profile."""
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    team_needs.to_csv(OUTPUT_FILE, index=False)


def main() -> None:
    teams, team_season, batting, pitching = load_data()

    team_needs = calculate_team_needs(
        teams,
        team_season,
        batting,
        pitching,
    )

    validate_team_needs(team_needs)
    save_data(team_needs)

    print(f"Successfully calculated needs for {len(team_needs)} teams.")
    print(f"Processed data saved to: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()