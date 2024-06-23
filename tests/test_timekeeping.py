import os

import numpy as np
import pytest

from floorball_penalty_timekeeping.io import events_from_json
from floorball_penalty_timekeeping.timekeeping import timekeeping
from floorball_penalty_timekeeping.utils import prepare_events

__testpath__ = os.path.dirname(os.path.abspath(__file__))


def load_penalty_timekeeping_events(name):
    path = os.path.join(__testpath__, "data", "datasets.json")
    return events_from_json(path, name)


@pytest.fixture
def penalty_times_by_team(name):
    events = load_penalty_timekeeping_events(name)
    events_prepared = prepare_events(events)
    return timekeeping(events_prepared)


def test_event_preprocessing():
    penalty_timekeeping_events = load_penalty_timekeeping_events("test_terminate_running_minor_penalty")
    events = prepare_events(penalty_timekeeping_events)
    np.testing.assert_array_almost_equal(
        events["seconds"],
        penalty_timekeeping_events["seconds"]
        + penalty_timekeeping_events["minutes"] * 60,
    )


@pytest.mark.parametrize("name", ["test_terminate_running_minor_penalty"])
def test_terminate_running_minor_penalty(penalty_times_by_team):
    assert penalty_times_by_team["A"]["time_end"].sum() == 330


@pytest.mark.parametrize("name", ["test_break_running_personal_penalty"])
def test_break_running_personal_penalty(penalty_times_by_team):
    assert penalty_times_by_team["A"]["time_end"].sum() == 1740


@pytest.mark.parametrize("name", ["test_example_1"])
def test_example_1(penalty_times_by_team):
    assert penalty_times_by_team["A"]["time_end"].sum() == 930


@pytest.mark.parametrize("name", ["test_example_2"])
def test_example_2(penalty_times_by_team):
    assert penalty_times_by_team["A"]["time_end"].sum() == 1140


@pytest.mark.parametrize("name", ["test_example_3"])
def test_example_3(penalty_times_by_team):
    assert penalty_times_by_team["A"]["time_end"].sum() == 1140


@pytest.mark.parametrize("name", ["test_example_4"])
def test_example_4(penalty_times_by_team):
    assert penalty_times_by_team["A"]["time_end"].sum() == 2010


@pytest.mark.parametrize("name", ["test_example_5"])
def test_example_5(penalty_times_by_team):
    assert penalty_times_by_team["A"]["time_end"].sum() == 2010


@pytest.mark.parametrize("name", ["test_example_6"])
def test_example_6(penalty_times_by_team):
    assert penalty_times_by_team["A"]["time_end"].sum() == 270
    assert penalty_times_by_team["B"]["time_end"].sum() == 300
