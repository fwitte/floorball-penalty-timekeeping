from dataclasses import dataclass

ALL_EVENTS = {
    0: {
        "display": "goal",
        "duration": "NaN",
        "can_terminate_penalty": True,
    },
    1: {
        "display": "goal by penalty shot",
        "duration": "NaN",
        "can_terminate_penalty": False,
    },
    2: {
        "display": "minor penalty (2')",
        "duration": 120,
    },
    4: {
        "display": "major penalty (2'+2')",
        "replace_by": 2,
    },
    3: {
        "display": "personal penalty (10')",
        "duration": 600,
        "adds": 2
    },
    5: {
        "display": "personal penalty (match penalty)",
        "duration": "NaN",
        "adds": 3
    },
}
GOAL_EVENTS = {event: ALL_EVENTS[event] for event in ALL_EVENTS if event <= 1}
PENALTY_EVENTS = {event: ALL_EVENTS[event] for event in ALL_EVENTS if event > 1}
NUM_PLAYERS = {"KF": 4, "GF": 6}
MINIMUM_NUM_PLAYERS = {"KF": 3, "GF": 4}
RINK = "GF"


def seconds_to_mmss(seconds):
    minutes = seconds // 60
    seconds = seconds % 60
    return f'{minutes:02}:{seconds:02}'


def prepare_events(events):
    events.columns = [col.lower() for col in events.columns]
    ordered_events = events.sort_values(by=["minutes", "seconds", "event"])
    ordered_events = ordered_events.reset_index()
    ordered_events["seconds"] = ordered_events["minutes"] * 60 + ordered_events["seconds"]
    return ordered_events.drop(columns="minutes")


@dataclass
class Event:
    team: str
    player: str
    event: int
    minutes: int
    seconds: int

    def validate(self) -> dict[str, str]:
        result = {}
        for key, value in self.__dict__.items():
            if isinstance(self.__dict__[key], str):
                if value == "":
                    result[key] = f"{key} must not be empty"
        return result

_FORM_COMPONENT_KEY="dc_form_component"
_FORM_VALIDATION_KEY="dc_form_validation"