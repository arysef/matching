import argparse
import csv
import datetime
from collections import defaultdict
from dataclasses import dataclass, field
from typing import List, Optional, Set

try:
    from tabulate import tabulate  # type: ignore
except ImportError:  # pragma: no cover - optional dependency
    tabulate = None


day_names = {
    'monday': 'Monday',
    'tuesday': 'Tuesday',
    'wednesday': 'Wednesday',
    'thursday': 'Thursday',
    'friday': 'Friday',
    'saturday': 'Saturday',
    'sunday': 'Sunday',
}


def parse_bool(value: str) -> Optional[bool]:
    if value is None:
        return None
    value = value.strip().lower()
    if not value:
        return None
    if value in {"y", "yes", "true", "1"}:
        return True
    if value in {"n", "no", "false", "0"}:
        return False
    return None


def parse_days(value: str) -> Set[str]:
    if not value:
        return set()
    days = set()
    for part in value.split("|"):
        d = part.strip().lower()
        if d:
            days.add(d)
    return days


@dataclass
class Participant:
    name: str
    preferred_school: Optional[bool]
    preferred_days: Set[str]
    distance: Optional[float]
    country: Optional[str]
    gender: Optional[str]
    assignments: List["Event"] = field(default_factory=list)


@dataclass
class Event:
    name: str
    date: datetime.date
    location: str
    capacity: int
    school_event: Optional[bool]
    assignments: List[Participant] = field(default_factory=list)


def read_participants(path: str) -> List[Participant]:
    participants = []
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            participant = Participant(
                name=row.get("name", "").strip(),
                preferred_school=parse_bool(row.get("preferred_school")),
                preferred_days=parse_days(row.get("preferred_days", "")),
                distance=float(row["distance"]) if row.get("distance") else None,
                country=row.get("country") or None,
                gender=(row.get("gender") or "").strip().upper() or None,
            )
            participants.append(participant)
    return participants


def read_events(path: str) -> List[Event]:
    events = []
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            date = datetime.datetime.fromisoformat(row["date"]).date()
            event = Event(
                name=row.get("name", "").strip(),
                date=date,
                location=row.get("location", ""),
                capacity=int(row.get("capacity", 0)),
                school_event=parse_bool(row.get("school_event")),
            )
            events.append(event)
    return events


def days_between(d1: datetime.date, d2: datetime.date) -> int:
    return abs((d1 - d2).days)


def gender_diff(gender_counts: defaultdict, gender: str) -> int:
    counts = gender_counts.copy()
    if gender:
        counts[gender] += 1
    return abs(counts.get("M", 0) - counts.get("F", 0))


def candidate_key(participant: Participant, event: Event,
                   country_counts: defaultdict, gender_counts: defaultdict):
    school_score = 0
    if participant.preferred_school is not None and event.school_event is not None:
        if participant.preferred_school != event.school_event:
            school_score = 1
    day = event.date.strftime("%A").lower()
    day_score = 0
    if participant.preferred_days and day not in participant.preferred_days:
        day_score = 1
    distance_score = participant.distance if participant.distance is not None else 0.0
    country_score = country_counts.get(participant.country, 0)
    gender_score = gender_diff(gender_counts, participant.gender)
    return (school_score, day_score, distance_score, country_score, gender_score)


def assign_events(participants: List[Participant], events: List[Event]):
    for event in events:
        country_counts = defaultdict(int)
        gender_counts = defaultdict(int)
        for _ in range(event.capacity):
            candidates = [p for p in participants
                          if len(p.assignments) < 2
                          and all(days_between(event.date, e.date) >= 30 for e in p.assignments)]
            if not candidates:
                break
            candidates.sort(key=lambda p: candidate_key(p, event, country_counts, gender_counts))
            chosen = candidates[0]
            event.assignments.append(chosen)
            chosen.assignments.append(event)
            if chosen.country:
                country_counts[chosen.country] += 1
            if chosen.gender:
                gender_counts[chosen.gender] += 1


def output_assignments(events: List[Event], path: Optional[str] = None) -> None:
    if path:
        if path.endswith('.csv'):
            with open(path, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['event', 'date', 'location', 'participant'])
                for event in events:
                    for p in event.assignments:
                        writer.writerow([event.name, event.date.isoformat(), event.location, p.name])
            return
        if path.endswith('.html'):
            with open(path, 'w') as f:
                f.write('<html><body>\n')
                for event in events:
                    f.write(f'<h2>{event.name} ({event.date}) at {event.location}</h2>\n<ul>')
                    for p in event.assignments:
                        f.write(f'<li>{p.name}</li>')
                    f.write('</ul>\n')
                f.write('</body></html>')
            return

    for event in events:
        print(f"Event: {event.name} ({event.date}) at {event.location}")
        rows = [[p.name, p.country or '', p.gender or ''] for p in event.assignments]
        if tabulate:
            print(tabulate(rows, headers=['Participant', 'Country', 'Gender']))
        else:
            for r in rows:
                print(f"  - {r[0]} ({r[1]} {r[2]})")
        print()


def filter_participants(participants: List[Participant], gender=None, country=None,
                        day=None, school=None, max_distance=None) -> List[Participant]:
    day = day.lower() if day else None
    result = []
    for p in participants:
        if gender and (p.gender or "").upper() != gender.upper():
            continue
        if country and (p.country or "").lower() != country.lower():
            continue
        if day and p.preferred_days and day not in p.preferred_days:
            continue
        if school is not None and p.preferred_school is not None and p.preferred_school != school:
            continue
        if max_distance is not None and p.distance is not None and p.distance > max_distance:
            continue
        result.append(p)
    return result


def main():
    parser = argparse.ArgumentParser(description="Assign participants to events")
    subparsers = parser.add_subparsers(dest="command", required=True)

    assign_parser = subparsers.add_parser("assign", help="Assign people to events")
    assign_parser.add_argument("participants")
    assign_parser.add_argument("events")
    assign_parser.add_argument("--output", help="Write assignments to file (CSV or HTML)")

    filter_parser = subparsers.add_parser("filter", help="Filter participants")
    filter_parser.add_argument("participants")
    filter_parser.add_argument("--gender")
    filter_parser.add_argument("--country")
    filter_parser.add_argument("--day")
    filter_parser.add_argument("--school", choices=["Y", "N"])
    filter_parser.add_argument("--max-distance", type=float)

    args = parser.parse_args()

    if args.command == "assign":
        participants = read_participants(args.participants)
        events = read_events(args.events)
        assign_events(participants, events)
        output_assignments(events, path=args.output)
    elif args.command == "filter":
        participants = read_participants(args.participants)
        school = None
        if args.school:
            school = args.school.upper() == "Y"
        filtered = filter_participants(participants, gender=args.gender,
                                       country=args.country, day=args.day,
                                       school=school, max_distance=args.max_distance)
        for p in filtered:
            print(p.name)


if __name__ == "__main__":
    main()
