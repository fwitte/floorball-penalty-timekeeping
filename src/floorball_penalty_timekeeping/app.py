import pandas as pd
import streamlit as st

from floorball_penalty_timekeeping.timekeeping import timekeeping
from floorball_penalty_timekeeping.utils import Event
from floorball_penalty_timekeeping.utils import prepare_events
from floorball_penalty_timekeeping.views import create_input_form
from floorball_penalty_timekeeping.views import create_result_layout


def add_new_event(dataobj):
    st.session_state.events.append(
        dataobj.__dict__
    )


def delete_last_event():
    st.session_state.events.pop()
    st.rerun()


def layout():

    if "events" not in st.session_state:
        st.session_state.events = []

    events = st.session_state.events

    create_input_form(Event, add_new_event)

    if len(events) > 0:
        events = pd.DataFrame(events).astype({"team": str, "player": str})
        preprocessed_events = prepare_events(pd.DataFrame(events))
        penalty_times_by_teams = timekeeping(preprocessed_events.copy())
        goals = preprocessed_events.loc[preprocessed_events["event"] == 0].copy()
        teams = list(penalty_times_by_teams.keys())
        print(penalty_times_by_teams)
        create_result_layout(preprocessed_events, penalty_times_by_teams, goals, teams)

if __name__ == "__main__":
    layout()