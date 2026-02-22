# streamlit_student_dashboard_full.py
import streamlit as st
import pandas as pd
import plotly.express as px
import re
import os
from typing import Tuple, Dict, Optional

# ===================== PAGE CONFIG =====================
st.set_page_config(page_title="Student Result Dashboard", layout="wide")

# ===================== STYLE =====================
st.markdown("""
<style>
.card {
    background-color: #ffffff;
    padding: 1rem 1.25rem;
    border-radius: 1rem;
    box-shadow: 0 2px 8px rgba(0,0,0,0.08);
    margin-bottom: 1rem;
}
</style>
""", unsafe_allow_html=True)

# ===================== CONFIG / CONSTANTS =====================
DEPARTMENTS = ["CSE", "AIML", "ISE", "AIDS"]
YEARS = ["2022", "2023", "2024", "2025"]
SEMESTERS = [f"Semester {i}" for i in range(1, 9)]

DEFAULT_DATA_DIR = "data"
SCAN_DIRS = [DEFAULT_DATA_DIR, "/mnt/data"]

# ===================== HELPERS: DISPLAY =====================
def display_card(title, value, icon="🎯"):
    st.markdown(
        f"<div class='card'><h3>{icon} {title}</h3>"
        f"<h2 style='color:#16a085;font-weight:bold'>{value}</h2></div>",
        unsafe_allow_html=True
    )

# ===================== HELPERS: FILENAME PARSING =====================
def parse_filename_option1(fn: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """
    Try to parse filenames like:
    AIML_2024_2SEM.xlsx
    CSE-2023-sem5.xlsx
    ISE2022_08sem.xlsx
    """
    fn_clean = os.path.basename(fn).strip()
    fn_clean = re.sub(r'\s+\.xlsx$', '.xlsx', fn_clean, flags=re.IGNORECASE)
    name, _ = os.path.splitext(fn_clean)
    name = name.replace('-', '_').replace(' ', '_')
    name_low = name.lower()

    # Pattern: DEPT_YYYY_[N]sem OR DEPT_YYYY_semN OR DEPT_YYYY_NSEM
    m = re.search(
        r'(?P<dept>[a-zA-Z]+)[_\s-]*[_]?(?P<year>20\d{2})[_\s-]*[_]?'
        r'(?:(?P<n>\d{1,2})[_]?(?:sem|semester)|sem(?:ester)?[_\s-]*(?P<n2>\d{1,2}))',
        name_low
    )
    if m:
        dept = (m.group('dept') or '').upper()
        year = m.group('year')
        n = m.group('n') or m.group('n2')
        try:
            sem = int(n)
            if dept and year:
                return dept.upper(), f"Batch_{year}", f"Semester {sem}"
        except Exception:
            pass

    # Fallback: just DEPT + YEAR and try to guess sem from first digit
    m2 = re.search(r'(?P<dept>[a-zA-Z]+)[_\s-]*(?P<year>20\d{2})', name_low)
    if m2:
        dept = m2.group('dept').upper()
        year = m2.group('year')
        m3 = re.search(r'(\d)', name_low)
        if m3:
            sem = int(m3.group(1))
            return dept, f"Batch_{year}", f"Semester {sem}"
        return dept, f"Batch_{year}", None

    return None, None, None

# ===================== HELPERS: EXCEL LOADING & NORMALIZATION =====================
def safe_read_excel(path_or_file) -> Optional[pd.DataFrame]:
    """Read Excel safely; show error if openpyxl is missing or file is bad."""
    try:
        df = pd.read_excel(path_or_file, engine="openpyxl")
        return df
    except ImportError:
        st.sidebar.error(
            "Missing optional dependency 'openpyxl'. "
            "Install it with: pip install openpyxl"
        )
        return None
    except Exception as e:
        name = getattr(path_or_file, "name", str(path_or_file))
        st.sidebar.error(f"Error reading {name}: {e}")
        return None

def _find_col(cols, substrings):
    """Helper: find first column whose name contains any of the substrings (case-insensitive)."""
    for c in cols:
        cl = c.lower()
        if any(s in cl for s in substrings):
            return c
    return None

def normalize_vtu_sheet(df: pd.DataFrame) -> pd.DataFrame:
    """
    Convert VTU 2022-style wide result sheet into a long/normalized table.

    Output columns:
        Semester
        University Seat Number
        Student Name
        Subject Code
        Subject Name
        Internal Marks
        External Marks
        Total Marks (Subject)
        Subject Result
        Credit
        Grade Point
        C*GP
        Total C*GP
        Total Credits
        SGPA
        Total Marks (Overall)
        Percentage
        Final Result
        Rank
    """
    df = df.copy()

    # Clean headers
    df.columns = (
        df.columns.astype(str)
        .str.strip()
        .str.replace('\n', ' ')
        .str.replace(r'\s+', ' ', regex=True)
        .str.title()
    )
    cols = list(df.columns)

    # Core identity columns
    sem_col = _find_col(cols, ['semester'])
    usn_col = _find_col(cols, ['university seat number', 'usn'])
    name_col = _find_col(cols, ['student name', 'name'])

    # Summary columns
    total_cgp_col = _find_col(cols, ['total c*gp', 'total cgp'])
    total_credits_col = _find_col(cols, ['total credits'])
    sgpa_col = _find_col(cols, ['sgpa'])
    total_marks_col = _find_col(cols, ['total marks'])
    percent_col = _find_col(cols, ['%', 'percentage'])

    # Final result column: usually right after % column
    final_result_col = None
    if percent_col and percent_col in cols:
        idx_p = cols.index(percent_col)
        if idx_p + 1 < len(cols) and cols[idx_p + 1].startswith("Result"):
            final_result_col = cols[idx_p + 1]
    if not final_result_col:
        result_candidates = [c for c in cols if c.startswith("Result")]
        if result_candidates:
            final_result_col = result_candidates[-1]

    rank_col = _find_col(cols, ['rank'])

    # Subject block starts: "Subject Code", "Subject Code.1", ...
    sub_code_indices = [
        i for i, c in enumerate(cols) if c.startswith("Subject Code")
    ]

    normalized_rows = []

    for _, row in df.iterrows():
        sem = row.get(sem_col) if sem_col else None
        usn = row.get(usn_col) if usn_col else None
        name = row.get(name_col) if name_col else None

        total_cgp_val = row.get(total_cgp_col) if total_cgp_col else None
        total_credits_val = row.get(total_credits_col) if total_credits_col else None
        sgpa_val = row.get(sgpa_col) if sgpa_col else None
        total_marks_val = row.get(total_marks_col) if total_marks_col else None
        percent_val = row.get(percent_col) if percent_col else None
        final_result_val = row.get(final_result_col) if final_result_col else None
        rank_val = row.get(rank_col) if rank_col else None

        for idx in sub_code_indices:
            # Each subject block assumed 9 columns
            if idx + 8 >= len(cols):
                continue

            sub_code = row.iloc[idx]
            if pd.isna(sub_code) or str(sub_code).strip() == "":
                continue

            sub_name = row.iloc[idx + 1]
            internal = row.iloc[idx + 2]
            external = row.iloc[idx + 3]
            total_sub = row.iloc[idx + 4]
            sub_result = row.iloc[idx + 5]
            credit = row.iloc[idx + 6]
            gp = row.iloc[idx + 7]
            cgp = row.iloc[idx + 8]

            normalized_rows.append({
                "Semester": sem,
                "University Seat Number": usn,
                "Student Name": name,
                "Subject Code": sub_code,
                "Subject Name": sub_name,
                "Internal Marks": pd.to_numeric(internal, errors='coerce'),
                "External Marks": pd.to_numeric(external, errors='coerce'),
                "Total Marks (Subject)": pd.to_numeric(total_sub, errors='coerce'),
                "Subject Result": None if pd.isna(sub_result) else str(sub_result),
                "Credit": pd.to_numeric(credit, errors='coerce'),
                "Grade Point": pd.to_numeric(gp, errors='coerce'),
                "C*GP": pd.to_numeric(cgp, errors='coerce'),
                # summary columns (same for all subjects of that student)
                "Total C*GP": pd.to_numeric(total_cgp_val, errors='coerce') if total_cgp_val is not None else None,
                "Total Credits": pd.to_numeric(total_credits_val, errors='coerce') if total_credits_val is not None else None,
                "SGPA": pd.to_numeric(sgpa_val, errors='coerce') if sgpa_val is not None else None,
                "Total Marks (Overall)": pd.to_numeric(total_marks_val, errors='coerce') if total_marks_val is not None else None,
                "Percentage": percent_val,
                "Final Result": None if pd.isna(final_result_val) else str(final_result_val) if final_result_val is not None else None,
                "Rank": pd.to_numeric(rank_val, errors='coerce') if rank_val is not None else None
            })

    if not normalized_rows:
        # Fallback: if sheet is not VTU-style, just return cleaned original
        st.warning("Could not detect VTU-style subject blocks; using raw sheet.")
        return df

    norm_df = pd.DataFrame(normalized_rows)
    # Basic clean
    for col in norm_df.select_dtypes(include=['object']):
        norm_df[col] = norm_df[col].astype(str).str.strip()
    norm_df.drop_duplicates(inplace=True)
    return norm_df

def format_excel(df: pd.DataFrame) -> pd.DataFrame:
    """Main entry: normalize VTU sheet into long format."""
    try:
        return normalize_vtu_sheet(df)
    except Exception as e:
        st.error(f"Error normalizing Excel: {e}")
        return df

# ===================== PLACEHOLDER PATH MAPPING =====================
placeholder_mapping: Dict[str, Dict[str, Dict[str, Optional[str]]]] = {}
for dept in DEPARTMENTS:
    placeholder_mapping[dept] = {}
    for year in YEARS:
        batch = f"Batch_{year}"
        placeholder_mapping[dept][batch] = {}
        for sem in range(1, 9):
            placeholder_mapping[dept][batch][f"Semester {sem}"] = os.path.join(
                DEFAULT_DATA_DIR,
                f"{dept}_{year}_SEM{sem}.xlsx"
            )

# ===================== SCAN FILESYSTEM FOR EXISTING FILES =====================
filesystem_files: Dict[str, Dict[str, Dict[str, Optional[str]]]] = {}
for dept in DEPARTMENTS:
    filesystem_files[dept] = {}
    for year in YEARS:
        filesystem_files[dept][f"Batch_{year}"] = {}
        for sem in SEMESTERS:
            filesystem_files[dept][f"Batch_{year}"][sem] = None

for directory in SCAN_DIRS:
    if not os.path.isdir(directory):
        continue
    for fname in os.listdir(directory):
        fpath = os.path.join(directory, fname)
        if not re.search(r'\.xls[x]?$', fname, flags=re.IGNORECASE):
            continue
        dept, batch, sem = parse_filename_option1(fname)
        if dept and batch:
            if sem is None:
                m = re.search(r'[_\s-](\d{1,2})[_\s-]*(?:sem|semester)', fname, flags=re.IGNORECASE)
                if m:
                    sem = f"Semester {int(m.group(1))}"
            if sem is None:
                sem = "Semester 1"
            if dept not in filesystem_files:
                filesystem_files[dept] = {}
            filesystem_files.setdefault(dept, {}).setdefault(batch, {})[sem] = fpath

# ===================== SESSION STATE INIT =====================
if 'uploaded_overrides' not in st.session_state:
    st.session_state.uploaded_overrides = {}  # dept->batch->sem->df
if 'final_mapping' not in st.session_state:
    st.session_state.final_mapping = {}  # dept->batch->sem->normalized_df

# Merge order: uploaded > scanned > placeholder files
def build_final_mapping():
    mapping = {}
    for dept in DEPARTMENTS:
        mapping[dept] = {}
        for year in YEARS:
            batch = f"Batch_{year}"
            mapping[dept][batch] = {}
            for sem in SEMESTERS:
                df_obj = None
                overrides = st.session_state.get('uploaded_overrides', {})
                if dept in overrides and batch in overrides[dept] and sem in overrides[dept][batch]:
                    df_obj = overrides[dept][batch][sem]

                if df_obj is None:
                    fs_df_path = filesystem_files.get(dept, {}).get(batch, {}).get(sem)
                    if fs_df_path:
                        df_read = safe_read_excel(fs_df_path)
                        if df_read is not None:
                            df_obj = format_excel(df_read)

                if df_obj is None:
                    placeholder_path = placeholder_mapping[dept][batch][sem]
                    if os.path.exists(placeholder_path):
                        df_read = safe_read_excel(placeholder_path)
                        if df_read is not None:
                            df_obj = format_excel(df_read)

                mapping[dept][batch][sem] = df_obj
    st.session_state.final_mapping = mapping

build_final_mapping()

# ===================== UPLOAD UI (overrides) =====================
st.sidebar.markdown("---")
st.sidebar.subheader("Upload Excel files")
uploaded_files = st.sidebar.file_uploader(
    "Choose one or more Excel files",
    accept_multiple_files=True,
    type=['xls', 'xlsx']
)
if uploaded_files:
    added = 0
    for f in uploaded_files:
        dept, batch, sem = parse_filename_option1(f.name)
        if not dept or not batch:
            st.sidebar.warning(
                f"Could not auto-detect metadata for {f.name}. "
                "Assign it manually below."
            )
        df_raw = safe_read_excel(f)
        if df_raw is None:
            st.sidebar.error(f"Could not read {f.name}. Skipping.")
            continue
        df_norm = format_excel(df_raw)
        if dept and batch and sem:
            st.session_state.uploaded_overrides.setdefault(dept, {}).setdefault(batch, {})[sem] = df_norm
            added += 1
        else:
            st.session_state.uploaded_overrides.setdefault("UNKNOWN_UPLOADS", {})[f.name] = df_norm
            added += 1
    if added:
        st.sidebar.success(f"{added} file(s) processed and added as overrides.")
    build_final_mapping()

# ===================== TEMPLATE DOWNLOAD IN SIDEBAR =====================
st.sidebar.markdown("---")
st.sidebar.subheader("Download Excel Template")

template_path = "data/Result_sheet Template.xlsx"   # ← FIX THIS LINE

if os.path.exists(template_path):
    with open(template_path, "rb") as tf:
        st.sidebar.download_button(
            label="📄 Download Result Sheet Template",
            data=tf,
            file_name="Result_sheet_Template.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
else:
    st.sidebar.error("Template file not found in data/ folder!")


# Manual assignment for unknown uploads
if 'UNKNOWN_UPLOADS' in st.session_state.uploaded_overrides and st.session_state.uploaded_overrides['UNKNOWN_UPLOADS']:
    st.sidebar.markdown("---")
    st.sidebar.subheader("Assign metadata for unrecognized uploads")
    unknown_items = list(st.session_state.uploaded_overrides['UNKNOWN_UPLOADS'].keys())
    for key in unknown_items:
        st.sidebar.write(f"File: {key}")
        dept_sel = st.sidebar.selectbox(f"Dept for {key}", options=["--"] + DEPARTMENTS, key=f"man_dept_{key}")
        batch_sel = st.sidebar.selectbox(
            f"Batch for {key}",
            options=["--"] + [f"Batch_{y}" for y in YEARS],
            key=f"man_batch_{key}"
        )
        sem_sel = st.sidebar.selectbox(
            f"Semester for {key}",
            options=["--"] + SEMESTERS,
            key=f"man_sem_{key}"
        )
        if dept_sel != "--" and batch_sel != "--" and sem_sel != "--":
            df_obj = st.session_state.uploaded_overrides['UNKNOWN_UPLOADS'].pop(key)
            st.session_state.uploaded_overrides.setdefault(dept_sel, {}).setdefault(batch_sel, {})[sem_sel] = df_obj
            st.sidebar.success(f"Assigned {key} -> {dept_sel}/{batch_sel}/{sem_sel}")
            build_final_mapping()

# ===================== UI: SELECTORS =====================
st.title("🎓 Student Result Dashboard")

col1, _ = st.columns([3, 1])
with col1:
    st.subheader("Select Department / Batch / Semester")
    dept_choice = st.selectbox("Department", options=["-- Select Dept --"] + DEPARTMENTS)
    if dept_choice == "-- Select Dept --":
        st.warning("Select a department to continue.")
        st.stop()
    batch_choice = st.selectbox("Batch (year)", options=["-- Select Batch --"] + [f"Batch_{y}" for y in YEARS])
    if batch_choice == "-- Select Batch --":
        st.warning("Select a batch to continue.")
        st.stop()
    sem_choice = st.selectbox("Semester", options=["-- Select Semester --"] + SEMESTERS)
    if sem_choice == "-- Select Semester --":
        st.warning("Select a semester to continue.")
        st.stop()

def get_df(dept: str, batch: str, sem: str) -> Optional[pd.DataFrame]:
    try:
        return st.session_state.final_mapping.get(dept, {}).get(batch, {}).get(sem)
    except Exception:
        return None

# ===================== NAVIGATION =====================
st.sidebar.markdown("---")
menu = st.sidebar.radio(
    "Go to:",
    ["🏠 Dashboard", "📘 Subject Analysis", "🏆 Top Students", "📊 Batch Comparison"],
    index=0
)

# Helper: get summary-level df (one row per student)
def get_summary_df(norm_df: pd.DataFrame) -> pd.DataFrame:
    if norm_df is None or norm_df.empty:
        return pd.DataFrame()
    keys = ["University Seat Number"]
    summary_cols = [
        "Student Name", "Semester",
        "Total C*GP", "Total Credits", "SGPA",
        "Total Marks (Overall)", "Percentage", "Final Result", "Rank"
    ]
    summary_df = norm_df.drop_duplicates(subset=keys)
    keep_cols = keys + [c for c in summary_cols if c in norm_df.columns]
    return summary_df[keep_cols]

# ---------- DASHBOARD ----------
if menu == "🏠 Dashboard":
    st.header("📊 Class Overview")
    df = get_df(dept_choice, batch_choice, sem_choice)
    if df is None or df.empty:
        st.warning("No data available for this selection. Upload a file or choose a different semester/batch.")
    else:
        with st.expander("Show Full Normalized Data (Subject-wise)"):
            st.dataframe(df)

        summary_df = get_summary_df(df)
        total_students = summary_df["University Seat Number"].nunique() if not summary_df.empty else 0
        avg_sgpa = None
        if "SGPA" in summary_df.columns:
            avg_sgpa = round(summary_df["SGPA"].dropna().astype(float).mean(), 2)

        c1, c2 = st.columns(2)
        with c1:
            display_card("Total Students", total_students, "👨‍🎓")
        with c2:
            display_card("Average SGPA", avg_sgpa if avg_sgpa is not None else "N/A", "📈")

        if "SGPA" in summary_df.columns:
            st.subheader("Pass vs Fail (by SGPA)")
            pass_mark = st.slider("Pass SGPA threshold", 0.0, 10.0, 5.0, 0.1)
            s = summary_df["SGPA"].astype(float)
            pass_count = (s >= pass_mark).sum()
            fail_count = (s < pass_mark).sum()
            res_df = pd.DataFrame({
                "Result": ["Pass", "Fail"],
                "Count": [int(pass_count), int(fail_count)]
            })
            st.plotly_chart(
                px.pie(res_df, names="Result", values="Count", title="Pass vs Fail Distribution"),
                use_container_width=True
            )

        if "Final Result" in summary_df.columns:
            st.subheader("Final Result Classes (FCD / FC / P / Fail)")
            res_counts = summary_df["Final Result"].value_counts().reset_index()
            res_counts.columns = ["Final Result", "Count"]
            st.plotly_chart(
                px.bar(res_counts, x="Final Result", y="Count", text_auto=True, title="Final Result Distribution"),
                use_container_width=True
            )

# ---------- SUBJECT ANALYSIS ----------
elif menu == "📘 Subject Analysis":
    st.header("📘 Subject Analysis")
    df = get_df(dept_choice, batch_choice, sem_choice)
    if df is None or df.empty:
        st.warning("No data for selection.")
    else:
        if "Subject Name" not in df.columns:
            st.warning("No 'Subject Name' column found in normalized data.")
        else:
            subjects = sorted(df["Subject Name"].dropna().unique().tolist())
            if not subjects:
                st.info("No subject names detected.")
            else:
                subj = st.selectbox("Choose subject", options=subjects)
                if subj:
                    sub_df = df[df["Subject Name"] == subj].copy()
                    if sub_df.empty:
                        st.info("No data for selected subject.")
                    else:
                        col_l, col_r = st.columns(2)
                        if "Internal Marks" in sub_df.columns:
                            with col_l:
                                display_card(
                                    "Avg Internal",
                                    round(sub_df["Internal Marks"].dropna().astype(float).mean(), 2),
                                    "📝"
                                )
                        if "External Marks" in sub_df.columns:
                            with col_r:
                                display_card(
                                    "Avg External",
                                    round(sub_df["External Marks"].dropna().astype(float).mean(), 2),
                                    "📝"
                                )

                        if "Subject Result" in sub_df.columns:
                            cnts = sub_df["Subject Result"].value_counts().reset_index()
                            cnts.columns = ["Result", "Count"]
                            st.plotly_chart(
                                px.pie(cnts, names="Result", values="Count", title="Pass / Fail (Subject)"),
                                use_container_width=True
                            )

                        with st.expander("Show subject-level data"):
                            show_cols = [
                                c for c in [
                                    "University Seat Number", "Student Name",
                                    "Internal Marks", "External Marks",
                                    "Total Marks (Subject)", "Subject Result", "Credit", "Grade Point"
                                ] if c in sub_df.columns
                            ]
                            st.dataframe(sub_df[show_cols])

# ---------- TOP STUDENTS ----------
elif menu == "🏆 Top Students":
    st.header("🏆 Top Students by SGPA")
    df = get_df(dept_choice, batch_choice, sem_choice)
    if df is None or df.empty:
        st.warning("No data.")
    else:
        summary_df = get_summary_df(df)
        if "SGPA" not in summary_df.columns:
            st.warning("SGPA column not present in normalized data.")
        else:
            top_n = st.slider("How many top students?", 3, 50, 10)
            tmp = summary_df.copy()
            tmp["SGPA"] = tmp["SGPA"].astype(float)
            top_df = (
                tmp[["Student Name", "SGPA"]]
                .dropna()
                .drop_duplicates()
                .sort_values("SGPA", ascending=False)
                .head(top_n)
            )
            st.plotly_chart(
                px.bar(top_df, x="Student Name", y="SGPA", text_auto=True, title=f"Top {top_n} Students"),
                use_container_width=True
            )
            with st.expander("Top students table"):
                st.dataframe(top_df)

# ---------- BATCH COMPARISON ----------
elif menu == "📊 Batch Comparison":
    st.header("📊 Batch Comparison")
    mode = st.radio("Mode:", ["Within Same Dept", "Across Departments"])
    if mode == "Within Same Dept":
        dept = st.selectbox("Department", DEPARTMENTS, index=DEPARTMENTS.index(dept_choice))
        batches = [f"Batch_{y}" for y in YEARS]
        b1 = st.selectbox("Batch 1", options=batches, index=batches.index(batch_choice))
        b2 = st.selectbox("Batch 2", options=[b for b in batches if b != b1])
        sem = st.selectbox("Semester", SEMESTERS, index=SEMESTERS.index(sem_choice))

        df1 = get_df(dept, b1, sem)
        df2 = get_df(dept, b2, sem)

        if df1 is None or df2 is None or df1.empty or df2.empty:
            st.warning("Data missing for one or both selected batch/semester.")
        else:
            sum1 = get_summary_df(df1)
            sum2 = get_summary_df(df2)

            c1, c2 = st.columns(2)
            with c1:
                st.markdown(f"### {b1} - {dept}")
                if "Final Result" in sum1.columns:
                    tmp = sum1["Final Result"].value_counts().reset_index()
                    tmp.columns = ["Final Result", "Count"]
                    st.plotly_chart(
                        px.pie(tmp, names="Final Result", values="Count", title=f"{b1} Final Results"),
                        use_container_width=True
                    )
                elif "SGPA" in sum1.columns:
                    st.info("No Final Result column; using SGPA only for averages.")

            with c2:
                st.markdown(f"### {b2} - {dept}")
                if "Final Result" in sum2.columns:
                    tmp = sum2["Final Result"].value_counts().reset_index()
                    tmp.columns = ["Final Result", "Count"]
                    st.plotly_chart(
                        px.pie(tmp, names="Final Result", values="Count", title=f"{b2} Final Results"),
                        use_container_width=True
                    )
                elif "SGPA" in sum2.columns:
                    st.info("No Final Result column; using SGPA only for averages.")

            if "SGPA" in sum1.columns and "SGPA" in sum2.columns:
                avg1 = sum1["SGPA"].dropna().astype(float).mean()
                avg2 = sum2["SGPA"].dropna().astype(float).mean()
                avg_df = pd.DataFrame({
                    "Batch": [b1, b2],
                    "Average SGPA": [avg1, avg2]
                })
                st.plotly_chart(
                    px.bar(avg_df, x="Batch", y="Average SGPA", text_auto=True, title="Average SGPA Comparison"),
                    use_container_width=True
                )

    else:  # Across Departments
        sem = st.selectbox("Semester (across depts)", SEMESTERS, index=SEMESTERS.index(sem_choice))
        batch_sel = st.selectbox(
            "Select Batch (year)",
            [f"Batch_{y}" for y in YEARS],
            index=[f"Batch_{y}" for y in YEARS].index(batch_choice)
        )

        avg_list = []
        for dept in DEPARTMENTS:
            df_tmp = get_df(dept, batch_sel, sem)
            if df_tmp is not None and not df_tmp.empty:
                sum_tmp = get_summary_df(df_tmp)
                if "SGPA" in sum_tmp.columns:
                    avg_list.append({
                        "Department": dept,
                        "Average SGPA": float(sum_tmp["SGPA"].dropna().astype(float).mean())
                    })

        if not avg_list:
            st.warning("No data found for the selected semester/batch across departments.")
        else:
            st.plotly_chart(
                px.bar(pd.DataFrame(avg_list), x="Department", y="Average SGPA",
                       text_auto=True, title=f"{batch_sel} - Avg SGPA Across Departments"),
                use_container_width=True
            )

# ===================== FOOTER & NOTES =====================
st.markdown("---")

used_df = get_df(dept_choice, batch_choice, sem_choice)
if used_df is not None and not used_df.empty:
    st.info(
        f"Data loaded for {dept_choice} / {batch_choice} / {sem_choice} "
        f"— subject-wise rows: {len(used_df)}"
    )
else:
    candidate_paths = []
    scanned = filesystem_files.get(dept_choice, {}).get(batch_choice, {}).get(sem_choice)
    if scanned:
        candidate_paths.append(scanned)
    placeholder_path = placeholder_mapping.get(dept_choice, {}).get(batch_choice, {}).get(sem_choice)
    if placeholder_path:
        candidate_paths.append(placeholder_path)
    if candidate_paths:
        st.info("No dataframe loaded but found candidate files (not successfully read):")
        for p in candidate_paths:
            st.write(f"- {p}")

# === End of file ===
