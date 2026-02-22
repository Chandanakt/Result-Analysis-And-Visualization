# 🎓 Student Result Dashboard (Streamlit)

A **web-based interactive dashboard** built with **Streamlit, Pandas, and Plotly** that visualizes and analyzes student academic performance from Excel result sheets.

This system supports **multiple departments, batches, and semesters**, auto-detects uploaded Excel files, normalizes VTU-style result sheets, and provides insights such as **SGPA trends, pass/fail distribution, subject analysis, top performers, and batch comparisons**.

---

## 🚀 Features

* 📂 Upload multiple Excel result sheets
* 🧠 Auto-detect department, batch, and semester from filenames
* 🔄 Normalize VTU-style wide Excel sheets into structured format
* 📊 Interactive charts using Plotly
* 👨‍🎓 Total students & average SGPA overview
* 📘 Subject-wise internal/external marks analysis
* 🏆 Top students ranking by SGPA
* 📊 Batch-to-batch and department comparison
* 📥 Downloadable Excel template for data entry

---

## 🛠️ Tech Stack

* Python 3.8+
* Streamlit
* Pandas
* Plotly Express
* OpenPyXL

---

## 📁 Project Structure

``` bash
student-result-dashboard/
│
├── streamlit_student_dashboard_full.py
├── data/
│   ├── Result_sheet_Template.xlsx
│   ├── CSE_2024_SEM1.xlsx
│   ├── AIML_2024_SEM2.xlsx
│   └── ...
│
├── requirements.txt
└── README.md

```
---

## 📦 Installation

### 1️⃣ Clone Repository

```bash
git clone https://github.com/Chandanakt/Result-Analysis-And-Visualization.git
cd Result-Analysis-And-Visualization
````
### 2️⃣ Install Dependencies

```bash
pip install streamlit pandas plotly openpyxl
pip install -r requirements.txt
```
### ▶️ Run Application

```bash
streamlit run streamlit_student_dashboard_full.py
```

---

## 🧾 Excel File Naming Format

To enable auto-detection: DEPT_YEAR_SEMn.xlsx
Examples:
* CSE_2024_SEM1.xlsx
* AIML_2023_SEM5.xlsx
* ISE_2022_SEM3.xlsx

---

## 📊 Dashboard Modules

### 🏠 Dashboard
* Total Students
* Average SGPA
* Pass vs Fail Pie Chart
* Final Result Distribution

### 📘 Subject Analysis
* Avg Internal Marks
* Avg External Marks
* Subject Pass/Fail
* Student-wise marks table

### 🏆 Top Students
* Top N students by SGPA
* Bar chart + table

### 📊 Batch Comparison
* Compare batches in same department
* Compare SGPA across departments

---

## 🧠 How Normalization Works
The system converts VTU-style wide Excel sheets into a long format with columns:
* University Seat Number
* Student Name
* Subject Code
* Subject Name
* Internal Marks
* External Marks
* Total Marks
* Credit
* Grade Point
* SGPA
* Percentage
* Final Result
* Rank

---

## 👤 Author
Chandana K T & Amulya U 
Computer Science Undergraduate, GSSSIETW
