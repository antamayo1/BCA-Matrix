import streamlit as st
import pandas as pd
import standard
import numpy as np
from openai import OpenAI

AI_client = OpenAI(
  api_key=st.secrets["OPEN_AI_KEY"]
)

def table_format(x, metric):
  try:
    num = float(x)
    if np.isnan(num):
      return ""
    if metric == "Defect %" or metric == "MARGIN %" or metric == "Contribution Margin %":
      if num < 0:
        return f"{abs(num*100):,.2f} %"
      return f"{num*100:,.2f} %"
    elif metric == "QTY Gross" or metric == "QTY Defect" or metric == "QTY Total":
      if num < 0:
        return f'{(int(num)):,}'
      return f'{(int(num)):,}'
    if num < 0:
      return f"$ ({abs(num):,.2f})"
    return f"$ {num:,.2f}"
  except:
    return x

st.set_page_config(
  page_title="Rapid BCA Matrix Analyzer",
  page_icon="logo-spectra-premium.jpg", 
  layout="wide"
)

def check_password():
  def password_entered():
    if (st.session_state["username"] == "BCA_User" and st.session_state["password"] == "Analyzer"):
      st.session_state["authenticated"] = True
    else:
      st.error("Incorrect username or password")
      st.session_state["authenticated"] = False
      
  _, col, _ = st.columns([2, 1, 2])
  with col:
      if "authenticated" not in st.session_state or st.session_state["authenticated"] is False:
        container = st.container(border=True)
        with container:
          st.image("logo-spectra-premium.jpg", width=300)
          st.session_state["username"] = st.text_input("Username", key="username_input")
          st.session_state["password"] = st.text_input("Password", type="password", key="password_input")
          st.button("Login", on_click=password_entered, key="login_button", use_container_width=True, type="primary")
          return False
      elif not st.session_state["authenticated"]:
        return False
      else:
        return True

def getBCAs(files):
  BCAs = {}
  Plines = []
  Metrics = []
  PerUnitMetrics = []
  customers = st.session_state.fileDetails["Customer Name"].unique()
  for (customer, file) in zip(customers, files):
    info = pd.read_excel(file, sheet_name='Data')
    metrics = pd.read_excel(file, sheet_name='Format')
    Plines.extend(info["P Line"].dropna().unique())
    Metrics.extend(metrics["METRIC"].dropna().unique())
    BCA, _, _, _ = standard.getSummary(file)
    PerUnitMetrics.extend(BCA[~pd.isna(BCA.iloc[:, 2])].loc[:, "Metric"].tolist())
    st.session_state[customer] = BCA.set_index("Metric")
  return BCAs, list(set(Plines)), list(set(Metrics)), list(set(PerUnitMetrics))

def highlight_negative(val):
  try:
    num = float(val.replace('%','').replace('$','').replace(',','').replace('(','-').replace(')',''))
    color = '#FFECEC' if num < 0 else '#E8F9EE'
    if num == 0:
      color = '#FFFCE7'
  except:
    color = '#E8F2FC'
  return f'background-color: {color}'

def getDescripancy(comparison):
  outlier_result = {}
  customers = list(comparison['Customer'])
  for pline in comparison.columns[1:]:
    values = []
    cust_names = []
    for idx, v in enumerate(comparison[pline]):
      if v != '-' and v != '':
        try:
          val = float(str(v).replace('%','').replace(',','').replace('$','').replace('(','-').replace(')',''))
          values.append(val)
          cust_names.append(customers[idx])
        except:
          continue
    outliers = []
    for idx, val in enumerate(values):
      lower = min(val * 0.95, val * 1.05)
      upper = max(val * 0.95, val * 1.05)
      others = [v for i, v in enumerate(values) if i != idx]
      if all(other < lower or other > upper for other in others):
        outliers.append(cust_names[idx])
    if outliers:
      outlier_result[pline] = outliers
  return outlier_result

def getFileDetails(files):
    file_details = []
    for file in files:
        [name, date] = file.name.split("-")
        file_details.append({
            "Customer Name": name,
            "Date": date.replace(".xlsx", "").replace(".xls", ""),
        })
    file_details = pd.DataFrame(file_details)
    return file_details

if check_password():
  
  # Initializations
  st.session_state.mode = "Cumulative"

  header_container = st.container()
  with header_container:
    col1, col2 = st.columns([3, 1])
    with col1:
      st.markdown("""
      <div class="title-section">
        <h1 style="margin-bottom: 5px;">Rapid BCA Matrix Analyzer</h1>
        <h3 style="color: #6c757d; font-weight: 400; margin-top: 0;">Instantly Analyze Business Cases</h3>
      </div>
      """, unsafe_allow_html=True)

  with col2:
    st.markdown("""
    <div class="logo-section">
    """, unsafe_allow_html=True)
    st.image("logo-spectra-premium.jpg", width=300)
    st.markdown("</div>", unsafe_allow_html=True)

  body_container = st.container(
    border=True
  )

  with body_container:
    input_tab = st.tabs(["Matrix Comparison "])
    st.subheader("Upload Files", anchor=False)
    with st.expander("View details"):
      st.warning("**Please note the filename format `<customer name>-<date>.xlsx` or `<customer name>-<date>.xlsx`**", icon="⚠️")
      st.markdown("**Upload your Excel files containing BCA matrices. Supported formats: `.xlsx`, `.xls`.**")
      st.session_state.input_files = st.file_uploader(
        "file input",
        accept_multiple_files=True,
        type=['xlsx', 'xls'],
        label_visibility="collapsed"
      )
    if st.session_state.input_files:
      st.success(f"**Detected {len(st.session_state.input_files)} file(s) successfully!**", icon="✅")
    if st.session_state.input_files:
      st.session_state.fileDetails = getFileDetails(st.session_state.input_files)
      column1, column2 = st.columns([2, 1])
      with column1:
        st.subheader("Detected Customers Details", anchor=False)
        with st.expander("View details"):
          BCAs, Plines, Metrics, PerUnitMetrics = getBCAs(st.session_state.input_files)
          st.dataframe(st.session_state.fileDetails, hide_index=True)
      with column2:
        st.subheader("Detected Product Lines", anchor=False)
        with st.expander("View details"):
          plines = pd.DataFrame(Plines, columns=["Product Line/s"])
          st.dataframe(plines, hide_index=True)
      st.subheader("Difference Matrix", anchor=False)
      column1, column2 = st.columns([1, 4])
      with column1:
        st.session_state.mode = st.radio("Select View", ["Cumulative", "Per Unit"], index=0)
      with column2:
        if st.session_state.mode == "Cumulative":
          selectedMetric = st.selectbox("Select Metric for Comparison", options=Metrics, index=Metrics.index("Contribution Margin"))
        else:
          selectedMetric = st.selectbox("Select Metric for Comparison", options=PerUnitMetrics, index=PerUnitMetrics.index("Contribution Margin"))
  
      comparison = pd.DataFrame(columns=['Customer'])
      comparison['Customer'] = st.session_state.fileDetails["Customer Name"].unique()
      for pline in Plines:
        values = []
        for customer in comparison['Customer']:
          try:
            if st.session_state.mode == "Per Unit":
              values.append(st.session_state[customer].loc[selectedMetric, f'{pline} Per Unit'])
            else:
              values.append(st.session_state[customer].loc[selectedMetric, f'{pline} Cumulative'])
          except:
            values.append('-')
        comparison[pline] = values

      styled_df = comparison.set_index('Customer').map(table_format, metric=selectedMetric)
      styled = styled_df.style.map(highlight_negative)

      st.dataframe(styled)
      descripancy = pd.DataFrame(getDescripancy(comparison))
      st.subheader("Discrepancy Report", anchor=False)
      st.write("These are the **product lines** with price discrepancies from the other retailers. Consider the listed retailers to be outliers in certain product lines.")
      if descripancy.empty:
        st.success("No discrepancies found.", icon="✅")
      else:
        st.dataframe(descripancy, hide_index=True)
    else:
      st.error("Please upload at least one Excel file to proceed.", icon="❗")
  
  _, footer, _ = st.columns([1, 2, 1])
  with footer:
    st.markdown("""
    <div style="text-align: center; color: #6c757d; font-size: 14px; margin-top: 30px;">
      <p style="margin-bottom: 0px;"><strong>Rapid BCA Matrix Analyzer</strong></p>
      <a style="margin-bottom: 0px; text-decoration: none;" href="https://lernmoreconsulting.com">© 2025 LernMore Consulting</a>
      <p>Secure • Fast • Accurate</p>
    </div>
    """, unsafe_allow_html=True)
