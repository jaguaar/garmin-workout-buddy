# Garmin Workout Uploader

This tool uploads structured workouts to Garmin Connect using JSON files.

## Environment Setup

Use the `connect` virtual environment for all commands:

```bash
# macOS/Linux
source connect/bin/activate
connect/bin/python garmin_workout_uploader.py <command>

# Windows
.\connect\Scripts\activate
connect\Scripts\python.exe garmin_workout_uploader.py <command>
```

**Note:** Commands below use `python` assuming venv is activated. Replace with full path if not.

## Quick Commands

```bash
# Upload workout(s)
python garmin_workout_uploader.py upload workouts/my_workout.json
python garmin_workout_uploader.py upload workouts/*.json  # Multiple files

# List existing workouts
python garmin_workout_uploader.py list
python garmin_workout_uploader.py list -n 50  # Show 50 workouts

# Show workout details (formatted view of steps)
python garmin_workout_uploader.py show <workout_id>

# Delete a workout
python garmin_workout_uploader.py delete <workout_id>

# Schedule to calendar
python garmin_workout_uploader.py schedule <workout_id> 2025-02-01

# List completed activities
python garmin_workout_uploader.py activities
python garmin_workout_uploader.py activities -n 30           # Show 30 activities
python garmin_workout_uploader.py activities -t running      # Filter by type
python garmin_workout_uploader.py activities -t lap_swimming # Swimming activities

# Show activity details (duration, pace, HR, training effect, intervals, etc.)
python garmin_workout_uploader.py activity <activity_id>
python garmin_workout_uploader.py activity <activity_id> --json  # Raw JSON output
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

## Authentication

The script uses OAuth via the `garminconnect` library:
- Tokens are stored in `.garth/` directory
- First run prompts for email/password
- MFA is supported (will prompt for code if enabled)
- Subsequent runs reuse saved tokens automatically

## Activity Metrics Displayed

The `activity` command shows comprehensive metrics:

| Category | Metrics |
|----------|---------|
| Core | Duration (total/moving), distance, pace/speed, calories, steps |
| Heart Rate | Average, max, min, recovery HR |
| Running Dynamics | Cadence, stride length, ground contact time, vertical oscillation, vertical ratio |
| Power | Average, normalized, max power |
| Swimming | Pool length, lengths, strokes/length, SWOLF, **intervals with rest periods** |
| Elevation | Gain, loss, min/max elevation |
| Training Effect | Aerobic TE, anaerobic TE, training load |
| Workout Feedback | Compliance score, perceived effort, feel |
| Conditions | Temperature |
| Intensity | Vigorous/moderate intensity minutes |

## Swimming Activity Intervals

For swimming activities, the `activity` command fetches detailed interval/lap data using `client.get_activity_splits()` and displays:

**Per swim interval:**
- Distance and number of lengths
- Duration and pace (per 100m)
- Stroke type (freestyle, backstroke, etc.)
- Strokes per length
- SWOLF score
- Heart rate (avg/max)

**Rest periods between intervals:**
- Duration
- Average HR during recovery

**Example output:**
```
Intervals (6 swim, 6 rest)
----------------------------------------
  1. 100m (4 lengths) - 2min @ 2:00/100m [freestyle]
     12.3 str/len, SWOLF 42, HR 127/139
     ~ Rest: 1min 28s (HR 109)
  2. 400m (16 lengths) - 8min 25s @ 2:06/100m [freestyle]
     12.2 str/len, SWOLF 44, HR 134/153
     ~ Rest: 1min 51s (HR 122)
```

**API data structure** (from `get_activity_splits`):
- `lapDTOs[]` - array of laps/intervals
  - `distance` - meters (0 for rest intervals)
  - `duration` - seconds
  - `averageStrokes` - strokes per length
  - `averageSWOLF` - SWOLF score
  - `averageHR`, `maxHR` - heart rate
  - `numberOfActiveLengths` - pool lengths in this interval
  - `lengthDTOs[]` - individual pool lengths with `swimStroke` type

## Activity Types for Filtering

Common values for `activities -t <type>`:
- `running`
- `lap_swimming`
- `cycling`
- `walking`
- `hiking`
- `strength_training`

## Garmin Connect API Methods

The `garminconnect` library provides these useful activity methods:

| Method | Description |
|--------|-------------|
| `get_activity(id)` | Basic activity data (summary, metadata) |
| `get_activity_splits(id)` | Lap/interval data with `lapDTOs` array |
| `get_activity_details(id)` | Detailed metrics and charts |
| `get_activity_hr_in_timezones(id)` | Heart rate zone distribution |
| `get_activity_weather(id)` | Weather conditions during activity |
| `get_activity_gear(id)` | Equipment used |
| `get_activities(start, limit)` | List activities with pagination |

**Workout methods:**
| Method | Description |
|--------|-------------|
| `get_workouts(start, limit)` | List saved workouts |
| Custom API call to `workout-service/workout` | Create/update workouts |
| Custom API call to `workout-service/schedule` | Schedule workout to calendar |
