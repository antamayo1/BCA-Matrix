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
  customers = st.session_state.fileDetails["Customer Name"].unique()
  for (customer, file) in zip(customers, files):
    info = pd.read_excel(file, sheet_name='Data')
    metrics = pd.read_excel(file, sheet_name='Format')
    Plines.extend(info["P Line"].dropna().unique())
    Metrics.extend(metrics["METRIC"].dropna().unique())
    BCA, _, _, _ = standard.getSummary(file)
    st.session_state[customer] = BCA.set_index("Metric")
  return BCAs, list(set(Plines)), list(set(Metrics))

def highlight_negative(val):
  try:
      num = float(val.replace('%','').replace('$','').replace(',','').replace('(','-').replace(')',''))
      color = '#FFECEC' if num < 0 else '#E8F9EE'
      if num == 0:
          color = '#FFFCE7'
  except:
      color = '#E8F2FC'
  return f'background-color: {color}'

def outlier_dict_to_table(outlier_dict):
  if isinstance(outlier_dict, str):
    return outlier_dict
  table = "| Product Line | Retailer | Value |\n|--------------|----------|-------|\n"
  for pline, entries in outlier_dict.items():
    for entry in entries:
      for retailer, value in entry.items():
        table += f"| {pline} | {retailer.strip()} | {value:,.2f} |\n"
  return table

def getDescripancy(comparison):
  # outlier_result = {}
  # customers = list(comparison['Customer'])
  # for pline in comparison.columns[1:]:
  #   values = []
  #   cust_names = []
  #   for idx, v in enumerate(comparison[pline]):
  #     if v != '-' and v != '':
  #       try:
  #         val = float(str(v).replace('%','').replace(',','').replace('$','').replace('(','-').replace(')',''))
  #         values.append(val)
  #         cust_names.append(customers[idx])
  #       except:
  #         continue
  #   if len(values) > 2:
  #     q1 = np.percentile(values, 25)
  #     q3 = np.percentile(values, 75)
  #     iqr = q3 - q1
  #     lower = q1 - 1.5 * iqr
  #     upper = q3 + 1.5 * iqr
  #     outliers = []
  #     for name, val in zip(cust_names, values):
  #       if val < lower or val > upper:
  #         outliers.append({name: val})
  #     if outliers:
  #       outlier_result[pline] = outliers

  #     if outlier_result:
  #       outlier =  str(outlier_result)
  #     else:
  #       outlier = "No outliers detected for any product line."
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
      lower = val * 0.9
      upper = val * 1.1
      # Compare val's range to all other values
      others = [v for i, v in enumerate(values) if i != idx]
      if all(other < lower or other > upper for other in others):
        outliers.append(cust_names[idx])
    if outliers:
        outlier_result[pline] = outliers

    if outlier_result:
      outlier_string = outlier_result
    else:
      outlier_string = "No outliers detected for any product line."

      # response = AI_client.chat.completions.create(
      #   model="gpt-3.5-turbo",
      #   messages=[
      #       {
      #           "role": "system",
      #           "content": (
      #               "You are an expert business case analyst specializing in financial impact assessment and strategic decision-making. "
      #               "You analyze the results of an outlier test and provide insights on potential business implications."
      #           )
      #       },
      #       {
      #           "role": "user",
      #           "content": f'''
      #   You are given a string that is either "No outliers detected for any product line." or a structured data like this:
      #   {outlier}
      #   These are the product lines that have outliers, and inside them is the retailer and the value of it being an outlier.

      #   Please output a markdown table for each product line with outliers, using this format:

      #   ### <Product Line>
      #   | Retailer   | Value   |
      #   |------------|---------|
      #   | Amazon     | 123.45  |
      #   | Amazon 2   | 98.76   |

      #   After the tables, provide a brief executive summary of the business implications. If there are no outliers, simply state "No outliers detected for any product line."
      #   '''
      #       }
      #   ],
      #   temperature=0.25
      # )
  

  return outlier_string

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
      input_files = st.file_uploader(
        "file input",
        accept_multiple_files=True,
        type=['xlsx', 'xls'],
        label_visibility="collapsed"
      )
    if input_files:
      st.success(f"**Detected {len(input_files)} file(s) successfully!**", icon="✅")
    if input_files:
      st.session_state.fileDetails = getFileDetails(input_files)
      column1, column2 = st.columns([2, 1])
      with column1:
        st.subheader("Detected Customers Details", anchor=False)
        with st.expander("View details"):
          BCAs, Plines, Metrics = getBCAs(input_files)
          st.dataframe(st.session_state.fileDetails, hide_index=True)
      with column2:
        st.subheader("Detected Product Lines", anchor=False)
        with st.expander("View details"):
          plines = pd.DataFrame(Plines, columns=["Product Line/s"])
          st.dataframe(plines, hide_index=True)
      st.subheader("Difference Matrix", anchor=False)
      selectedMetric = st.selectbox("Select Metric for Comparison", options=Metrics)
      comparison = pd.DataFrame(columns=['Customer'])
      comparison['Customer'] = st.session_state.fileDetails["Customer Name"].unique()
      for pline in Plines:
        values = []
        for customer in comparison['Customer']:
          try:
            values.append(st.session_state[customer].loc[selectedMetric, f'{pline} Cumulative'])
          except:
            values.append('-')
        comparison[pline] = values

      styled_df = comparison.set_index('Customer').map(table_format, metric=selectedMetric)
      styled = styled_df.style.map(highlight_negative)

      st.dataframe(styled)
      with st.spinner("Analyzing discrepancies..."):
        try:
          st.table(getDescripancy(comparison))
        except:
          st.success("No discrepancies found.", icon="✅")
    else:
      st.error("Please upload at least one Excel file to proceed.", icon="❗")
  
  _, footer, _ = st.columns([1, 2, 1])
  with footer:
    st.markdown("""
    <div style="text-align: center; color: #6c757d; font-size: 14px; margin-top: 30px;">
      <p style="margin-bottom: 0px;"><strong>Rapid BCA Analyzer</strong></p>
      <a style="margin-bottom: 0px; text-decoration: none;" href="https://lernmoreconsulting.com">© 2025 LernMore Consulting</a>
      <p>Secure • Fast • Accurate</p>
    </div>
    """, unsafe_allow_html=True)
