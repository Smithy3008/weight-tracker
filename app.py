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

def update_meal(meal_id, meal_name, calories, meal_time, entry_date, notes):
    conn = sqlite3.connect("health_tracker.db")
    c = conn.cursor()
    c.execute("""
        UPDATE meals
        SET meal_name = ?, calories = ?, meal_time = ?, entry_date = ?, notes = ?
        WHERE id = ?
    """, (meal_name, calories, meal_time, entry_date, notes, meal_id))
    conn.commit()
    conn.close()

def get_meals():
    conn = sqlite3.connect("health_tracker.db")
    df = pd.read_sql_query("SELECT * FROM meals ORDER BY entry_date DESC", conn)
    conn.close()
    return df

def get_calories_burned():
    try:
        df = pd.read_csv("calories_burned.csv")
        df["date"] = pd.to_datetime(df["date"])
        return df
    except Exception:
        return pd.DataFrame(columns=["date", "calories_burned"])

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

    meal_name = st.text_input("Meal Name")
    calories = st.number_input("Calories", min_value=0, step=10)
    meal_time = st.time_input("Meal Time")
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
    # EDIT MEAL
    # -----------------------------
    st.subheader("Edit an Existing Meal")

    if not meals_df.empty:
        meal_to_edit = st.selectbox(
            "Select a meal to edit",
            meals_df["id"],
            format_func=lambda x: f"{meals_df.loc[meals_df['id']==x, 'meal_name'].values[0]} ({meals_df.loc[meals_df['id']==x, 'entry_date'].values[0]})"
        )

        selected = meals_df[meals_df["id"] == meal_to_edit].iloc[0]

        new_name = st.text_input("Meal Name (edit)", selected["meal_name"])
        new_calories = st.number_input("Calories (edit)", min_value=0, step=10, value=int(selected["calories"]))
        new_time = st.time_input("Meal Time (edit)", datetime.strptime(selected["meal_time"], "%H:%M").time())
        new_date = st.date_input("Date (edit)", datetime.strptime(selected["entry_date"], "%Y-%m-%d").date())
        new_notes = st.text_area("Notes (edit)", selected["notes"] if selected["notes"] else "")

        if st.button("Save Changes", use_container_width=True):
            update_meal(
                meal_to_edit,
                new_name,
                new_calories,
                new_time.strftime("%H:%M"),
                new_date.isoformat(),
                new_notes
            )
            st.success("Meal updated successfully!")

    # -----------------------------
    # COPY MEAL (OPTION B)
    # -----------------------------
    st.subheader("Copy a Meal From Another Day")

    if not meals_df.empty:
        copy_date = st.date_input("Select a date to copy from", value=date.today())
        meals_on_date = meals_df[meals_df["entry_date"] == copy_date.isoformat()]

        if not meals_on_date.empty:
            meal_to_copy = st.selectbox(
                "Select a meal to copy",
                meals_on_date["id"],
                format_func=lambda x: meals_on_date.loc[meals_on_date["id"] == x, "meal_name"].values[0]
            )

            selected_copy = meals_on_date[meals_on_date["id"] == meal_to_copy].iloc[0]

            copy_name = st.text_input("Meal Name (copy)", selected_copy["meal_name"])
            copy_calories = st.number_input("Calories (copy)", min_value=0, step=10, value=int(selected_copy["calories"]))
            copy_time = st.time_input("Meal Time (copy)", datetime.strptime(selected_copy["meal_time"], "%H:%M").time())
            copy_notes = st.text_area("Notes (copy)", selected_copy["notes"] if selected_copy["notes"] else "")

            # Default date = TODAY (Option A)
            copy_date_final = date.today()

            if st.button("Save Copied Meal", use_container_width=True):
                add_meal(
                    copy_name,
                    copy_calories,
                    copy_time.strftime("%H:%M"),
                    copy_date_final.isoformat(),
                    copy_notes
                )
                st.success("Meal copied to today!")
        else:
            st.info("No meals found for that date.")

# -----------------------------
# DAILY SUMMARY DASHBOARD
# -----------------------------
elif page == "📊 Daily Summary Dashboard":
    st.subheader("Daily Summary")

    summary_date = st.date_input("Select a date", value=date.today())

    weight_df = get_weight_entries()
    meals_df = get_meals()
    cal_burn_df = get_calories_burned()

    weight_for_day = None
    if not weight_df.empty:
        weight_df["entry_date"] = pd.to_datetime(weight_df["entry_date"])
        past_weights = weight_df[weight_df["entry_date"] <= pd.to_datetime(summary_date)]
        if not past_weights.empty:
            weight_for_day = past_weights.iloc[-1]["weight"]

    meals_for_day = meals_df[meals_df["entry_date"] == summary_date.isoformat()] \
                    if not meals_df.empty else pd.DataFrame()

    total_calories = meals_for_day["calories"].sum() if not meals_for_day.empty else 0

    burned_today = None
    if not cal_burn_df.empty:
        row = cal_burn_df[cal_burn_df["date"] == pd.to_datetime(summary_date)]
        if not row.empty:
            burned_today = int(row.iloc[0]["calories_burned"])

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Weight", f"{weight_for_day} kg" if weight_for_day else "No data")

    with col2:
        st.metric("Calories Eaten", f"{total_calories}")

    with col3:
        st.metric("Calories Burned", burned_today if burned_today is not None else "No data")

    with col4:
        if burned_today is not None:
            net = total_calories - burned_today
            st.metric("Net Calories", net)
        else:
            st.metric("Net Calories", "No data")

    st.markdown("---")

    st.subheader("Meals for the Day")

    if not meals_for_day.empty:
        st.dataframe(meals_for_day, use_container_width=True)
    else:
        st.info("No meals logged for this day.")

    st.markdown("---")

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

    st.markdown("---")

    st.subheader("Backup Your Data")

    with open("health_tracker.db", "rb") as f:
        st.download_button(
            label="Download Database",
            data=f,
            file_name="health_tracker.db",
            mime="application/octet-stream"
        )