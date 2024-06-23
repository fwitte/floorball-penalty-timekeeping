from dataclasses import MISSING
from dataclasses import fields

import numpy as np
import pandas as pd
import streamlit as st
from matplotlib import pyplot as plt

from floorball_penalty_timekeeping.utils import _FORM_COMPONENT_KEY
from floorball_penalty_timekeeping.utils import _FORM_VALIDATION_KEY
from floorball_penalty_timekeeping.utils import ALL_EVENTS
from floorball_penalty_timekeeping.utils import Event
from floorball_penalty_timekeeping.utils import seconds_to_mmss

COLORS = {"A": "red", "B": "blue"}


def create_input_form(dataobj, action) -> None:

    validation_results = st.session_state.pop(_FORM_VALIDATION_KEY, {})

    base_type: type = dataobj if isinstance(dataobj, type) else type(dataobj)

    result = {}
    with st.form(key=_FORM_COMPONENT_KEY, clear_on_submit=True):
        cols = st.columns([1, 1, 2, 1, 1])
        for col, field in zip(cols, fields(base_type)):

            value = getattr(dataobj, field.name, None)
            if value in (MISSING, None):
                if field.default is not MISSING:
                    value = field.default
                elif field.default_factory is not MISSING:
                    value = field.default_factory()
                else:
                    value = field.type()

            # show field
            field_key = f"{_FORM_COMPONENT_KEY}_field_{field.name}"
            label = f"{field.name}:"
            with col:
                if field.name == "team":
                    result[field.name] = st.selectbox(label, options=["A", "B"], key=field_key)
                elif field.name == "event":
                    result[field.name] = st.selectbox(label, options=[ALL_EVENTS[_]["display"] for _ in ALL_EVENTS], key=field_key)
                    result[field.name] = [event for event in ALL_EVENTS if ALL_EVENTS[event]["display"] == result[field.name]][0]
                elif field.type is str:
                    result[field.name] = st.text_input(label, value, key=field_key)
                elif field.type is int:
                    result[field.name] = st.number_input(label, value, key=field_key)

            if field.name in validation_results:
                st.warning(f"**Error:** {validation_results[field.name]}")

        if st.form_submit_button("Add"):
            validation_results = {}
            try:
                new_object = base_type(**result)
                if getattr(base_type, "validate", None):
                    validation_results = new_object.validate()
            except Exception as e:
                # CATCH VALIDATION ERROR AND POPULATE THE DICT WITH IT
                pass
            if validation_results:
                st.session_state[_FORM_VALIDATION_KEY] = validation_results
                st.rerun()
            else:
                action(new_object)


def create_result_layout(events, penalties, goals, teams):

    st.write("# Events")
    st.write(display_event_table(events).to_html(), unsafe_allow_html=True)
    if st.button("Remove last event"):
        st.session_state.events.pop()
        st.rerun()

    if not all([penalty_table.empty for penalty_table in penalties.values()]):
        st.write("# Timekeeping ")
        st.write("## Plot")

        fig, ax = plt.subplots(1)

        penalties_to_plot, plot_params = _prepare_penalty_times_for_plot(penalties, teams)
        goals_to_plot = _prepare_goals(goals, teams)
        plot_bench_penalties(ax, penalties_to_plot)
        plot_goals(ax, goals_to_plot)
        plot_personal_penalties(ax, penalties_to_plot)
        make_plot_stylish(ax, **plot_params)

        st.pyplot(fig)

        tables = st.columns(2)
        for table, team in zip(tables, teams):
            with table:
                st.write(f"## {team}")
                st.write(display_penalty_table(penalties[team]).to_html(), unsafe_allow_html=True)


def _format_event_display(events):
    return events.replace(
        {event: ALL_EVENTS[event]["display"] for event in ALL_EVENTS}
    )


def display_penalty_table(penalites):
    df = penalites[["player", "to_bench", "time_start", "time_end"]].rename(
        columns={"player": "Player", "to_bench": "To bench", "time_start": "Start", "time_end": "End"}
    )
    for col in ["To bench", "Start", "End"]:
        df[col] = df[col].apply(seconds_to_mmss)

    return df


def display_event_table(events):
    df = pd.DataFrame(columns=["Time", "Team", "Player"])

    events = events.sort_values(by=["seconds", "event"]).reset_index()

    df["Time"] = events["seconds"].apply(seconds_to_mmss)
    df["Team"] = events["team"]
    df["Player"] = events["player"]
    df["Event"] = _format_event_display(events["event"])

    return df.style.apply(_style_row, axis=1)


def _style_row(row):
    if row['Team'] == "A":
        color = 'background-color: #fbb0af;'
    else:
        color = 'background-color: #9cdeff;'
    return [color] * len(row)


def _prepare_penalty_times_for_plot(penalty_times_by_teams, teams):
    unique_players_per_team = {
        team: penalty_times_by_teams[team]["player"].unique() for team in teams
    }
    all_player_ticks = []
    y_value_player_map = {}

    min_time = 10000
    max_time = 0

    df_by_team = {}

    for k, team in enumerate(teams):
        if len(unique_players_per_team[team]) == 0:
            continue
        player_y_value_map = {
            player: (y + 1) * (-1) ** k
            for y, player in enumerate(unique_players_per_team[team])
        }
        y_value_player_map.update(
            {y: player for player, y in player_y_value_map.items()}
        )
        df = penalty_times_by_teams[team].copy()

        max_time = max(max_time, df["time_end"].max())
        min_time = min(min_time, df["to_bench"].min())

        df = df.groupby(by=["event_id"]).agg({
            "player": "first",
            "to_bench": "first",
            "time_start": "first",
            "time_end": "last"
        }).reset_index(drop=True)

        df["y_base"] = df["player"].map(player_y_value_map)
        all_player_ticks += list(set(df["y_base"].tolist()))
        df["y_base_copy"] = df["y_base"]
        delta = 0.25
        df = df.groupby("y_base").apply(
            assign_y_locations, delta=delta, include_groups=False
        ).reset_index(drop=True)

        df_by_team[team] = df

    plot_params = {
        "all_player_ticks": all_player_ticks,
        "max_time": max_time,
        "min_time": min_time,
        "y_value_player_map": y_value_player_map,
    }
    return df_by_team, plot_params


def _prepare_goals(goals, teams):
    goals["y_position"] = goals["team"].map(
        {team: 0.25 * (-1) ** k for k, team in enumerate(teams)}
    )
    goals["color"] = goals["team"].map(COLORS)
    return goals


def plot_bench_penalties(ax, df_by_teams):

    for team, df in df_by_teams.items():
        ax.plot(
            [df["to_bench"], df["time_start"]],
            [df["y_position"] for _ in range(2)],
            "--",
            marker="|",
            color=COLORS[team]
        )
        ax.plot(
            [df["time_start"], df["time_end"]],
            [df["y_position"] for _ in range(2)],
            "-",
            marker="|",
            color=COLORS[team]
        )
        ax.plot(
            [df["to_bench"] for _ in range(2)],
            [np.zeros(len(df)), df["y_position"]],
            "--",
            color=COLORS[team],
            linewidth=0.5
        )


def plot_goals(ax, goals):
    ax.scatter(
        goals["seconds"], goals["y_position"], marker="x", c=goals["color"]
    )


def make_plot_stylish(ax, all_player_ticks=None, max_time=None, min_time=None, y_value_player_map=None):

    ax.spines['bottom'].set_position(('data', 0))
    ax.spines['top'].set_color('none')
    ax.spines['right'].set_color('none')

    all_player_ticks = sorted(all_player_ticks)
    ax.set_yticks(all_player_ticks, minor=False)
    minor_ticks = (
        [tick - 0.5 for tick in all_player_ticks]
        + [-0.5] + [all_player_ticks[-1] + 0.5]
    )
    ax.set_yticks(minor_ticks, minor=True)
    ax.set_yticklabels([y_value_player_map[tick] for tick in all_player_ticks])
    ax.yaxis.set_ticks_position('left')

    ax.xaxis.set_ticks_position('bottom')

    major_time_step = 60
    while (max_time - min_time) // major_time_step > 8:
        major_time_step += 60

    major_ticks = np.arange(
        (min_time // major_time_step) * major_time_step,
        max_time + 1,
        major_time_step
    )
    ax.set_xticks(major_ticks)
    f = np.vectorize(seconds_to_mmss)
    ax.set_xticklabels(f(major_ticks))

    ax.xaxis.grid(which="major")
    ax.yaxis.grid(which="minor")

    ax.set_axisbelow(True)


def plot_personal_penalties(ax, personal_penalties):
    pass


def assign_y_locations(group, delta):
    group = group.sort_values(by="to_bench").reset_index(drop=True)
    results = []
    n = len(group)
    overlapping = {0: [0]}

    k = 0
    for i in range(1, n):
        if group.loc[i, "to_bench"] <= group.loc[i - 1, "time_end"]:
            overlapping[k] += [i]
        else:
            k += 1
            overlapping[k] = [i]

    center = group["y_base_copy"].iloc[0]
    min_value = center - delta
    max_value = center + delta

    for overlapped in overlapping.values():
        num_overlaps = len(overlapped)
        if num_overlaps > 1:
            results += np.linspace(min_value, max_value, num_overlaps).tolist()
        else:
            results += [center]

    group["y_position"] = results

    return group
