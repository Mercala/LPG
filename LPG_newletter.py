from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
from matplotlib.offsetbox import TextArea, DrawingArea, OffsetImage, AnnotationBbox
import matplotlib.image as mpimg
from bs4 import BeautifulSoup
import streamlit as st
import pandas as pd
import numpy as np
import requests
import json
import re

def numbers(query):
    # Cleanse Square Meters, Ratios and Non-numeric characters
    query = str(query)
    query = re.sub(r'm\s?2', '', query)
    query = query.replace('sq.meters', '')
    query = query.replace('1/2', '.5')
    query = re.sub(r'[^0-9.,]', '', query)

    # Split by non-numeric characters
    lst = re.split(r'\D', query)

    # Control for proper decimal period
    proper = re.search(r'\.\d{1,2}$', query)
    if not proper:

        # Place period infront of decimals
        if len(lst) > 1:
            if len(lst[-1]) < 3:
                lst[-1] = '.' + lst[-1]

            return ''.join(lst)

        else:
            return lst[0]

    else:
        return ''.join(lst[:-1]) + proper.group()

# Spot price API call
API_KEY = 'Eer2dRfSFCypYopfa4qWO8A1Psi79atcfGaR594H'
url = f"https://api.eia.gov/series/?api_key={API_KEY}&series_id=PET.EER_EPLLPA_PF4_Y44MB_DPG.D"

# Response and Json
@st.cache
def get_data():
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()
    else:
        return st.write('Unable to connect to EIA')

dct = get_data()

# Initialize DataFrame
df = pd.DataFrame(dct['series'][0]['data'], columns=['date', 'spot price'])
df.date = pd.to_datetime(df.date)
df = df.set_index('date')

sales_input = st.sidebar.text_input('Total HSH Sales (lb)', value='7,354,733')
sales_hsh = float(numbers(sales_input))

# Convert $/gallon -> Afl./lb
conversion = 1.8 * (1 + .013 + .0025) / (3.785 * .5 * 2.205)
df['freight'] = df['spot price'] * 0.21978
df['insurance'] = df['spot price'] * 0.00322
df['FOB'] = df['spot price'] + df.freight + df.insurance
df['excises'] = df.FOB * 0.06
df['handling'] = 344.5 / sales_hsh * 9.4
df['inspection'] = 4865 / sales_hsh * 9.4
df['discharge'] = 6000 / sales_hsh * 9.4
df['wharfage'] = 0.00042
df['landed'] = df.FOB + df.excises + df.handling + df.inspection + df.discharge + df.wharfage


currecy_select = st.sidebar.selectbox('Currency/Unit', options=['USD/Gallon', 'AWG/Pound'])
time_select = st.sidebar.selectbox('Time Window', options=['Weekly', 'Monthly'])

if currecy_select == 'AWG/Pound':
    df = df * conversion

dct_time = {
    'W': -53,
    'M': -13,
}

time_frequency = time_select[0]

# time_frequency
df_resampled = df.resample(time_frequency).mean()

cols = st.columns([1.5, 8.5])
cols[0].markdown('<div><img height="60px" src="https://www.arugas.com/_next/static/images/logo-cc6fef370ad4b98c665401e88beb82c0.svg"></div>', unsafe_allow_html=True)
cols[1].title('LPG Weekly Update')

st.write('')
st.write('')
st.write('')
st.write('')

# ------------------------------------------------------------------------------
# GRAPH

# Color Pallette
color1 = '#0C04B4'
color2 = '#606D5D'
color3 = '#FFFFFF'
color4 = '#D00000'
color5 = '#adaeae'

# Fontsize
h1 = 24
h2 = 20
h3 = 16

fontname = 'monospace'

# period = df_resampled.loc['2022-01-26':'2021-01-26']

def plot(period):
    fig, ax = plt.subplots(figsize=(16,8))

    ax.plot(period.resample('W').mean(), color='#1A069A')
    # Plot the average
    ax.plot(period.index, np.repeat(period.mean(), len(period.index)), color='black', linewidth=1)

    # Titles
    fig.suptitle("Mont Belvieu, TX Propane Landed Price, Daily",
             fontsize=h1,
             fontweight='bold',
             x=0.125,
             ha='left',
             fontname='monospace'
            )

    ax.set_title(f"{currecy_select}",
                 fontdict={'fontsize': h2,
                      'verticalalignment': 'baseline',
                      'horizontalalignment': 'left'
                          },
                 loc='left',
                 fontname='monospace'
                )
    # Grid lines
    ax.yaxis.grid(linestyle='--')

    ax.tick_params(labelsize=h3)
    # Hide Spines
    ax.spines['right'].set_visible(False)
    ax.spines['top'].set_visible(False)
    ax.spines['left'].set_visible(False)

    # Fill Losses with red
    ax.fill_between(period.loc[:'2009-07-01'].index,
                    period.mean(),
                    period.loc[:'2009-07-01'].values,
                    where= period.loc[:'2009-07-01'].values > period.mean(),
                    alpha=0.3,
                    color=color4,
    #                 label='Loss'
                   )

    # Fill profits with green
    ax.fill_between(period.loc[:'2009-07-01'].index,
                    period.mean(),
                    period.loc[:'2009-07-01'].values,
                    where= period.loc[:'2009-07-01'].values < period.mean(),
                    alpha=0.3,
                    color='green',
    #                 label='Profit'
                   )

    return fig

# cols = st.columns([9, 1])
# cols[1].markdown('<div><img height="50px" src="https://upload.wikimedia.org/wikipedia/commons/thumb/1/1f/Energy_Information_Administration_logo.svg/1200px-Energy_Information_Administration_logo.svg.png"></div>', unsafe_allow_html=True)

st.write(plot(df.loc[datetime.today():datetime.today() - timedelta(365)].landed))

st.write('')
st.write('')
st.write('')
st.write('')


# ------------------------------------------------------------------------------
def create_columns(col_name, time_frequency):
    # Get column index of columns name
    col_index = list(df_resampled.columns).index(col_name)

    # Compute metrics
    cols = st.columns(4)
    # cols[0].write('')
    cols[0].write('')
    cols[0].text(f"Average\n{col_name.title()} Price\n{currecy_select}")
    cols[1].metric('Last week', f"{df_resampled.iloc[-1, col_index]:,.3f}")
    cols[2].metric('Two weeks ago', f"{df_resampled.iloc[-2, col_index]:,.3f}", delta=f"{(df_resampled.iloc[-1, col_index] / df_resampled.iloc[-2, col_index] - 1) * 100:,.1f}%")
    cols[3].metric('Year-over-Year', f"{df_resampled.iloc[dct_time.get(time_frequency), col_index]:,.3f}", delta=f"{(df_resampled.iloc[-1, col_index] / df_resampled.iloc[dct_time.get(time_frequency), col_index] - 1) * 100:,.1f}%")

    # cols[4].write('')

# create_columns('spot price', time_frequency)

col_names = ['freight', 'excises', 'handling', 'inspection', 'discharge', 'wharfage']

# with st.expander('Detailed Breakdown'):
#     for col_name in col_names:
#         create_columns(col_name, time_frequency)



create_columns('landed', time_frequency)



# ------------------------------------------------------------------------------
# Retrieve News from LPGas

def check_date(div):
    # Extract date
    date = div.h2.get_text('|', strip=True).split('|')[0]
    article_date = datetime.strptime(date, '%B %d, %Y By')
    # Evaluate date
    if (datetime.today() - article_date).days <= 7:
        return article_date
    return None

def get_news():
    url = 'https://www.lpgasmagazine.com/category/news/'
    response = requests.get(url)
    soup = BeautifulSoup(response.content, 'html.parser')
    # Get individual new articles
    divs = soup.findAll('div', {'class': 'entry-content'})

    lst = []
    for index, div in enumerate(divs):
        if check_date(div):
            lst.append((index+ 1, check_date(div), div.p.get_text('strip=True'), div.a['href']))

    return lst

st.write('')
st.write('')
st.markdown("## This week's news")

for news in get_news():
    st.write(news[0], news[1].strftime('%B %d, %Y'))
    st.markdown(f"""<div>{news[2]} <a target="_blank" href={news[3]}>Read more</a><br><br></div>""", unsafe_allow_html=True)
