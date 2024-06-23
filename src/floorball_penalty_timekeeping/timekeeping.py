import pandas as pd
from copy import deepcopy

from floorball_penalty_timekeeping.utils import PENALTY_EVENTS


def mask_running_penalties(penalty_times):
    return ~penalty_times["time_start"].isna() & penalty_times["time_end"].isna()


def mask_penalty_ended_by_time(current_time, penalty_times):
    return current_time - 120 >= penalty_times["time_start"]


def mask_waiting_penalties(current_time, penalty_times):
    return penalty_times["time_start"].isna() & (current_time >= penalty_times["to_bench"])


def mask_available_to_start_penalties(current_time, penalty_times):
    mask_running = mask_running_penalties(penalty_times)
    mask_waiting = mask_waiting_penalties(current_time, penalty_times)
    players_waiting = penalty_times.loc[mask_waiting, "player"].values
    players_running_penalty = penalty_times.loc[mask_running, "player"].values
    available_players = [player for player in players_waiting if player not in players_running_penalty]
    mask_available = penalty_times["player"].isin(available_players)
    return mask_waiting & mask_available


def get_next_penalty_to_start(penalty_times):
    return penalty_times["time_start"].isna().idxmax()


def get_number_running_penalties(penalty_times):
    return sum(mask_running_penalties(penalty_times))


def timekeeping(ordered_events):
    teams = ordered_events["team"].unique().tolist()

    if len(teams) == 1:
        teams += ["EasterEgg"]

    ordered_events.loc[10000] = [10000, teams[0], "0", 999, 10000]
    ordered_events.loc[10001] = [10001, teams[1], "0", 999, 10001]

    penalty_times_by_team = {
        team: pd.DataFrame(columns=["event_id", "player", "to_bench", "time_start", "time_end"])
        for team in teams
    }
    personal_penalties_by_team = deepcopy(penalty_times_by_team)

    for _, event in ordered_events.iterrows():
        current_time = event["seconds"]

        for team in teams:
            penalty_times = penalty_times_by_team[team]
            personal_penalties = personal_penalties_by_team[team]

            mask_waiting = mask_waiting_penalties(current_time, penalty_times)
            mask_running = mask_running_penalties(penalty_times)
            mask_to_be_ended = mask_penalty_ended_by_time(current_time, penalty_times)
            mask = (mask_running & mask_to_be_ended) | mask_waiting

            while mask.any():
                # end running penalties
                penalty_times.loc[mask_running & mask_to_be_ended, "time_end"] = penalty_times.loc[mask_running & mask_to_be_ended, "time_start"] + 120
                num_running_penalties_per_team = get_number_running_penalties(penalty_times)

                if num_running_penalties_per_team == 2:
                    break

                available_to_start = penalty_times.loc[mask_available_to_start_penalties(current_time, penalty_times)]
                available_to_start = available_to_start.drop_duplicates(subset="player", keep="first")

                if len(available_to_start) == 0:
                    break

                if num_running_penalties_per_team == 1 or len(available_to_start) == 1:
                    end_times = penalty_times.loc[penalty_times["time_end"].notna(), "time_end"].sort_values()

                    next_index = available_to_start.index.min()

                    next_player = penalty_times.loc[next_index, "player"]
                    last_time_of_player = penalty_times.loc[penalty_times["player"] == next_player, "time_end"].max()
                    time_start = min(last_time_of_player, end_times.iloc[-1])
                    penalty_times.loc[next_index, "time_start"] = time_start

                else:
                    end_times = penalty_times.loc[penalty_times["time_end"].notna(), "time_end"].sort_values()

                    next_index = available_to_start.index.min()
                    next_player = penalty_times.loc[next_index, "player"]
                    last_time_of_player = penalty_times.loc[penalty_times["player"] == next_player, "time_end"].max()
                    time_start = max(last_time_of_player, end_times.iloc[-2])
                    penalty_times.loc[next_index, "time_start"] = time_start

                    if time_start != end_times.iloc[-2]:
                        time_start = end_times.iloc[-2]
                    else:
                        time_start = end_times.iloc[-1]

                    available_to_start = penalty_times.loc[mask_available_to_start_penalties(current_time, penalty_times)]
                    next_index = available_to_start.index.min()
                    penalty_times.loc[next_index, "time_start"] = time_start

                # check if there are still penalties running that have been terminated in the meantime
                mask_available_to_start = mask_available_to_start_penalties(current_time, penalty_times)
                mask_running = mask_running_penalties(penalty_times)
                mask_to_be_ended = mask_penalty_ended_by_time(current_time, penalty_times)
                mask = (mask_running & mask_to_be_ended) | mask_available_to_start

            # start, pause or end personal penalty
            mask = personal_penalties["time_end"].isna()
            not_ended_personal_penalties = personal_penalties.loc[mask]
            for index, row in not_ended_personal_penalties.iterrows():
                if ordered_events.loc[row["event_id"], "event"] == 3:
                    mask = penalty_times["player"] == f"Bgl. {row['player']}"
                    other_penalties_by_player = penalty_times.loc[mask]

                    not_on_bench = []
                    for idx, penalty in other_penalties_by_player.iterrows():
                        if idx == other_penalties_by_player.index[0]:
                            not_on_bench += [penalty["time_end"]]
                        else:
                            if penalty["to_bench"] <= not_on_bench[-1]:
                                not_on_bench[-1] = penalty["time_end"]
                            else:
                                not_on_bench += penalty[["to_bench", "time_end"]].tolist()

                    for i, time in enumerate(not_on_bench):
                        if i == 0:
                            personal_penalties.loc[index, "time_start"] = time
                        elif i % 2 == 0:
                            personal_penalties.loc[index, f"time_start_pause_{i}"] = time
                        else:
                            personal_penalties.loc[index, f"time_end_pause_{i}"] = time

                    not_on_bench += [current_time]
                    total_time_on_bench = 0
                    if len(not_on_bench) > 2:
                        total_time_on_bench = sum([end - start for start, end in zip(not_on_bench[1:-1:2], not_on_bench[2::2])])

                    total_time_not_on_bench = sum([end - start for start, end in zip(not_on_bench[::2], not_on_bench[1::2])])
                    if total_time_not_on_bench >= 600:
                        personal_penalties.loc[index, "time_end"] = personal_penalties.loc[index, "time_start"] + total_time_on_bench + 600

            personal_penalties

        if event["event"] in PENALTY_EVENTS:
            penalty_times = penalty_times_by_team[event["team"]]
            personal_penalties = personal_penalties_by_team[event["team"]]

            next_index = penalty_times.index.max() + 1 if not penalty_times.empty else 0
            penalty_times.loc[next_index, "event_id"] = event["index"]
            penalty_times.loc[next_index, "to_bench"] = current_time
            player = event["player"]

            if event["event"] in [3, 5]:
                next_pp_index = personal_penalties.index.max() + 1 if not personal_penalties.empty else 0
                personal_penalties.loc[next_pp_index, "event_id"] = event["index"]
                personal_penalties.loc[next_pp_index, "player"] = player
                personal_penalties.loc[next_pp_index, "to_bench"] = current_time
                # change player to other
                player = f"Bgl. {event['player']}"

            else:
                mask = personal_penalties["time_end"].isna()
                if player in personal_penalties.loc[mask, "player"].values:
                    player = f"Bgl. {event['player']}"

            penalty_times.loc[next_index, "player"] = player

            # enter second set of 2 minute penalties for major and match penalties
            if event["event"] in [4, 5]:
                penalty_times.loc[next_index + 1, "event_id"] = event["index"]
                penalty_times.loc[next_index + 1, "to_bench"] = current_time
                penalty_times.loc[next_index + 1, "player"] = player

            num_running_penalties_per_team = get_number_running_penalties(penalty_times)

            if num_running_penalties_per_team < 2:
                available_to_start = penalty_times.loc[mask_available_to_start_penalties(current_time, penalty_times)]
                available_to_start = available_to_start.drop_duplicates(subset="player", keep="first")
                if next_index in available_to_start.index:
                    penalty_times.loc[next_index, "time_start"] = current_time

        if event["event"] == 0:
            team = list(set(teams) - set(event["team"]))[0]
            penalty_times = penalty_times_by_team[team]

            num_penalties = get_number_running_penalties(penalty_times)
            num_penalties_other_team = get_number_running_penalties(penalty_times_by_team[event["team"]])

            if num_penalties > num_penalties_other_team:
                if penalty_times["time_end"].isna().any():
                    mask_running = mask_running_penalties(penalty_times)
                    time_start_earliest = penalty_times.loc[mask_running, "time_start"].min()
                    mask_earliest = penalty_times["time_start"] == time_start_earliest
                    terminate_penalty_idx = penalty_times.loc[mask_running & mask_earliest].index.min()

                    penalty_times.loc[terminate_penalty_idx, "time_end"] = current_time

                    available_to_start = mask_available_to_start_penalties(current_time, penalty_times)

                    if available_to_start.any():
                        next_index = penalty_times.loc[available_to_start].index.min()
                        penalty_times.loc[next_index, "time_start"] = current_time

    for team in teams:
        personal_penalties_by_team[team]["event_id"] += 999
        penalty_times_by_team[team] = pd.concat([penalty_times_by_team[team], personal_penalties_by_team[team]])

    return penalty_times_by_team