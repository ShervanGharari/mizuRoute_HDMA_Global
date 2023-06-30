#!/usr/bin/env python

import os
import sys
import numpy as np
import pandas as pd
import time

print("\nThe Python version: %s.%s.%s" % sys.version_info[:3])

# setup
network_data = 'mosart0.5'

# input ascii
gauge_catch_in  = '/glade/p/ral/hap/mizukami/global_mizuRoute/obs/D09/D09_925.%s.asc'%network_data
# output ascii
gauge_catch_out = gauge_catch_in.replace('.asc','.v1.asc')
df_gauge = pd.read_csv(gauge_catch_in)
df_gauge = df_gauge.astype({'pct_area_bias': 'float32'})

# 1st criteria
# remove gauge large difference in area
#df_gauge1 = df_gauge.loc[(df_gauge['pct_area_bias'] < 10) &
#                         (df_gauge['pct_area_bias'] > -10) &
#                         (df_gauge['flag'] == 0)]
df_gauge1 = df_gauge
# 2nd criteria
# select one gauges out of multiple hrus that match area
df_gauge1 = df_gauge1.sort_values('pct_area_bias')
df_gauge2 = df_gauge1.drop_duplicates(['route_id'], keep='first')

df_out = df_gauge2.sort_values('gauge_id')
print(df_out)

df_out.to_csv(gauge_catch_out, index=False, float_format='%10.2f')
