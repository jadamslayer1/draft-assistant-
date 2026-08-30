import streamlit as st

import sleeper
from sleeper import (
    get_draft_from_league,
    get_draft_by_id,
    get_picks
)

from draft_logic import (
    load_rankings,
    load_target_list,
    remove_drafted_players,
    best_player,
    best_by_position,
    top_available,
    clean_name
)

st.set_page_config(
    page_title="Fantasy Draft Assistant",
    layout="wide"
)

st.title("Fantasy Draft Assistant")

st.info(
    "Paste a Sleeper Draft ID for mock drafts or leave blank to use your league draft."
)

# ----------------------------------------------------
# LOAD RANKINGS
# ----------------------------------------------------

@st.cache_data
def get_rankings():
    return load_rankings("FantasyPros.csv")


@st.cache_data
def get_targets():
    return load_target_list("adam.csv")


df = get_rankings()
targets = get_targets()

df["TARGET"] = df["PLAYER CLEAN"].isin(targets)

# ----------------------------------------------------
# EXTRACT IDS FROM SLEEPER URLS
# ----------------------------------------------------

import re

def extract_id(text):

    numbers = re.findall(r"\d+", text)

    if len(numbers):
        return numbers[0]

    return None


# ----------------------------------------------------
# DRAFT CONNECTION
# ----------------------------------------------------


draft_input = st.text_input(
    "Paste a Sleeper URL, Draft ID, or League ID"
)


if draft_input.strip():

    extracted_id = extract_id(draft_input)

    # Only re-resolve League ID -> Draft ID when the pasted input
    # actually changes. Streamlit reruns this script on every
    # interaction (slider drag, button click, etc), so re-hitting
    # both Sleeper endpoints every single time just adds extra
    # chances for a transient network failure.
    if st.session_state.get("resolved_input") != extracted_id:

        league_draft_id = get_draft_from_league(extracted_id)

        st.session_state.resolved_input = extracted_id
        st.session_state.resolved_draft_id = (
            get_draft_by_id(league_draft_id)
            if league_draft_id
            else get_draft_by_id(extracted_id)
        )

    draft_id = st.session_state.resolved_draft_id

    st.success("Connected.")

else:

    draft_id = None

    st.info(
        "No draft connected. Rankings only mode enabled."
    )


if draft_id:

    st.success(f"Connected to {draft_id}")


# ----------------------------------------------------
# REFRESH BUTTON
# ----------------------------------------------------

if st.button("🔄 Refresh Sleeper Data Now"):

    st.rerun()
# ----------------------------------------------------
# GET PICKS
# ----------------------------------------------------

# Save the last successful draft update
if "previous_picks" not in st.session_state:

    st.session_state.previous_picks = []

if draft_id:

    with st.spinner("Fetching latest picks from Sleeper..."):
        new_picks = get_picks(draft_id)

    if new_picks is None:
        # The Sleeper fetch failed (timeout, rate limit, etc).
        # Say so — including the specific reason — and keep
        # showing the last known-good state instead of silently
        # doing nothing.
        st.warning(
            "⚠️ Couldn't reach Sleeper — showing the last successful "
            f"draft update. Reason: {sleeper.LAST_ERROR}"
        )

    # Never allow the draft to move backwards
    elif len(new_picks) >= len(
        st.session_state.previous_picks
    ):

        st.session_state.previous_picks = new_picks

    picks = st.session_state.previous_picks

else:

    picks = []

# ----------------------------------------------------
# DRAFTED PLAYERS
# ----------------------------------------------------

drafted = []

for pick in picks:

    try:

        drafted.append(

            clean_name(
                f"{pick['metadata']['first_name']} {pick['metadata']['last_name']}"
            )

        )

    except Exception:

        pass


available = remove_drafted_players(
    df,
    drafted
)

# ----------------------------------------------------
# YOUR TARGETS
# ----------------------------------------------------

my_targets = available[available["TARGET"]].sort_values("RK")

if not my_targets.empty:

    st.subheader("🎯 Your Targets Still Available")

    current_rank = len(drafted) + 1

    target_display = my_targets[
        ["RK", "PLAYER NAME", "POS", "TEAM"]
    ].copy()

    target_display["PICKS UNTIL TYPICAL GONE"] = (
        target_display["RK"] - current_rank
    ).clip(lower=0).astype(int)

    st.dataframe(
        target_display,
        use_container_width=True,
        hide_index=True
    )

elif targets:

    st.info("None of your targeted players are available anymore.")

# ----------------------------------------------------
# BEST PLAYER
# ----------------------------------------------------

best = best_player(available)

# ----------------------------------------------------
# LAYOUT
# ----------------------------------------------------

left, right = st.columns([3, 1])

with left:

    st.subheader("Available Players")

    display = top_available(
        available,
        25
    )[
        [
            "RK",
            "PLAYER NAME",
            "POS",
            "TEAM",
            "TIERS",
            "VALUE",
            "TARGET"
        ]
    ].copy()

    display["PLAYER NAME"] = display.apply(
        lambda r: f"🎯 {r['PLAYER NAME']}" if r["TARGET"] else r["PLAYER NAME"],
        axis=1
    )

    display = display.drop(columns=["TARGET"])

    st.dataframe(
        display,
        use_container_width=True,
        hide_index=True
    )

with right:

    st.subheader("⭐ Best Pick")

    if best is not None:

        st.markdown(
            f"## {best['PLAYER NAME']}"
        )

        st.write(best["POS"])

        st.write(best["TEAM"])

    st.divider()

    st.metric(
        "Drafted",
        len(drafted)
    )

    st.metric(
        "Available",
        len(available)
    )

# ----------------------------------------------------
# BEST AT EACH POSITION
# ----------------------------------------------------

st.subheader("Best Available By Position")

best_pos = best_by_position(available)

cols = st.columns(4)

positions = ["QB", "RB", "WR", "TE"]

for i, pos in enumerate(positions):

    with cols[i]:

        st.markdown(f"### {pos}")

        if pos in best_pos:

            for _, player in best_pos[pos].iterrows():

                name = player["PLAYER NAME"]

                if player["TARGET"]:
                    name = f"🎯 {name}"

                st.write(name)

                st.caption(f"{player['TEAM']} · Rank {int(player['RK'])}")