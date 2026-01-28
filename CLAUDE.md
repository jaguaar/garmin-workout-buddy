# Garmin Workout Uploader

This tool uploads structured workouts to Garmin Connect using JSON files.

## Environment Setup

Use the `connect` virtual environment for all commands:

```bash
# Activate the venv (Windows)
.\connect\Scripts\activate

# Or run directly with venv python
connect/Scripts/python.exe garmin_workout_uploader.py <command>
```

## Quick Commands

```bash
# Upload workout(s)
connect/Scripts/python.exe garmin_workout_uploader.py upload workouts/my_workout.json

# List existing workouts
python garmin_workout_uploader.py list

# Delete a workout
python garmin_workout_uploader.py delete <workout_id>

# Schedule to calendar
python garmin_workout_uploader.py schedule <workout_id> 2025-02-01
```

## Workflow for Creating Weekly Workouts

When the user asks for running/swimming workouts for the week:
1. Create JSON files in `workouts/` directory with descriptive names
2. Upload them using the CLI tool
3. Optionally schedule them to specific dates

**Important:** Skip warmup and cooldown steps unless the user explicitly requests them.

## JSON Format Reference

### Step DTO Types (REQUIRED)
Each step MUST have a `type` field:
| Step Kind | type |
|-----------|------|
| Regular steps (warmup, cooldown, interval, recovery, rest) | ExecutableStepDTO |
| Repeat groups | RepeatGroupDTO |

### Sport Types
| Sport | sportTypeId | sportTypeKey |
|-------|-------------|--------------|
| Running | 1 | running |
| Swimming | 5 | lap_swimming |

### Step Types
| Step | stepTypeId | stepTypeKey |
|------|------------|-------------|
| Warmup | 1 | warmup |
| Cooldown | 2 | cooldown |
| Interval | 3 | interval |
| Recovery | 4 | recovery |
| Rest | 5 | rest |
| Repeat | 6 | repeat |

### End Conditions
| Condition | conditionTypeId | conditionTypeKey | Value Unit |
|-----------|-----------------|------------------|------------|
| Lap Button | 1 | lap.button | - |
| Time | 2 | time | seconds |
| Distance | 3 | distance | meters |

### Target Types (Running)
| Target | workoutTargetTypeId | workoutTargetTypeKey |
|--------|---------------------|----------------------|
| No Target | 1 | no.target |
| Cadence | 3 | cadence.zone |
| Heart Rate Zone | 4 | heart.rate.zone |
| Pace Zone | 6 | pace.zone |

**Pace values are in meters per second (m/s)**, not seconds/km.

### Stroke Types (Swimming)
| Stroke | strokeTypeId | strokeTypeKey |
|--------|--------------|---------------|
| Backstroke | 1 | back |
| Breaststroke | 2 | breast |
| Butterfly | 3 | fly |
| Freestyle | 4 | free |
| Drill | 5 | drill |
| Mixed | 6 | mixed |

### Equipment Types (Swimming, optional)
| Equipment | equipmentTypeId | equipmentTypeKey |
|-----------|-----------------|------------------|
| None | 1 | none |
| Fins | 2 | fins |
| Kickboard | 3 | kickboard |
| Paddles | 4 | paddles |
| Pull Buoy | 5 | pull_buoy |

## Running Workout Template

```json
{
  "workoutName": "Workout Name",
  "sportType": {"sportTypeId": 1, "sportTypeKey": "running"},
  "workoutSegments": [{
    "segmentOrder": 1,
    "sportType": {"sportTypeId": 1, "sportTypeKey": "running"},
    "workoutSteps": [
      {
        "type": "ExecutableStepDTO",
        "stepOrder": 1,
        "stepType": {"stepTypeId": 1, "stepTypeKey": "warmup"},
        "endCondition": {"conditionTypeId": 2, "conditionTypeKey": "time"},
        "endConditionValue": 600
      },
      {
        "type": "RepeatGroupDTO",
        "stepOrder": 2,
        "stepType": {"stepTypeId": 6, "stepTypeKey": "repeat"},
        "numberOfIterations": 5,
        "workoutSteps": [
          {
            "type": "ExecutableStepDTO",
            "stepOrder": 1,
            "stepType": {"stepTypeId": 3, "stepTypeKey": "interval"},
            "endCondition": {"conditionTypeId": 3, "conditionTypeKey": "distance"},
            "endConditionValue": 800,
            "targetType": {"workoutTargetTypeId": 6, "workoutTargetTypeKey": "pace.zone"},
            "targetValueOne": 3.704,
            "targetValueTwo": 4.167
          },
          {
            "type": "ExecutableStepDTO",
            "stepOrder": 2,
            "stepType": {"stepTypeId": 4, "stepTypeKey": "recovery"},
            "endCondition": {"conditionTypeId": 2, "conditionTypeKey": "time"},
            "endConditionValue": 120
          }
        ]
      },
      {
        "type": "ExecutableStepDTO",
        "stepOrder": 3,
        "stepType": {"stepTypeId": 2, "stepTypeKey": "cooldown"},
        "endCondition": {"conditionTypeId": 1, "conditionTypeKey": "lap.button"}
      }
    ]
  }]
}
```

## Swimming Workout Template

```json
{
  "workoutName": "Workout Name",
  "sportType": {"sportTypeId": 5, "sportTypeKey": "lap_swimming"},
  "poolLength": 25,
  "poolLengthUnit": {"unitKey": "meter"},
  "workoutSegments": [{
    "segmentOrder": 1,
    "sportType": {"sportTypeId": 5, "sportTypeKey": "lap_swimming"},
    "workoutSteps": [
      {
        "type": "ExecutableStepDTO",
        "stepOrder": 1,
        "stepType": {"stepTypeId": 1, "stepTypeKey": "warmup"},
        "endCondition": {"conditionTypeId": 3, "conditionTypeKey": "distance"},
        "endConditionValue": 200,
        "strokeType": {"strokeTypeId": 4, "strokeTypeKey": "free"}
      },
      {
        "type": "RepeatGroupDTO",
        "stepOrder": 2,
        "stepType": {"stepTypeId": 6, "stepTypeKey": "repeat"},
        "numberOfIterations": 4,
        "workoutSteps": [
          {
            "type": "ExecutableStepDTO",
            "stepOrder": 1,
            "stepType": {"stepTypeId": 3, "stepTypeKey": "interval"},
            "endCondition": {"conditionTypeId": 3, "conditionTypeKey": "distance"},
            "endConditionValue": 100,
            "strokeType": {"strokeTypeId": 4, "strokeTypeKey": "free"}
          },
          {
            "type": "ExecutableStepDTO",
            "stepOrder": 2,
            "stepType": {"stepTypeId": 5, "stepTypeKey": "rest"},
            "endCondition": {"conditionTypeId": 2, "conditionTypeKey": "time"},
            "endConditionValue": 30
          }
        ]
      },
      {
        "type": "ExecutableStepDTO",
        "stepOrder": 3,
        "stepType": {"stepTypeId": 2, "stepTypeKey": "cooldown"},
        "endCondition": {"conditionTypeId": 3, "conditionTypeKey": "distance"},
        "endConditionValue": 100,
        "strokeType": {"strokeTypeId": 4, "strokeTypeKey": "free"}
      }
    ]
  }]
}
```

## Pace Conversion (min/km to m/s)

Formula: `m/s = 1000 / (minutes * 60 + seconds)`

| Pace | m/s |
|------|-----|
| 4:00/km | 4.167 |
| 4:30/km | 3.704 |
| 5:00/km | 3.333 |
| 5:30/km | 3.030 |
| 6:00/km | 2.778 |
| 6:30/km | 2.564 |
| 7:00/km | 2.381 |

For pace zones, `targetValueOne` is the slower pace (lower m/s) and `targetValueTwo` is the faster pace (higher m/s).

## Notes

- Every step MUST have a `type` field (ExecutableStepDTO or RepeatGroupDTO)
- Repeat groups use `numberOfIterations`, not `repeatValue`
- Pool length defaults to 25m; set to 50 for long course
- Time values are always in seconds
- Distance values are always in meters
- Repeat steps contain nested workoutSteps array
- stepOrder must be sequential within each level
