import streamlit as st
import pandas as pd
import urllib.request
import folium
from streamlit_folium import folium_static
import json
import plotly.express as px

# Page Config
st.set_page_config(
    page_title="NS Disruptions",
    page_icon="",
    layout="wide",
    initial_sidebar_state="expanded")

# Load Dataset
disruptions = pd.concat([pd.read_csv(f'disruptions-{year}.csv') for year in range(2019, 2024)])

# Convert 'start_time' and 'end_time' columns to datetime format
disruptions['start_time'] = pd.to_datetime(disruptions['start_time'])
disruptions['end_time'] = pd.to_datetime(disruptions['end_time'])
disruptions['date_n'] = disruptions['start_time'].dt.date

# Sidebar
with st.sidebar:
    st.title('NS Disruptions')
    
    statistical_cause_list = list(disruptions.statistical_cause_en.unique())[::-1]
    
    selected_cause = st.selectbox('Select a Statistical Cause', statistical_cause_list, index=len(statistical_cause_list)-1)
    df_statistical_cause = disruptions[disruptions.statistical_cause_en == selected_cause]

    selected_year_list = ["All Years"] + [str(year) for year in range(2019, 2024)]
    selected_year = st.selectbox('Select a Year', selected_year_list)

    st.header("Map Settings")
    # Add controls to adjust map size
    map_width = st.slider("Map Width", min_value=200, max_value=1000, value=600)
    map_height = st.slider("Map Height", min_value=200, max_value=800, value=400)

# Column Config
col = st.columns((1.5, 4.5, 0.5), gap='medium')

def load_data():
    try:
        url = "https://gateway.apiportal.ns.nl/Spoorkaart-API/api/v1/spoorkaart"
        hdr ={
            # Request headers
            'Cache-Control': 'no-cache',
            'Ocp-Apim-Subscription-Key': '0e44159e9b524b75a167f07cd3e7bbe9',
        }
        req = urllib.request.Request(url, headers=hdr)
        req.get_method = lambda: 'GET'
        response = urllib.request.urlopen(req)
        data = json.loads(response.read())  # Load JSON data
        return data
    except Exception as e:
        st.error(f"An error occurred: {e}")

def main():
    st.title("Train Rail Network Map")

    # Load data
    data = load_data()

    # Set up layout with multiple columns
    col1, col2 = st.columns([1, 2])

    # Create a map centered on the Netherlands
    folium_map = folium.Map(location=[52.1326, 5.2913], width=map_width, height=map_height, zoom_start=7, tiles="Cartodb dark_matter")

    # Iterate over each feature in the GeoJSON data and add it to the map
    if data:
        for feature in data['payload']['features']:
            line_coords = feature['geometry']['coordinates']
            # Swap longitude and latitude coordinates
            line_coords = [(lat, lon) for lon, lat in line_coords]
            folium.PolyLine(locations=line_coords, color='red', weight=1).add_to(folium_map)

    # Add Layer Control to the map
    folium.LayerControl().add_to(folium_map)

    # Filter data based on selected year
    if selected_year == "All Years":
        disruptions_yearly = disruptions
    else:
        disruptions_yearly = disruptions[pd.to_datetime(disruptions['date_n']).dt.year == int(selected_year)]

    # Filter data based on selected statistical cause
    disruptions_cause = disruptions_yearly[disruptions_yearly['statistical_cause_en'] == selected_cause]

    # Group the data by station code and count the number of occurrences of each cause
    station_cause_counts = disruptions_cause.groupby('rdt_station_codes').size().reset_index(name='cause_count')

    # Add points to the map corresponding to the stations with sizes based on the counts of causes
    for feature in data['payload']['features']:
        line_coords = feature['geometry']['coordinates']
        first_coordinate = line_coords[0]  # Extract the first coordinate
        station_code = feature['properties']['from']
        cause_count = station_cause_counts[station_cause_counts['rdt_station_codes'] == station_code]['cause_count'].values
        if len(cause_count) > 0:
            cause_count = cause_count[0]
            folium.CircleMarker(location=first_coordinate, radius=cause_count*2, color='blue', fill=True, fill_color='blue').add_to(folium_map)

    # Display the map in Streamlit
    with col1:
        folium_static(folium_map, width=map_width, height=map_height)
        st.header("Disruptions by Month")
        
        # Group the data by month and count the number of disruptions per month
        disruptions_monthly = disruptions_cause.groupby(pd.Grouper(key='start_time', freq='M')).size().reset_index(name='number_of_disruptions')
        fig = px.bar(disruptions_monthly, x='start_time', y='number_of_disruptions', labels={'start_time': 'Month', 'number_of_disruptions': 'Number of Disruptions'})
        st.plotly_chart(fig)

        with st.expander('About', expanded=False):
            st.write('''
                - Data: [NS SpoorKaart API](<https://apiportal.ns.nl/api-details#api=spoorkaart-api&operation=getSpoorkaart>), 
                        [NS Disruptions](<https://www.rijdendetreinen.nl/open-data>)
                - Authors: Wesley Hendriks, Pam Smit, Moraysha Chowhari, Scott van Hagen
                ''')
        

        
if __name__ == "__main__":
    main()
