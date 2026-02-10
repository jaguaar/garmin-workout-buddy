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


def _readiness_label(score: int) -> str:
    """Get a label for a training readiness score."""
    if score >= 80:
        return "Excellent"
    elif score >= 60:
        return "Good"
    elif score >= 40:
        return "Fair"
    elif score >= 20:
        return "Low"
    return "Poor"


def _stress_label(score: int) -> str:
    """Get a label for a stress score."""
    if score <= 25:
        return "Rest"
    elif score <= 50:
        return "Low"
    elif score <= 75:
        return "Medium"
    return "High"


def _format_sleep_duration(seconds: float) -> str:
    """Format sleep duration as Xh Ym."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    if hours > 0:
        return f"{hours}h {minutes:02d}m"
    return f"{minutes}m"


def format_status_report(status: dict) -> str:
    """Format the daily status dict into a readable CLI report."""
    lines = []

    # Training Readiness
    tr = status.get("training_readiness")
    if tr and tr.get("score") is not None:
        score = tr["score"]
        label = tr.get("level") or _readiness_label(score)
        lines.append(f"Training Readiness: {score}/100 ({label})")
    else:
        lines.append("Training Readiness: N/A")

    # Body Battery
    bb = status.get("body_battery")
    if bb and bb.get("current") is not None:
        lines.append(f"Body Battery:       {bb['current']}/100")
    else:
        lines.append("Body Battery:       N/A")

    # Training Status
    ts = status.get("training_status")
    if ts and ts.get("status"):
        lines.append(f"Training Status:    {ts['status']}")
    else:
        lines.append("Training Status:    N/A")

    lines.append("")

    # Sleep
    sl = status.get("sleep")
    if sl and sl.get("duration") is not None:
        dur_str = _format_sleep_duration(sl["duration"])
        quality = f" ({sl['quality']})" if sl.get("quality") else ""
        lines.append(f"Sleep:              {dur_str}{quality}")
        stages = []
        if sl.get("deep") is not None:
            stages.append(f"Deep: {_format_sleep_duration(sl['deep'])}")
        if sl.get("light") is not None:
            stages.append(f"Light: {_format_sleep_duration(sl['light'])}")
        if sl.get("rem") is not None:
            stages.append(f"REM: {_format_sleep_duration(sl['rem'])}")
        if sl.get("awake") is not None:
            stages.append(f"Awake: {_format_sleep_duration(sl['awake'])}")
        if stages:
            lines.append(f"  {' | '.join(stages)}")
    else:
        lines.append("Sleep:              N/A")

    lines.append("")

    # HRV
    hrv = status.get("hrv")
    if hrv and hrv.get("weekly_avg") is not None:
        label = f" ({hrv['status']})" if hrv.get("status") else ""
        lines.append(f"HRV:                {hrv['weekly_avg']}ms{label}")
    else:
        lines.append("HRV:                N/A")

    # Resting HR
    rhr = status.get("resting_hr")
    if rhr and rhr.get("value") is not None:
        lines.append(f"Resting HR:         {rhr['value']} bpm")
    else:
        lines.append("Resting HR:         N/A")

    # Stress
    st = status.get("stress")
    if st and st.get("overall") is not None:
        label = _stress_label(st["overall"])
        lines.append(f"Stress:             {st['overall']} ({label})")
    else:
        lines.append("Stress:             N/A")

    return "\n".join(lines)
