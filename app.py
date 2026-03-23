import sqlite3
from datetime import date

import altair as alt
import pandas as pd
import streamlit as st

DB_PATH = "health_tracker.db"


# -----------------------------
# Database helpers
# -----------------------------
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Entries table (with notes)
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            entry_date TEXT NOT NULL,
            weight REAL,
            calories_in INTEGER,
            calories_out INTEGER,
            notes TEXT
        )
        """
    )

    # Goal table
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS goal (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            goal_weight REAL
        )
        """
    )

    # Ensure a row exists
    c.execute("INSERT OR IGNORE INTO goal (id, goal_weight) VALUES (1, NULL)")

    conn.commit()
    conn.close()


def add_entry(entry_date, weight, calories_in, calories_out, notes):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        """
        INSERT INTO entries (entry_date, weight, calories_in, calories_out, notes)
        VALUES (?, ?, ?, ?, ?)
        """,
        (entry_date, weight, calories_in, calories_out, notes),
    )
    conn.commit()
    conn.close()


def load_data():
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("SELECT * FROM entries ORDER BY entry_date", conn)
    conn.close()
    if not df.empty:
        df["entry_date"] = pd.to_datetime(df["entry_date"]).dt.date
    return df


def get_goal_weight():
    conn = sqlite3.connect(DB_PATH)
    goal = conn.execute("SELECT goal_weight FROM goal WHERE id = 1").fetchone()[0]
    conn.close()
    return goal


def set_goal_weight(value):
    conn = sqlite3.connect(DB_PATH)
    conn.execute("UPDATE goal SET goal_weight = ? WHERE id = 1", (value,))
    conn.commit()
    conn.close()


# -----------------------------
# Streamlit app
# -----------------------------
def main():
    st.set_page_config(
        page_title="Weight Loss Tracker",
        page_icon="📉",
        layout="wide",
    )

    init_db()

    st.title("📉 Weight Loss & Calories Tracker")

    # ---- Goal weight section ----
    st.sidebar.header("🎯 Goal Weight")

    current_goal = get_goal_weight()

    new_goal = st.sidebar.number_input(
        "Set your goal weight (kg)",
        min_value=0.0,
        step=0.1,
        value=current_goal if current_goal else 0.0,
    )

    if st.sidebar.button("Save goal"):
        set_goal_weight(new_goal)
        st.sidebar.success("Goal updated!")

    st.sidebar.markdown("---")

    # ---- Input form ----
    st.sidebar.header("Log today's data")

    with st.sidebar.form("log_form", clear_on_submit=False):
        entry_date = st.date_input("Date", value=date.today())
        weight = st.number_input("Weight (kg)", min_value=0.0, step=0.1)
        calories_in = st.number_input("Calories in", min_value=0, step=10)
        calories_out = st.number_input("Calories burned", min_value=0, step=10)
        notes = st.text_area("Notes (optional)")

        submitted = st.form_submit_button("Add entry")

    if submitted:
        add_entry(
            entry_date.isoformat(),
            float(weight) if weight else None,
            int(calories_in) if calories_in else None,
            int(calories_out) if calories_out else None,
            notes,
        )
        st.sidebar.success("Entry saved ✅")

    # ---- Load data ----
    df = load_data()

    if df.empty:
        st.info("No data yet. Add your first entry in the sidebar.")
        return

    latest = df.iloc[-1]

    # ---- Summary metrics ----
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Latest weight (kg)", f"{latest['weight']:.1f}" if latest["weight"] else "—")

    with col2:
        st.metric("Latest calories in", int(latest["calories_in"]) if latest["calories_in"] else "—")

    with col3:
        st.metric("Latest calories out", int(latest["calories_out"]) if latest["calories_out"] else "—")

    with col4:
        if df["weight"].notna().sum() >= 2:
            start_weight = df["weight"].dropna().iloc[0]
            diff = latest["weight"] - start_weight
            st.metric("Change since start (kg)", f"{diff:+.1f}")
        else:
            st.metric("Change since start (kg)", "—")

    st.markdown("---")

    # ---- Goal progress ----
    goal_weight = get_goal_weight()

    if goal_weight and latest["weight"]:
        st.subheader("🎯 Goal Progress")

        start_weight = df["weight"].dropna().iloc[0]
        current = latest["weight"]
        remaining = current - goal_weight
        total_loss_needed = start_weight - goal_weight

        progress = (
            (total_loss_needed - remaining) / total_loss_needed
            if total_loss_needed != 0
            else 0
        )

        st.progress(max(0.0, min(1.0, progress)))

        st.write(f"**Current weight:** {current:.1f} kg")
        st.write(f"**Goal weight:** {goal_weight:.1f} kg")
        st.write(f"**Remaining:** {remaining:.1f} kg")

        st.markdown("---")

    # ---- Charts ----
    left, right = st.columns(2)

    with left:
        st.subheader("Weight over time")
        weight_df = df.dropna(subset=["weight"])
        if not weight_df.empty:
            chart = (
                alt.Chart(weight_df)
                .mark_line(point=True)
                .encode(
                    x="entry_date:T",
                    y=alt.Y("weight:Q", title="Weight (kg)"),
                    tooltip=["entry_date", "weight"],
                )
                .properties(height=300)
            )
            st.altair_chart(chart, use_container_width=True)
        else:
            st.write("No weight data yet.")

    with right:
        st.subheader("Calories in vs out")
        cal_df = df.dropna(subset=["calories_in", "calories_out"])
        if not cal_df.empty:
            cal_melt = cal_df.melt(
                id_vars=["entry_date"],
                value_vars=["calories_in", "calories_out"],
                var_name="type",
                value_name="calories",
            )
            cal_chart = (
                alt.Chart(cal_melt)
                .mark_line(point=True)
                .encode(
                    x="entry_date:T",
                    y=alt.Y("calories:Q", title="Calories"),
                    color=alt.Color("type:N", title=""),
                    tooltip=["entry_date", "type", "calories"],
                )
                .properties(height=300)
            )
            st.altair_chart(cal_chart, use_container_width=True)
        else:
            st.write("No calorie data yet.")

    st.markdown("---")

    # ---- Weekly averages ----
    st.subheader("📅 Weekly Averages")

    df["week"] = pd.to_datetime(df["entry_date"]).dt.to_period("W").apply(lambda r: r.start_time)

    weekly = df.groupby("week").agg(
        avg_weight=("weight", "mean"),
        avg_in=("calories_in", "mean"),
        avg_out=("calories_out", "mean"),
    )

    st.dataframe(weekly)

    chart_weekly = (
        alt.Chart(weekly.reset_index())
        .mark_line(point=True)
        .encode(
            x="week:T",
            y="avg_weight:Q",
            tooltip=["week", "avg_weight"],
        )
        .properties(title="Weekly Average Weight", height=300)
    )

    st.altair_chart(chart_weekly, use_container_width=True)

    st.markdown("---")

    # ---- Table ----
    st.subheader("Raw data")
    st.dataframe(df[["entry_date", "weight", "calories_in", "calories_out", "notes"]])


if __name__ == "__main__":
    main()
