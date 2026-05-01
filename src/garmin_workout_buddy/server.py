"""FastMCP server exposing Garmin Connect operations as MCP tools."""

import json
from typing import Optional

from mcp.server.fastmcp import FastMCP

from .auth import AuthenticationError, get_client
from .service import (
    ActivityNotFoundError,
    GarminService,
    GarminServiceError,
    WorkoutNotFoundError,
    WorkoutValidationError,
)

# Create the MCP server
mcp = FastMCP(
    "Garmin Workout Buddy",
    instructions="Upload and manage structured workouts on Garmin Connect",
)

# Cache the service instance
_service: Optional[GarminService] = None


def get_service() -> GarminService:
    """Get or create the Garmin service instance."""
    global _service
    if _service is None:
        try:
            client = get_client(interactive=False)
            _service = GarminService(client)
        except AuthenticationError as e:
            raise RuntimeError(str(e))
    return _service


@mcp.tool()
def list_workouts(limit: int = 20) -> str:
    """
    List saved workouts from Garmin Connect.

    Args:
        limit: Maximum number of workouts to retrieve (default: 20)

    Returns:
        JSON array of workout summaries with id, name, and sport type
    """
    try:
        service = get_service()
        workouts = service.list_workouts(limit=limit)
        return json.dumps(workouts, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def get_workout(workout_id: int) -> str:
    """
    Get detailed information about a specific workout.

    Args:
        workout_id: The Garmin workout ID

    Returns:
        JSON object with workout details including formatted steps
    """
    try:
        service = get_service()
        details = service.get_workout_details(workout_id)
        return json.dumps(details, indent=2)
    except WorkoutNotFoundError as e:
        return json.dumps({"error": str(e)})
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def upload_workout(workout_json: str) -> str:
    """
    Upload a structured workout to Garmin Connect.

    Args:
        workout_json: JSON string containing the workout definition.
                     Must include 'workoutName' and 'sportType' fields.

    Returns:
        JSON object with the created workout ID and name
    """
    try:
        service = get_service()
        workout_data = json.loads(workout_json)
        result = service.upload_workout(workout_data)
        return json.dumps(
            {
                "success": True,
                "workoutId": result.get("workoutId"),
                "workoutName": result.get("workoutName"),
            }
        )
    except json.JSONDecodeError as e:
        return json.dumps({"error": f"Invalid JSON: {e}"})
    except WorkoutValidationError as e:
        return json.dumps({"error": str(e)})
    except GarminServiceError as e:
        return json.dumps({"error": str(e)})
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def delete_workout(workout_id: int) -> str:
    """
    Delete a workout from Garmin Connect.

    Args:
        workout_id: The Garmin workout ID to delete

    Returns:
        JSON object indicating success or error
    """
    try:
        service = get_service()
        service.delete_workout(workout_id)
        return json.dumps({"success": True, "deleted": workout_id})
    except WorkoutNotFoundError as e:
        return json.dumps({"error": str(e)})
    except GarminServiceError as e:
        return json.dumps({"error": str(e)})
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def schedule_workout(workout_id: int, date: str) -> str:
    """
    Schedule a workout to a specific date on the Garmin calendar.

    Args:
        workout_id: The Garmin workout ID to schedule
        date: Date in YYYY-MM-DD format

    Returns:
        JSON object indicating success or error
    """
    try:
        service = get_service()
        service.schedule_workout(workout_id, date)
        return json.dumps({"success": True, "workoutId": workout_id, "scheduledDate": date})
    except WorkoutNotFoundError as e:
        return json.dumps({"error": str(e)})
    except GarminServiceError as e:
        return json.dumps({"error": str(e)})
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def list_activities(limit: int = 20, activity_type: Optional[str] = None) -> str:
    """
    List completed activities from Garmin Connect.

    Args:
        limit: Maximum number of activities to return (default: 20)
        activity_type: Filter by type (e.g., 'running', 'lap_swimming', 'cycling')

    Returns:
        JSON array of activity summaries with id, name, type, date, duration, distance
    """
    try:
        service = get_service()
        activities = service.list_activities(limit=limit, activity_type=activity_type)
        return json.dumps(activities, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def get_activity(activity_id: int) -> str:
    """
    Get detailed information about a specific activity.

    Includes comprehensive metrics: duration, distance, pace, heart rate,
    running dynamics, power, elevation, training effect, and for swimming
    activities, interval/lap details.

    Args:
        activity_id: The Garmin activity ID

    Returns:
        JSON object with all activity details and metrics
    """
    try:
        service = get_service()
        details = service.get_activity_details(activity_id)
        return json.dumps(details, indent=2)
    except ActivityNotFoundError as e:
        return json.dumps({"error": str(e)})
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def get_splits(activity_id: int) -> str:
    """
    Get per-km split data for a running activity.

    Returns distance, time, pace, heart rate, and elevation for each km split.

    Args:
        activity_id: The Garmin activity ID

    Returns:
        JSON array of split objects, one per km
    """
    try:
        service = get_service()
        splits = service.get_running_splits(activity_id)
        return json.dumps(splits, indent=2)
    except ActivityNotFoundError as e:
        return json.dumps({"error": str(e)})
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def get_status(date: Optional[str] = None) -> str:
    """
    Get training readiness and fatigue status for a date.

    Returns body battery, training readiness, sleep quality, HRV, stress,
    resting heart rate, and training status in a single overview.

    Args:
        date: Date in YYYY-MM-DD format (default: today)

    Returns:
        JSON object with training readiness, body battery, sleep, HRV, stress,
        resting HR, and training status
    """
    try:
        service = get_service()
        status = service.get_daily_status(date_str=date)
        return json.dumps(status, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


def main():
    """Run the MCP server."""
    mcp.run()


if __name__ == "__main__":
    main()
