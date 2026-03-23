import streamlit as st
import sqlite3
import pandas as pd
from datetime import date, datetime

# -----------------------------
# PAGE CONFIG
# -----------------------------
st.set_page_config(
    page_title="Health Tracker",
    page_icon="💪",
    layout="centered",
)

# -----------------------------
# HEADER
# -----------------------------
st.markdown(
    """
    <h1 style='text-align: center; color: #4CAF50;'>
        Health Tracker 💪
    </h1>
    <p style='text-align: center; font-size: 18px; color: #555;'>
        Track your weight, meals, and daily progress
    </p>
    <hr>
    """,
    unsafe_allow_html=True
)

# -----------------------------
# DATABASE FUNCTIONS
# -----------------------------
def init_db():
    conn = sqlite3.connect("health_tracker.db")
    c = conn.cursor()

    # Weight table
    c.execute("""
        CREATE TABLE IF NOT EXISTS weight_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            weight REAL NOT NULL,
            entry_date TEXT NOT NULL
        )
    """)

    # Meals table
    c.execute("""
        CREATE TABLE IF NOT EXISTS meals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            meal_name TEXT NOT NULL,
            calories INTEGER NOT NULL,
            meal_time TEXT NOT NULL,
            entry_date TEXT NOT NULL,
            notes TEXT
        )
    """)

    conn.commit()
    conn.close()

def add_weight_entry(weight, entry_date):
    conn = sqlite3.connect("health_tracker.db")
    c = conn.cursor()
    c.execute("INSERT INTO weight_entries (weight, entry_date) VALUES (?, ?)",
              (weight, entry_date))
    conn.commit()
    conn.close()

def get_weight_entries():
    conn = sqlite3.connect("health_tracker.db")
    df = pd.read_sql_query("SELECT * FROM weight_entries ORDER BY entry_date", conn)
    conn.close()
    return df

def add_meal(meal_name, calories, meal_time, entry_date, notes):
    conn = sqlite3.connect("health_tracker.db")
    c = conn.cursor()
    c.execute("""
        INSERT INTO meals (meal_name, calories, meal_time, entry_date, notes)
        VALUES (?, ?, ?, ?, ?)
    """, (meal_name, calories, meal_time, entry_date, notes))
    conn.commit()
    conn.close()

def get_meals():
    conn = sqlite3.connect("health_tracker.db")
    df = pd.read_sql_query("SELECT * FROM meals ORDER BY entry_date DESC", conn)
    conn.close()
    return df

# Initialize DB
init_db()

# -----------------------------
# SIDEBAR NAVIGATION
# -----------------------------
page = st.sidebar.radio(
    "Navigation",
    ["🏋️ Weight Tracker", "🍽️ Meals Log", "📊 Daily Summary Dashboard"]
)

# -----------------------------
# WEIGHT TRACKER PAGE
# -----------------------------
if page == "🏋️ Weight Tracker":
    st.subheader("Add New Weight Entry")

    col1, col2 = st.columns(2)

    with col1:
        weight = st.number_input("Weight (kg)", min_value=1.0, step=0.1)

    with col2:
        entry_date = st.date_input("Date", value=date.today())

    if st.button("Save Weight Entry", use_container_width=True):
        add_weight_entry(weight, entry_date.isoformat())
        st.success("Weight entry saved!")

    st.subheader("Your Weight History")
    df = get_weight_entries()

    if not df.empty:
        st.dataframe(df, use_container_width=True)
    else:
        st.info("No entries yet. Add your first entry above.")

    st.subheader("Weight Trend")
    if not df.empty:
        df_chart = df.copy()
        df_chart["entry_date"] = pd.to_datetime(df_chart["entry_date"])
        df_chart = df_chart.set_index("entry_date")
        st.line_chart(df_chart["weight"])
    else:
        st.info("Add entries to see your progress over time.")

# -----------------------------
# MEALS LOG PAGE
# -----------------------------
elif page == "🍽️ Meals Log":
    st.subheader("Log a Meal")

    meal_name = st.text_input("Meal Name (e.g., Breakfast, Chicken Salad)")
    calories = st.number_input("Calories", min_value=0, step=10)
    meal_time = st.time_input("Meal Time", value=datetime.now().time())
    entry_date = st.date_input("Date", value=date.today())
    notes = st.text_area("Notes (optional)")

    if st.button("Save Meal", use_container_width=True):
        add_meal(
            meal_name,
            calories,
            meal_time.strftime("%H:%M"),
            entry_date.isoformat(),
            notes
        )
        st.success("Meal logged!")

    st.subheader("Meal History")
    meals_df = get_meals()

    if not meals_df.empty:
        st.dataframe(meals_df, use_container_width=True)
    else:
        st.info("No meals logged yet.")

# -----------------------------
# DAILY SUMMARY DASHBOARD
# -----------------------------
elif page == "📊 Daily Summary Dashboard":
    st.subheader("Daily Summary")

    # Select date
    summary_date = st.date_input("Select a date", value=date.today())

    # Load data
    weight_df = get_weight_entries()
    meals_df = get_meals()

    # -----------------------------
    # Weight for the selected day
    # -----------------------------
    weight_for_day = None

    if not weight_df.empty:
        weight_df["entry_date"] = pd.to_datetime(weight_df["entry_date"])
        past_weights = weight_df[weight_df["entry_date"] <= pd.to_datetime(summary_date)]
        if not past_weights.empty:
            weight_for_day = past_weights.iloc[-1]["weight"]

    # -----------------------------
    # Meals + calories for the day
    # -----------------------------
    meals_for_day = meals_df[meals_df["entry_date"] == summary_date.isoformat()] \
                    if not meals_df.empty else pd.DataFrame()

    total_calories = meals_for_day["calories"].sum() if not meals_for_day.empty else 0

    # -----------------------------
    # Summary cards
    # -----------------------------
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Weight", f"{weight_for_day} kg" if weight_for_day else "No data")

    with col2:
        st.metric("Calories Eaten", f"{total_calories}")

    with col3:
        st.metric("Calories Burned", "Coming soon")

    st.markdown("---")

    # -----------------------------
    # Meals list
    # -----------------------------
    st.subheader("Meals for the Day")

    if not meals_for_day.empty:
        st.dataframe(meals_for_day, use_container_width=True)
    else:
        st.info("No meals logged for this day.")

    st.markdown("---")

    # -----------------------------
    # 7-day weight trend
    # -----------------------------
    st.subheader("Last 7 Days Weight Trend")

    if not weight_df.empty:
        last_week = weight_df[weight_df["entry_date"] >= (pd.to_datetime(summary_date) - pd.Timedelta(days=7))]
        if not last_week.empty:
            last_week_chart = last_week.set_index("entry_date")
            st.line_chart(last_week_chart["weight"])
        else:
            st.info("Not enough data for a 7-day trend.")
    else:
        st.info("No weight data available.")
