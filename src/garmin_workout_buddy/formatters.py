"""Formatting utilities for displaying workout and activity data."""

from typing import Any


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


def format_workout_summary(workout: dict) -> dict[str, Any]:
    """Format a workout into a summary dictionary."""
    return {
        "id": workout.get("workoutId"),
        "name": workout.get("workoutName"),
        "sport": workout.get("sportType", {}).get("sportTypeKey", "unknown"),
    }


def format_activity_summary(activity: dict) -> dict[str, Any]:
    """Format an activity into a summary dictionary."""
    return {
        "id": activity.get("activityId"),
        "name": activity.get("activityName", "Unnamed"),
        "type": activity.get("activityType", {}).get("typeKey", "unknown"),
        "date": activity.get("startTimeLocal", "")[:10],
        "duration": format_duration(activity.get("duration", 0)) if activity.get("duration") else None,
        "distance": format_distance(activity.get("distance", 0)) if activity.get("distance") else None,
    }
