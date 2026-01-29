import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from fpdf import FPDF
import sympy as sp
import io

st.set_page_config(page_title="Attendance Tracker", layout="wide")
st.title("📊 Attendance Tracker")
st.write("Upload your attendance CSV file or paste a CSV URL with columns: Subject, Present, Absent.")

# -------------------------- Functions --------------------------
def load_data(uploaded_file):
    df = pd.read_csv(uploaded_file)
    df['Total'] = df['Present'] + df['Absent']
    df['Attendance%'] = df['Present'] / df['Total'] * 100
    return df

def plot_bar_chart(df):
    plt.figure(figsize=(8,4))  # slightly smaller width for mobile
    barplot = sns.barplot(x='Subject', y='Present', data=df, palette='Set2')
    
    # Annotate bars
    for p in barplot.patches:
        barplot.annotate(f'{int(p.get_height())}', 
                         (p.get_x() + p.get_width()/2, p.get_height()),
                         ha='center', va='bottom', fontsize=9)
    
    # Rotate x labels and adjust font size
    plt.xticks(rotation=60, ha='right', fontsize=9)
    plt.yticks(fontsize=9)
    
    plt.title("Present Classes per Subject", fontsize=12)
    plt.tight_layout()  # prevent overlapping
    st.pyplot(plt)
    plt.close()


def plot_donut_charts(df):
    n_rows = (len(df)+2)//3
    fig, axes = plt.subplots(n_rows, 3, figsize=(9, n_rows*3))  # smaller figure
    axes = axes.flatten()
    for i, ax in enumerate(axes):
        if i >= len(df):
            ax.axis('off')
            continue
        row = df.iloc[i]
        values = [row['Present'], row['Absent']]
        ax.pie(values, labels=['',''], colors=['#1abc9c','#f39c12'],
               startangle=90, wedgeprops={'width':0.4,'edgecolor':'white'})
        ax.text(0,0,f"{row['Attendance%']:.0f}%", ha='center', va='center', fontsize=10, fontweight='bold')
        ax.set_title(row['Subject'], fontsize=10, fontweight='bold')
    plt.tight_layout()
    st.pyplot(fig)
    plt.close()

def target_attendance(present, total_classes, target_percent):
    x = sp.symbols('x')
    solution = sp.solve((present + x)/(total_classes + x) - target_percent/100, x)
    return int(solution[0]) if solution else 0

def plot_pie_chart(subject, present, absent):
    values = [present, absent]
    labels = ['Present', 'Absent']
    colors = ['#1abc9c','#f39c12']
    plt.figure(figsize=(5,5))  # smaller pie chart
    plt.pie(values, labels=labels, autopct='%1.1f%%', startangle=90,
            colors=colors, wedgeprops={'edgecolor':'white'})
    plt.title(f"Attendance for {subject}", fontsize=12)
    st.pyplot(plt)
    plt.close()

def generate_pdf(df, subject, target_percent, classes_needed, total_present, total_absent, target_aggregate):
    pdf = FPDF('P','mm','A4')
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=10)
    pdf.set_font("Arial",'B',20)
    pdf.cell(0,10,"Attendance Report",ln=True,align='C')
    pdf.ln(10)

    pdf.set_font("Arial",'B',14)
    pdf.cell(0,8,"Aggregate Attendance",ln=True)
    pdf.set_font("Arial",'',12)
    total_classes = total_present + total_absent
    overall_attendance = total_present/total_classes*100 if total_classes>0 else 0
    pdf.cell(0,6,f"Total Present: {total_present}",ln=True)
    pdf.cell(0,6,f"Total Absent: {total_absent}",ln=True)
    pdf.cell(0,6,f"Overall Attendance: {overall_attendance:.1f}%",ln=True)
    pdf.ln(5)

    pdf.set_font("Arial",'B',14)
    pdf.cell(0,8,"Subjects Attendance Data",ln=True)
    pdf.set_font("Arial",'',12)
    for idx,r in df.iterrows():
        pdf.cell(0,6,f"{r['Subject']}: Present {r['Present']}, Absent {r['Absent']}, Attendance {r['Attendance%']:.1f}%",ln=True)
    pdf.ln(5)

    pdf.set_font("Arial",'B',14)
    pdf.cell(0,8,"Target Attendance",ln=True)
    pdf.set_font("Arial",'',12)
    pdf.cell(0,6,f"Subject: {subject}",ln=True)
    pdf.cell(0,6,f"Target: {target_percent}%",ln=True)
    pdf.cell(0,6,f"Classes needed to reach target: {classes_needed}",ln=True)
    pdf.cell(0,6,f"Target Aggregate Attendance: {target_aggregate}%",ln=True)
    return pdf.output(dest='S').encode('latin-1')

# -------------------------- Interface --------------------------
# Option: upload or URL
upload_option = st.radio("How do you want to provide the CSV?", ("Upload File", "CSV URL"))

df = None

if upload_option == "Upload File":
    uploaded_file = st.file_uploader("Upload CSV", type=None)  # Allow all file types
    if uploaded_file:
        if uploaded_file.name.endswith('.csv'):
            df = load_data(uploaded_file)
        else:
            st.error("Please upload a CSV file!")
elif upload_option == "CSV URL":
    url = st.text_input("Enter CSV file URL")
    if url:
        try:
            df = pd.read_csv(url)
            df['Total'] = df['Present'] + df['Absent']
            df['Attendance%'] = df['Present'] / df['Total'] * 100
        except Exception as e:
            st.error(f"Error loading CSV: {e}")

# If data is loaded
if df is not None:
    st.subheader("Preview")
    st.dataframe(df)

    # Aggregate Attendance
    st.subheader("📊 Aggregate Attendance")
    total_present = df['Present'].sum()
    total_absent = df['Absent'].sum()
    total_classes = total_present + total_absent
    overall_attendance = total_present/total_classes*100 if total_classes>0 else 0
    st.metric("Total Present", total_present)
    st.metric("Total Absent", total_absent)
    st.metric("Overall Attendance %", f"{overall_attendance:.1f}%")

    # Pie chart
    plt.figure(figsize=(5,5))
    plt.pie([total_present,total_absent], labels=['Present','Absent'], autopct='%1.1f%%', startangle=90,
            colors=['#1abc9c','#f39c12'], wedgeprops={'edgecolor':'white'})
    plt.title("Aggregate Attendance", fontsize=12)
    st.pyplot(plt)
    plt.close()

    # Target Attendance per subject
    st.subheader("🎯 Target Attendance per Subject")
    target = st.number_input("Enter your target attendance (%)", min_value=0,max_value=100,value=75)
    subject = st.selectbox("Select Subject", df['Subject'])
    row = df[df['Subject']==subject].iloc[0]
    present = row['Present']
    total_subject_classes = row['Total']
    classes_needed = target_attendance(present,total_subject_classes,target)
    st.write(f"✅ You need to attend **{classes_needed} more classes** in {subject} to reach {target}% attendance.")

    # Target Aggregate Attendance
    st.subheader("🎯 Target Attendance Aggregate")
    target_aggregate = st.number_input("Enter target aggregate attendance (%)", min_value=0,max_value=100,value=75)
    aggregate_needed = target_attendance(total_present,total_classes,target_aggregate)
    st.write(f"🎯 You need to attend **{aggregate_needed} more classes overall** to reach {target_aggregate}% aggregate attendance.")

    # Pie & donut charts
    st.subheader(f"Pie Chart for {subject}")
    plot_pie_chart(subject,present,row['Absent'])

    st.subheader("Bar Chart of Present Classes")
    plot_bar_chart(df)

    st.subheader("Donut Charts per Subject")
    plot_donut_charts(df)

    # PDF Download
    st.subheader("📄 Download PDF Report")
    pdf_bytes = generate_pdf(df, subject, target, classes_needed, total_present, total_absent, target_aggregate)
    st.download_button("📥 Download PDF", data=pdf_bytes, file_name="attendance_report.pdf", mime="application/pdf")
