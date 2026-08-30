import pandas as pd
import re


# -----------------------------
# LOAD RANKINGS
# -----------------------------
def load_rankings(csv_path="FantasyPros.csv"):
    df = pd.read_csv(csv_path)

    # Remove completely blank rows
    df = df.dropna(how="all")

    # Make sure PLAYER NAME exists
    df["PLAYER NAME"] = (
        df["PLAYER NAME"]
        .astype(str)
        .str.strip()
    )

    # Remove bad player names
    df = df[
        (df["PLAYER NAME"] != "")
        & (df["PLAYER NAME"] != "nan")
        & (df["PLAYER NAME"] != "None")
    ]

    # Clean player names for matching
    df["PLAYER CLEAN"] = (
        df["PLAYER NAME"]
        .apply(clean_name)
    )

    # Remove any rows that became blank after cleaning
    df = df[
        df["PLAYER CLEAN"] != ""
    ]

    # Convert value column
    df["VALUE"] = pd.to_numeric(
        df["ECR VS. ADP"],
        errors="coerce"
    ).fillna(0)

    # Convert rankings column
    df["RK"] = pd.to_numeric(
        df["RK"],
        errors="coerce"
    )

    # Remove rows without rankings
    df = df[
        df["RK"].notna()
    ]

    # Sort by rankings just to be safe
    df = df.sort_values(
        by="RK"
    )

    return df


# -----------------------------
# CLEAN PLAYER NAMES
# -----------------------------
def clean_name(name):
    """Normalize player names so CSV and Sleeper names match."""
    if pd.isna(name):
        return ""

    name = str(name).lower()

    # Remove punctuation
    name = re.sub(r"[.'\-]", "", name)

    # Remove common suffixes
    name = re.sub(
        r"\b(jr|sr|ii|iii|iv|v)\b",
        "",
        name
    )

    # Remove commas
    name = name.replace(",", "")

    # Remove extra spaces
    name = " ".join(name.split())

    return name


# -----------------------------
# LOAD TARGET LIST
# -----------------------------
def load_target_list(csv_path="adam.csv"):
    """
    Load a simple list of player names (one per line, no header)
    that the user specifically wants to target, and return their
    cleaned names for matching against PLAYER CLEAN.
    """
    try:
        with open(csv_path, "r", encoding="utf-8-sig") as f:
            names = [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        return set()

    return {clean_name(n) for n in names if clean_name(n)}


# -----------------------------
# REMOVE DRAFTED PLAYERS
# -----------------------------
def remove_drafted_players(df, drafted):
    drafted = {clean_name(x) for x in drafted}
    return df[
        ~df["PLAYER CLEAN"].isin(drafted)
    ].copy()


# -----------------------------
# BEST PLAYER
# -----------------------------
def best_player(df):
    if len(df) == 0:
        return None
    return df.iloc[0]


# -----------------------------
# BEST BY POSITION
# -----------------------------
def best_by_position(available_df, count=3):
    positions = ["QB", "RB", "WR", "TE"]
    best = {}
    for pos in positions:
        players = available_df[
            available_df["POS"].astype(str).str.startswith(pos)
        ]
        if not players.empty:
            best[pos] = players.head(count)
    return best


# -----------------------------
# VALUE STEALS
# -----------------------------
def value_steals(df, amount=10):
    # Ignore defenses and kickers
    df = df[
        ~df["POS"].isin(["DST", "K"])
    ]

    # Ignore players ranked outside the top 100
    df = df[
        df["RK"] <= 100
    ]

    return (
        df.sort_values(
            "VALUE",
            ascending=False
        )
        .head(amount)
    )


# -----------------------------
# TOP AVAILABLE
# -----------------------------
def top_available(df, amount=25):
    return df.head(amount)