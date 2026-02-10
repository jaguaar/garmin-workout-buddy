"""Command-line interface for Garmin Workout Buddy."""

import argparse
import json
import sys
from pathlib import Path

from .auth import AuthenticationError, get_client
from .formatters import (
    format_activity_pace,
    format_distance,
    format_duration,
    format_speed_as_pace,
    format_status_report,
    format_step,
    format_swim_pace,
)
from .service import (
    ActivityNotFoundError,
    GarminService,
    GarminServiceError,
    WorkoutNotFoundError,
)


def print_error(message: str) -> None:
    """Print an error message and exit."""
    print(f"Error: {message}", file=sys.stderr)
    sys.exit(1)


def cmd_upload(service: GarminService, args: argparse.Namespace) -> None:
    """Handle the upload command."""
    for file_path in args.files:
        try:
            result = service.upload_workout_from_file(file_path)
            print(f"Uploaded workout: {result.get('workoutName')} (ID: {result.get('workoutId')})")
        except FileNotFoundError as e:
            print_error(str(e))
        except GarminServiceError as e:
            print_error(str(e))


def cmd_list(service: GarminService, args: argparse.Namespace) -> None:
    """Handle the list command."""
    workouts = service.list_workouts(limit=args.limit)

    if not workouts:
        print("No workouts found.")
        return

    print(f"Found {len(workouts)} workout(s):\n")
    for workout in workouts:
        print(f"  ID: {workout['id']}")
        print(f"  Name: {workout['name']}")
        print(f"  Sport: {workout['sport']}")
        print()


def cmd_show(service: GarminService, args: argparse.Namespace) -> None:
    """Handle the show command."""
    try:
        details = service.get_workout_details(args.workout_id)

        print(f"\n{details['name']}")
        print("=" * len(details["name"]))
        print(f"Sport: {details['sport'].replace('_', ' ').title()}")
        print(f"ID: {details['id']}")

        if details.get("poolLength"):
            print(f"Pool: {details['poolLength']}")

        print()
        for line in details["steps"]:
            print(line)
        print()

    except WorkoutNotFoundError as e:
        print_error(str(e))


def cmd_delete(service: GarminService, args: argparse.Namespace) -> None:
    """Handle the delete command."""
    try:
        service.delete_workout(args.workout_id)
        print(f"Deleted workout ID: {args.workout_id}")
    except WorkoutNotFoundError as e:
        print_error(str(e))
    except GarminServiceError as e:
        print_error(str(e))


def cmd_schedule(service: GarminService, args: argparse.Namespace) -> None:
    """Handle the schedule command."""
    try:
        service.schedule_workout(args.workout_id, args.date)
        print(f"Scheduled workout {args.workout_id} for {args.date}")
    except WorkoutNotFoundError as e:
        print_error(str(e))
    except GarminServiceError as e:
        print_error(str(e))


def cmd_activities(service: GarminService, args: argparse.Namespace) -> None:
    """Handle the activities command."""
    activities = service.list_activities(limit=args.limit, activity_type=args.activity_type)

    if not activities:
        msg = "No activities found."
        if args.activity_type:
            msg = f"No {args.activity_type} activities found."
        print(msg)
        return

    print(f"Found {len(activities)} activity(ies):\n")
    for activity in activities:
        print(f"  ID: {activity['id']}")
        print(f"  Name: {activity['name']}")
        print(f"  Type: {activity['type']}")
        print(f"  Date: {activity['date']}")
        if activity.get("duration"):
            print(f"  Duration: {activity['duration']}")
        if activity.get("distance"):
            print(f"  Distance: {activity['distance']}")
        print()


def cmd_status(service: GarminService, args: argparse.Namespace) -> None:
    """Handle the status command."""
    status = service.get_daily_status(date_str=args.date)
    print(f"\nDaily Status ({status['date']})")
    print("=" * 40)
    print(format_status_report(status))
    print()


def cmd_activity(service: GarminService, args: argparse.Namespace) -> None:
    """Handle the activity command."""
    try:
        if args.json:
            # Raw JSON output
            activity = service.get_activity(args.activity_id)
            print(json.dumps(activity, indent=2))
            return

        details = service.get_activity_details(args.activity_id)

        # Header
        print(f"\n{details['name']}")
        print("=" * len(details["name"]))
        print(f"Type: {details['type']}")
        if details.get("location"):
            print(f"Location: {details['location']}")
        print(f"ID: {details['id']}")
        if details.get("date"):
            print(f"Date: {details['date']}")
        if details.get("description"):
            print(f"Notes: {details['description']}")

        print()

        # Core Metrics
        print("Core Metrics")
        print("-" * 40)

        if details.get("duration"):
            dur_str = details["duration"]
            if details.get("movingDuration"):
                dur_str += f" (moving: {details['movingDuration']})"
            print(f"Duration: {dur_str}")

        if details.get("distance"):
            print(f"Distance: {details['distance']}")

        if details.get("pace"):
            print(f"Pace: {details['pace']}")

        if details.get("calories"):
            print(f"Calories: {details['calories']} kcal")

        if details.get("steps"):
            print(f"Steps: {details['steps']:,}")

        # Heart Rate
        hr = details.get("heartRate", {})
        if hr:
            print()
            print("Heart Rate")
            print("-" * 40)
            if hr.get("average"):
                print(f"Average: {hr['average']} bpm")
            if hr.get("max"):
                print(f"Max: {hr['max']} bpm")
            if hr.get("min"):
                print(f"Min: {hr['min']} bpm")
            if hr.get("recovery"):
                print(f"Recovery: -{hr['recovery']} bpm (1 min)")

        # Running Dynamics
        dynamics = details.get("runningDynamics", {})
        if dynamics:
            print()
            print("Running Dynamics")
            print("-" * 40)
            if dynamics.get("cadence"):
                cad_str = f"{dynamics['cadence']} spm"
                if dynamics.get("maxCadence"):
                    cad_str += f" (max: {dynamics['maxCadence']})"
                print(f"Cadence: {cad_str}")
            if dynamics.get("strideLength"):
                print(f"Stride Length: {dynamics['strideLength']}m")
            if dynamics.get("groundContactTime"):
                print(f"Ground Contact: {dynamics['groundContactTime']}ms")
            if dynamics.get("verticalOscillation"):
                print(f"Vertical Oscillation: {dynamics['verticalOscillation']}cm")
            if dynamics.get("verticalRatio"):
                print(f"Vertical Ratio: {dynamics['verticalRatio']}%")

        # Power
        power = details.get("power", {})
        if power:
            print()
            print("Power")
            print("-" * 40)
            if power.get("average"):
                print(f"Average: {power['average']}W")
            if power.get("normalized"):
                print(f"Normalized: {power['normalized']}W")
            if power.get("max"):
                print(f"Max: {power['max']}W")

        # Swimming Metrics
        swim = details.get("swimming", {})
        if swim:
            print()
            print("Swimming Metrics")
            print("-" * 40)
            if swim.get("poolLength"):
                print(f"Pool Length: {swim['poolLength']}m")
            if swim.get("lengths"):
                print(f"Lengths: {swim['lengths']}")
            if swim.get("avgStrokesPerLength"):
                print(f"Avg Strokes/Length: {swim['avgStrokesPerLength']}")
            if swim.get("avgSwolf"):
                print(f"Avg SWOLF: {swim['avgSwolf']}")

        # Swimming Intervals
        intervals = details.get("intervals", [])
        if intervals:
            swim_count = len([i for i in intervals if i["type"] == "swim"])
            rest_count = len([i for i in intervals if i["type"] == "rest"])
            print()
            print(f"Intervals ({swim_count} swim, {rest_count} rest)")
            print("-" * 40)

            swim_num = 0
            for interval in intervals:
                if interval["type"] == "swim":
                    swim_num += 1
                    line = f"  {swim_num}. {interval['distance']} ({interval['lengths']} lengths)"
                    line += f" - {interval['duration']} @ {interval.get('pace', 'N/A')}"
                    if interval.get("stroke"):
                        line += f" [{interval['stroke']}]"
                    print(line)

                    metrics = []
                    if interval.get("strokesPerLength"):
                        metrics.append(f"{interval['strokesPerLength']} str/len")
                    if interval.get("swolf"):
                        metrics.append(f"SWOLF {interval['swolf']}")
                    if interval.get("avgHR"):
                        hr_str = f"HR {interval['avgHR']}"
                        if interval.get("maxHR") and interval["maxHR"] != interval["avgHR"]:
                            hr_str += f"/{interval['maxHR']}"
                        metrics.append(hr_str)
                    if metrics:
                        print(f"     {', '.join(metrics)}")

                elif interval["type"] == "rest":
                    rest_line = f"     ~ Rest: {interval['duration']}"
                    if interval.get("avgHR"):
                        rest_line += f" (HR {interval['avgHR']})"
                    print(rest_line)

        # Elevation
        elevation = details.get("elevation", {})
        if elevation:
            print()
            print("Elevation")
            print("-" * 40)
            if elevation.get("gain"):
                print(f"Gain: +{elevation['gain']}m")
            if elevation.get("loss"):
                print(f"Loss: -{elevation['loss']}m")
            if elevation.get("min") is not None and elevation.get("max") is not None:
                print(f"Range: {elevation['min']}m - {elevation['max']}m")

        # Training Effect
        training = details.get("trainingEffect", {})
        if training:
            print()
            print("Training Effect")
            print("-" * 40)
            if training.get("aerobicTE"):
                te_str = f"{training['aerobicTE']}"
                if training.get("label"):
                    te_str += f" ({training['label']})"
                print(f"Aerobic TE: {te_str}")
            if training.get("anaerobicTE"):
                print(f"Anaerobic TE: {training['anaerobicTE']}")
            if training.get("load"):
                print(f"Training Load: {training['load']}")

        print()

    except ActivityNotFoundError as e:
        print_error(str(e))


def main():
    """Main entry point for the CLI."""
    parser = argparse.ArgumentParser(
        description="Upload structured workouts to Garmin Connect",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s upload workout.json          Upload a single workout
  %(prog)s upload workouts/*.json       Upload multiple workouts
  %(prog)s list                         List existing workouts
  %(prog)s show 12345                   Show workout details
  %(prog)s delete 12345                 Delete workout by ID
  %(prog)s schedule 12345 2025-02-01    Schedule workout to date
  %(prog)s status                       Show training readiness & fatigue
  %(prog)s status --date 2026-02-09    Status for a specific date
  %(prog)s activities                   List recent completed activities
  %(prog)s activities -t running        List recent running activities
  %(prog)s activity 12345               Show activity details
        """,
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    # Upload command
    upload_parser = subparsers.add_parser("upload", help="Upload workout(s) from JSON file(s)")
    upload_parser.add_argument(
        "files",
        nargs="+",
        type=Path,
        help="Path(s) to workout JSON file(s)",
    )

    # List command
    list_parser = subparsers.add_parser("list", help="List existing workouts")
    list_parser.add_argument(
        "-n",
        "--limit",
        type=int,
        default=20,
        help="Maximum number of workouts to list (default: 20)",
    )

    # Show command
    show_parser = subparsers.add_parser("show", help="Show workout details")
    show_parser.add_argument(
        "workout_id",
        type=int,
        help="The workout ID to display",
    )

    # Delete command
    delete_parser = subparsers.add_parser("delete", help="Delete a workout by ID")
    delete_parser.add_argument(
        "workout_id",
        type=int,
        help="The workout ID to delete",
    )

    # Schedule command
    schedule_parser = subparsers.add_parser("schedule", help="Schedule a workout to calendar")
    schedule_parser.add_argument(
        "workout_id",
        type=int,
        help="The workout ID to schedule",
    )
    schedule_parser.add_argument(
        "date",
        help="Date in YYYY-MM-DD format",
    )

    # Status command (training readiness & fatigue)
    status_parser = subparsers.add_parser("status", help="Show training readiness & fatigue status")
    status_parser.add_argument(
        "--date",
        default=None,
        help="Date in YYYY-MM-DD format (default: today)",
    )

    # Activities command (list completed activities)
    activities_parser = subparsers.add_parser("activities", help="List completed activities")
    activities_parser.add_argument(
        "-n",
        "--limit",
        type=int,
        default=20,
        help="Number of activities to list (default: 20)",
    )
    activities_parser.add_argument(
        "-t",
        "--type",
        dest="activity_type",
        help="Filter by activity type (e.g., running, lap_swimming, cycling)",
    )

    # Activity command (show single activity details)
    activity_parser = subparsers.add_parser("activity", help="Show activity details")
    activity_parser.add_argument(
        "activity_id",
        type=int,
        help="The activity ID to display",
    )
    activity_parser.add_argument(
        "--json",
        action="store_true",
        help="Output raw JSON response",
    )

    args = parser.parse_args()

    # Authenticate
    try:
        client = get_client(interactive=True)
        print("Authenticated using saved session.")
    except AuthenticationError as e:
        print_error(str(e))

    service = GarminService(client)

    # Dispatch command
    if args.command == "upload":
        cmd_upload(service, args)
    elif args.command == "list":
        cmd_list(service, args)
    elif args.command == "show":
        cmd_show(service, args)
    elif args.command == "delete":
        cmd_delete(service, args)
    elif args.command == "schedule":
        cmd_schedule(service, args)
    elif args.command == "status":
        cmd_status(service, args)
    elif args.command == "activities":
        cmd_activities(service, args)
    elif args.command == "activity":
        cmd_activity(service, args)


if __name__ == "__main__":
    main()
