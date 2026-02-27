import pandapower as pp

net = pp.networks.case14() # create the IEEE 14 bus test case

pp.runpp(net) # run power flow calculation

# Export to Excel (each element table as a sheet)
pp.to_excel(net, "case14_network.xlsx", include_results=True)