from pathlib import Path

import pandas as pd


BATTING_FILE = Path(
    "Data/Processed/fact_batting_player_team_season_2025.csv"
)
TEAM_DIMENSION_FILE = Path("Data/Processed/dim_team_2025.csv")
OUTPUT_FILE = Path("Data/Processed/fact_team_position_needs_2025.csv")

SEASON = 2025
MINIMUM_PLAYER_PLATE_APPEARANCES = 50

OPS_NEED_WEIGHT = 0.80
COVERAGE_NEED_WEIGHT = 0.20

POSITION_GROUPS = [
    "Catcher",
    "First Base",
    "Second Base",
    "Third Base",
    "Shortstop",
    "Outfield",
    "Designated Hitter",
]


def load_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Load batting and team reference data."""
    batting = pd.read_csv(BATTING_FILE)
    teams = pd.read_csv(TEAM_DIMENSION_FILE)

    return batting, teams


def validate_required_columns(
    data: pd.DataFrame,
    required_columns: list[str],
    dataset_name: str,
) -> None:
    """Raise a clear error if a required source column is absent."""
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
    """Convert selected fields to numeric values."""
    converted_data = data.copy()

    for column in columns:
        converted_data[column] = pd.to_numeric(
            converted_data[column],
            errors="coerce",
        )

    return converted_data


def standardize_position(position_name: object) -> str | None:
    """Map source primary-position text into analysis-friendly groups."""
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


def min_max_scale(
    values: pd.Series,
    higher_value_means_higher_need: bool,
) -> pd.Series:
    """Scale values to 0-100 and optionally reverse a performance measure."""
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


def assign_need_level(score: float) -> str:
    """Translate a 0-100 score into a readable need classification."""
    if pd.isna(score):
        return "Insufficient Data"
    if score >= 75:
        return "High Need"
    if score >= 50:
        return "Moderate Need"
    if score >= 25:
        return "Low Need"
    return "Relative Strength"


def calculate_position_needs(
    batting: pd.DataFrame,
    teams: pd.DataFrame,
) -> pd.DataFrame:
    """Calculate team offensive need scores by standardized position group."""
    validate_required_columns(
        batting,
        [
            "team_id",
            "team_name",
            "season",
            "position_name",
            "plate_appearances",
            "at_bats",
            "hits",
            "base_on_balls",
            "hit_by_pitch",
            "sacrifice_flies",
            "total_bases",
            "home_runs",
        ],
        "Player-team batting data",
    )

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

    batting = convert_to_numeric(
        batting,
        [
            "team_id",
            "season",
            "plate_appearances",
            "at_bats",
            "hits",
            "base_on_balls",
            "hit_by_pitch",
            "sacrifice_flies",
            "total_bases",
            "home_runs",
        ],
    )

    teams = convert_to_numeric(teams, ["team_id"])

    eligible_batting = batting[
        batting["plate_appearances"] >= MINIMUM_PLAYER_PLATE_APPEARANCES
    ].copy()

    eligible_batting["position_group"] = eligible_batting[
        "position_name"
    ].apply(standardize_position)

    eligible_batting = eligible_batting[
        eligible_batting["position_group"].notna()
    ].copy()

    grouped_batting = (
        eligible_batting.groupby(
            ["team_id", "team_name", "position_group"],
            as_index=False,
        )
        .agg(
            player_count=("player_id", "nunique"),
            total_plate_appearances=("plate_appearances", "sum"),
            total_at_bats=("at_bats", "sum"),
            total_hits=("hits", "sum"),
            total_walks=("base_on_balls", "sum"),
            total_hit_by_pitch=("hit_by_pitch", "sum"),
            total_sacrifice_flies=("sacrifice_flies", "sum"),
            total_bases=("total_bases", "sum"),
            total_home_runs=("home_runs", "sum"),
        )
    )

    all_team_positions = (
        teams[
            [
                "team_id",
                "team_name",
                "team_abbreviation",
                "league_name",
                "division_name",
            ]
        ]
        .assign(_join_key=1)
        .merge(
            pd.DataFrame(
                {
                    "position_group": POSITION_GROUPS,
                    "_join_key": 1,
                }
            ),
            on="_join_key",
            how="inner",
        )
        .drop(columns="_join_key")
    )

    position_needs = all_team_positions.merge(
        grouped_batting,
        on=["team_id", "team_name", "position_group"],
        how="left",
    )

    count_columns = [
        "player_count",
        "total_plate_appearances",
        "total_at_bats",
        "total_hits",
        "total_walks",
        "total_hit_by_pitch",
        "total_sacrifice_flies",
        "total_bases",
        "total_home_runs",
    ]

    for column in count_columns:
        position_needs[column] = position_needs[column].fillna(0)

    on_base_denominator = (
        position_needs["total_at_bats"]
        + position_needs["total_walks"]
        + position_needs["total_hit_by_pitch"]
        + position_needs["total_sacrifice_flies"]
    )

    position_needs["position_obp"] = (
        (
            position_needs["total_hits"]
            + position_needs["total_walks"]
            + position_needs["total_hit_by_pitch"]
        )
        / on_base_denominator
    ).where(on_base_denominator > 0)

    position_needs["position_slg"] = (
        position_needs["total_bases"]
        / position_needs["total_at_bats"]
    ).where(position_needs["total_at_bats"] > 0)

    position_needs["position_ops"] = (
        position_needs["position_obp"] + position_needs["position_slg"]
    )

    position_needs["ops_need_component"] = (
        position_needs.groupby("position_group")["position_ops"]
        .transform(
            lambda values: min_max_scale(
                values,
                higher_value_means_higher_need=False,
            )
        )
        .fillna(100)
    )

    position_needs["coverage_need_component"] = (
        position_needs.groupby("position_group")["total_plate_appearances"]
        .transform(
            lambda values: min_max_scale(
                values,
                higher_value_means_higher_need=False,
            )
        )
        .fillna(100)
    )

    position_needs["position_need_score"] = (
        OPS_NEED_WEIGHT * position_needs["ops_need_component"]
        + COVERAGE_NEED_WEIGHT * position_needs["coverage_need_component"]
    ).clip(lower=0, upper=100)

    position_needs["position_need_level"] = position_needs[
        "position_need_score"
    ].apply(assign_need_level)

    position_needs["season"] = SEASON
    position_needs["minimum_player_plate_appearances"] = (
        MINIMUM_PLAYER_PLATE_APPEARANCES
    )
    position_needs["ops_need_weight"] = OPS_NEED_WEIGHT
    position_needs["coverage_need_weight"] = COVERAGE_NEED_WEIGHT

    position_needs = position_needs.sort_values(
        ["team_name", "position_need_score"],
        ascending=[True, False],
    ).reset_index(drop=True)

    return position_needs


def validate_position_needs(position_needs: pd.DataFrame) -> None:
    """Validate the team-position need output before saving."""
    expected_record_count = 30 * len(POSITION_GROUPS)

    if len(position_needs) != expected_record_count:
        raise ValueError(
            f"Expected {expected_record_count} team-position records, "
            f"found {len(position_needs)}."
        )

    duplicate_records = position_needs.duplicated(
        subset=["team_id", "position_group", "season"],
        keep=False,
    )

    if duplicate_records.any():
        raise ValueError(
            "Team-position needs output contains duplicate team-position "
            "records."
        )

    invalid_scores = position_needs[
        position_needs["position_need_score"].isna()
        | (position_needs["position_need_score"] < 0)
        | (position_needs["position_need_score"] > 100)
    ]

    if not invalid_scores.empty:
        issue_details = invalid_scores[
            ["team_name", "position_group", "position_need_score"]
        ].to_dict("records")

        raise ValueError(
            "Team-position needs output contains invalid scores: "
            f"{issue_details}"
        )


def save_data(position_needs: pd.DataFrame) -> None:
    """Save the team-position needs output."""
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    position_needs.to_csv(OUTPUT_FILE, index=False)


def main() -> None:
    batting, teams = load_data()

    position_needs = calculate_position_needs(
        batting,
        teams,
    )

    validate_position_needs(position_needs)
    save_data(position_needs)

    print(
        f"Successfully calculated position needs for "
        f"{len(position_needs)} team-position records."
    )
    print(f"Processed data saved to: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()