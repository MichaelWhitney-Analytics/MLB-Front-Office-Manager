# MLB Front Office Manager: Roster-Fit Methodology

## Purpose

This project is an independent baseball analytics and business intelligence
portfolio project. It uses public Major League Baseball statistics to create
an explainable decision-support prototype for team needs analysis and
external player roster-fit evaluation.

The outputs are intended to demonstrate an end-to-end analytics workflow:

1. Extract public source data.
2. Store raw data separately from processed analytical outputs.
3. Transform nested source data into validated fact and dimension tables.
4. Calculate transparent team and position need scores.
5. Generate explainable hitter and pitcher candidate rankings.

This project is not affiliated with Major League Baseball, any MLB club, or
any player. It is not a prediction system, trade recommendation engine, or
financial valuation model.

## Scope

The initial release uses 2025 MLB regular-season data and focuses on:

- Team performance and run differential
- Individual player batting performance
- Individual player pitching performance
- Player-team-season contribution records
- Team offensive, starting-pitching, and bullpen needs
- Team offensive need by position group
- External hitter roster-fit candidates
- External pitcher roster-fit candidates

## Data Sources

The project retrieves public data from MLB Stats API endpoints, including:

- MLB team reference data
- Regular-season standings
- Individual player hitting statistics
- Individual player pitching statistics
- Team-specific player hitting statistics
- Team-specific player pitching statistics

Raw API responses are stored locally in `Data/Raw/`.

Processed datasets are generated locally in `Data/Processed/`.

Raw and processed data files are excluded from the public repository by
`.gitignore`. This keeps the repository lightweight and ensures the
documented pipeline is the source of truth.

## Data Model

### Dimension: DimTeam

**File:** `dim_team_2025.csv`

**Grain:** One row per MLB team.

**Purpose:** Provides a reusable team lookup including team identifiers,
league, division, abbreviation, and venue context.

### Fact: FactTeamSeason

**File:** `fact_team_season_2025.csv`

**Grain:** One row per MLB team for the 2025 season.

**Purpose:** Stores standings and team performance data such as wins, losses,
runs scored, runs allowed, and run differential.

### Fact: FactBattingSeason

**File:** `fact_batting_season_2025.csv`

**Grain:** One row per player for the 2025 season.

**Purpose:** Supports league-wide player evaluation and hitter candidate
performance scoring.

**Important limitation:** The source team attached to this dataset is
reference context only. A player’s statistics may include performance for
multiple teams during the season.

### Fact: FactBattingPlayerTeamSeason

**File:** `fact_batting_player_team_season_2025.csv`

**Grain:** One row per player, team, and season.

**Purpose:** Supports team-specific offensive contribution, team roster
analysis, position need scoring, and identification of players who appeared
for multiple teams.

### Fact: FactPitchingPlayerTeamSeason

**File:** `fact_pitching_player_team_season_2025.csv`

**Grain:** One row per player, team, and season.

**Purpose:** Supports team-specific pitching contribution, role
classification, starting-pitching analysis, bullpen analysis, and player
movement analysis.

### Fact: FactTeamNeeds

**File:** `fact_team_needs_2025.csv`

**Grain:** One row per MLB team for the 2025 season.

**Purpose:** Stores relative offensive, starting-pitching, bullpen, and
overall need scores on a 0-100 scale.

### Fact: FactTeamPositionNeeds

**File:** `fact_team_position_needs_2025.csv`

**Grain:** One row per team, position group, and season.

**Purpose:** Stores relative offensive need scores for Catcher, First Base,
Second Base, Third Base, Shortstop, Outfield, and Designated Hitter.

### Fact: FactHitterRosterFitV2

**File:** `fact_hitter_roster_fit_v2_2025.csv`

**Grain:** One row per eligible hitter candidate, target team, and season.

**Purpose:** Provides position-aware external hitter fit scores.

### Fact: FactPitcherRosterFit

**File:** `fact_pitcher_roster_fit_2025.csv`

**Grain:** One row per eligible pitcher candidate, target team, and season.

**Purpose:** Provides role-aware external pitcher fit scores.

## Team Need Methodology

Need scores are relative 0-100 values. A higher score means a larger
relative need compared with the other MLB teams included in the model.

### Offensive Need Score

The offensive score uses player-team batting records with at least 50 plate
appearances. It combines:

- Team OPS, weighted at 70%
- Runs scored per game, weighted at 30%

Lower team offensive performance produces a higher offensive need score.

### Starting-Pitching Need Score

The starting-pitching score uses pitcher-team records with:

- At least 10 games started
- At least 50 innings pitched

It combines:

- Starter ERA, weighted at 50%
- Starter WHIP, weighted at 30%
- Starter strikeouts per nine innings, weighted at 20%

Higher ERA and WHIP increase need. Higher strikeouts per nine innings reduce
need.

### Bullpen Need Score

The bullpen score uses pitcher-team records with:

- Fewer than 10 games started
- At least 20 innings pitched

It combines:

- Bullpen ERA, weighted at 60%
- Bullpen WHIP, weighted at 40%

Higher ERA and WHIP increase need.

### Overall Team Need Score

```text
Overall Need Score =
    40% Offensive Need Score
  + 35% Starting-Pitching Need Score
  + 25% Bullpen Need Score
```

## Position Need Methodology

Position need uses team-specific hitter records with at least 50 plate
appearances and standardizes source positions into these groups:

- Catcher
- First Base
- Second Base
- Third Base
- Shortstop
- Outfield
- Designated Hitter

```text
Position Need Score =
    80% Low-OPS Need Component
  + 20% Low-Plate-Appearance Coverage Need Component
```

Higher scores indicate lower offensive production, lower qualified
playing-time coverage, or both, relative to the league at that position
group.

## Hitter Roster-Fit Methodology

Eligible hitter candidates must have:

- At least 100 plate appearances
- A non-null OPS value
- No player-team relationship with the target team during the selected season

```text
Hitter Roster-Fit Score =
    45% Player Performance Score
  + 25% Target Team Offensive Need Score
  + 20% Target Position Need Score
  + 10% Playing-Time Context Score
```

### Hitter components

- **Player Performance Score:** Relative OPS among eligible hitter candidates.
- **Target Team Offensive Need Score:** Relative team offensive need.
- **Target Position Need Score:** Relative need for the candidate’s
  standardized position group on the target team.
- **Playing-Time Context Score:** Relative plate-appearance volume among
  eligible candidates.

A player with an unmapped primary position receives a neutral position-need
score of 50 rather than an assumed positional match.

## Pitcher Roster-Fit Methodology

Eligible pitcher candidates must have:

- At least 25 innings pitched
- Non-null ERA, WHIP, and strikeouts per nine innings
- No player-team relationship with the target team during the selected season

Pitchers are classified as:

- **Starter:** At least one game started
- **Relief:** No games started
- **Swing:** At least one start and at least one relief appearance

```text
Pitcher Roster-Fit Score =
    55% Pitcher Performance Score
  + 30% Role-Aligned Team Need Score
  + 15% Workload Context Score
```

### Pitcher performance score

```text
Pitcher Performance Score =
    45% Inverted ERA Score
  + 35% Inverted WHIP Score
  + 20% Strikeout-Rate Score
```

Lower ERA and WHIP produce higher performance scores. Higher strikeouts per
nine innings produce higher performance scores.

### Role-aligned team need

- Starter candidates use the target team’s starting-pitching need score.
- Relief candidates use the target team’s bullpen need score.
- Swing candidates use the larger of the target team’s starting-pitching
  and bullpen need scores.

## Data Quality Controls

The pipeline includes validation checks such as:

- Expected MLB team counts
- Unique team identifiers
- Unique player-team-season records
- Non-negative count statistics
- Hits not exceeding at-bats
- Wins plus losses equaling games played
- Run differential reconciling to runs scored minus runs allowed
- Earned runs not exceeding total runs allowed
- Games started not exceeding games pitched
- Scores constrained to a 0-100 range
- Exclusion of candidates already associated with the target team

## Key Limitations

This project does not yet account for:

- Player age, contract status, salary, service time, or free-agency status
- Trade availability, transaction type, or organizational strategy
- Injuries or medical information
- Defensive metrics
- Minor-league performance
- Scouting assessments
- Park factors or league adjustments
- Advanced batted-ball or pitch-tracking metrics
- Current-season live data
- Multi-position eligibility beyond the source primary position

A high roster-fit score means a player’s statistical profile and position
align with the model’s documented needs. It does not mean the player is
available, affordable, or advisable to acquire.

## Reproducing the Pipeline

1. Create and activate a Python virtual environment.
2. Install dependencies:

```powershell
python -m pip install -r requirements.txt
```

3. Run the scripts in numerical order from the project root:

```powershell
python Python/01_extract_mlb_data.py
python Python/02_extract_standings.py
python Python/03_extract_hitting_stats.py
python Python/04_extract_pitching_stats.py
python Python/05_transform_team_data.py
python Python/06_transform_standings_data.py
python Python/07_transform_hitting_stats.py
python Python/08_extract_team_hitting_stats.py
python Python/09_transform_team_hitting_stats.py
python Python/10_extract_team_pitching_stats.py
python Python/11_transform_team_pitching_stats.py
python Python/12_calculate_team_needs.py
python Python/13_calculate_hitter_roster_fit.py
python Python/14_calculate_team_position_needs.py
python Python/15_calculate_hitter_roster_fit_v2.py
python Python/16_calculate_pitcher_roster_fit.py
```

## Future Enhancements

Potential future improvements include:

- Add age, contract, salary, and service-time context
- Add defensive and advanced baseball metrics
- Add park-factor and league adjustments
- Add player transaction history
- Add current-season refresh capabilities
- Add Power BI dashboard pages
- Add automated tests with pytest
- Add a GitHub Actions workflow for validation
- Add interactive GitHub Pages documentation