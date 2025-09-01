from ctypes import util
import pandas as pd

def getSumGivenColumn(Pline, dataframe, column):
  if Pline == 'All':
    return dataframe[column].sum()
  else:
    if 'Pline' in dataframe.columns:
      filtered_data = dataframe[dataframe['Pline'] == Pline]
    elif 'P Line' in dataframe.columns:
      filtered_data = dataframe[dataframe['P Line'] == Pline]
    else:
      raise KeyError("Neither 'Pline' nor 'P Line' column found in dataframe.")
    total_gross = filtered_data[column].sum()
    return total_gross
  
def getQTYTotalAndDefect(dataframe):
  cumulative_columns = [col for col in dataframe.columns if 'Cumulative' in col]
  for column in cumulative_columns:
    QTY_gross = dataframe.loc[dataframe['Metric'] == 'QTY Gross', column].iloc[0]
    QTY_defect = dataframe.loc[dataframe['Metric'] == 'QTY Defect', column].iloc[0]
    dataframe.loc[dataframe['Metric'] == 'QTY Total', column] = QTY_gross + QTY_defect
    dataframe.loc[dataframe['Metric'] == 'Defect %', column] = QTY_defect / QTY_gross if QTY_gross != 0 else 0
  return dataframe

def getSumAndPerUnit(Pline, dataframe, column):
  if Pline == 'All':
    total = dataframe[column].sum()
    per_unit = total / dataframe['L12 Shipped'].sum() if dataframe['L12 Shipped'].sum() != 0 else 0
    return total, per_unit
  else:
    filtered_data = dataframe[dataframe['Pline'] == Pline] or dataframe[dataframe['P Line'] == Pline]
    total = filtered_data[column].sum()
    per_unit = total / filtered_data['L12 Shipped'].sum() if filtered_data['L12 Shipped'].sum() != 0 else 0
    return total, per_unit

# STANDARD HELPER
def extract_parentheses_content(text):
  start = text.find('(')
  end = text.find(')')
  if start != -1 and end != -1 and start < end:
    content = text[start+1:end]
    return [item.strip() for item in content.split(',')]
  return []

# STANDARD HELPER
def getPerUnit(row, column, output):
  return output.loc[row, column] / output.loc['QTY Gross', column]

# STANDARD
def QTY_CALCULATIONS(PRODUCT_LINES, output, DATA, ASSUMPTIONS, volume):
  print(ASSUMPTIONS)
  total_gross = 0
  for line in PRODUCT_LINES:
    gross = getSumGivenColumn(line, DATA, 'Qty')
    output.loc['QTY Gross', f'{line} Cumulative'] = gross + (gross*volume)
    total_gross += output.loc['QTY Gross', f'{line} Cumulative']
    try:
      output.loc['Defect %', f'{line} Cumulative'] = ASSUMPTIONS.loc[line, 'Defect %']
    except:
      output.loc['Defect %', f'{line} Cumulative'] = ASSUMPTIONS.loc['-', 'Defect %']

  output.loc['QTY Gross', 'All Lines Cumulative'] = total_gross
  total_defect = 0
  total_total = 0
  for line in PRODUCT_LINES:
    output.loc['QTY Defect', f'{line} Cumulative'] = output.loc['QTY Gross', f'{line} Cumulative'] * output.loc['Defect %', f'{line} Cumulative'] * -1
    output.loc['QTY Total', f'{line} Cumulative'] = output.loc['QTY Gross', f'{line} Cumulative'] + output.loc['QTY Defect', f'{line} Cumulative']
    total_defect += output.loc['QTY Defect', f'{line} Cumulative']
    total_total += output.loc['QTY Total', f'{line} Cumulative']
  output.loc['QTY Defect', 'All Lines Cumulative'] = total_defect
  output.loc['QTY Total', 'All Lines Cumulative'] = total_total
  defect_percent = total_defect / total_gross
  output.loc['Defect %', 'All Lines Cumulative'] = defect_percent * -1
  return output

# STANDARD
def GET_NETSALES_MARGIN_METRICS(FORMAT):
  defect_idx = FORMAT.index.get_loc('Defect %')
  net_sales_idx = FORMAT.index.get_loc('NET SALES')
  total_variable_cost_idx = FORMAT.index.get_loc('TOTAL VARIABLE COST')

  net_sales_metrics = FORMAT.index[defect_idx+1:net_sales_idx]
  net_sales_list = net_sales_metrics.tolist()
  if 'Agency Rep' in net_sales_list:
    net_sales_list.remove('Agency Rep')
    net_sales_list.append('Agency Rep')
    net_sales_metrics = pd.Index(net_sales_list)

  margin_metrics = FORMAT.index[net_sales_idx+1:total_variable_cost_idx]
  margin_list = margin_metrics.tolist()
  if 'Scrap Return Rate' in margin_list:
    margin_list.remove('Scrap Return Rate')
    margin_list.append('Scrap Return Rate')
    margin_metrics = pd.Index(margin_list)

  return net_sales_metrics, margin_metrics

# STANDARD
def GET_SGA_METRICS(FORMAT):
  margin_idx = FORMAT.index.get_loc('MARGIN %')
  sga_idx = FORMAT.index.get_loc('SG&A')
  sga_metrics = FORMAT.index[margin_idx+1:sga_idx]
  return sga_metrics.tolist()

def NET_SALES_CALCULATIONS(output, DATA, ASSUMPTIONS, NET_SALES_METRICS, PRODUCT_LINES, DEFAULTS, volume):
  for metric in NET_SALES_METRICS:
    total_metric = 0
    specific_pline = extract_parentheses_content(metric)
    if metric == 'Defect':
      for line in PRODUCT_LINES:
        try:
          output.loc[metric, f'{line} Cumulative'] = output.loc['Sales', f'{line} Cumulative'] * ASSUMPTIONS.loc[line, 'Defect %'] * -1
        except:
          output.loc[metric, f'{line} Cumulative'] = output.loc['Sales', f'{line} Cumulative'] * ASSUMPTIONS.loc['-', 'Defect %'] * -1
        total_metric += output.loc[metric, f'{line} Cumulative']
        output.loc[metric, f'{line} Per Unit'] = getPerUnit(metric, f'{line} Cumulative', output)
    elif metric not in DEFAULTS:
      for line in PRODUCT_LINES:
        temp_sale = getSumGivenColumn(line, DATA, metric)
        output.loc[metric, f'{line} Cumulative'] = temp_sale + (temp_sale*volume)
        total_metric += output.loc[metric, f'{line} Cumulative']
        output.loc[metric, f'{line} Per Unit'] = getPerUnit(metric, f'{line} Cumulative', output)
    else:
      loss = -1
      if 'in Lieu' in metric:
        loss = 1
      for line in PRODUCT_LINES:
        if line in specific_pline or specific_pline == []:
          output.loc[metric, f'{line} Cumulative'] = output.loc['Sales', f'{line} Cumulative'] * DEFAULTS.get(metric) * loss
          total_metric += output.loc[metric, f'{line} Cumulative']
        else:
          output.loc[metric, f'{line} Cumulative'] = 0
        output.loc[metric, f'{line} Per Unit'] = getPerUnit(metric, f'{line} Cumulative', output)
    output.loc[metric, 'All Lines Cumulative'] = total_metric
  total_metric = 0
  for line in PRODUCT_LINES:
    agency_rep = 0
    for metric in NET_SALES_METRICS:
      if metric != 'Agency Rep':
        agency_rep += output.loc[metric, f'{line} Cumulative']
    output.loc['Agency Rep', f'{line} Cumulative'] = agency_rep * -1 * DEFAULTS.get('Agency Rep', 0)
    total_metric += output.loc['Agency Rep', f'{line} Cumulative']
    output.loc['Agency Rep', f'{line} Per Unit'] = getPerUnit('Agency Rep', f'{line} Cumulative', output)
  output.loc['Agency Rep', 'All Lines Cumulative'] = total_metric
  total_net_sales = 0
  for line in PRODUCT_LINES:
    net_sales = 0
    for metric in NET_SALES_METRICS:
      net_sales += output.loc[metric, f'{line} Cumulative']
    output.loc['NET SALES', f'{line} Cumulative'] = net_sales
    total_net_sales += net_sales
    output.loc['NET SALES', f'{line} Per Unit'] = getPerUnit('NET SALES', f'{line} Cumulative', output)

  output.loc['NET SALES', 'All Lines Cumulative'] = total_net_sales
  for metric in NET_SALES_METRICS:
    output.loc[metric, 'All Lines Per Unit'] = getPerUnit(metric, 'All Lines Cumulative', output)
  output.loc['NET SALES', 'All Lines Per Unit'] = getPerUnit('NET SALES', 'All Lines Cumulative', output)
  return output

# STANDARD
def MARGIN_CALCULATIONS(PRODUCT_LINES, MARGIN_METRICS, output, DATA, DEFAULTS, FORMAT):
  for metric in MARGIN_METRICS:
    output.loc[metric, 'All Lines Cumulative'] = 0
  for line in PRODUCT_LINES:
    for metric in MARGIN_METRICS:
      try:
        if metric == 'Cost':
          output.loc[metric, f'{line} Cumulative'] = getSumGivenColumn(line, DATA, 'Total Cost')
          output.loc[metric, 'All Lines Cumulative'] += output.loc[metric, f'{line} Cumulative']
        else:
          output.loc[metric, f'{line} Cumulative'] = getSumGivenColumn(line, DATA, metric)
          output.loc[metric, 'All Lines Cumulative'] += output.loc[metric, f'{line} Cumulative']
      except:
        output.loc[metric, f'{line} Cumulative'] = 0
      output.loc[metric, f'{line} Per Unit'] = getPerUnit(metric, f'{line} Cumulative', output)
      output.loc[metric, 'All Lines Per Unit'] = getPerUnit(metric, 'All Lines Cumulative', output)

  total_metric = 0
  for line in PRODUCT_LINES:
    scrap_return = 0
    for metric in MARGIN_METRICS:
      if metric != 'Scrap Return Rate':
        if FORMAT.loc[metric].iloc[1] == 1:
          scrap_return += output.loc[metric, f'{line} Per Unit']
    return_allowance = output.loc['Return Allowance', f'{line} Cumulative']
    per_unit_sales = output.loc['NET SALES', f'{line} Per Unit']
    output.loc['Scrap Return Rate', f'{line} Cumulative'] = (1-DEFAULTS.get('Scrap Return Rate'))*(return_allowance/per_unit_sales)*scrap_return
    total_metric += output.loc['Scrap Return Rate', f'{line} Cumulative']
    output.loc['Scrap Return Rate', f'{line} Per Unit'] = getPerUnit('Scrap Return Rate', f'{line} Cumulative', output)
  output.loc['Scrap Return Rate', 'All Lines Cumulative'] = total_metric
  output.loc['Scrap Return Rate', 'All Lines Per Unit'] = getPerUnit('Scrap Return Rate', 'All Lines Cumulative', output)

  total_variable_cost = 0
  total_margin = 0
  for line in PRODUCT_LINES:
    variable_cost = 0
    for metric in MARGIN_METRICS:
      variable_cost += output.loc[metric, f'{line} Cumulative']
    output.loc['TOTAL VARIABLE COST', f'{line} Cumulative'] = variable_cost
    total_variable_cost += variable_cost
    output.loc['TOTAL VARIABLE COST', f'{line} Per Unit'] = getPerUnit('TOTAL VARIABLE COST', f'{line} Cumulative', output)
    net_sales = output.loc['NET SALES', f'{line} Cumulative']
    margin = net_sales - output.loc['TOTAL VARIABLE COST', f'{line} Cumulative']
    output.loc['MARGIN', f'{line} Cumulative'] = margin
    total_margin += margin
    output.loc['MARGIN', f'{line} Per Unit'] = getPerUnit('MARGIN', f'{line} Cumulative', output)
    margin_perc = margin / net_sales
    output.loc['MARGIN %', f'{line} Cumulative'] = margin_perc

  output.loc['TOTAL VARIABLE COST', 'All Lines Cumulative'] = total_variable_cost
  output.loc['TOTAL VARIABLE COST', 'All Lines Per Unit'] = getPerUnit('TOTAL VARIABLE COST', 'All Lines Cumulative', output)
  output.loc['MARGIN', 'All Lines Cumulative'] = total_margin
  output.loc['MARGIN', 'All Lines Per Unit'] = getPerUnit('MARGIN', 'All Lines Cumulative', output)
  output.loc['MARGIN %', 'All Lines Cumulative'] = output.loc['MARGIN', 'All Lines Cumulative'] / output.loc['NET SALES', 'All Lines Cumulative']

  return output

# STANDARD
def SGA_CALCULATIONS(PRODUCT_LINES, output, ASSUMPTIONS, DEFAULTS, SGA_METRICS, file):

  print(SGA_METRICS)

  for metric in SGA_METRICS:
    output.loc[metric, 'All Lines Cumulative'] = 0
  output.loc['SG&A', 'All Lines Cumulative'] = 0
  for line in PRODUCT_LINES:
    for metric in SGA_METRICS:
      if metric == 'Fill Rate Fines':
        output.loc['Fill Rate Fines', f'{line} Cumulative'] = output.loc['NET SALES', f'{line} Cumulative'] * DEFAULTS.get('Fill Rate Fines', 0)
        output.loc['Fill Rate Fines', 'All Lines Cumulative'] += output.loc['Fill Rate Fines', f'{line} Cumulative']
        output.loc['Fill Rate Fines', f'{line} Per Unit'] = getPerUnit('Fill Rate Fines', f'{line} Cumulative', output)
      elif metric == 'Inspect Return':
        output.loc['Inspect Return', f'{line} Per Unit'] = output.loc['Handling/Shipping', f'{line} Per Unit']
      elif metric == 'Return Allowance Put Away/Rebox':
        output.loc['Return Allowance Put Away/Rebox', f'{line} Per Unit'] = output.loc['Handling/Shipping', f'{line} Per Unit'] + ASSUMPTIONS.loc[line, 'Return Allowance Put Away/Rebox']
      else:
        output.loc[metric, f'{line} Per Unit'] = ASSUMPTIONS.loc[line, metric]
        output.loc[metric, f'{line} Cumulative'] = ASSUMPTIONS.loc[line, metric] * output.loc['QTY Gross', f'{line} Cumulative']
        output.loc[metric, 'All Lines Cumulative'] += output.loc[metric, f'{line} Cumulative']

    return_allowance = output.loc['Return Allowance', f'{line} Cumulative']
    per_unit_sales = output.loc['NET SALES', f'{line} Per Unit']
    per_unit_inspect = output.loc['Inspect Return', f'{line} Per Unit']
    per_unit_rebox = output.loc['Return Allowance Put Away/Rebox', f'{line} Per Unit']
    if DEFAULTS.get('Scrap Return Rate') == 1:
      output.loc['Inspect Return', f'{line} Cumulative'] = 0
    else:
      output.loc['Inspect Return', f'{line} Cumulative'] = (return_allowance/per_unit_sales)*per_unit_inspect*-1
      output.loc['Inspect Return', 'All Lines Cumulative'] += output.loc['Inspect Return', f'{line} Cumulative']

    output.loc['Return Allowance Put Away/Rebox', f'{line} Cumulative'] = (return_allowance/per_unit_sales)*per_unit_rebox*-1*(1-DEFAULTS.get('Scrap Return Rate', 0))
    output.loc['Return Allowance Put Away/Rebox', 'All Lines Cumulative'] += output.loc['Return Allowance Put Away/Rebox', f'{line} Cumulative']
    
    SGA = 0
    for metric in SGA_METRICS:
      SGA += output.loc[metric, f'{line} Cumulative']
    output.loc['SG&A', f'{line} Cumulative'] = SGA
    output.loc['SG&A', 'All Lines Cumulative'] += SGA
    output.loc['SG&A', f'{line} Per Unit'] = getPerUnit('SG&A', f'{line} Cumulative', output)

  for metric in SGA_METRICS:
    output.loc[metric, 'All Lines Per Unit'] = getPerUnit(metric, 'All Lines Cumulative', output)
  output.loc['SG&A', 'All Lines Per Unit'] = getPerUnit('SG&A', 'All Lines Cumulative', output)

  return output