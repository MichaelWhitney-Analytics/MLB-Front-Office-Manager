# Business Requirements

## Purpose

Build a portfolio analytics solution that simulates how a baseball operations
department could use public data to assess team needs, player performance,
and potential roster fit.

## Primary Users

- Baseball operations analyst
- General manager or assistant general manager
- Scouting and player personnel staff
- Coaching or player-development staff
- Baseball analytics stakeholder

## Scope

The initial project scope will focus on Major League Baseball regular-season
data and the following analytical areas:

- Team offense
- Team pitching
- Player batting performance
- Player pitching performance
- Team standings and win-loss results
- Position-group roster needs
- Transparent player roster-fit scoring

## Key Business Questions

1. Which teams have the greatest offensive, pitching, or positional needs?
2. Which players may be a strong analytical fit for a selected team?
3. Which players have improved or declined compared with prior periods?
4. Which teams demonstrate strengths or weaknesses in offense, pitching,
   and close-game performance?
5. What data-quality exceptions must be resolved before metrics are used?

## Functional Requirements

- Retrieve public MLB player, team, schedule, standings, and statistical data.
- Standardize source fields into consistent analytical datasets.
- Store raw data separately from processed data.
- Create a documented logical star schema for reporting.
- Create validation checks for duplicates, missing keys, invalid values, and
  metric consistency.
- Produce team-level and player-level reporting outputs.
- Create an explainable roster-fit score using documented assumptions.
- Document data sources, definitions, limitations, and transformation logic.

## Non-Functional Requirements

- Use only free tools and publicly available data sources.
- Do not require personal credentials, subscription services, or paid APIs.
- Keep the project reproducible using documented setup instructions.
- Do not store secrets, keys, or local configuration files in GitHub.
- Keep raw downloaded data out of the repository unless it is a small,
  intentionally included sample dataset.
- Clearly state that this is an independent educational project.

## Success Criteria

The first release will be successful when a user can:

1. Run the extraction and transformation scripts.
2. Review validation results and exception output.
3. Understand the data model and core metrics from project documentation.
4. Identify a team's roster needs from the reporting model.
5. Review player-fit results and understand how each score was calculated.