"""Core service layer for Garmin Connect operations.

This module provides data-returning functions without side effects like printing or sys.exit.
All functions return data structures or raise exceptions on failure.
"""

import json
from datetime import date
from pathlib import Path
from typing import Any, Optional

from garminconnect import Garmin
from garminconnect.exceptions import GarminConnectConnectionError

from .formatters import (
    format_activity_pace,
    format_activity_summary,
    format_distance,
    format_duration,
    format_step,
    format_swim_pace,
    format_workout_summary,
)


class GarminServiceError(Exception):
    """Base exception for Garmin service errors."""

    pass


class WorkoutNotFoundError(GarminServiceError):
    """Raised when a workout is not found."""

    pass


class ActivityNotFoundError(GarminServiceError):
    """Raised when an activity is not found."""

    pass


class WorkoutValidationError(GarminServiceError):
    """Raised when workout data is invalid."""

    pass


class GarminService:
    """Service layer for Garmin Connect operations."""

    def __init__(self, client: Garmin):
        """Initialize the service with an authenticated client.

        Args:
            client: Authenticated Garmin client
        """
        self.client = client

    # --- Workout Operations ---

    def list_workouts(self, limit: int = 20) -> list[dict]:
        """
        List existing workouts from Garmin Connect.

        Args:
            limit: Maximum number of workouts to retrieve

        Returns:
            List of workout summaries with id, name, and sport
        """
        workouts = self.client.get_workouts(0, limit)
        if not workouts:
            return []
        return [format_workout_summary(w) for w in workouts]

    def get_workout(self, workout_id: int) -> dict:
        """
        Fetch a workout's full details from Garmin Connect.

        Args:
            workout_id: The ID of the workout to fetch

        Returns:
            The workout data dictionary

        Raises:
            WorkoutNotFoundError: If workout doesn't exist
            GarminServiceError: If API request fails
        """
        try:
            return self.client.connectapi(f"/workout-service/workout/{workout_id}")
        except GarminConnectConnectionError as e:
            if "404" in str(e):
                raise WorkoutNotFoundError(f"Workout not found: {workout_id}") from e
            raise GarminServiceError(f"Error fetching workout: {e}") from e

    def get_workout_details(self, workout_id: int) -> dict[str, Any]:
        """
        Get workout details formatted for display.

        Args:
            workout_id: The ID of the workout to fetch

        Returns:
            Dictionary with workout details including formatted steps
        """
        workout = self.get_workout(workout_id)

        result = {
            "id": workout_id,
            "name": workout.get("workoutName", "Unnamed"),
            "sport": (workout.get("sportType") or {}).get("sportTypeKey", "unknown"),
            "steps": [],
        }

        # Swimming-specific
        pool_length = workout.get("poolLength")
        if pool_length:
            unit = (workout.get("poolLengthUnit") or {}).get("unitKey", "meter")
            result["poolLength"] = f"{pool_length}{unit[0]}"

        # Format steps
        segments = workout.get("workoutSegments", [])
        for segment in segments:
            steps = segment.get("workoutSteps", [])
            sorted_steps = sorted(steps, key=lambda s: s.get("stepOrder", 0))
            for step in sorted_steps:
                result["steps"].extend(format_step(step))

        return result

    def upload_workout(self, workout_data: dict) -> dict:
        """
        Upload a workout to Garmin Connect.

        Args:
            workout_data: The workout data dictionary

        Returns:
            The created workout data from Garmin

        Raises:
            WorkoutValidationError: If workout data is invalid
            GarminServiceError: If upload fails
        """
        if "workoutName" not in workout_data:
            raise WorkoutValidationError("Workout must contain 'workoutName' field")
        if "sportType" not in workout_data:
            raise WorkoutValidationError("Workout must contain 'sportType' field")

        try:
            return self.client.client.post("", "/workout-service/workout", json=workout_data, api=True)
        except GarminConnectConnectionError as e:
            raise GarminServiceError(f"Error uploading workout: {e}") from e

    def upload_workout_from_file(self, file_path: Path) -> dict:
        """
        Upload a workout from a JSON file.

        Args:
            file_path: Path to the workout JSON file

        Returns:
            The created workout data from Garmin

        Raises:
            FileNotFoundError: If file doesn't exist
            WorkoutValidationError: If workout data is invalid
            GarminServiceError: If upload fails
        """
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        with open(file_path, "r", encoding="utf-8") as f:
            workout_data = json.load(f)

        return self.upload_workout(workout_data)

    def delete_workout(self, workout_id: int) -> bool:
        """
        Delete a workout from Garmin Connect.

        Args:
            workout_id: The ID of the workout to delete

        Returns:
            True if deletion was successful

        Raises:
            WorkoutNotFoundError: If workout doesn't exist
            GarminServiceError: If deletion fails
        """
        try:
            self.client.client.delete("", f"/workout-service/workout/{workout_id}")
            return True
        except GarminConnectConnectionError as e:
            if "404" in str(e):
                raise WorkoutNotFoundError(f"Workout not found: {workout_id}") from e
            raise GarminServiceError(f"Error deleting workout: {e}") from e

    def schedule_workout(self, workout_id: int, date: str) -> bool:
        """
        Schedule a workout to the Garmin calendar.

        Args:
            workout_id: The ID of the workout to schedule
            date: The date in YYYY-MM-DD format

        Returns:
            True if scheduling was successful

        Raises:
            WorkoutNotFoundError: If workout doesn't exist
            GarminServiceError: If scheduling fails
        """
        try:
            self.client.client.post("", f"/workout-service/schedule/{workout_id}", json={"date": date})
            return True
        except GarminConnectConnectionError as e:
            if "404" in str(e):
                raise WorkoutNotFoundError(f"Workout not found: {workout_id}") from e
            raise GarminServiceError(f"Error scheduling workout: {e}") from e

    # --- Daily Status Operations ---

    def get_daily_status(self, date_str: Optional[str] = None) -> dict[str, Any]:
        """
        Get training readiness and fatigue status for a given date.

        Fetches multiple recovery metrics, each wrapped in try/except so one
        failing metric doesn't break the whole command.

        Args:
            date_str: Date in YYYY-MM-DD format (defaults to today)

        Returns:
            Dictionary with sections: training_readiness, body_battery, sleep,
            hrv, stress, resting_hr, training_status
        """
        if not date_str:
            date_str = date.today().isoformat()

        result: dict[str, Any] = {"date": date_str}

        # Training Readiness (API returns a list, first entry is most recent)
        try:
            data = self.client.get_training_readiness(date_str)
            if data:
                entry = data[0] if isinstance(data, list) else data
                result["training_readiness"] = {
                    "score": int(entry["score"]) if entry.get("score") is not None else None,
                    "level": (entry.get("level") or "").replace("_", " ").title() or None,
                }
            else:
                result["training_readiness"] = None
        except Exception:
            result["training_readiness"] = None

        # Body Battery (API returns a list wrapping a dict with bodyBatteryValuesArray)
        try:
            data = self.client.get_body_battery(date_str)
            current = None
            if data:
                day = data[0] if isinstance(data, list) else data
                entries = day.get("bodyBatteryValuesArray", []) if isinstance(day, dict) else []
                # Each entry is [timestamp, level]; get the most recent
                for entry in reversed(entries):
                    if isinstance(entry, (list, tuple)) and len(entry) >= 2 and entry[1] is not None and entry[1] > 0:
                        current = int(entry[1])
                        break
            result["body_battery"] = {"current": current}
        except Exception:
            result["body_battery"] = None

        # Sleep
        try:
            data = self.client.get_sleep_data(date_str)
            if data and data.get("dailySleepDTO"):
                sleep_dto = data["dailySleepDTO"]
                duration = sleep_dto.get("sleepTimeSeconds")
                result["sleep"] = {
                    "duration": duration,
                    "quality": sleep_dto.get("sleepQualityTypePK", "").replace("_", " ").title() if sleep_dto.get("sleepQualityTypePK") else None,
                    "deep": sleep_dto.get("deepSleepSeconds"),
                    "light": sleep_dto.get("lightSleepSeconds"),
                    "rem": sleep_dto.get("remSleepSeconds"),
                    "awake": sleep_dto.get("awakeSleepSeconds"),
                }
            else:
                result["sleep"] = None
        except Exception:
            result["sleep"] = None

        # HRV
        try:
            data = self.client.get_hrv_data(date_str)
            if data and data.get("hrvSummary"):
                summary = data["hrvSummary"]
                result["hrv"] = {
                    "weekly_avg": int(summary["weeklyAvg"]) if summary.get("weeklyAvg") is not None else None,
                    "last_night": int(summary["lastNight"]) if summary.get("lastNight") is not None else None,
                    "status": summary.get("status", "").replace("_", " ").title() if summary.get("status") else None,
                }
            else:
                result["hrv"] = None
        except Exception:
            result["hrv"] = None

        # Stress (uses avgStressLevel, not overallStressLevel)
        try:
            data = self.client.get_stress_data(date_str)
            if data:
                result["stress"] = {
                    "overall": int(data["avgStressLevel"]) if data.get("avgStressLevel") is not None else None,
                    "max": int(data["maxStressLevel"]) if data.get("maxStressLevel") is not None else None,
                }
            else:
                result["stress"] = None
        except Exception:
            result["stress"] = None

        # Resting HR (key is WELLNESS_RESTING_HEART_RATE)
        try:
            data = self.client.get_rhr_day(date_str)
            rhr_val = None
            if data and isinstance(data, dict):
                if data.get("allMetrics"):
                    for m in data["allMetrics"].get("metricsMap", {}).get("WELLNESS_RESTING_HEART_RATE", []):
                        if m.get("value"):
                            rhr_val = int(m["value"])
                            break
                if not rhr_val:
                    rhr_val = data.get("restingHeartRate") or data.get("value")
            result["resting_hr"] = {"value": int(rhr_val) if rhr_val else None}
        except Exception:
            result["resting_hr"] = None

        # Training Status (nested under mostRecentTrainingStatus)
        try:
            data = self.client.get_training_status(date_str)
            status_text = None
            if data and isinstance(data, dict):
                ts_data = data.get("mostRecentTrainingStatus")
                if ts_data:
                    status_text = ts_data.get("trainingStatusPhrase")
                if not status_text:
                    # Also check for trainingLoadBalance feedback
                    tlb = data.get("mostRecentTrainingLoadBalance", {})
                    for dev_data in tlb.get("metricsTrainingLoadBalanceDTOMap", {}).values():
                        status_text = dev_data.get("trainingBalanceFeedbackPhrase")
                        if status_text:
                            break
            result["training_status"] = {
                "status": status_text.replace("_", " ").title() if status_text else None,
            }
        except Exception:
            result["training_status"] = None

        return result

    # --- Activity Operations ---

    def list_activities(self, limit: int = 20, activity_type: Optional[str] = None) -> list[dict]:
        """
        List completed activities from Garmin Connect.

        Args:
            limit: Maximum number of activities to return
            activity_type: Filter by activity type (running, lap_swimming, etc.)

        Returns:
            List of activity summaries
        """
        if not activity_type:
            activities = self.client.get_activities(0, limit)
            if not activities:
                return []
            return [format_activity_summary(a) for a in activities]

        # Fetch in batches until we have enough of the specified type
        activities = []
        batch_size = 50
        offset = 0
        max_fetches = 20

        for _ in range(max_fetches):
            batch = self.client.get_activities(offset, batch_size)
            if not batch:
                break

            for a in batch:
                if a.get("activityType", {}).get("typeKey", "").lower() == activity_type.lower():
                    activities.append(a)
                    if len(activities) >= limit:
                        break

            if len(activities) >= limit:
                break

            offset += batch_size

        return [format_activity_summary(a) for a in activities]

    def get_activity(self, activity_id: int) -> dict:
        """
        Fetch an activity's details from Garmin Connect.

        Args:
            activity_id: The ID of the activity to fetch

        Returns:
            The activity data dictionary

        Raises:
            ActivityNotFoundError: If activity doesn't exist
        """
        try:
            return self.client.get_activity(activity_id)
        except Exception as e:
            raise ActivityNotFoundError(f"Activity not found: {activity_id}") from e

    def get_activity_splits(self, activity_id: int) -> Optional[dict]:
        """
        Fetch an activity's splits/laps data.

        Args:
            activity_id: The ID of the activity

        Returns:
            The splits data dictionary with lapDTOs, or None if unavailable
        """
        try:
            return self.client.get_activity_splits(activity_id)
        except Exception:
            return None

    def get_activity_details(self, activity_id: int) -> dict[str, Any]:
        """
        Get comprehensive activity details formatted for display.

        Args:
            activity_id: The ID of the activity to fetch

        Returns:
            Dictionary with all activity metrics and details
        """
        activity = self.get_activity(activity_id)
        summary = activity.get("summaryDTO", {})
        activity_type_dto = activity.get("activityTypeDTO", {})
        activity_type = activity_type_dto.get("typeKey", "unknown")
        is_swimming = "swim" in activity_type.lower()

        result = {
            "id": activity_id,
            "name": activity.get("activityName", "Unnamed"),
            "type": activity_type.replace("_", " ").title(),
            "location": activity.get("locationName"),
            "description": activity.get("description"),
        }

        # Date/Time
        start_time = summary.get("startTimeLocal", "Unknown")
        if start_time and start_time != "Unknown":
            result["date"] = start_time.replace("T", " ").split(".")[0][:-3]

        # Core metrics
        if summary.get("duration"):
            result["duration"] = format_duration(summary["duration"])
            if summary.get("movingDuration"):
                moving = summary["movingDuration"]
                if abs(moving - summary["duration"]) > 10:
                    result["movingDuration"] = format_duration(moving)

        if summary.get("distance"):
            result["distance"] = format_distance(summary["distance"])

            # Pace
            duration_secs = summary.get("duration", 0)
            distance_m = summary["distance"]
            if is_swimming:
                result["pace"] = format_swim_pace(duration_secs, distance_m)
            elif duration_secs:
                result["pace"] = format_activity_pace(duration_secs, distance_m)

        if summary.get("calories"):
            result["calories"] = int(summary["calories"])

        if summary.get("steps"):
            result["steps"] = int(summary["steps"])

        # Heart rate
        hr = {}
        if summary.get("averageHR"):
            hr["average"] = int(summary["averageHR"])
        if summary.get("maxHR"):
            hr["max"] = int(summary["maxHR"])
        if summary.get("minHR"):
            hr["min"] = int(summary["minHR"])
        if summary.get("recoveryHeartRate"):
            hr["recovery"] = int(summary["recoveryHeartRate"])
        if hr:
            result["heartRate"] = hr

        # Running dynamics
        dynamics = {}
        if summary.get("averageRunCadence"):
            dynamics["cadence"] = int(summary["averageRunCadence"])
            if summary.get("maxRunCadence"):
                dynamics["maxCadence"] = int(summary["maxRunCadence"])
        if summary.get("strideLength"):
            dynamics["strideLength"] = round(summary["strideLength"] / 100, 2)
        if summary.get("groundContactTime"):
            dynamics["groundContactTime"] = int(summary["groundContactTime"])
        if summary.get("verticalOscillation"):
            dynamics["verticalOscillation"] = round(summary["verticalOscillation"], 1)
        if summary.get("verticalRatio"):
            dynamics["verticalRatio"] = round(summary["verticalRatio"], 1)
        if dynamics:
            result["runningDynamics"] = dynamics

        # Power
        power = {}
        if summary.get("averagePower"):
            power["average"] = int(summary["averagePower"])
        if summary.get("normalizedPower"):
            power["normalized"] = int(summary["normalizedPower"])
        if summary.get("maxPower"):
            power["max"] = int(summary["maxPower"])
        if power:
            result["power"] = power

        # Swimming metrics
        if is_swimming:
            swim = {}
            if summary.get("poolLength"):
                swim["poolLength"] = int(summary["poolLength"])
            if summary.get("numberOfActiveLengths"):
                swim["lengths"] = summary["numberOfActiveLengths"]
            if summary.get("averageStrokes"):
                swim["avgStrokesPerLength"] = round(summary["averageStrokes"], 1)
            if summary.get("averageSWOLF"):
                swim["avgSwolf"] = int(summary["averageSWOLF"])
            if swim:
                result["swimming"] = swim

            # Fetch intervals
            splits = self.get_activity_splits(activity_id)
            if splits and splits.get("lapDTOs"):
                intervals = self._format_swim_intervals(splits["lapDTOs"])
                if intervals:
                    result["intervals"] = intervals

        # Elevation
        elevation = {}
        if summary.get("elevationGain"):
            elevation["gain"] = int(summary["elevationGain"])
        if summary.get("elevationLoss"):
            elevation["loss"] = int(summary["elevationLoss"])
        if summary.get("minElevation") is not None and summary.get("maxElevation") is not None:
            elevation["min"] = int(summary["minElevation"])
            elevation["max"] = int(summary["maxElevation"])
        if elevation:
            result["elevation"] = elevation

        # Training effect
        training = {}
        if summary.get("trainingEffect"):
            training["aerobicTE"] = round(summary["trainingEffect"], 1)
            if summary.get("trainingEffectLabel"):
                training["label"] = summary["trainingEffectLabel"].replace("_", " ").title()
        if summary.get("anaerobicTrainingEffect"):
            training["anaerobicTE"] = round(summary["anaerobicTrainingEffect"], 1)
        if summary.get("activityTrainingLoad"):
            training["load"] = int(summary["activityTrainingLoad"])
        if training:
            result["trainingEffect"] = training

        return result

    def get_running_splits(self, activity_id: int) -> list[dict]:
        """
        Fetch and format per-km split data for a running activity.

        Args:
            activity_id: The ID of the activity

        Returns:
            List of split dicts with distance, time, pace, HR, and elevation

        Raises:
            ActivityNotFoundError: If activity doesn't exist
            GarminServiceError: If splits are unavailable
        """
        splits_data = self.get_activity_splits(activity_id)
        if not splits_data:
            raise GarminServiceError("No split data available for this activity")

        laps = splits_data.get("lapDTOs", [])
        if not laps:
            raise GarminServiceError("No lap data found in splits")

        result = []
        for i, lap in enumerate(laps, 1):
            dist = lap.get("distance", 0)
            dur = lap.get("duration", 0)

            split: dict[str, Any] = {"split": i}

            if dist:
                split["distance"] = format_distance(dist)
            if dur:
                split["time"] = format_duration(dur)
            if dur and dist:
                split["pace"] = format_activity_pace(dur, dist)

            hr: dict[str, int] = {}
            if lap.get("averageHR"):
                hr["average"] = int(lap["averageHR"])
            if lap.get("maxHR"):
                hr["max"] = int(lap["maxHR"])
            if hr:
                split["heartRate"] = hr

            elev: dict[str, int] = {}
            if lap.get("elevationGain"):
                elev["gain"] = int(lap["elevationGain"])
            if lap.get("elevationLoss"):
                elev["loss"] = int(lap["elevationLoss"])
            if elev:
                split["elevation"] = elev

            result.append(split)

        return result

    def _format_swim_intervals(self, laps: list[dict]) -> list[dict]:
        """Format swim lap data into interval summaries."""
        intervals = []

        for lap in laps:
            dist = lap.get("distance", 0)
            dur = lap.get("duration", 0)

            if dist > 0:
                # Swim interval
                interval = {
                    "type": "swim",
                    "distance": format_distance(dist),
                    "duration": format_duration(dur),
                    "lengths": lap.get("numberOfActiveLengths", 0),
                }

                if dur and dist:
                    interval["pace"] = format_swim_pace(dur, dist)

                if lap.get("averageStrokes"):
                    interval["strokesPerLength"] = round(lap["averageStrokes"], 1)

                if lap.get("averageSWOLF"):
                    interval["swolf"] = int(lap["averageSWOLF"])

                if lap.get("averageHR"):
                    interval["avgHR"] = int(lap["averageHR"])
                if lap.get("maxHR"):
                    interval["maxHR"] = int(lap["maxHR"])

                # Detect stroke type
                length_dtos = lap.get("lengthDTOs", [])
                if length_dtos:
                    strokes = set(l.get("swimStroke", "").lower() for l in length_dtos if l.get("swimStroke"))
                    if len(strokes) == 1:
                        interval["stroke"] = strokes.pop()

                intervals.append(interval)

            elif dur > 5:
                # Rest interval (skip very short ones)
                rest = {
                    "type": "rest",
                    "duration": format_duration(dur),
                }
                if lap.get("averageHR"):
                    rest["avgHR"] = int(lap["averageHR"])
                intervals.append(rest)

        return intervals
