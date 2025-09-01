import pandas as pd
import utility_library as util

def getSummary(file, user_defaults_df=None, volume=0.0):
  FORMAT = pd.read_excel(file, sheet_name="Format", index_col="METRIC")
  all_lines = FORMAT.loc['QTY Gross', 'Add All Lines']
  NET_SALES_METRICS, MARGIN_METRICS = util.GET_NETSALES_MARGIN_METRICS(FORMAT)
  SGA_METRICS = util.GET_SGA_METRICS(FORMAT)
  DATA = pd.read_excel(file, sheet_name="Data")
  PRODUCT_LINES = DATA['P Line'].unique()
  if user_defaults_df is not None:
    ASSUMPTIONS = pd.DataFrame()
    DEFAULTS = user_defaults_df
    for data in user_defaults_df:
      product_lines = list(PRODUCT_LINES.copy())
      product_lines.append('-')
      for pline in product_lines:
        if pline in data:
          row, col = data.split(' ', 1)
          ASSUMPTIONS.at[row, col] = user_defaults_df[data]
  else:
    ASSUMPTIONS = pd.read_excel(file, sheet_name="Defaults & Assumptions", index_col="P Line").fillna(0)
    DEFAULTS = {}
    for metric in FORMAT.index:
      if(pd.notna(FORMAT.loc[metric].iloc[0])):
        if "Tariffs" not in metric: 
          DEFAULTS[metric] = FORMAT.loc[metric].iloc[0]
  columns = [
    'All Lines Cumulative',
    'All Lines Per Unit'
  ]
  for line in PRODUCT_LINES:
    columns.append(f'{line} Cumulative')
    columns.append(f'{line} Per Unit')

  output = pd.DataFrame(index=FORMAT.index, columns=columns)

  output = util.QTY_CALCULATIONS(PRODUCT_LINES, output, DATA, ASSUMPTIONS, volume)
  output = util.NET_SALES_CALCULATIONS(output, DATA, ASSUMPTIONS, NET_SALES_METRICS, PRODUCT_LINES, DEFAULTS, volume)
  output = util.MARGIN_CALCULATIONS(PRODUCT_LINES, MARGIN_METRICS, output, DATA, DEFAULTS, FORMAT)
  output = util.SGA_CALCULATIONS(PRODUCT_LINES, output, ASSUMPTIONS, DEFAULTS, SGA_METRICS, file)

  total_factoring = 0
  total_contribution_margin = 0
  for line in PRODUCT_LINES:
    net_sales = output.loc['NET SALES', f'{line} Cumulative']
    output.loc['FACTORING %', f'{line} Cumulative'] = net_sales * DEFAULTS['FACTORING %']
    total_factoring += output.loc['FACTORING %', f'{line} Cumulative']
    output.loc['FACTORING %', f'{line} Per Unit'] = util.getPerUnit('FACTORING %', f'{line} Cumulative', output)
    margin = output.loc['MARGIN', f'{line} Cumulative']
    SGA = output.loc['SG&A', f'{line} Cumulative']
    factoring = output.loc['FACTORING %', f'{line} Cumulative']
    output.loc['Contribution Margin', f'{line} Cumulative'] = margin - SGA - factoring
    total_contribution_margin += margin - SGA - factoring
    output.loc['Contribution Margin', f'{line} Per Unit'] = util.getPerUnit('Contribution Margin', f'{line} Cumulative', output)
    output.loc['Contribution Margin %', f'{line} Cumulative'] = output.loc['Contribution Margin', f'{line} Cumulative'] / net_sales
  output.loc['FACTORING %', 'All Lines Cumulative'] = total_factoring
  output.loc['FACTORING %', 'All Lines Per Unit'] = util.getPerUnit('FACTORING %', 'All Lines Cumulative', output)
  output.loc['Contribution Margin', 'All Lines Cumulative'] = total_contribution_margin
  output.loc['Contribution Margin', 'All Lines Per Unit'] = util.getPerUnit('Contribution Margin', 'All Lines Cumulative', output)
  total_margin = output.loc['Contribution Margin', 'All Lines Cumulative']
  total_net_sales = output.loc['NET SALES', 'All Lines Cumulative']
  output.loc['Contribution Margin %', 'All Lines Cumulative'] = total_margin / total_net_sales

  assumptions_list = {}
  for column in ASSUMPTIONS.columns:
    for index in ASSUMPTIONS.index:
      if 'Unnamed' in column or index not in PRODUCT_LINES:
        continue
      parameter_name = f"{index} {column}"
      value = ASSUMPTIONS.loc[index, column]
      assumptions_list[parameter_name] = round(float(value),4)

  if all_lines != True:
    output = output.drop(['All Lines Cumulative', 'All Lines Per Unit'], axis=1)

  return output.reset_index().rename(columns={'METRIC': 'Metric'}), DEFAULTS, assumptions_list, FORMAT