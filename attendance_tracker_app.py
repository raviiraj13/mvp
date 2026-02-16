import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from fpdf import FPDF
import sympy as sp
import math
import re
import time

# Selenium
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager


# ---------------- CONFIG ----------------
st.set_page_config(page_title="SKIT Attendance Tracker", layout="wide")

st.title("📊 SKIT Attendance Tracker")

PRESENT_COLOR = "#1ABC9C"
ABSENT_COLOR = "#F39C12"


# ---------------- FETCH FROM ERP ----------------
@st.cache_data
def fetch_attendance():

    options = webdriver.ChromeOptions()

    # Save login session (VERY IMPORTANT)
    options.add_argument("user-data-dir=chrome_profile")

    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=options
    )

    driver.get("https://erp.skit.ac.in")

    st.info("If first time, login manually and solve CAPTCHA")

    time.sleep(20)

    try:
        driver.get("https://erp.skit.ac.in/Student/Attendance")

        time.sleep(5)

        table = driver.find_element(By.TAG_NAME, "table")

        rows = table.find_elements(By.TAG_NAME, "tr")

        data = []

        for row in rows[1:]:

            cols = row.find_elements(By.TAG_NAME, "td")

            data.append([col.text for col in cols])

        driver.quit()

        df = pd.DataFrame(data)

        return df

    except:
        driver.quit()
        return None


# ---------------- PARSE ----------------
def parse_df(raw_df):

    df = pd.DataFrame()

    df["Subject"] = raw_df.iloc[:,2]

    df["Present"] = raw_df.iloc[:,4].astype(int)

    df["Makeup"] = raw_df.iloc[:,6].astype(int)

    df["Absent"] = raw_df.iloc[:,7].astype(int)

    # Present = Present + Makeup
    df["Effective Present"] = df["Present"] + df["Makeup"]

    df["Total Classes"] = df["Effective Present"] + df["Absent"]

    df["Attendance%"] = (
        df["Effective Present"] /
        df["Total Classes"] * 100
    ).round(2)

    return df


# ---------------- DONUT ----------------
def plot_overall_donut(present, absent):

    total = present + absent

    present_percent = present / total * 100
    absent_percent = 100 - present_percent

    fig, ax = plt.subplots()

    ax.pie(
        [present_percent, absent_percent],
        labels=["Present", "Absent"],
        colors=[PRESENT_COLOR, ABSENT_COLOR],
        autopct="%1.1f%%",
        wedgeprops={"width":0.4}
    )

    ax.set_title("Overall Attendance")

    st.pyplot(fig)


def plot_subject_donut(df):

    st.subheader("Subject-wise Donut Charts")

    cols = st.columns(3)

    for i in range(len(df)):

        row = df.iloc[i]

        present = row["Effective Present"]
        absent = row["Absent"]

        total = present + absent

        present_percent = present / total * 100
        absent_percent = 100 - present_percent

        fig, ax = plt.subplots()

        ax.pie(
            [present_percent, absent_percent],
            labels=["Present", "Absent"],
            colors=[PRESENT_COLOR, ABSENT_COLOR],
            autopct="%1.1f%%",
            wedgeprops={"width":0.4}
        )

        ax.set_title(row["Subject"])

        cols[i % 3].pyplot(fig)


# ---------------- TARGET ----------------
def classes_needed(present, total, target):

    x = sp.symbols("x")

    sol = sp.solve(
        (present+x)/(total+x)-target/100,
        x
    )

    if sol:
        return max(0, math.ceil(sol[0]))

    return 0


# ---------------- PDF ----------------
def generate_pdf(attendance, df):

    pdf = FPDF()

    pdf.add_page()

    pdf.set_font("Arial","B",16)

    pdf.cell(0,10,"SKIT Attendance Report", ln=True)

    pdf.cell(0,10,f"Attendance: {attendance:.2f}%", ln=True)

    for _,row in df.iterrows():

        pdf.cell(
            0,10,
            f"{row['Subject']} : {row['Attendance%']}%",
            ln=True
        )

    return pdf.output(dest="S").encode("latin-1")


# ---------------- BUTTON ----------------
if st.button("Fetch Attendance from SKIT ERP"):

    raw_df = fetch_attendance()

    if raw_df is None:

        st.error("Failed to fetch attendance")

    else:

        df = parse_df(raw_df)

        st.success("Attendance fetched successfully")

        st.dataframe(df)


        # summary
        total_present = df["Effective Present"].sum()
        total_absent = df["Absent"].sum()

        total = total_present + total_absent

        attendance = total_present / total * 100

        st.metric("Overall Attendance", f"{attendance:.2f}%")


        # donuts
        plot_overall_donut(total_present, total_absent)

        plot_subject_donut(df)


        # target
        target = st.number_input("Target %", value=75)

        need = classes_needed(total_present, total, target)

        st.info(f"Attend {need} classes to reach {target}%")


        # PDF
        pdf = generate_pdf(attendance, df)

        st.download_button(
            "Download PDF",
            pdf,
            "attendance.pdf"
        )
