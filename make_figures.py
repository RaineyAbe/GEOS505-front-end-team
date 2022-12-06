# Make figures for the GEOS 505 Climate Dashboard
# Front End Team
# Fall 2022

import pandas as pd
import numpy as np
import os
import panel as pn
pn.extension()
import xarray as xr
import folium as fm
import matplotlib
import matplotlib.pyplot as plt
import hvplot.pandas
import holoviews as hv
import branca
import glob
import io
from PIL import Image

# -----Define paths in directory, load data
# path to data
data_path = '/Users/raineyaberle/Courses/GEOS_505_ResearchComputing/data/dashboard/'
# path where outputs will be saved
out_path = data_path + '../../dashboard/GEOS505-front-end-team/figures/'
# load data files as xarray.Datasets
os.chdir(data_path)
ds_p = xr.open_dataset('cfs_prate_20221130.nc') # precipitation rate
ds_sde = xr.open_dataset('cfs_sde_20221130.nc') # snow depth
ds_t = xr.open_dataset('cfs_t_20221130.nc')     # air temperature
ds_wr = xr.open_dataset('cfs_watr_20221130.nc') # water runoff
# merge Datasets
ds = xr.merge([ds_p, ds_sde, ds_t, ds_wr])
# replace no data values with NaN
for data_var in ds.data_vars:
    ds[data_var] = ds[data_var].where(ds[data_var]!=ds[data_var].GRIB_missingValue)
# subset the data to the PNW
ds_PNW = ds.where((ds.latitude > 35) & (ds.latitude < 50)
                  & (ds.longitude > 230) & (ds.longitude < 250), drop=True)

# -----Create interactive map and scatterplot for each of the data variables
# create drop down bar to select forecast timeframe
select = pn.widgets.Select(name='Select forecast timeframe:', options=['Day', 'Week', 'Month'])

# set up data for plotting
### identify start and end times
# for the sample dataset, we'll set today as the first valid_time in the dataset
# t_start = np.datetime64('today')
t_start = ds['valid_time'].data[0]
if select.value=='Day':
    t_end = t_start + np.timedelta64(1, 'D')
elif select.value=='Week':
    t_end = t_start + np.timedelta64(7, 'D')
elif select.value=='Month':
    t_end = t_start + np.timedelta64(30, 'D')
### Calculate median of each variable over time (for map)
ds_PNW_time_median = ds_PNW.sel(valid_time=slice(t_start, t_end)).median(dim='valid_time')
### Calculate median and standard deviation of each variable over space (for line chart)
ds_PNW_space_median = ds_PNW.sel(valid_time=slice(t_start, t_end)).median(dim=['latitude', 'longitude'])
ds_PNW_space_std = ds_PNW.sel(valid_time=slice(t_start, t_end)).std(dim=['latitude', 'longitude'])
### Plot settings
# data variables to plot
data_vars = ['prate', 'sde', 't', 'watr']
# display names for each data variable
data_vars_display = ['Preciptiation rate [kg m^-2 s^-1]', 
                     'Snow depth [m]', 
                     'Air temperature [K]', 
                     'Water runoff [kg m^-2]']
# colormaps for map
cmaps = [matplotlib.cm.get_cmap('Blues'), 
         matplotlib.cm.get_cmap('cool'),
         matplotlib.cm.get_cmap('coolwarm'),
         matplotlib.cm.get_cmap('GnBu')]
# colors for line charts
chart_colors = [cmaps[0](150),
                cmaps[1](50),
                cmaps[2](150),
                cmaps[3](150)
               ]
# min and max of map
xmin, xmax = np.min(ds_PNW.longitude.data), np.max(ds_PNW.longitude.data)
ymin, ymax = np.min(ds_PNW.latitude.data), np.max(ds_PNW.latitude.data)
# function to "colorize" the data
# from: https://www.linkedin.com/pulse/visualize-dem-interactive-map-chonghua-yin/?trk=related_artice_Visualize%20DEM%20in%20An%20Interactive%20Map_article-card_title
def colorize(array, cmap):
    normed_data = (array - np.nanmin(array)) / (np.nanmax(array) - np.nanmin(array))   
    cm = cmap
    return cm(normed_data)

# -----Loop through data variables
for i, data_var in enumerate(data_vars):
    
    print(data_var)
    print('---------')
    
    # -----Create line chart
    # create pandas.DataFrame
    df = pd.DataFrame()
    df['valid_time'] = ds_PNW_space_median.valid_time.data
    df['median'] = ds_PNW_space_median['prate'].data
    df['low'] = ds_PNW_space_median['prate'].data - ds_PNW_space_std['prate'].data
    df['high'] = ds_PNW_space_median['prate'].data + ds_PNW_space_std['prate'].data
    # line plot for median, area plot for std
    std_plot = df.hvplot.area(x='valid_time', y='low', y2='high', label='standard deviation', color=chart_colors[i])
    med_plot = df.hvplot.line(x='valid_time', y='median', label='median', color='black')
    list_of_curves = [std_plot, med_plot]
    # add list of curves to plot
    chart = hv.Overlay(list_of_curves).opts(
        height=500, 
        width=800,
        ylabel=data_vars_display[i],
        xlabel='',
        title='Median and standard deviation of ' + data_var + ' for the next ' + str(select.value),
        legend_position='bottom_right',
    )
    # save chart to file
    fn = out_path + 'chart_'+data_var+'.html'
    hvplot.save(chart, fn)
    print('chart saved to file: '+fn)
    
    # -----Create map
    m = fm.Map(location=[np.nanmean(ds_PNW.latitude.data),  # mean latitude value in data 
                         np.nanmean(ds_PNW.longitude.data)], # mean longitude value in data
                      zoom_start=4, # initial map zoom level
                      tiles='StamenTerrain', # basemap
                      width=500, # map width
                      height=400) # map height
    # create colormap for legend
    cmap_legend = branca.colormap.LinearColormap([cmaps[i](j) for j in np.arange(0,256)], 
                                                 vmin=np.nanmin(ds_PNW_time_median[data_var]), 
                                                 vmax=np.nanmax(ds_PNW_time_median[data_var]), 
                                                 caption=data_vars_display[i], 
                                                 tick_labels=[np.nanmin(ds_PNW_time_median[data_var].data),
                                                              np.nanmax(ds_PNW_time_median[data_var].data),
                                                              np.nanmax(ds_PNW_time_median[data_var].data)]
                                                )
    # colorize the data
    data_colorized = colorize(ds_PNW_time_median[data_var].data, cmaps[i])
    # add image to map
    fm.raster_layers.ImageOverlay(image=data_colorized, 
                                  bounds=[[ymin, xmin], [ymax, xmax]], 
                                  opacity=0.8,
                                  origin='upper', 
                                ).add_to(m)
    # add colormap legend to map
    m.add_child(cmap_legend)
    # save to file as png
    fn = out_path + 'map_'+data_var + ".html"
    m.save(fn)
    print('map saved to file: ' + fn)
    print(' ')

# NOTE: The Folium maps and charts can be added to the Panel dashboard 
# as in the following command (like this example: https://panel.holoviz.org/gallery/external/Folium.html):
# pn.panel(map, height=400)
