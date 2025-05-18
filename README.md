# Matching Script

This repository contains a simple Python script for assigning participants to events based on several preferences.

## Usage

Prepare two CSV files:

- `participants.csv` with columns:
  - `name`
  - `preferred_school` (Y/N or blank)
  - `preferred_days` (pipe-separated days, e.g. `Mon|Wed`)
  - `distance` (numeric, distance from workplace to event location)
  - `country`
  - `gender`

- `events.csv` with columns:
  - `name`
  - `date` (YYYY-MM-DD)
  - `location`
  - `capacity` (number of participants needed)
  - `school_event` (Y/N or blank)

Run the script to assign people to events:

```bash
python assign_events.py assign participants.csv events.csv --output assignments.html
```
The `--output` option can save the assignments to a CSV or HTML file for easier viewing.

To filter participants by certain criteria:

```bash
python assign_events.py filter participants.csv --gender F --country "United States" --day Wednesday
```

## Requirements

The script only depends on the optional `tabulate` package for nicer console output. Install it with:

```bash
pip install -r requirements.txt
```
