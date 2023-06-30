#!/usr/bin/env python

import os
import sys
import numpy as np
import xarray as xr
import geopandas as gpd
import pandas as pd
import osgeo.ogr, osgeo.osr #we will need some packages
from osgeo import ogr #and one more for the creation of a new field
import matplotlib.pyplot as plt
from timeit import default_timer as timer

print("\nThe Python version: %s.%s.%s" % sys.version_info[:3])
print(xr.__name__, xr.__version__)


class AutoVivification(dict):
    """Implementation of perl's autovivification feature to initialize structure."""
    def __getitem__(self, item):
        try:
            return dict.__getitem__(self, item)
        except KeyError:
            value = self[item] = type(self)()
        return value


# Read original D09 discharge netcdf (remove chars coordinate)
D09_path = '/glade/work/mizukami/data/river_discharge/D09'
ds_org = xr.open_dataset(os.path.join(D09_path,'coastal-stns-Vol-monthly.updated-May2019.nc'), decode_times=False, mask_and_scale=False)
ds_org = ds_org.drop('chars')
print(ds_org)

#Redo character array and convert it to string

cfield_list ={'ct_name':2,'cn_name':2,'riv_name':15,'ocn_name':3,'stn_name':11}

attrs = {}
for key in cfield_list.keys():
    del ds_org[key].attrs['_FillValue']
    attrs[key] = ds_org[key].attrs

for jdx, (field, nchar) in enumerate(cfield_list.items()):
    str_array = np.full(925, 'missing', dtype='<U16')
    for idx in range(925):
        str_array[idx]= ds_org[field].values[idx,0:nchar].tostring().decode('utf-8',errors='ignore').strip()
    dr = xr.DataArray(str_array, coords=[ds_org.station], dims=['station'])
    if jdx==0:
        ds_str = dr.to_dataset(name = field)
    else:
        ds_str[field] = dr


#Replace character array in original one with string array and save as modified netCDF
ds_new = ds_org.drop(cfield_list.keys())
ds_new = ds_new.merge(ds_str)

for key in cfield_list.keys():
    ds_new[key].attrs=dict(attrs[key])
print(ds_new)
ds_new.to_netcdf(os.path.join(D09_path,'coastal-stns-Vol-monthly.updated-May2019.mod.nc'))

sys.exit()
# extract the reachID orders
latitude = ds_new['lat'].values
longitude = ds_new['lon'].values
field_list =['id','lon','lat','lon_mou','lat_mou','area_stn','area_mou','vol_stn','ratio_m2s','xnyr','yrb','yre','elev','ct_name','cn_name','riv_name','ocn_name','stn_name']

driver = osgeo.ogr.GetDriverByName('ESRI Shapefile') # will select the driver for our shp-file creation.

EPSG_code=4326

spatialReference = osgeo.osr.SpatialReference() #will create a spatial reference locally to tell the system what the reference will be
spatialReference.ImportFromEPSG(int(EPSG_code)) #here we define this reference to be the EPSG code

shapeData = driver.CreateDataSource(os.path.join(D09_path,'D09_925.v1.shp')) #so there we will store our data

layer = shapeData.CreateLayer('layer', spatialReference, osgeo.ogr.wkbPoint) #this will create a corresponding layer for our data with given spatial information.

layer_defn = layer.GetLayerDefn() # gets parameters of the current shapefile

for field in ds_new.variables:
    if field in field_list:
        if ds_new[field].dtype == 'int32':
            new_field = ogr.FieldDefn(field, ogr.OFTInteger) #we will create a new field with the content of our header
        elif ds_new[field].dtype == 'float32' or ds_new[field].dtype == 'float64':
            new_field = ogr.FieldDefn(field, ogr.OFTReal) #we will create a new field with the content of our header
        else:
            new_field = ogr.FieldDefn(field, ogr.OFTString) #we will create a new field with the content of our header
        layer.CreateField(new_field)

for idx, (lat,lon) in enumerate(zip(latitude,longitude)):
    point = osgeo.ogr.Geometry(osgeo.ogr.wkbPoint)
    point.AddPoint(float(lon), float(lat)) #we do have LATs and LONs as Strings, so we convert them

    feature = osgeo.ogr.Feature(layer_defn)
    feature.SetGeometry(point) #set the coordinates
    feature.SetFID(idx)
    for field in field_list:
        val =  ds_new[field].loc[idx].values
        if ds_new[field].dtype == 'int32':
            feature.SetField(field,int(val))
        elif ds_new[field].dtype == 'float32':
            feature.SetField(field,float(val))
        else:
            feature.SetField(field, str(val))
    layer.CreateFeature(feature)

shapeData.Destroy() #lets close the shapefile
