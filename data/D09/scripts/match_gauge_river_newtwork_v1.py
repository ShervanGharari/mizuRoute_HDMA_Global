#!/usr/bin/env python

import os
import sys
import numpy as np
import xarray as xr
import geopandas as gpd
import fiona
import pandas as pd
import time
from timeit import default_timer as timer

print("\nThe Python version: %s.%s.%s" % sys.version_info[:3])
print(xr.__name__, xr.__version__)

def records(filename, usecols, **kwargs):

    with fiona.open(filename, 'r') as src:

        for feature in src:
            f = {k: feature[k] for k in ['id', 'geometry']}
            f['properties'] = {k: feature['properties'][k] for k in usecols}
            yield f

def read_shps(river_shp_list, comm_id, **kwargs):

     with open(river_shp_list) as fin:

         gdf_frame = []

         for shp in fin:
             gdf_frame.append(gpd.GeoDataFrame.from_features(records(shp.strip('\n'), [comm_id], **kwargs)))
             print('Finished reading %s'%shp.strip('\n'))

         df_river = pd.concat(gdf_frame)
         print(df_river)

     return df_river


# setup
network_data = 'MERIT_Hydro'
dist_buffer = 0.05            # buffer distance for point gauge [degree]  hdma: 0.07, merit: 0.05
area_tol    = 30              # percent area difference tolerance [percent]
name_gauge_area = 'area_stn'  # basin area variable name from gauge report
name_route_area = 'totalArea' # basin area variable name from routing network
name_route_id   = 'seg_id'    # reach ID variable name from routing network

# gauge point shapefile
gauge_points = gpd.GeoDataFrame.from_file('/glade/work/mizukami/data/river_gauge_data/D09/geospatial/D09_925.shp')

# output ascii
gauge_catch_out = '/glade/p/ral/hap/mizukami/global_mizuRoute/obs/D09/D09_925.%s.asc.test'%network_data

# network specific catchment shapefiles/river network
if network_data == 'HDMA':
  #catch_polys = gpd.GeoDataFrame.from_file('/glade/work/mizukami/data/HDMA/gpkg/hdma_global_catch_v3.gpkg')
  name_hruid_cat = 'hruid'
  catch_polys = read_shps('ancillary_data/HDMA_cat_shp.list',name_hruid_cat)
  ds_network = xr.open_dataset('/glade/work/mizukami/test_mizuRoute/HDMA_global/ancillary_data/ntopo_global_HDMA_aug.nc')
elif network_data == 'MERIT_Hydro':
  name_hruid_cat = 'hruid'   # COMID for v0
  catch_polys = read_shps('ancillary_data/MERIT_Hydro_cat_shp.list',name_hruid_cat)
  ds_network = xr.open_dataset('/glade/work/mizukami/mizuRoute_data/network_data/MERIT_Hydro/v1/ntopo_MERIT_Hydro_v1.aug.nc')  # v0/ntopo_MERIT_Hydro_v0.aug.nc for v0
elif network_data == 'mosart0.5':
  name_hruid_cat = 'hru_id'
  catch_polys = read_shps('ancillary_data/mosart0.5_cat_shp.list',name_hruid_cat)
  ds_network = xr.open_dataset('/glade/work/mizukami/mizuRoute_data/network_data/mosart0.125/mizuRoute_MOSART_Global_half_20161105a.aug.nc')
elif network_data == 'mosart0.125':
  name_hruid_cat = 'hru_id'
  catch_polys = read_shps('ancillary_data/mosart0.125_cat_shp.list',name_hruid_cat)
  ds_network = xr.open_dataset('/glade/work/mizukami/mizuRoute_data/network_data/mosart0.125/mizuRoute_MOSART_Global_8th_20160716a_aug.nc')
else:
  print('%s not valid'%network_data)
  sys.exit(1)

# clean network data
ds_seg = ds_network.drop_dims(['hru','upAll','uh','upHRU','upSeg'])
ds_seg[name_route_area] = ds_seg[name_route_area]/10**6  #m2 ->km2
print('2. Read network netCDF:')
print(ds_seg)

# Find intersected polygon with bufferred gauge points
gauge_points_buffer = gauge_points
gauge_points_buffer['geometry'] = gauge_points_buffer.geometry.buffer(dist_buffer)
polyWithPoints = gpd.sjoin(catch_polys, gauge_points_buffer, op='intersects')
print('3. Spatial joined bufferred gauge point shapefile:')
print('Length of data: %d'%len(polyWithPoints))
print(polyWithPoints.head(20))

# https://stackoverflow.com/questions/31690076/creating-large-pandas-dataframes-preallocation-vs-append-vs-concat
#df_tmp = pd.DataFrame(columns=['gauge_id', 'route_id', 'gauge_area', 'route_area','pct_area_bias', 'flag', 'riv_name'])
df_list = []

for ix, point in gauge_points.iterrows():
  print(point['id'])
  flag = 0

  # select candidate hrus. i.e., intersected catchment hrus
  t0 = time.time()
  df_candidate = polyWithPoints[polyWithPoints['id'].isin([point['id']])]
  t1 = time.time()
  print('Elapsed time: select candidate hrus = %.5f'%(t1-t0))

  t0 = time.time()
  selected = ds_seg[name_route_id].isin([df_candidate[name_hruid_cat].values])
  ix_selected = np.where(selected.values)[0]
  t1 = time.time()
  print('Elapsed time: get selected hru indices in network data = %.5f'%(t1-t0))

  if (np.count_nonzero(selected))>0:
      t0 = time.time()
      ds_subset = ds_seg.isel(seg=ix_selected)
      t1 = time.time()
      print('Elapsed time: subset network data = %.5f'%(t1-t0))

      # check drainage areas for candidate hrus and then select min difference from reported gauge drainage area
      diff = (100*(ds_subset[name_route_area].values - point[name_gauge_area])/point[name_gauge_area])
      idx = np.argmin(abs(diff))

      if abs(diff[idx]) > area_tol:
        flag = 1

      # populate dataframe
      t0 = time.time()
      data = {'gauge_id':       [point['id']],
              'route_id':       [ds_subset[name_route_id].values[idx]],
              'gauge_area':     [point[name_gauge_area]],
              'route_area':     [ds_subset[name_route_area].values[idx]],
              'pct_area_bias':  [diff[idx]],
              'flag':           [flag],
              'riv_name':       [point['riv_name']]}
      df_tmp = pd.DataFrame (data, columns=['gauge_id', 'route_id', 'gauge_area', 'route_area','pct_area_bias', 'flag', 'riv_name'])
      df_list.append(df_tmp)
      t1 = time.time()
      print('Elapsed time: populate dataframe = %.5f'%(t1-t0))

  else:
      print('point: %d not intersected by any hrus'%(point['id']))

df_out = pd.concat(df_list)

df_out  = df_out.astype({'gauge_id':      'int32',
                         'gauge_area':    'float32',
                         'route_id':      'int32',
                         'route_area':    'float32',
                         'pct_area_bias':'float32',
                         'flag':          'int32',
                         'riv_name':      '<U16'})

df_out.to_csv(gauge_catch_out, index=False, float_format='%10.2f')
