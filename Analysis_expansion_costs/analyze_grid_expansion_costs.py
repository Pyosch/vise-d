# -*- coding: utf-8 -*-
"""
Created on Wed Jan 15 16:20:43 2025

@author: lilienkampa
"""


import os
from os import listdir
from os.path import isfile, join
import pandas as pd
import sqlite3
import glob
import random
import sys
import time
import matplotlib.pyplot as plt
import pickle
import numpy as np
import statsmodels.api as sm
import geopandas as gpd


l_runs  = [("baseFlex",2030),("moreFlex",2030),("baseFlex",2045)]
dict_flex = {"baseFlex":"Base","moreFlex":"moreFlex"}

plot = False
plot_cost_curve = False
cause = True

#%% expansion requirements aggregated profiles


dict_evaluation = {}
for i,j in l_runs:
    
    dict_evaluation[i+"_"+str(j)] = {}
    for k in ["noFlex","Flex"]:
        
        dict_evaluation[i+"_"+str(j)][k] = {}
    
        conNoCons  = sqlite3.connect(r"inputs\results_paper_{}NoConstraints_{}_{}.sqlite".format(k,dict_flex[i],j))
        conCons = sqlite3.connect(r"inputs\results_paper_{}Constraints_{}_{}.sqlite".format(k,dict_flex[i],j))

        df_Cons = pd.DataFrame(pd.read_sql_query("SELECT * FROM out_systemcosts_v2", conCons))
        df_Cons = df_Cons[df_Cons["b"]=="DE"]["value"]/1000
        df_NoCons = pd.DataFrame(pd.read_sql_query("SELECT * FROM out_systemcosts_v2", conNoCons))
        df_NoCons = df_NoCons[df_NoCons["b"]=="DE"]["value"]/1000
        dict_evaluation[i+"_"+str(j)][k]["diff_costs"]  = (df_Cons - df_NoCons).item()
                            
        dict_evaluation[i+"_"+str(j)][k]["diff_load"]   = pd.DataFrame(pd.read_sql_query("SELECT * FROM CHARGE", conNoCons)[["d","h","value"]].merge(pd.read_sql_query("SELECT * FROM charge_uncontrolled", conNoCons),on=["d","h"],how="left").fillna(0).set_index(["d","h"]).sum(axis=1).round(4),columns=["load"]).reset_index(drop=True) \
                                                        - pd.DataFrame(pd.read_sql_query("SELECT * FROM CHARGE", conCons)[["d","h","value"]].merge(pd.read_sql_query("SELECT * FROM charge_uncontrolled", conCons),on=["d","h"],how="left").fillna(0).set_index(["d","h"]).sum(axis=1).round(4),columns=["load"]).reset_index(drop=True)
    
        dict_evaluation[i+"_"+str(j)][k]["expansion"]   = dict_evaluation[i+"_"+str(j)][k]["diff_load"].max().max()
        
    conCons.close()
    conNoCons.close() 
    


#%% generate transformer cost function

# Daten aus Excel-Datei einlesen
#cost_function = pd.read_excel("cost_data.xlsx", sheet_name="linearized costs", usecols="A:B", nrows=11, skiprows=1, header=0)
cost_function = pd.read_excel(r"inputs\cost_data.xlsx", sheet_name="linearized costs", usecols="A:B", nrows=5, skiprows=1, header=0)

# Daten für die Regression
X = cost_function['capacity_kVA']
y = cost_function['costs_EUR']

# Einfügen einer Konstanten (für den y-Achsenabschnitt)
X_with_const = sm.add_constant(X)

# OLS-Modell (Ordinary Least Squares) erstellen
model = sm.OLS(y, X_with_const)

# Anpassen des Modells an die Daten
results = model.fit()

# Ausgeben der Regressionskoeffizienten
#print("Gefittete Regressionskoeffizienten:")
#print(results.params)

# Die gefittete Regressionsgerade
slope = results.params.iloc[1]
intercept = results.params.iloc[0]
print(f"Gefittete Gleichung: y = {intercept:.2f} + {slope:.2f}x")

X_with_const.loc[8] = (1,0)
X_with_const.loc[9] = (1,80000)
# Vorhersagen der y-Werte mit der gefitteten Gleichung
y_pred = results.predict(X_with_const)/1000000

if plot_cost_curve:
    # Subplot erstellen (mit fig, ax)
    fig, ax = plt.subplots(figsize=(7.5,2.5))
    
    # Scatter-Plot der Datenpunkte
    ax.scatter(X, y/1000000, label="data points", color="tab:blue")
    
    # Plot der gefitteten Linie
    ax.plot(X_with_const["capacity_kVA"], y_pred,color="tab:orange", label=f"fittet cost function: y = {slope:.2f}x + {intercept:.0f} für x>0")
    
    # Achsenbeschriftungen und Titel
    ax.set_xlabel("kVA")
    ax.set_ylabel("million EUR/kVA")
    
    #ax.set_ylim(0,0.75)
    ax.set_ylim(0,0.2)
    #ax.set_xlim(0,65000)
    ax.set_xlim(0,2000)
    # Legende hinzufügen
    ax.legend()
    
    #fig.savefig(r'figures\trafo_cost_function.jpg',format='jpg', dpi=1500,bbox_inches='tight') 
    
    # Plot anzeigen
    plt.show()


#%% read GAMS - Flex -> expansion requirements by grid


max_diff = {}
for i,j in l_runs:
    max_diff[i+"_"+str(j)] = pd.read_csv(r"inputs\total_cause_{}_{}_neu.csv".format(i,j)).set_axis(["m","nuts","run","cause","Val"],axis=1)
    max_diff[i+"_"+str(j)] = max_diff[i+"_"+str(j)][~ max_diff[i+"_"+str(j)]["run"].isin(["FlexConstraintsNoPVOpt"])]

    min_cap = 0.63
    
    max_diff[i+"_"+str(j)]["required_transformers"] = np.ceil(max_diff[i+"_"+str(j)]["Val"]/min_cap)
    
    max_diff[i+"_"+str(j)]["tx"] = max_diff[i+"_"+str(j)]["m"].apply(lambda x: x.split("_")[-2])
    max_diff[i+"_"+str(j)] = max_diff[i+"_"+str(j)].drop(columns=["m"])
    
#%% calculation of costs

redundancy = 2
share_operational_costs = 0.025
# calculation annuity factor
lifetime_grid_asset = 40
int_rate = 0.055
costs_ONT = 10000
costs_rONT = 21200
annuity_factor_grid =  (int_rate*(1+int_rate)**lifetime_grid_asset)/(((1+int_rate)**lifetime_grid_asset)-1)

dict_eval_expansion = {}

for i,j in l_runs:
    max_diff[i+"_"+str(j)]["costs_rONT"] = redundancy * max_diff[i+"_"+str(j)]["required_transformers"] * (costs_rONT + intercept)
    max_diff[i+"_"+str(j)]["costs_ONT"] = redundancy * max_diff[i+"_"+str(j)]["required_transformers"] * (costs_ONT + intercept)
    
    max_diff[i+"_"+str(j)]["operational_costs_rONT"] = share_operational_costs * max_diff[i+"_"+str(j)]["costs_rONT"]
    max_diff[i+"_"+str(j)]["operational_costs_ONT"] = share_operational_costs * max_diff[i+"_"+str(j)]["costs_ONT"]
    
    max_diff[i+"_"+str(j)]["annualized_costs_rONT"] = max_diff[i+"_"+str(j)]["operational_costs_rONT"] + annuity_factor_grid * max_diff[i+"_"+str(j)]["costs_rONT"]
    max_diff[i+"_"+str(j)]["annualized_costs_ONT"] = max_diff[i+"_"+str(j)]["operational_costs_ONT"] + annuity_factor_grid * max_diff[i+"_"+str(j)]["costs_ONT"]
    
    dict_eval_expansion[i+"_"+str(j)] = {}
    dict_eval_expansion[i+"_"+str(j)]["annualized_costs"]   = (max_diff[i+"_"+str(j)].groupby("run")['annualized_costs_ONT'].sum()+max_diff[i+"_"+str(j)].groupby("run")['annualized_costs_rONT'].sum())/2/10**9
    dict_eval_expansion[i+"_"+str(j)]["tot_exp"]            = max_diff[i+"_"+str(j)].groupby("run")['Val'].sum()
    dict_eval_expansion[i+"_"+str(j)]["max_exp"]            = max_diff[i+"_"+str(j)].groupby("run")['Val'].max()
    dict_eval_expansion[i+"_"+str(j)]["mean_exp"]           = max_diff[i+"_"+str(j)].groupby("run")['Val'].mean()
    dict_eval_expansion[i+"_"+str(j)]["share_exp"]          = max_diff[i+"_"+str(j)].groupby("run")['Val'].count()/16192
    dict_eval_expansion[i+"_"+str(j)]["cause"]              = max_diff[i+"_"+str(j)].groupby(["run","cause"])['Val'].sum()

#%% plot costs

colors = ["indianred", "orange", "paleturquoise","indianred","orange",
          "lightcoral",  "moccasin", "lightcyan",  "lightcoral", "moccasin"]

l_colors = ["white","white","white","white","indianred","lightcoral","white","orange",  "moccasin","white", "paleturquoise", "lightcyan"]    
    
cm = 1 / 2.54
fig_costs, ax_costs = plt.subplots(1,figsize=(22*cm, 10*cm))

df_costs = pd.DataFrame([(dict_evaluation[i+"_"+str(j)][k]["diff_costs"],
                          dict_eval_expansion[i+"_"+str(j)]["annualized_costs"].loc[k[0].upper()+k[1:]+"NoConstraints"]) for i,j in l_runs for k in ["noFlex","Flex"]],
                        columns=["System costs","expansion costs"],index=[i+"_"+str(j)+"_"+k for i,j in l_runs for k in ["noFlex","Flex"]])
  
# moreFlex_noFlex = baseFlex_noFlex
df_costs = df_costs.drop(index=["moreFlex_2030_noFlex"],errors="ignore")  
ax_costs = df_costs.plot.bar(width=0.8, ax=ax_costs, legend=False)
for i, patch in enumerate(ax_costs.patches):
    patch.set_facecolor(colors[i])  # Jede Säule bekommt ihre eigene Farbe


ax_costs.axvline(2.5, color="black", linewidth=0.5, linestyle="--")
ax_costs.set_ylabel('bn. EUR/a')
ax_costs.set_xticks(np.arange(0, len(df_costs), 0.5))
ax_costs.set_xticklabels(["","","2030","","","","","2045","",""],rotation=0)
ax_costs.tick_params(axis='x', length=0) 
ax_costs.set_ylim(0,1.6)

for bar in ax_costs.patches:
    height = bar.get_height()  # Höhe des Balkens (Wert)
    ax_costs.text(
        bar.get_x() + bar.get_width() / 2,  # x-Position in der Mitte des Balkens
        height + 0.05,  # y-Position leicht über dem Balken
        f'{height:.2f}',  # Textformat ohne Nachkommastellen
        ha='center',  # Horizontale Zentrierung
        va='bottom',  # Vertikale Positionierung
    )

handles = [plt.Rectangle((0, 0), 1, 1, color=l_colors[bar]) for bar in range(12)]
ax_costs.legend(
    handles=handles,
    labels=["","    Congestion costs","    Expansion costs","  Early", "","","   Flex ","","", "moreFlex","",""],
    loc="lower center",
    ncol=4,
    bbox_to_anchor=(0.5,-0.35),  # + verschiebt es hoch 
    handletextpad=-3,
    alignment = "center"
)

plt.show()

fig_costs.savefig(r'figures\cost_comparison.jpg',format='jpg', dpi=1500,bbox_inches='tight') 


#%% plot costs

if plot:    
    colors = ["orange", "moccasin"]
    
    cm = 1 / 2.54
    fig, ax = plt.subplots(1,figsize=(22*cm, 10*cm))
    
    df_costs = pd.DataFrame([(dict_evaluation[i+"_"+str(j)][k]["diff_costs"],
                              dict_eval_expansion[i+"_"+str(j)]["annualized_costs"].loc[k[0].upper()+k[1:]+"NoConstraints"]) for i,j in l_runs for k in ["noFlex","Flex"]],
                            columns=["congestion costs","expansion costs"],index=[i+"_"+str(j)+"_"+k for i,j in l_runs for k in ["noFlex","Flex"]])
      
    # moreFlex_noFlex = baseFlex_noFlex
    df_costs = df_costs.drop(index=["moreFlex_2030_noFlex"],errors="ignore")  
    ax = df_costs.plot.bar(width=0.8, ax=ax, color=colors)
    
    ax.axvline(2.5, color="black", linewidth=0.5, linestyle="--")
    ax.set_ylabel('annualized costs (bn. EUR/a)')
    ax.set_xticklabels(["Early","Flex","moreFlex","Early","Flex"],rotation=0)
    ax.set_xlabel('                                     2030                                                                 2045                      ')
    
    plt.show()


#%% installed capacities

cm = 1 / 2.54
fig, ax = plt.subplots(1,figsize=(22*cm, 10*cm))

if cause:
    dict_merged_eval = {}
    dict_cause = {}
    for i,j in l_runs: 
        dict_cause[i+"_"+str(j)]        = dict_eval_expansion[i+"_"+str(j)].pop('cause')
        dict_merged_eval[i+"_"+str(j)]  = pd.DataFrame(pd.DataFrame(dict_eval_expansion[i+"_"+str(j)]).unstack(),columns=[i+"_"+str(j)])
    
    dict_merged_eval = pd.concat([dict_merged_eval[i+"_"+str(j)] for i,j in l_runs],axis=1)
    dict_merged_eval = dict_merged_eval.stack().reset_index().set_axis(["var","flex","run","val"],axis=1).pivot(index="var",columns=["run","flex"],values="val")
    
    dict_merged_eval = dict_merged_eval[[('baseFlex_2030', 'NoFlexNoConstraints'),('baseFlex_2030', 'FlexNoConstraints'),('moreFlex_2030',   'FlexNoConstraints'),('baseFlex_2045', 'NoFlexNoConstraints'),('baseFlex_2045', 'FlexNoConstraints')]]
    
    dict_cause = pd.DataFrame(dict_cause).stack().reset_index().set_axis(["run","cause","flex","val"],axis=1).pivot(index=["flex","run"],columns="cause",values="val")
    dict_cause = dict_cause.loc[[('baseFlex_2030', 'NoFlexNoConstraints'),('baseFlex_2030', 'FlexNoConstraints'),('moreFlex_2030',   'FlexNoConstraints'),('baseFlex_2045', 'NoFlexNoConstraints'),('baseFlex_2045', 'FlexNoConstraints')],["pv","ev"]]

    cause=False
    
colors = ["indianred", "orange", "paleturquoise","indianred","orange"]

(dict_merged_eval.loc["tot_exp"]/1000).plot.bar(label="GW",ax=ax,color=colors)
ax.set_xticks(np.arange(0, len(df_costs), 0.5))
ax.set_xticklabels(["","","2030","","","","","2045","",""],rotation=0)
ax.tick_params(axis='x', length=0) 
ax.axvline(2.5, color="black", linewidth=0.5, linestyle="--")
ax.set_xlabel("")
ax.set_ylabel("GW")
ax.set_ylim(0,60)
#ax.set_title("Total Expansion")

for bar in ax.patches:
    height = bar.get_height()  # Höhe des Balkens (Wert)
    ax.text(
        bar.get_x() + bar.get_width() / 2,  # x-Position in der Mitte des Balkens
        height + 0.05,  # y-Position leicht über dem Balken
        f'{height:.1f}',  # Textformat ohne Nachkommastellen
        ha='center',  # Horizontale Zentrierung
        va='bottom',  # Vertikale Positionierung
    )

handles = [plt.Rectangle((0, 0), 1, 1, color=colors[bar]) for bar in range(3)]
fig.legend(
    handles=handles,
    labels=["Early","Flex ","moreFlex"],
    loc="lower center",
    ncol=4,
    bbox_to_anchor=(0.5,-0.04),  # + verschiebt es hoch 
    alignment = "center"
)

fig.savefig(r'figures\eval_expansion.jpg',format='jpg', dpi=1500,bbox_inches='tight') 

#%% installed capacities grouped

cm = 1 / 2.54
fig_cap, ax_cap = plt.subplots(1,figsize=(22*cm, 10*cm))

colors = ["indianred", "orange", "paleturquoise","indianred","orange",
          "lightcoral",  "moccasin", "lightcyan",  "lightcoral", "moccasin"]

l_colors = ["white","white","white","white","indianred","lightcoral","white","orange",  "moccasin","white", "paleturquoise", "lightcyan"]    
    

(dict_cause/1000).plot.bar(label="GW",ax=ax_cap,stacked=True)
for i, patch in enumerate(ax_cap.patches):
    patch.set_facecolor(colors[i])  # Jede Säule bekommt ihre eigene Farbe
ax_cap.set_xticks(np.arange(0, len(df_costs), 0.5))
ax_cap.set_xticklabels(["","","2030","","","","","2045","",""],rotation=0)
ax_cap.tick_params(axis='x', length=0) 
ax_cap.axvline(2.5, color="black", linewidth=0.5, linestyle="--")
ax_cap.set_xlabel("")
ax_cap.set_ylabel("GW")
ax_cap.set_ylim(0,60)
#ax_cap.set_title("Total Expansion")

height_base = {}
for i in range(6): height_base[i] = 0

for num,bar in enumerate(ax_cap.patches):
    height = bar.get_height()  # Höhe des Balkens (Wert)
    height_base[num+5] = height
    ax_cap.text(
        bar.get_x() + bar.get_width() / 2,  # x-Position in der Mitte des Balkens
        height_base[num]+height/2-1.5, # y-Position leicht über dem Balken
        f'{height:.1f}',  # Textformat ohne Nachkommastellen
        ha='center',  # Horizontale Zentrierung
        va='bottom',  # Vertikale Positionierung
        fontsize=8
    )
    
    if height_base[num] > 0: 
        ax_cap.text(
            bar.get_x() + bar.get_width() / 2,  # x-Position in der Mitte des Balkens
            height_base[num]+height+2, # y-Position leicht über dem Balken
            f'{height_base[num]+height:.1f}',  # Textformat ohne Nachkommastellen
            ha='center',  # Horizontale Zentrierung
            va='bottom',  # Vertikale Positionierung
        )
    
handles = [plt.Rectangle((0, 0), 1, 1, color=l_colors[bar]) for bar in range(12)]
ax_cap.legend(
    handles=handles,
    labels=["","        PV","        EV","  Early  ", ""," ","   Flex "," "," ", "moreFlex    "," "," "],
    loc="lower center",
    ncol=4,
    bbox_to_anchor=(0.5,-0.35),  # + verschiebt es hoch 
    handletextpad=-3,
    alignment = "center"
)

fig_cap.savefig(r'figures\eval_expansion.jpg',format='jpg', dpi=1500,bbox_inches='tight') 

#%% costs of expansion and capacity merged

cm = 1 / 2.54
fig, (ax2, ax1) = plt.subplots(1, 2, figsize=(22*cm, 10*cm),
                               gridspec_kw={"width_ratios": [1, 1.5]})  # Zwei Subplots nebeneinander

# -------------------- Plot 1 --------------------
colors1 = ["indianred", "orange", "paleturquoise", "indianred", "orange",
           "lightcoral", "moccasin", "lightcyan", "lightcoral", "moccasin"]

l_colors1 = ["white", "white", "white", "white", "indianred", "lightcoral",
             "white", "orange", "moccasin", "white", "paleturquoise", "lightcyan"]

df_costs = pd.DataFrame([(dict_evaluation[i+"_"+str(j)][k]["diff_costs"],
                          dict_eval_expansion[i+"_"+str(j)]["annualized_costs"].loc[k[0].upper()+k[1:]+"NoConstraints"])
                         for i, j in l_runs for k in ["noFlex", "Flex"]],
                        columns=["System costs", "expansion costs"],
                        index=[i+"_"+str(j)+"_"+k for i, j in l_runs for k in ["noFlex", "Flex"]])

df_costs = df_costs.drop(index=["moreFlex_2030_noFlex"], errors="ignore")
df_costs.plot.bar(width=0.85, ax=ax1, legend=False)

for i, patch in enumerate(ax1.patches):
    patch.set_facecolor(colors1[i])

ax1.axvline(2.5, color="black", linewidth=0.5, linestyle="--")
ax1.set_ylabel('bn. EUR/a')
ax1.set_xticks(np.arange(0, len(df_costs), 0.5))
ax1.set_xticklabels(["", "", "2030", "", "", "", "", "2045", "", ""], rotation=0)
ax1.tick_params(axis='x', length=0)
ax1.set_ylim(0, 1.6)

for bar in ax1.patches:
    height = bar.get_height()
    ax1.text(bar.get_x() + bar.get_width() / 2,
             height + 0.05,
             f'{height:.2f}',
             ha='center', va='bottom')

handles1 = [plt.Rectangle((0, 0), 1, 1, color=l_colors1[bar]) for bar in range(12)]
ax1.legend(handles=handles1,
           labels=["", "    Congestion costs", "    Expansion costs", "  Early", "", "", "   Flex ", "", "", "moreFlex", "", ""],
           loc="lower center", ncol=4,
           bbox_to_anchor=(0.5, -0.35),
           handletextpad=-3,
           alignment="center")

# -------------------- Plot 2 --------------------
colors2 = colors1
l_colors2 = l_colors1

(dict_cause/1000).plot.bar(label="GW", ax=ax2, stacked=True, width=0.7)

for i, patch in enumerate(ax2.patches):
    patch.set_facecolor(colors2[i])

ax2.set_xticks(np.arange(0, len(df_costs), 0.5))
ax2.set_xticklabels(["", "", "2030", "", "", "", "", "2045", "", ""], rotation=0)
ax2.tick_params(axis='x', length=0)
ax2.axvline(2.5, color="black", linewidth=0.5, linestyle="--")
ax2.set_xlabel("")
ax2.set_ylabel("GW")
ax2.set_ylim(0, 60)

height_base = {}
for i in range(6):
    height_base[i] = 0

for num, bar in enumerate(ax2.patches):
    height = bar.get_height()
    height_base[num+5] = height
    ax2.text(bar.get_x() + bar.get_width() / 2,
             height_base[num] + height / 2 - 1.5,
             f'{height:.1f}', ha='center', va='bottom', fontsize=8)

    if height_base[num] > 0:
        ax2.text(bar.get_x() + bar.get_width() / 2,
                 height_base[num] + height + 2,
                 f'{height_base[num] + height:.1f}',
                 ha='center', va='bottom')

handles2 = [plt.Rectangle((0, 0), 1, 1, color=l_colors2[bar]) for bar in range(12)]
ax2.legend(handles=handles2,
           labels=["", "        PV", "        EV", "  Early  ", "", " ", "   Flex ", " ", " ", "moreFlex    ", " ", " "],
           loc="lower center", ncol=4,
           bbox_to_anchor=(0.5, -0.35),
           handletextpad=-3,
           alignment="center")

plt.tight_layout()
plt.show()

fig.savefig(r'figures\expansion_costs_cap.jpg',format='jpg', dpi=1500,bbox_inches='tight') 

#%% regionalized expansion

nuts3 = gpd.read_file(r"inputs/nuts250_12-31.utm32s.shape/nuts250_1231/NUTS250_N3.shp")
nuts3 = nuts3[nuts3.GF==4] # only keep land

for i,j in l_runs:
    agg_exp_nuts = max_diff[i+"_"+str(j)].groupby(["run","nuts"]).sum()["Val"]
    for run in ["NoFlexNoConstraints","FlexNoConstraints"]:
        nuts3[i+"_"+str(j) + "_expansion_" + run] = nuts3.NUTS_CODE.apply(lambda x: agg_exp_nuts.loc[run].reindex(nuts3.NUTS_CODE).fillna(0).loc[x])/1000

vmin=0
vmax=0.5#nuts3[[i+"_"+str(j) + "_expansion" for i,j in l_runs]].max().max()

fig, axes = plt.subplots(1,5,figsize=(22*cm, 22*cm))
num =0
for i,j in l_runs:
    for k in ["NoFlexNoConstraints","FlexNoConstraints"]:
        if i+"_"+str(j) + "_expansion_" + k == 'moreFlex_2030_expansion_NoFlexNoConstraints': continue
        nuts3.plot(column=i+"_"+str(j) + "_expansion_" + k ,edgecolor='lightgrey',cmap="Oranges", linewidth=0.2,ax=axes[num],vmin=vmin, vmax=vmax)
        axes[num].set_xticks([])  # Entfernt X-Ticks
        axes[num].set_yticks([])  # Entfernt Y-Ticks
        axes[num].spines['top'].set_visible(False)
        axes[num].spines['right'].set_visible(False)
        axes[num].spines['left'].set_visible(False)
        axes[num].spines['bottom'].set_visible(False)
        num += 1

plt.subplots_adjust(wspace=0.01)
sm = plt.cm.ScalarMappable(cmap="Oranges", norm=plt.Normalize(vmin=vmin, vmax=vmax))
cbar = fig.colorbar(sm, ax=axes, orientation="horizontal",shrink=0.5, pad=0.075)

cbar.set_ticks([i/10 for i in range(6)])              # Ticks setzen
cbar.set_ticklabels([i/10 for i in range(5)]+[">0.5"])   # Strings als Labels setzen
cbar.set_label("expansion [GW]")
        

x0, y0, width, height   = axes[0].get_tightbbox(fig.canvas.get_renderer()).transformed(fig.transFigure.inverted()).bounds
x2      = axes[2].get_tightbbox(fig.canvas.get_renderer()).transformed(fig.transFigure.inverted()).bounds[0]
x3      = axes[3].get_tightbbox(fig.canvas.get_renderer()).transformed(fig.transFigure.inverted()).bounds[0]
x4      = axes[4].get_tightbbox(fig.canvas.get_renderer()).transformed(fig.transFigure.inverted()).bounds[0]


linewidth = 1
fig.add_artist(plt.Line2D((x0, x0), (y0, y0+height), transform=fig.transFigure, color="grey", linewidth=linewidth))
fig.add_artist(plt.Line2D((x0+x3-0.1275, x0+x3-0.1275), (y0, y0+height), transform=fig.transFigure, color="grey", linewidth=linewidth, linestyle="--"))

fig.add_artist(plt.Line2D((x0, x0+x3-0.1275), (y0,y0), transform=fig.transFigure, color="grey", linewidth=linewidth))
fig.add_artist(plt.Line2D((x0, x0+x3-0.1275), (y0+height,y0+height), transform=fig.transFigure, color="grey", linewidth=linewidth))

fig.add_artist(plt.Line2D((x0+x3-0.1275,x4+0.155), (y0+height,y0+height), transform=fig.transFigure, color="grey", linewidth=linewidth))
fig.add_artist(plt.Line2D((x0+x3-0.1275,x4+0.155), (y0,y0), transform=fig.transFigure, color="grey", linewidth=linewidth))
fig.add_artist(plt.Line2D((x4+0.155,x4+0.155), (y0,y0+height), transform=fig.transFigure, color="grey", linewidth=linewidth))

l_xlabel = ["Early","Flex","moreFlex","Early","Flex"]

num =0
for i,j in l_runs:
    for k in ["NoFlexNoConstraints","FlexNoConstraints"]:
        if i+"_"+str(j) + "_expansion_" + k == 'moreFlex_2030_expansion_NoFlexNoConstraints': continue
        axes[num].set_xlabel(l_xlabel[num],labelpad=5)        
        num += 1
        
fig.suptitle("                2030                                                       2045", y=0.265)

fig.savefig(r'figures\expansion_heat_maps.jpg',format='jpg', dpi=1500,bbox_inches='tight') 
plt.show()





#%% regionalized expansion cause

nuts3 = gpd.read_file(r"inputs/nuts250_12-31.utm32s.shape/nuts250_1231/NUTS250_N3.shp")
nuts3 = nuts3[nuts3.GF==4] # only keep land

calc = [('baseFlex_2030', 'NoFlexNoConstraints'),
        ('baseFlex_2030', 'FlexNoConstraints'),
        ('moreFlex_2030', 'FlexNoConstraints'),
        ('baseFlex_2045', 'NoFlexNoConstraints'),
        ('baseFlex_2045', 'FlexNoConstraints')]

reg = {}
for i,j in l_runs:
    reg[i+"_"+str(j)] = pd.read_csv(r"inputs\total_cause_{}_{}_neu.csv".format(i,j)).set_axis(["m","nuts","run","cause","Val"],axis=1)
    reg[i+"_"+str(j)] = reg[i+"_"+str(j)].groupby(["nuts","cause","run"]).sum()["Val"].reset_index()
    reg[i+"_"+str(j)] = reg[i+"_"+str(j)][~reg[i+"_"+str(j)]["run"].isin(["NoFlexConstraints","FlexConstraints"])].set_index(["nuts","cause","run"])


reg = pd.concat([reg[r].set_axis([r],axis=1) for r in reg],axis=1).fillna(0)
reg = reg.stack().reset_index().set_axis(["nuts","cause","run","flex","val"],axis=1).pivot(index="nuts",columns=["flex","run","cause"],values="val").fillna(0)
reg = reg[[('baseFlex_2030', 'NoFlexNoConstraints',"pv"),('baseFlex_2030', 'NoFlexNoConstraints',"ev"),
           ('baseFlex_2030', 'FlexNoConstraints',"pv"),('baseFlex_2030', 'FlexNoConstraints',"ev"),
           ('moreFlex_2030', 'FlexNoConstraints',"pv"),('moreFlex_2030', 'FlexNoConstraints',"ev"),
           ('baseFlex_2045', 'NoFlexNoConstraints',"pv"),('baseFlex_2045', 'NoFlexNoConstraints',"ev"),
           ('baseFlex_2045', 'FlexNoConstraints',"pv"),('baseFlex_2045', 'FlexNoConstraints',"ev")]]
reg = pd.DataFrame({c:(reg[c]["pv"]/reg[c].sum(axis=1)).fillna(0) for c in calc})

nuts3 = pd.concat((nuts3,nuts3["NUTS_CODE"].apply(lambda x: reg.loc[x])),axis=1)

vmin=0
vmax=1

fig, axes = plt.subplots(1,5,figsize=(22*cm, 22*cm))
num =0
for i,j in l_runs:
    for k in ["NoFlexNoConstraints","FlexNoConstraints"]:
        if i+"_"+str(j) + "_expansion_" + k == 'moreFlex_2030_expansion_NoFlexNoConstraints': continue
        nuts3.plot(column=(i+"_"+str(j), k) ,edgecolor='lightgrey',cmap="RdYlGn", linewidth=0.2,ax=axes[num],vmin=vmin, vmax=vmax)
        axes[num].set_xticks([])  # Entfernt X-Ticks
        axes[num].set_yticks([])  # Entfernt Y-Ticks
        axes[num].spines['top'].set_visible(False)
        axes[num].spines['right'].set_visible(False)
        axes[num].spines['left'].set_visible(False)
        axes[num].spines['bottom'].set_visible(False)
        num += 1

plt.subplots_adjust(wspace=0.01)
sm = plt.cm.ScalarMappable(cmap="RdYlGn", norm=plt.Normalize(vmin=vmin, vmax=vmax))
cbar = fig.colorbar(sm, ax=axes, orientation="horizontal",shrink=0.5, pad=0.075)

cbar.set_ticks([0,0.5,1])              # Ticks setzen
cbar.set_ticklabels(["100% LOAD","eq. shares","100% RES"])   # Strings als Labels setzen
cbar.set_label("expansion driver")
        

x0, y0, width, height   = axes[0].get_tightbbox(fig.canvas.get_renderer()).transformed(fig.transFigure.inverted()).bounds
x2      = axes[2].get_tightbbox(fig.canvas.get_renderer()).transformed(fig.transFigure.inverted()).bounds[0]
x3      = axes[3].get_tightbbox(fig.canvas.get_renderer()).transformed(fig.transFigure.inverted()).bounds[0]
x4      = axes[4].get_tightbbox(fig.canvas.get_renderer()).transformed(fig.transFigure.inverted()).bounds[0]


linewidth = 1
fig.add_artist(plt.Line2D((x0, x0), (y0, y0+height), transform=fig.transFigure, color="grey", linewidth=linewidth))
fig.add_artist(plt.Line2D((x0+x3-0.1275, x0+x3-0.1275), (y0, y0+height), transform=fig.transFigure, color="grey", linewidth=linewidth, linestyle="--"))

fig.add_artist(plt.Line2D((x0, x0+x3-0.1275), (y0,y0), transform=fig.transFigure, color="grey", linewidth=linewidth))
fig.add_artist(plt.Line2D((x0, x0+x3-0.1275), (y0+height,y0+height), transform=fig.transFigure, color="grey", linewidth=linewidth))

fig.add_artist(plt.Line2D((x0+x3-0.1275,x4+0.155), (y0+height,y0+height), transform=fig.transFigure, color="grey", linewidth=linewidth))
fig.add_artist(plt.Line2D((x0+x3-0.1275,x4+0.155), (y0,y0), transform=fig.transFigure, color="grey", linewidth=linewidth))
fig.add_artist(plt.Line2D((x4+0.155,x4+0.155), (y0,y0+height), transform=fig.transFigure, color="grey", linewidth=linewidth))

l_xlabel = ["Early","Flex","moreFlex","Early","Flex"]

num =0
for i,j in l_runs:
    for k in ["NoFlexNoConstraints","FlexNoConstraints"]:
        if (i+"_"+str(j), k) == ('moreFlex_2030','NoFlexNoConstraints'): continue
        axes[num].set_xlabel(l_xlabel[num],labelpad=5)        
        num += 1
        
fig.suptitle("                2030                                                       2045", y=0.265)

fig.savefig(r'figures\expansion_heat_maps_cause.jpg',format='jpg', dpi=1500,bbox_inches='tight') 
plt.show()

#%% merge maps

nuts3 = gpd.read_file(r"inputs/nuts250_12-31.utm32s.shape/nuts250_1231/NUTS250_N3.shp")
nuts3 = nuts3[nuts3.GF==4] # only keep land

for i,j in l_runs:
    agg_exp_nuts = max_diff[i+"_"+str(j)].groupby(["run","nuts"]).sum()["Val"]
    for run in ["NoFlexNoConstraints","FlexNoConstraints"]:
        nuts3[i+"_"+str(j) + "_expansion_" + run] = nuts3.NUTS_CODE.apply(lambda x: agg_exp_nuts.loc[run].reindex(nuts3.NUTS_CODE).fillna(0).loc[x])/1000

vmin=0
vmax=0.5

fig, axes = plt.subplots(2,5,figsize=(22*cm, 22*cm))
num =0
for i,j in l_runs:
    for k in ["NoFlexNoConstraints","FlexNoConstraints"]:
        if i+"_"+str(j) + "_expansion_" + k == 'moreFlex_2030_expansion_NoFlexNoConstraints': continue
        nuts3.plot(column=i+"_"+str(j) + "_expansion_" + k ,edgecolor='grey',cmap="Oranges", linewidth=0.2,ax=axes[0][num],vmin=vmin, vmax=vmax)
        axes[0][num].set_xticks([])  # Entfernt X-Ticks
        axes[0][num].set_yticks([])  # Entfernt Y-Ticks
        axes[0][num].spines['top'].set_visible(False)
        axes[0][num].spines['right'].set_visible(False)
        axes[0][num].spines['left'].set_visible(False)
        axes[0][num].spines['bottom'].set_visible(False)
        num += 1

plt.subplots_adjust(wspace=0.01)
sm = plt.cm.ScalarMappable(cmap="Oranges", norm=plt.Normalize(vmin=vmin, vmax=vmax))
cbar = fig.colorbar(sm, ax=axes, orientation="horizontal",shrink=0.5, pad=0.075)
pos = cbar.ax.get_position()
cbar.ax.set_position([pos.x0, pos.y0+0.35, pos.width, pos.height])

cbar.set_ticks([i/10 for i in range(6)])              # Ticks setzen
cbar.set_ticklabels([i/10 for i in range(5)]+[">0.5"])   # Strings als Labels setzen
cbar.set_label("expansion [GW]")
        
x0, y0, width, height   = axes[0][0].get_tightbbox(fig.canvas.get_renderer()).transformed(fig.transFigure.inverted()).bounds
x2      = axes[0][2].get_tightbbox(fig.canvas.get_renderer()).transformed(fig.transFigure.inverted()).bounds[0]
x3      = axes[0][3].get_tightbbox(fig.canvas.get_renderer()).transformed(fig.transFigure.inverted()).bounds[0]
x4      = axes[0][4].get_tightbbox(fig.canvas.get_renderer()).transformed(fig.transFigure.inverted()).bounds[0]

linewidth = 1
fig.add_artist(plt.Line2D((x0, x0), (y0, y0+height), transform=fig.transFigure, color="grey", linewidth=linewidth))
fig.add_artist(plt.Line2D((x0+x3-0.1275, x0+x3-0.1275), (y0, y0+height), transform=fig.transFigure, color="grey", linewidth=linewidth, linestyle="--"))

fig.add_artist(plt.Line2D((x0, x0+x3-0.1275), (y0,y0), transform=fig.transFigure, color="grey", linewidth=linewidth))
fig.add_artist(plt.Line2D((x0, x0+x3-0.1275), (y0+height,y0+height), transform=fig.transFigure, color="grey", linewidth=linewidth))

fig.add_artist(plt.Line2D((x0+x3-0.1275,x4+0.155), (y0+height,y0+height), transform=fig.transFigure, color="grey", linewidth=linewidth))
fig.add_artist(plt.Line2D((x0+x3-0.1275,x4+0.155), (y0,y0), transform=fig.transFigure, color="grey", linewidth=linewidth))
fig.add_artist(plt.Line2D((x4+0.155,x4+0.155), (y0,y0+height), transform=fig.transFigure, color="grey", linewidth=linewidth))

# lower heatmap
nuts3 = gpd.read_file(r"inputs/nuts250_12-31.utm32s.shape/nuts250_1231/NUTS250_N3.shp")
nuts3 = nuts3[nuts3.GF==4] # only keep land

calc = [('baseFlex_2030', 'NoFlexNoConstraints'),
        ('baseFlex_2030', 'FlexNoConstraints'),
        ('moreFlex_2030', 'FlexNoConstraints'),
        ('baseFlex_2045', 'NoFlexNoConstraints'),
        ('baseFlex_2045', 'FlexNoConstraints')]

reg = {}
for i,j in l_runs:
    reg[i+"_"+str(j)] = pd.read_csv(r"inputs\total_cause_{}_{}_neu.csv".format(i,j)).set_axis(["m","nuts","run","cause","Val"],axis=1)
    reg[i+"_"+str(j)] = reg[i+"_"+str(j)].groupby(["nuts","cause","run"]).sum()["Val"].reset_index()
    reg[i+"_"+str(j)] = reg[i+"_"+str(j)][~reg[i+"_"+str(j)]["run"].isin(["NoFlexConstraints","FlexConstraints"])].set_index(["nuts","cause","run"])

reg = pd.concat([reg[r].set_axis([r],axis=1) for r in reg],axis=1).fillna(0)
reg = reg.stack().reset_index().set_axis(["nuts","cause","run","flex","val"],axis=1).pivot(index="nuts",columns=["flex","run","cause"],values="val").fillna(0)
reg = reg[[('baseFlex_2030', 'NoFlexNoConstraints',"pv"),('baseFlex_2030', 'NoFlexNoConstraints',"ev"),
           ('baseFlex_2030', 'FlexNoConstraints',"pv"),('baseFlex_2030', 'FlexNoConstraints',"ev"),
           ('moreFlex_2030', 'FlexNoConstraints',"pv"),('moreFlex_2030', 'FlexNoConstraints',"ev"),
           ('baseFlex_2045', 'NoFlexNoConstraints',"pv"),('baseFlex_2045', 'NoFlexNoConstraints',"ev"),
           ('baseFlex_2045', 'FlexNoConstraints',"pv"),('baseFlex_2045', 'FlexNoConstraints',"ev")]]
reg = pd.DataFrame({c:(reg[c]["pv"]/reg[c].sum(axis=1)).fillna(0) for c in calc})

nuts3 = pd.concat((nuts3,nuts3["NUTS_CODE"].apply(lambda x: reg.loc[x])),axis=1)

vmin=0
vmax=1

num =0
for i,j in l_runs:
    for k in ["NoFlexNoConstraints","FlexNoConstraints"]:
        if i+"_"+str(j) + "_expansion_" + k == 'moreFlex_2030_expansion_NoFlexNoConstraints': continue
        nuts3.plot(column=(i+"_"+str(j), k) ,edgecolor='lightgrey',cmap="RdYlGn", linewidth=0.2,ax=axes[1][num],vmin=vmin, vmax=vmax)
        axes[1][num].set_xticks([])  # Entfernt X-Ticks
        axes[1][num].set_yticks([])  # Entfernt Y-Ticks
        axes[1][num].spines['top'].set_visible(False)
        axes[1][num].spines['right'].set_visible(False)
        axes[1][num].spines['left'].set_visible(False)
        axes[1][num].spines['bottom'].set_visible(False)
        num += 1

plt.subplots_adjust(wspace=0.01)
sm = plt.cm.ScalarMappable(cmap="RdYlGn", norm=plt.Normalize(vmin=vmin, vmax=vmax))
cbar = fig.colorbar(sm, ax=axes, orientation="horizontal",shrink=0.5, pad=0.075)

cbar.set_ticks([0,0.5,1])              # Ticks setzen
cbar.set_ticklabels(["100% LOAD","eq. shares","100% RES"])   # Strings als Labels setzen
cbar.set_label("expansion driver")
        
x0, y0, width, height   = axes[1][0].get_tightbbox(fig.canvas.get_renderer()).transformed(fig.transFigure.inverted()).bounds
x2      = axes[1][2].get_tightbbox(fig.canvas.get_renderer()).transformed(fig.transFigure.inverted()).bounds[0]
x3      = axes[1][3].get_tightbbox(fig.canvas.get_renderer()).transformed(fig.transFigure.inverted()).bounds[0]
x4      = axes[1][4].get_tightbbox(fig.canvas.get_renderer()).transformed(fig.transFigure.inverted()).bounds[0]

linewidth = 1
fig.add_artist(plt.Line2D((x0, x0), (y0, y0+height), transform=fig.transFigure, color="grey", linewidth=linewidth))
fig.add_artist(plt.Line2D((x0+x3-0.1275, x0+x3-0.1275), (y0, y0+height), transform=fig.transFigure, color="grey", linewidth=linewidth, linestyle="--"))

fig.add_artist(plt.Line2D((x0, x0+x3-0.1275), (y0,y0), transform=fig.transFigure, color="grey", linewidth=linewidth))
fig.add_artist(plt.Line2D((x0, x0+x3-0.1275), (y0+height,y0+height), transform=fig.transFigure, color="grey", linewidth=linewidth))

fig.add_artist(plt.Line2D((x0+x3-0.1275,x4+0.155), (y0+height,y0+height), transform=fig.transFigure, color="grey", linewidth=linewidth))
fig.add_artist(plt.Line2D((x0+x3-0.1275,x4+0.155), (y0,y0), transform=fig.transFigure, color="grey", linewidth=linewidth))
fig.add_artist(plt.Line2D((x4+0.155,x4+0.155), (y0,y0+height), transform=fig.transFigure, color="grey", linewidth=linewidth))

l_xlabel = ["Early","Flex","moreFlex","Early","Flex"]

num =0
for i,j in l_runs:
    for k in ["NoFlexNoConstraints","FlexNoConstraints"]:
        if (i+"_"+str(j), k) == ('moreFlex_2030','NoFlexNoConstraints'): continue
        axes[1][num].set_xlabel(l_xlabel[num],labelpad=5)        
        num += 1
        
fig.suptitle("                2030                                                       2045", y=0.265)
    
fig.savefig(r'figures\expansion_heat_maps_merged.jpg',format='jpg', dpi=1500,bbox_inches='tight') 
plt.show()


# =============================================================================
# %% INTERACTIVE MAP — Plotly (Option A: single map + dropdown)
#
# Reproduces the merged heatmap (expansion GW + expansion driver) as one
# interactive Plotly map with a dropdown to switch between all 5 scenarios
# and both data layers.
#
# OUTPUT FILES:
#   figures/interactive_expansion_map.html  → open in any browser
# =============================================================================
# %% INTERACTIVE MAP — Plotly (Option A: single map + dropdown)
#
# Reproduces the merged heatmap (expansion GW + expansion driver) as one
# interactive Plotly map with a dropdown to switch between all 5 scenarios
# and both data layers.
#
# OUTPUT FILES:
#   figures/interactive_expansion_map.html  → open in any browser
#   figures/interactive_expansion_map.json  → load in Streamlit with:
#       import plotly.io as pio
#       fig = pio.read_json("path/to/interactive_expansion_map.json")
#       st.plotly_chart(fig, use_container_width=True)
#
# NOTE: Copy this entire section into your Streamlit page and replace the
#       last three lines (write_html / write_json / show) with:
#           st.plotly_chart(fig_interactive, use_container_width=True)
# =============================================================================

import plotly.graph_objects as go
import plotly.io as pio
import json

# ── 1. Load shapefile; compute centroids in projected CRS, then reproject ─────
nuts3_int = gpd.read_file(
    r"inputs/nuts250_12-31.utm32s.shape/nuts250_1231/NUTS250_N3.shp"
)
nuts3_int = nuts3_int[nuts3_int.GF == 4].copy()

# Simplify the geometry to drastically reduce file size (from 200MB to ~5MB)
# 1000m tolerance reduces vertices while preserving high visual quality
nuts3_int.geometry = nuts3_int.geometry.simplify(1000, preserve_topology=True)

# Compute centroids while still in projected UTM32S (accurate, no warnings)
_nuts3_cents_wgs84 = nuts3_int.geometry.centroid.to_crs(epsg=4326)

# Now reproject the full GeoDataFrame to WGS84 for Plotly
nuts3_int = nuts3_int.to_crs(epsg=4326)
nuts3_int["lon"] = _nuts3_cents_wgs84.x
nuts3_int["lat"] = _nuts3_cents_wgs84.y

# ── 2. Attach expansion data for all 5 scenarios ─────────────────────────────
scenarios_def = [
    ("baseFlex",  2030, "NoFlexNoConstraints", "Early 2030"),
    ("baseFlex",  2030, "FlexNoConstraints",   "Flex 2030"),
    ("moreFlex",  2030, "FlexNoConstraints",   "moreFlex 2030"),
    ("baseFlex",  2045, "NoFlexNoConstraints", "Early 2045"),
    ("baseFlex",  2045, "FlexNoConstraints",   "Flex 2045"),
]

for flex, year, run, scen_label in scenarios_def:
    key = flex + "_" + str(year)
    agg_exp = max_diff[key].groupby(["run", "nuts"]).sum()["Val"]
    exp_series = agg_exp.loc[run] / 1000          # convert MW → GW
    nuts3_int[f"exp_{key}_{run}"] = (
        nuts3_int["NUTS_CODE"].map(exp_series).fillna(0)
    )

# ── 3. Attach expansion-driver data for all 5 scenarios ──────────────────────
calc_int = [
    ("baseFlex_2030", "NoFlexNoConstraints"),
    ("baseFlex_2030", "FlexNoConstraints"),
    ("moreFlex_2030", "FlexNoConstraints"),
    ("baseFlex_2045", "NoFlexNoConstraints"),
    ("baseFlex_2045", "FlexNoConstraints"),
]

reg_i = {}
for flex, year in l_runs:
    key = flex + "_" + str(year)
    df_i = (
        pd.read_csv(r"inputs\total_cause_{}_{}_neu.csv".format(flex, year))
        .set_axis(["m", "nuts", "run", "cause", "Val"], axis=1)
    )
    df_i = df_i.groupby(["nuts", "cause", "run"]).sum()["Val"].reset_index()
    df_i = df_i[
        ~df_i["run"].isin(["NoFlexConstraints", "FlexConstraints"])
    ].set_index(["nuts", "cause", "run"])
    reg_i[key] = df_i

reg_i_df = pd.concat(
    [reg_i[r].set_axis([r], axis=1) for r in reg_i], axis=1
).fillna(0)
reg_i_df = (
    reg_i_df.stack()
    .reset_index()
    .set_axis(["nuts", "cause", "run", "flex", "val"], axis=1)
    .pivot(index="nuts", columns=["flex", "run", "cause"], values="val")
    .fillna(0)
)
reg_i_df = reg_i_df[
    [
        ("baseFlex_2030", "NoFlexNoConstraints", "pv"),
        ("baseFlex_2030", "NoFlexNoConstraints", "ev"),
        ("baseFlex_2030", "FlexNoConstraints",   "pv"),
        ("baseFlex_2030", "FlexNoConstraints",   "ev"),
        ("moreFlex_2030", "FlexNoConstraints",   "pv"),
        ("moreFlex_2030", "FlexNoConstraints",   "ev"),
        ("baseFlex_2045", "NoFlexNoConstraints", "pv"),
        ("baseFlex_2045", "NoFlexNoConstraints", "ev"),
        ("baseFlex_2045", "FlexNoConstraints",   "pv"),
        ("baseFlex_2045", "FlexNoConstraints",   "ev"),
    ]
]
driver_ratio_int = pd.DataFrame(
    {c: (reg_i_df[c]["pv"] / reg_i_df[c].sum(axis=1)).fillna(0) for c in calc_int}
)

for flex_key, run_key in calc_int:
    nuts3_int[f"driver_{flex_key}_{run_key}"] = (
        nuts3_int["NUTS_CODE"].map(driver_ratio_int[(flex_key, run_key)]).fillna(0)
    )

# ── 4. Derive state (NUTS1) boundaries and names ──────────────────────────────
nuts3_int["NUTS1"] = nuts3_int["NUTS_CODE"].str[:3]
# Only dissolve geometry for state polygons (avoids Timestamp columns)
nuts1_int = nuts3_int[["NUTS1", "geometry"]].dissolve(by="NUTS1").reset_index()

GERMAN_STATES = {
    "DE1": "Baden-\nWürttemberg", "DE2": "Bayern",
    "DE3": "Berlin",              "DE4": "Brandenburg",
    "DE5": "Bremen",              "DE6": "Hamburg",
    "DE7": "Hessen",              "DE8": "Mecklenburg-\nVorpommern",
    "DE9": "Niedersachsen",       "DEA": "Nordrhein-\nWestfalen",
    "DEB": "Rheinland-Pfalz",     "DEC": "Saarland",
    "DED": "Sachsen",             "DEE": "Sachsen-Anhalt",
    "DEF": "Schleswig-\nHolstein","DEG": "Thüringen",
}
nuts1_int["state_name"] = nuts1_int["NUTS1"].map(GERMAN_STATES)

# Compute state centroids in projected CRS (UTM32S) before converting to WGS84
_nuts1_proj = nuts1_int.to_crs(epsg=32632)
_state_cents_wgs84 = _nuts1_proj.geometry.centroid.to_crs(epsg=4326)
nuts1_int["lon"] = _state_cents_wgs84.x
nuts1_int["lat"] = _state_cents_wgs84.y

# ── 5. Build GeoJSON — only serialize NUTS_CODE + GEN + geometry ──────────────
# Keeping only needed columns avoids Timestamp serialization errors from
# shapefile metadata columns (e.g. date fields)
_nuts3_for_json = nuts3_int[["NUTS_CODE", "NUTS_NAME", "geometry"]].copy()
nuts3_geojson_int = json.loads(_nuts3_for_json.to_json())
for feat in nuts3_geojson_int["features"]:
    feat["id"] = feat["properties"]["NUTS_CODE"]

# ── 6. Define all 10 trace combos (5 scenarios × 2 layers) ───────────────────
all_combos = []
for flex, year, run, scen_label in scenarios_def:
    key = flex + "_" + str(year)
    # Expansion layer
    all_combos.append({
        "label":       scen_label,
        "layer":       "expansion",
        "col":         f"exp_{key}_{run}",
        "colorscale":  "Oranges",
        "zmin": 0, "zmax": 0.5,
        "cb_title":    "Expansion<br>[GW]",
        "cb_tickvals": [0, 0.1, 0.2, 0.3, 0.4, 0.5],
        "cb_ticktext": ["0.0","0.1","0.2","0.3","0.4",">0.5"],
    })
    # Expansion driver layer
    all_combos.append({
        "label":       scen_label,
        "layer":       "driver",
        "col":         f"driver_{key}_{run}",
        "colorscale":  "RdYlGn",
        "zmin": 0, "zmax": 1,
        "cb_title":    "Expansion<br>Driver",
        "cb_tickvals": [0, 0.5, 1],
        "cb_ticktext": ["100% EV\nLoad", "Equal\nshares", "100%\nPV"],
    })

# ── 7. Build Plotly figure ────────────────────────────────────────────────────
fig_interactive = go.Figure()

for idx, combo in enumerate(all_combos):
    visible = (idx == 0)   # only first combo visible on load
    z       = nuts3_int[combo["col"]].tolist()
    names   = nuts3_int["NUTS_NAME"].tolist()
    codes   = nuts3_int["NUTS_CODE"].tolist()

    if combo["layer"] == "expansion":
        hover = [
            f"<b>{n}</b><br>NUTS: {c}<br>Expansion: {v:.3f} GW"
            for n, c, v in zip(names, codes, z)
        ]
    else:
        hover = [
            f"<b>{n}</b><br>NUTS: {c}<br>PV share: {v:.1%} | EV share: {1-v:.1%}"
            for n, c, v in zip(names, codes, z)
        ]

    # Choropleth layer. Use the mapbox trace type (not the Plotly-6 maplibre
    # "Choroplethmap"): Streamlit 1.39's bundled plotly.js renders mapbox
    # traces but not the newer maplibre ones, so maplibre traces show up as an
    # empty cartesian plot in the dashboard.
    fig_interactive.add_trace(go.Choroplethmapbox(
        geojson=nuts3_geojson_int,
        locations=codes,
        z=z,
        colorscale=combo["colorscale"],
        zmin=combo["zmin"],
        zmax=combo["zmax"],
        marker=dict(opacity=0.75, line=dict(width=0.3, color="#aaaaaa")),
        colorbar=dict(
            title=dict(text=combo["cb_title"], side="right"),
            tickvals=combo["cb_tickvals"],
            ticktext=combo["cb_ticktext"],
            thickness=14, len=0.45, x=1.01, y=0.5,
        ),
        hovertext=hover,
        hoverinfo="text",
        visible=visible,
        name=f"{combo['label']} | {'Expansion (GW)' if combo['layer']=='expansion' else 'Expansion Driver'}",
    ))

    # District name labels — small font, readable only when zoomed in
    fig_interactive.add_trace(go.Scattermapbox(
        lon=nuts3_int["lon"].tolist(),
        lat=nuts3_int["lat"].tolist(),
        mode="text",
        text=names,
        textfont=dict(size=7, color="rgba(20,20,20,0.70)"),
        hoverinfo="skip",
        visible=visible,
        showlegend=False,
        name=f"district_labels_{idx}",
    ))

# State name labels — bold, always visible at all zoom levels
fig_interactive.add_trace(go.Scattermapbox(
    lon=nuts1_int["lon"].tolist(),
    lat=nuts1_int["lat"].tolist(),
    mode="text",
    text=nuts1_int["state_name"].tolist(),
    textfont=dict(size=11, color="black"),
    hoverinfo="skip",
    visible=True,
    showlegend=False,
    name="state_labels",
))

# ── 8. Build dropdown buttons (10 options) ────────────────────────────────────
n_traces_total = len(all_combos) * 2 + 1  # choropleth + district_labels per combo + state_labels

dropdown_buttons = []
for idx, combo in enumerate(all_combos):
    vis = [False] * n_traces_total
    vis[idx * 2]     = True   # choropleth
    vis[idx * 2 + 1] = True   # district labels
    vis[-1]          = True   # state labels always on

    layer_disp = "Expansion [GW]" if combo["layer"] == "expansion" else "Expansion Driver"
    dropdown_buttons.append(dict(
        args=[{"visible": vis}],
        label=f"{combo['label']}  ·  {layer_disp}",
        method="update",
    ))

# ── 9. Layout ─────────────────────────────────────────────────────────────────
fig_interactive.update_layout(
    title=dict(
        text=(
            "<b>Grid Expansion — Interactive Map of Germany</b><br>"
            "<sup style='color:grey'>Select scenario and data layer · "
            "Zoom in to read district names · Hover for values</sup>"
        ),
        x=0.5, xanchor="center", y=0.97,
    ),
    updatemenus=[dict(
        buttons=dropdown_buttons,
        direction="down",
        showactive=True,
        x=0.01, xanchor="left",
        y=0.99, yanchor="top",
        bgcolor="white",
        bordercolor="#888888",
        font=dict(size=12),
        pad=dict(r=10, t=10),
    )],
    mapbox=dict(
        style="carto-positron",      # free tile, no Mapbox token needed
        center=dict(lat=51.2, lon=10.4),
        zoom=5,
    ),
    margin=dict(l=0, r=0, t=90, b=0),
    height=750,
    paper_bgcolor="white",
)

# ── 10. Save and display ──────────────────────────────────────────────────────
fig_interactive.write_html(r"figures\interactive_expansion_map.html")
# Write explicit UTF-8: pio.write_json() uses the platform default encoding
# (cp1252 on Windows), which the Streamlit Cloud loader (Linux/UTF-8) cannot
# decode for German district names such as "Böblingen".
with open(r"figures\interactive_expansion_map.json", "w", encoding="utf-8") as _f:
    _f.write(pio.to_json(fig_interactive))
print("Interactive map saved:")
print("   -> figures/interactive_expansion_map.html  (open in browser)")
print("   -> figures/interactive_expansion_map.json  (load in Streamlit)")
# fig_interactive.show()

