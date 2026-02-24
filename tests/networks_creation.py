import pandapower as pp
from pandapower.create import (
    create_empty_network,
    create_bus,
    create_ext_grid,
    create_transformer,
    create_line,
    create_switch,
    create_load,
    create_sgen,
    create_gen,
    create_shunt
)

net = create_empty_network() #create an empty network

bus1 = create_bus(net, name="HV Busbar", vn_kv=110, type="b")
bus2 = create_bus(net, name="HV Busbar 2", vn_kv=110, type="b")
bus3 = create_bus(net, name="HV Transformer Bus", vn_kv=110, type="n")
bus4 = create_bus(net, name="MV Transformer Bus", vn_kv=20, type="n")
bus5 = create_bus(net, name="MV Main Bus", vn_kv=20, type="b")
bus6 = create_bus(net, name="MV Bus 1", vn_kv=20, type="b")
bus7 = create_bus(net, name="MV Bus 2", vn_kv=20, type="b")

bus6
create_ext_grid(net, bus1, vm_pu=1.02, va_degree=50) # Create an external grid connection

net.ext_grid #show external grid table

trafo1 = create_transformer(net, bus3, bus4, name="110kV/20kV transformer", std_type="25 MVA 110/20 kV")

net.trafo #show transformer table
line1 = create_line(net, bus1, bus2, length_km=10, std_type="N2XS(FL)2Y 1x300 RM/35 64/110 kV",  name="Line 1")
line2 = create_line(net, bus5, bus6, length_km=2.0, std_type="NA2XS2Y 1x240 RM/25 12/20 kV", name="Line 2")
line3 = create_line(net, bus6, bus7, length_km=3.5, std_type="48-AL1/8-ST1A 20.0", name="Line 3")
line4 = create_line(net, bus7, bus5, length_km=2.5, std_type="NA2XS2Y 1x240 RM/25 12/20 kV", name="Line 4")

net.line # show line table

sw1 = create_switch(net, bus2, bus3, et="b", type="CB", closed=True)
sw2 = create_switch(net, bus4, bus5, et="b", type="CB", closed=True)
sw3 = create_switch(net, bus5, line2, et="l", type="LBS", closed=True)
sw4 = create_switch(net, bus6, line2, et="l", type="LBS", closed=True)
sw5 = create_switch(net, bus6, line3, et="l", type="LBS", closed=True)
sw6 = create_switch(net, bus7, line3, et="l", type="LBS", closed=False)
sw7 = create_switch(net, bus7, line4, et="l", type="LBS", closed=True)
sw8 = create_switch(net, bus5, line4, et="l", type="LBS", closed=True)

net.switch # show switch table

create_load(net, bus7, p_mw=2, q_mvar=4, scaling=0.6, name="load")

net.load

create_sgen(net, bus7, p_mw=2, q_mvar=-0.5, name="static generator")

net.sgen

create_gen(net, bus6, p_mw=6, max_q_mvar=3, min_q_mvar=-3, vm_pu=1.03, name="generator") 

net.gen

create_shunt(net, bus3, q_mvar=-0.96, p_mw=0, name='Shunt')

net.shunt

# Save network to Excel for dashboard testing
pp.to_excel(net, "test_network.xlsx")
print("Network saved to test_network.xlsx")