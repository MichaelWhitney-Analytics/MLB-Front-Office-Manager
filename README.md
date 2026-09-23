# MLB Front Office Manager

A baseball analytics and business intelligence portfolio project that uses
public MLB data to support front-office-style roster analysis.

The project ingests player, team, schedule, and statistical data; transforms
it into analytics-ready tables; applies transparent roster-fit scoring; and
presents findings through SQL, Python, and Power BI.

> This is an independent educational portfolio project. It is not affiliated
> with, endorsed by, or connected to Major League Baseball or any MLB club.

## Business Problem

Baseball operations staff must evaluate player performance, roster needs,
team trends, and potential player fits using data that is often distributed
across multiple systems and reporting views.

This project demonstrates how an analytics solution can:

- Consolidate public baseball data into reusable analytical datasets
- Define consistent player and team performance metrics
- Identify roster strengths and needs by team and position group
- Score potential player fits using documented and explainable criteria
- Present insights in a dashboard-ready reporting model
- Validate data quality before analytical results are used

## Core Questions

- Which teams have the greatest need at each position group?
- Which players best fit a selected team's identified needs?
- Which players show the strongest year-over-year performance improvement?
- Which teams outperform or underperform based on offensive, pitching, and
  close-game indicators?
- Are player, team, and season-level statistics complete and internally
  consistent before reporting?

## Planned Features

- Python-based extraction of public MLB data
- Data transformation and standardization pipeline
- SQL analytics model with dimensions and fact tables
- Data quality checks and exception reporting
- Explainable roster-fit scoring methodology
- Power BI dashboard for team, player, and roster analysis
- Optional GitHub Pages project showcase

## Technology Stack

- Python
- pandas
- requests
- SQL
- Power BI Desktop
- GitHub and GitHub Desktop
- Public MLB data endpoints

## Repository Structure

```text
data/       Raw, processed, and sample datasets
docs/       Business requirements, architecture, data dictionary, and methodology
python/     Data extraction, transformation, scoring, and validation scripts
sql/        Database schema, transformations, quality checks, and reporting views
powerbi/    Dashboard documentation, measures, and screenshots
site/       Optional GitHub Pages project showcase
tests/      Automated validation tests
```

## Project Status

**Current phase:** Project setup and requirements definition.

## Author

Michael A. Whitney Jr.  
Data Analyst | Business Intelligence | SQL, Python, & Power BI Development