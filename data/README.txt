Note on the HDMA + HydroLake Network Topology

1- Initially and becasue of close approximity of lake Superior, Lake Michigan and Lake Huron; Lake Michingan and Lake Huron were unresolved. A small portion of lake Huron is altered to have the model lake Huron resolvabale. Additionally lake Huron and Lake Michigan were merged (and their volume and surface area) and were given a lake id of maximume lake id in hydrolake + 1.

2- to avoid interference of lakes and river segment (identical lake_id and seg_id), all the lake id were summed by a value of 7000000.

3- lake 847 was removed from the lakes as it causes circular river network topology (perhaps should be solved by the new code)
