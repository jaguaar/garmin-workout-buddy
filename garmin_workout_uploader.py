#!/usr/bin/env python3
"""
Garmin Connect Workout Uploader

Upload structured workouts (running, swimming) to Garmin Connect using JSON files.
Uses OAuth authentication via the garminconnect library.
"""

import argparse
import json
import sys
from pathlib import Path

from garminconnect import Garmin


# Default token storage directory
TOKEN_DIR = Path(__file__).parent / ".garth"


def get_client() -> Garmin:
    """
    Get an authenticated Garmin Connect client.

    Attempts to resume from saved session tokens. If no valid session exists,
    prompts for credentials and saves the new session.
    """
    TOKEN_DIR.mkdir(exist_ok=True)
    token_path = str(TOKEN_DIR)

    client = Garmin()

    try:
        client.login(token_path)
        print("Authenticated using saved session.")
    except Exception:
        print("No valid session found. Please enter your Garmin Connect credentials.")
        email = input("Email: ")
        password = input("Password: ")

        try:
            client = Garmin(email, password)
            client.login()
            client.garth.dump(token_path)
            print("Login successful. Session saved.")
        except Exception as e:
            print(f"Authentication failed: {e}")
            sys.exit(1)

    return client


def upload_workout(client: Garmin, json_path: Path) -> dict:
    """
    Upload a workout from a JSON file to Garmin Connect.

    Args:
        client: Authenticated Garmin client
        json_path: Path to the workout JSON file

    Returns:
        The created workout data from Garmin
    """
    if not json_path.exists():
        print(f"Error: File not found: {json_path}")
        sys.exit(1)

    with open(json_path, "r", encoding="utf-8") as f:
        workout_data = json.load(f)

    if "workoutName" not in workout_data:
        print("Error: Workout JSON must contain 'workoutName' field")
        sys.exit(1)
    if "sportType" not in workout_data:
        print("Error: Workout JSON must contain 'sportType' field")
        sys.exit(1)

    # Upload using connectapi with OAuth header
    headers = {
        "Authorization": str(client.garth.oauth2_token),
        "Content-Type": "application/json",
        "NK": "NT",
    }
    url = "https://connectapi.garmin.com/workout-service/workout"
    response = client.garth.sess.post(url, json=workout_data, headers=headers)

    if response.status_code != 200:
        print(f"Error uploading workout: {response.status_code}")
        print(response.text)
        sys.exit(1)

    result = response.json()
    workout_id = result.get("workoutId")
    workout_name = result.get("workoutName")
    print(f"Uploaded workout: {workout_name} (ID: {workout_id})")
    return result


def list_workouts(client: Garmin, limit: int = 20) -> list:
    """
    List existing workouts from Garmin Connect.

    Args:
        client: Authenticated Garmin client
        limit: Maximum number of workouts to retrieve

    Returns:
        List of workout summaries
    """
    workouts = client.get_workouts(0, limit)

    if not workouts:
        print("No workouts found.")
        return []

    print(f"Found {len(workouts)} workout(s):\n")
    for workout in workouts:
        sport_type = workout.get("sportType", {}).get("sportTypeKey", "unknown")
        print(f"  ID: {workout.get('workoutId')}")
        print(f"  Name: {workout.get('workoutName')}")
        print(f"  Sport: {sport_type}")
        print()
    return workouts


def delete_workout(client: Garmin, workout_id: int) -> None:
    """
    Delete a workout from Garmin Connect.

    Args:
        client: Authenticated Garmin client
        workout_id: The ID of the workout to delete
    """
    headers = {
        "Authorization": str(client.garth.oauth2_token),
        "NK": "NT",
    }
    url = f"https://connectapi.garmin.com/workout-service/workout/{workout_id}"
    response = client.garth.sess.delete(url, headers=headers)

    if response.status_code == 204:
        print(f"Deleted workout ID: {workout_id}")
    elif response.status_code == 404:
        print(f"Workout not found: {workout_id}")
        sys.exit(1)
    else:
        print(f"Error deleting workout: {response.status_code}")
        print(response.text)
        sys.exit(1)


def schedule_workout(client: Garmin, workout_id: int, date: str) -> None:
    """
    Schedule a workout to the Garmin calendar.

    Args:
        client: Authenticated Garmin client
        workout_id: The ID of the workout to schedule
        date: The date in YYYY-MM-DD format
    """
    headers = {
        "Authorization": str(client.garth.oauth2_token),
        "Content-Type": "application/json",
        "NK": "NT",
    }
    url = f"https://connectapi.garmin.com/workout-service/schedule/{workout_id}"
    response = client.garth.sess.post(url, json={"date": date}, headers=headers)

    if response.status_code == 200:
        print(f"Scheduled workout {workout_id} for {date}")
    elif response.status_code == 404:
        print(f"Workout not found: {workout_id}")
        sys.exit(1)
    else:
        print(f"Error scheduling workout: {response.status_code}")
        print(response.text)
        sys.exit(1)


def get_workout(client: Garmin, workout_id: int) -> dict:
    """
    Fetch a workout's full details from Garmin Connect.

    Args:
        client: Authenticated Garmin client
        workout_id: The ID of the workout to fetch

    Returns:
        The workout data dictionary
    """
    headers = {
        "Authorization": str(client.garth.oauth2_token),
        "NK": "NT",
    }
    url = f"https://connectapi.garmin.com/workout-service/workout/{workout_id}"
    response = client.garth.sess.get(url, headers=headers)

    if response.status_code == 200:
        return response.json()
    elif response.status_code == 404:
        print(f"Workout not found: {workout_id}")
        sys.exit(1)
    else:
        print(f"Error fetching workout: {response.status_code}")
        print(response.text)
        sys.exit(1)


def format_duration(seconds: float) -> str:
    """Format seconds into a readable duration string."""
    if seconds < 60:
        return f"{int(seconds)}s"
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    if secs == 0:
        return f"{minutes}min"
    return f"{minutes}min {secs}s"


def format_distance(meters: float) -> str:
    """Format meters into a readable distance string."""
    if meters >= 1000:
        km = meters / 1000
        if km == int(km):
            return f"{int(km)}km"
        return f"{km:.1f}km"
    return f"{int(meters)}m"


def format_pace(ms: float) -> str:
    """Convert m/s to min/km pace string."""
    if ms <= 0:
        return "N/A"
    secs_per_km = 1000 / ms
    minutes = int(secs_per_km // 60)
    seconds = int(secs_per_km % 60)
    return f"{minutes}:{seconds:02d}/km"


def format_end_condition(step: dict) -> str:
    """Format the end condition of a step."""
    condition = step.get("endCondition") or {}
    condition_key = condition.get("conditionTypeKey", "")
    value = step.get("endConditionValue")

    if condition_key == "lap.button":
        return "Lap button"
    elif condition_key == "time" and value:
        return format_duration(value)
    elif condition_key == "distance" and value:
        return format_distance(value)
    return condition_key or "Unknown"


def format_target(step: dict) -> str:
    """Format the target of a step (pace, HR, cadence)."""
    target = step.get("targetType") or {}
    target_key = target.get("workoutTargetTypeKey", "")

    if target_key == "no.target" or not target_key:
        return ""

    val1 = step.get("targetValueOne")
    val2 = step.get("targetValueTwo")

    if target_key == "pace.zone" and val1 and val2:
        slow_pace = format_pace(val1)
        fast_pace = format_pace(val2)
        return f"Pace: {slow_pace} - {fast_pace}"
    elif target_key == "heart.rate.zone" and val1 and val2:
        return f"HR: {int(val1)}-{int(val2)} bpm"
    elif target_key == "cadence.zone" and val1 and val2:
        return f"Cadence: {int(val1)}-{int(val2)} spm"

    return ""


def format_step(step: dict, indent: int = 0) -> list[str]:
    """Format a workout step into lines of text."""
    lines = []
    prefix = "  " * indent

    step_type = (step.get("stepType") or {}).get("stepTypeKey", "step")
    step_type_display = step_type.capitalize()

    # Handle repeat groups
    if step.get("type") == "RepeatGroupDTO" or step_type == "repeat":
        iterations = step.get("numberOfIterations", 1)
        lines.append(f"{prefix}Repeat {iterations}x:")
        nested_steps = step.get("workoutSteps", [])
        for nested in sorted(nested_steps, key=lambda s: s.get("stepOrder", 0)):
            lines.extend(format_step(nested, indent + 1))
        return lines

    # Regular step
    end_cond = format_end_condition(step)
    target = format_target(step)

    # Swimming stroke
    stroke = (step.get("strokeType") or {}).get("strokeTypeKey", "")
    stroke_str = f" ({stroke})" if stroke else ""

    # Equipment
    equipment = (step.get("equipmentType") or {}).get("equipmentTypeKey", "")
    equip_str = f" [+{equipment}]" if equipment and equipment != "none" else ""

    line = f"{prefix}{step_type_display}: {end_cond}{stroke_str}{equip_str}"
    if target:
        line += f" @ {target}"
    lines.append(line)

    return lines


def list_activities(client: Garmin, limit: int = 20, activity_type: str = None) -> list:
    """
    List completed activities from Garmin Connect.

    Args:
        client: Authenticated Garmin client
        limit: Maximum number of activities to retrieve
        activity_type: Filter by activity type (running, swimming, etc.)

    Returns:
        List of activity summaries
    """
    activities = client.get_activities(0, limit)

    if not activities:
        print("No activities found.")
        return []

    # Filter by activity type if specified
    if activity_type:
        activities = [
            a for a in activities
            if a.get("activityType", {}).get("typeKey", "").lower() == activity_type.lower()
        ]

    if not activities:
        print(f"No {activity_type} activities found.")
        return []

    print(f"Found {len(activities)} activity(ies):\n")
    for activity in activities:
        activity_id = activity.get("activityId")
        name = activity.get("activityName", "Unnamed")
        activity_type_name = activity.get("activityType", {}).get("typeKey", "unknown")
        start_time = activity.get("startTimeLocal", "")[:10]  # Just the date

        # Duration
        duration_secs = activity.get("duration", 0)
        duration_str = format_duration(duration_secs) if duration_secs else "N/A"

        # Distance
        distance_m = activity.get("distance", 0)
        distance_str = format_distance(distance_m) if distance_m else "N/A"

        print(f"  ID: {activity_id}")
        print(f"  Name: {name}")
        print(f"  Type: {activity_type_name}")
        print(f"  Date: {start_time}")
        print(f"  Duration: {duration_str}")
        print(f"  Distance: {distance_str}")
        print()

    return activities


def get_activity(client: Garmin, activity_id: int) -> dict:
    """
    Fetch an activity's details from Garmin Connect.

    Args:
        client: Authenticated Garmin client
        activity_id: The ID of the activity to fetch

    Returns:
        The activity data dictionary
    """
    try:
        return client.get_activity(activity_id)
    except Exception as e:
        print(f"Error fetching activity: {e}")
        sys.exit(1)


def format_activity_pace(duration_secs: float, distance_m: float) -> str:
    """Calculate and format pace from duration and distance."""
    if not duration_secs or not distance_m:
        return "N/A"
    secs_per_km = duration_secs / (distance_m / 1000)
    minutes = int(secs_per_km // 60)
    seconds = int(secs_per_km % 60)
    return f"{minutes}:{seconds:02d}/km"


def format_speed_as_pace(speed_mps: float) -> str:
    """Convert m/s speed to min/km pace string."""
    if not speed_mps or speed_mps <= 0:
        return "N/A"
    secs_per_km = 1000 / speed_mps
    minutes = int(secs_per_km // 60)
    seconds = int(secs_per_km % 60)
    return f"{minutes}:{seconds:02d}/km"


def format_swim_pace(duration_secs: float, distance_m: float) -> str:
    """Calculate and format swimming pace (per 100m)."""
    if not duration_secs or not distance_m:
        return "N/A"
    secs_per_100m = duration_secs / (distance_m / 100)
    minutes = int(secs_per_100m // 60)
    seconds = int(secs_per_100m % 60)
    return f"{minutes}:{seconds:02d}/100m"


def show_activity(client: Garmin, activity_id: int) -> None:
    """
    Fetch and display an activity's details.

    Args:
        client: Authenticated Garmin client
        activity_id: The ID of the activity to display
    """
    activity = get_activity(client, activity_id)

    # Extract nested objects
    summary = activity.get("summaryDTO", {})
    activity_type_dto = activity.get("activityTypeDTO", {})
    metadata = activity.get("metadataDTO", {})

    # Header
    name = activity.get("activityName", "Unnamed")
    activity_type = activity_type_dto.get("typeKey", "unknown")
    is_swimming = "swim" in activity_type.lower()
    is_running = "running" in activity_type.lower() or "run" in activity_type.lower()

    location = activity.get("locationName", "")

    print(f"\n{name}")
    print("=" * len(name))
    print(f"Type: {activity_type.replace('_', ' ').title()}")
    if location:
        print(f"Location: {location}")
    print(f"ID: {activity_id}")

    # Date/Time
    start_time = summary.get("startTimeLocal", "Unknown")
    if start_time and start_time != "Unknown":
        # Format: "2026-01-28T11:43:19.0" -> "2026-01-28 11:43"
        start_time = start_time.replace("T", " ").split(".")[0][:-3]
    print(f"Date: {start_time}")

    # Description
    description = activity.get("description")
    if description:
        print(f"Notes: {description}")

    print()

    # --- Core Metrics ---
    print("Core Metrics")
    print("-" * 40)

    # Duration (moving vs elapsed)
    duration_secs = summary.get("duration", 0)
    moving_duration = summary.get("movingDuration")
    if duration_secs:
        duration_str = format_duration(duration_secs)
        if moving_duration and abs(moving_duration - duration_secs) > 10:
            duration_str += f" (moving: {format_duration(moving_duration)})"
        print(f"Duration: {duration_str}")

    # Distance
    distance_m = summary.get("distance", 0)
    if distance_m:
        print(f"Distance: {format_distance(distance_m)}")

    # Pace/Speed
    if is_swimming and distance_m and duration_secs:
        print(f"Avg Pace: {format_swim_pace(duration_secs, distance_m)}")
    elif distance_m and duration_secs:
        avg_pace = format_activity_pace(duration_secs, distance_m)
        max_speed = summary.get("maxSpeed")
        if max_speed:
            print(f"Pace: {avg_pace} (best: {format_speed_as_pace(max_speed)})")
        else:
            print(f"Avg Pace: {avg_pace}")

    # Calories
    calories = summary.get("calories")
    if calories:
        print(f"Calories: {int(calories)} kcal")

    # Steps
    steps = summary.get("steps")
    if steps:
        print(f"Steps: {int(steps):,}")

    # --- Heart Rate ---
    avg_hr = summary.get("averageHR")
    max_hr = summary.get("maxHR")
    min_hr = summary.get("minHR")
    if avg_hr or max_hr:
        print()
        print("Heart Rate")
        print("-" * 40)
        if avg_hr:
            print(f"Average: {int(avg_hr)} bpm")
        if max_hr:
            print(f"Max: {int(max_hr)} bpm")
        if min_hr:
            print(f"Min: {int(min_hr)} bpm")

        # Recovery HR
        recovery_hr = summary.get("recoveryHeartRate")
        if recovery_hr:
            print(f"Recovery: -{int(recovery_hr)} bpm (1 min)")

    # --- Running Dynamics ---
    avg_cadence = summary.get("averageRunCadence")
    max_cadence = summary.get("maxRunCadence")
    avg_stride = summary.get("strideLength")
    avg_ground_contact = summary.get("groundContactTime")
    avg_vertical_osc = summary.get("verticalOscillation")
    avg_vertical_ratio = summary.get("verticalRatio")
    gc_balance = summary.get("groundContactBalanceLeft")

    if any([avg_cadence, avg_stride, avg_ground_contact]):
        print()
        print("Running Dynamics")
        print("-" * 40)
        if avg_cadence:
            cadence_str = f"{int(avg_cadence)} spm"
            if max_cadence:
                cadence_str += f" (max: {int(max_cadence)})"
            print(f"Cadence: {cadence_str}")
        if avg_stride:
            # strideLength is in cm, convert to m
            print(f"Stride Length: {avg_stride / 100:.2f}m")
        if avg_ground_contact:
            gc_str = f"{int(avg_ground_contact)}ms"
            if gc_balance:
                gc_str += f" (L/R: {gc_balance:.1f}%/{100-gc_balance:.1f}%)"
            print(f"Ground Contact: {gc_str}")
        if avg_vertical_osc:
            print(f"Vertical Oscillation: {avg_vertical_osc:.1f}cm")
        if avg_vertical_ratio:
            print(f"Vertical Ratio: {avg_vertical_ratio:.1f}%")

    # --- Power (Running) ---
    avg_power = summary.get("averagePower")
    max_power = summary.get("maxPower")
    norm_power = summary.get("normalizedPower")

    if avg_power:
        print()
        print("Power")
        print("-" * 40)
        print(f"Average: {int(avg_power)}W")
        if norm_power:
            print(f"Normalized: {int(norm_power)}W")
        if max_power:
            print(f"Max: {int(max_power)}W")

    # --- Swimming Metrics ---
    if is_swimming:
        pool_length = summary.get("poolLength")
        avg_strokes = summary.get("avgStrokes")
        avg_swolf = summary.get("avgSwolf")
        num_lengths = summary.get("numberOfActiveLengths")

        if any([pool_length, avg_strokes, avg_swolf]):
            print()
            print("Swimming Metrics")
            print("-" * 40)
            if pool_length:
                print(f"Pool Length: {int(pool_length)}m")
            if num_lengths:
                print(f"Lengths: {num_lengths}")
            if avg_strokes:
                print(f"Avg Strokes/Length: {avg_strokes:.1f}")
            if avg_swolf:
                print(f"Avg SWOLF: {int(avg_swolf)}")

    # --- Elevation ---
    elev_gain = summary.get("elevationGain")
    elev_loss = summary.get("elevationLoss")
    min_elev = summary.get("minElevation")
    max_elev = summary.get("maxElevation")

    if any([elev_gain, elev_loss]):
        print()
        print("Elevation")
        print("-" * 40)
        if elev_gain:
            print(f"Gain: +{int(elev_gain)}m")
        if elev_loss:
            print(f"Loss: -{int(elev_loss)}m")
        if min_elev is not None and max_elev is not None:
            print(f"Range: {int(min_elev)}m - {int(max_elev)}m")

    # --- Training Effect ---
    aerobic_te = summary.get("trainingEffect")
    anaerobic_te = summary.get("anaerobicTrainingEffect")
    training_load = summary.get("activityTrainingLoad")
    te_label = summary.get("trainingEffectLabel")

    if any([aerobic_te, anaerobic_te, training_load]):
        print()
        print("Training Effect")
        print("-" * 40)
        if aerobic_te:
            te_str = f"{aerobic_te:.1f}"
            if te_label:
                te_str += f" ({te_label.replace('_', ' ').title()})"
            print(f"Aerobic TE: {te_str}")
        if anaerobic_te:
            print(f"Anaerobic TE: {anaerobic_te:.1f}")
        if training_load:
            print(f"Training Load: {int(training_load)}")

    # --- Workout Compliance ---
    compliance = summary.get("directWorkoutComplianceScore")
    rpe = summary.get("directWorkoutRpe")
    feel = summary.get("directWorkoutFeel")

    if compliance:
        print()
        print("Workout Feedback")
        print("-" * 40)
        print(f"Compliance: {int(compliance)}%")
        if rpe:
            print(f"Perceived Effort: {int(rpe)}%")
        if feel:
            print(f"Feel: {int(feel)}%")

    # --- Conditions ---
    min_temp = summary.get("minTemperature")
    max_temp = summary.get("maxTemperature")
    if min_temp is not None or max_temp is not None:
        print()
        print("Conditions")
        print("-" * 40)
        if min_temp is not None:
            print(f"Temperature: {int(min_temp)}°C")

    # --- Intensity Minutes ---
    moderate_mins = summary.get("moderateIntensityMinutes")
    vigorous_mins = summary.get("vigorousIntensityMinutes")
    if moderate_mins or vigorous_mins:
        print()
        print("Intensity")
        print("-" * 40)
        if vigorous_mins:
            print(f"Vigorous: {int(vigorous_mins)} min")
        if moderate_mins:
            print(f"Moderate: {int(moderate_mins)} min")

    print()


def show_workout(client: Garmin, workout_id: int) -> None:
    """
    Fetch and display a workout's details.

    Args:
        client: Authenticated Garmin client
        workout_id: The ID of the workout to display
    """
    workout = get_workout(client, workout_id)

    # Header
    name = workout.get("workoutName", "Unnamed")
    sport = (workout.get("sportType") or {}).get("sportTypeKey", "unknown")
    print(f"\n{name}")
    print("=" * len(name))
    print(f"Sport: {sport.replace('_', ' ').title()}")
    print(f"ID: {workout_id}")

    # Swimming-specific
    pool_length = workout.get("poolLength")
    if pool_length:
        unit = (workout.get("poolLengthUnit") or {}).get("unitKey", "meter")
        print(f"Pool: {pool_length}{unit[0]}")

    print()

    # Steps
    segments = workout.get("workoutSegments", [])
    for segment in segments:
        steps = segment.get("workoutSteps", [])
        sorted_steps = sorted(steps, key=lambda s: s.get("stepOrder", 0))
        for step in sorted_steps:
            for line in format_step(step):
                print(line)

    print()


def main():
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
        "-n", "--limit",
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

    # Activities command (list completed activities)
    activities_parser = subparsers.add_parser("activities", help="List completed activities")
    activities_parser.add_argument(
        "-n", "--limit",
        type=int,
        default=20,
        help="Maximum number of activities to list (default: 20)",
    )
    activities_parser.add_argument(
        "-t", "--type",
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

    client = get_client()

    if args.command == "upload":
        for file_path in args.files:
            upload_workout(client, file_path)
    elif args.command == "list":
        list_workouts(client, limit=args.limit)
    elif args.command == "show":
        show_workout(client, args.workout_id)
    elif args.command == "delete":
        delete_workout(client, args.workout_id)
    elif args.command == "schedule":
        schedule_workout(client, args.workout_id, args.date)
    elif args.command == "activities":
        list_activities(client, limit=args.limit, activity_type=args.activity_type)
    elif args.command == "activity":
        if args.json:
            activity = get_activity(client, args.activity_id)
            print(json.dumps(activity, indent=2))
        else:
            show_activity(client, args.activity_id)


if __name__ == "__main__":
    main()
