#%% -*- coding: utf-8 -*-
"""
Created on Tue Nov 12 12:01:32 2024

@author: lilienkampa
"""

import pandas as pd
import os
import numpy as np
import pickle
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
from matplotlib.lines import Line2D
import datetime
import matplotlib.gridspec as gridspec

import streamlit as st
from st_files_connection import FilesConnection

#%% FIGURE 5
def fig_5():
    
    conn = st.connection('gcs', type=FilesConnection)
    prices = conn.read("vise-d/prices.csv", input_format="csv", ttl=100)
    prices.index = prices["Unnamed: 0"]
    prices.drop(columns=["Unnamed: 0"], inplace=True)
    
    data = np.array(conn.read("vise-d/da_data.csv", input_format="csv", ttl=100))

    colors = {"offpeak":"burlywood","median":"burlywood","peak":"burlywood","rp_purchase":"burlywood","rp_grid":"lightgreen","rp_levy":"pink","rp_tax":"lightgrey","mean":"grey","day_ahead_price_q":"lightblue"}
    labels = {"offpeak":"burlywood","median":"burlywood","peak":"burlywood","rp_purchase":"procurement","rp_grid":"grid usage fee","rp_levy":"levies","rp_tax":"tax","mean":"mean","day_ahead_price_q":"wholesale price"}
    cm = 1 / 2.54
    fig, axes = plt.subplots(nrows=1, ncols=2, figsize=(18 * cm, 9 * cm),gridspec_kw={'width_ratios': [1, 2]})  # paper

    # fix fix component
    prices.loc["q00001","rp_purchase"] = 59.6
    #merge purchase component
    prices["purchase"] = prices[["rp_purchase","time_of_use_q"]].fillna(0).sum(axis=1)
    prices.drop(columns=["rp_purchase","time_of_use_q"],inplace=True)

    # calculate tax
    prices["rp_tax"] = (prices[["purchase","rp_grid","rp_levy"]].sum(axis=1) +20.5) * 0.19  +20.5
    # order df
    prices = prices[["purchase","rp_grid","rp_levy","rp_tax"]]
    prices.reset_index().plot.bar(stacked=True,ax=axes[1], legend=False, color=[colors[x] for x in ["rp_purchase","rp_grid","rp_levy","rp_tax"]])

    axes[1].tick_params(
        axis='x',          # changes apply to the x-axis
        which='both',      # both major and minor ticks are affected
        bottom=True,      # ticks along the bottom edge are off
        top=False,         # ticks along the top edge are off
        labelbottom=True, # labels along the bottom edge are off
        labelrotation=0)
    axes[1].set_xticklabels(["Fix","ToU\n(0-8)","ToU\n(8-16)","ToU\n(16-24)"])
    axes[1].set_ylabel("EUR/MWh")
    for bars in axes[1].containers:
        axes[1].bar_label(bars, label_type="center",fmt="%.1f")

    for num,index in enumerate(prices.index):
        y=(prices[["purchase","rp_grid","rp_levy","rp_tax"]].loc[index]).sum()
        axes[1].annotate("{:.1f}".format(y),(num, y), ha='center',xytext=(num, 270))

    axes[1].set_ylim((-17.5,317))
    #axes[1].set_title("B) Consumer price for electricity (fixed tariff and ToU-tariff)")
    axes[1].yaxis.grid(True)
    axes[1].set_axisbelow(True)
    axes[1].set_ylim((0,300))

    # fix consumer rate
    axes[0].yaxis.grid(True)
    axes[0].yaxis.set_ticks(np.arange(0, 110, 25))
    axes[0].xaxis.set_ticks(np.arange(-60, 150, 30))
    #axes[0].set_title("A) Electricity wholesale prices")

    p = 1. * np.arange(len(data)) / float(len(data) - 1) *100
    np.linspace(0, 1, len(data), endpoint=False)

    axes[0].plot(data, p,c=colors["day_ahead_price_q"])
    axes[0].set_xlabel('EUR/MWh')
    axes[0].set_ylabel('%',labelpad=-5)
    axes[0].set_ylim((0,100))

    patches_dict = {"day_ahead_price_q": Line2D([0], [0], lw=2, color=colors["day_ahead_price_q"], label=labels["day_ahead_price_q"]),
                    "rp_purchase": Patch(color=colors["rp_purchase"], label=labels["rp_purchase"]),
                    "rp_grid": Patch(color=colors["rp_grid"], label=labels["rp_grid"]),
                    "rp_levy": Patch(color=colors["rp_levy"], label=labels["rp_levy"]),
                    "rp_tax": Patch(color=colors["rp_tax"], label=labels["rp_tax"])}

    patches = []
    for patch in ["day_ahead_price_q","rp_purchase","rp_grid","rp_levy","rp_tax"]:
        patches.append(patches_dict[patch])

    lgd  = fig.legend(handles=patches, loc='lower center', ncol=3, bbox_to_anchor = [0.5, -0.17])

    fig.tight_layout()
    
    return fig

#%% FIGURE 7
def fig_7():

    conn = st.connection('gcs', type=FilesConnection)
    trafo_loadings = conn.read("vise-d/trafo_loadings.json", input_format="json", ttl=100)
    
    dRates = ['dRate_30', 'dRate_50', 'dRate_70']
    costs = {}
    for key in dRates:
        costs[key] = conn.read(f'vise-d/{key}_costs.csv', input_format="csv", ttl=100, header=[0, 1], index_col=[0])

    start_time = datetime.time(0, 0)
    # end_time = datetime.time(23, 59)
    time_step = datetime.timedelta(minutes=15)
    time_list = []
    current_time = datetime.datetime.combine(datetime.date.today(), start_time)
    while len(time_list) <= 288:
        time_list.append(current_time.time().strftime('%H:%M'))
        current_time += time_step

    color2 = "sandybrown"
    color3 = "salmon"

    cm = 1 / 2.54
    fig = plt.figure(figsize=(18*cm, 13*cm))
    # Define the grid
    gs = gridspec.GridSpec(3, 2, width_ratios=[7, 3])

    linewidth = 1.2
    ax = []

    # dRate 30
    ax.append(fig.add_subplot(gs[0, 0]))
    ax[0].plot(range(1, len(trafo_loadings['30']['0'])+1), trafo_loadings['30']['0'], color='black', linewidth=linewidth, linestyle='dashed')
    ax[0].plot(range(1, len(trafo_loadings['30']['2'])+1), trafo_loadings['30']['1'], color=color2, linewidth=linewidth)
    ax[0].plot(range(1, len(trafo_loadings['30']['1'])+1), trafo_loadings['30']['2'], color=color3, linewidth=linewidth)
    # ax[0].plot(range(1, len(trafo_loadings['30'][2])+1), np.ones(len(trafo_loadings['30'][2])) * 100, color='red', linewidth=linewidth)
    ax[0].set_ylabel(r'$\mathbf{dRate\ 30}$' +'\n\nMVA', fontsize=8)

    # dRate 50
    ax.append(fig.add_subplot(gs[1, 0]))
    ax[1].plot(range(1, len(trafo_loadings['50']['0'])+1), trafo_loadings['50']['0'], color='black', linewidth=linewidth, linestyle='dashed')
    ax[1].plot(range(1, len(trafo_loadings['50']['2'])+1), trafo_loadings['50']['1'], color=color2, linewidth=linewidth)
    ax[1].plot(range(1, len(trafo_loadings['50']['1'])+1), trafo_loadings['50']['2'], color=color3, linewidth=linewidth)
    # ax[1].plot(range(1, len(trafo_loadings['40'][2])+1), np.ones(len(trafo_loadings['40'][2])) * 100, color='red', linewidth=linewidth)
    ax[1].set_ylabel(r'$\mathbf{dRate\ 50}$' +'\n\nMVA', fontsize=8)

    # dRate 70
    ax.append(fig.add_subplot(gs[2, 0]))
    ax[2].plot(range(1, len(trafo_loadings['70']['0'])+1), trafo_loadings['70']['0'], color='black', linewidth=linewidth, linestyle='dashed')
    ax[2].plot(range(1, len(trafo_loadings['70']['2'])+1), trafo_loadings['70']['1'], color=color2, linewidth=linewidth)
    ax[2].plot(range(1, len(trafo_loadings['70']['1'])+1), trafo_loadings['70']['2'], color=color3, linewidth=linewidth)
    # ax[2].plot(range(1, len(trafo_loadings['50'][2])+1), np.ones(len(trafo_loadings['50'][2])) * 100, color='red', linewidth=linewidth)
    ax[2].set_ylabel(r'$\mathbf{dRate\ 70}$' +'\n\nMVA', fontsize=8)


    # all axis adjustments
    for i in range(3):
        ax[i].tick_params(axis='both', labelsize=8)

        ax[i].set_xticks(np.arange(0, 289, 32))
        time_list_part = [time_list[i] for i in np.arange(0, 289, 32)]
        ax[i].set_xticklabels(time_list_part)
        ax[i].set_ylim(0, 250)
        ax[i].set_yticks(np.arange(0, 251, 50))
        ax[i].grid(True, axis='y')
        # ax[i].set_yticklabels(["0 MVA", "0.125 MVA", "0.250 MVA", "0.375 MVA", "0.500 MVA", "0.625 MVA"])


    fig.tight_layout()

    plt.subplots_adjust(bottom=0.14)
    ax[2].legend(
            ['Fix tariff', 'ToU tariff', 'RT tariff'],
            loc='upper center',
            fontsize=8,
            bbox_to_anchor=(0.5, -0.28),
            ncol=4,
            fancybox=True
        )


    """ Costs Plotting v2 """

    labels = ['Fix', 'ToU', 'RT']
    dRates = ["dRate 30", "dRate 50", "dRate 70"]
    dRates2 = ["dRate_30", "dRate_50", "dRate_70"]

    bbox = {}
    for i, dRate in enumerate(dRates2):

        costs[dRate].set_index(np.arange(0, len(costs[dRate])), inplace=True)

        colors = ['grey', color2, color3]
        boxprops = dict(facecolor=colors)

        ax.append(fig.add_subplot(gs[i, 1]))

        x = np.arange(len(labels))
        #vheights = np.random.rand(len(labels)) * 100

        bbox[i] = ax[i+3].boxplot(costs[dRate],
                            showfliers=False,
                            patch_artist=True,
                            # boxprops=boxprops,
                            medianprops=dict(color='black'),
                            labels=labels)

        ax[i+3].set_xticks(x+1)
        ax[i+3].set_xticklabels(labels, fontsize=8)
        ax[i+3].yaxis.grid(True)
        ax[i+3].tick_params(axis='both', labelsize=8)
        ax[i+3].set_ylim(-150, 50)
        ax[i+3].set_yticks(np.arange(-150, 51, 50))
        ax[i+3].set_ylabel('EUR', fontsize=8)

        # plot fliers
        ax[i+3].scatter([1, 1], [np.max(costs[dRate].iloc[:, 0]), np.min(costs[dRate].iloc[:, 0])], facecolor='black', marker='x', linewidths=0.25)
        ax[i+3].scatter([2, 2], [np.max(costs[dRate].iloc[:, 1]), np.min(costs[dRate].iloc[:, 1])], facecolor='black', marker='x', linewidths=0.25)
        ax[i+3].scatter([3, 3], [np.max(costs[dRate].iloc[:, 2]), np.min(costs[dRate].iloc[:, 2])], facecolor='black', marker='x', linewidths=0.25)

        colors = ['grey', color2, color3]
        for key in bbox.keys():
            bplot = bbox[key]
            for patch, color in zip(bplot['boxes'], colors):
                patch.set_facecolor(color)

    plt.yticks(fontsize=8)
    plt.xticks(fontsize=8)

    fig.tight_layout()
    plt.subplots_adjust(bottom=0.132)
    # plt.show()

    return fig


#%% FIGURE 8
def fig_8():

    dRates = ['dRate_30', 'dRate_50', 'dRate_70']
    # days = ['d01', 'd02', 'd03', 'd04', 'd05', 'd06', 'd07', 'd08', 'd09', 'd10', 'd11', 'd12', 'd13', 'd14', 'd15', 'd16']

    flex_dict = {}

    flex_dict["dRate_30"] = {"Level1": 0.0,
                            "Level2": 0.0,
                            "Level3": 0.0,
                            "Level4": 56.1,
                            "Level5": 25.5,
                            "Level6": 10.1,
                            "Level7": 30.2,
                            "Level8": 15.5,
                            "Level9": 5.6,
                            }
    flex_dict["dRate_50"] = {"Level1": 0.0,
                            "Level2": 0.0,
                            "Level3": 0.0,
                            "Level4": 452.9,
                            "Level5": 248.7,
                            "Level6": 178.8,
                            "Level7": 385.1,
                            "Level8": 180.9,
                            "Level9": 130.1,
                            }
    flex_dict["dRate_70"] = {"Level1": 19.8,
                            "Level2": 18.8,
                            "Level3": 0.3,
                            "Level4": 1079.3,
                            "Level5": 632.4,
                            "Level6": 460.7,
                            "Level7": 933.3,
                            "Level8": 515.5,
                            "Level9": 376.4,
                            }


    """ Start Plotting """

    labels = ['Fix', 'ToU', 'RT']

    x = np.arange(3) * 2  # the label locations
    width = 0.5  # the width of the bars

    cm = 1 / 2.54
    fig, ax = plt.subplots(3, 3, figsize=(22 * cm, 14 * cm))  # paper

    counter = 0
    for dRate in dRates:
        for i in [0,1,2]:
            ax[counter][i].yaxis.grid(True, zorder=0)

        # Basic 1 4 7
        bars = np.round([flex_dict[dRate]["Level1"], flex_dict[dRate]["Level2"], flex_dict[dRate]["Level3"]], 1)
        rects = ax[counter][0].bar(["basic", "variable", "smart"], bars, color=['lightblue', 'moccasin', 'lightgreen'], edgecolor='black', zorder=3)
        for rect in rects:
            height = rect.get_height()
            ax[counter][0].text(rect.get_x() + rect.get_width() / 2.,  height, f'{height}', ha='center', va='bottom', fontsize=10, zorder=3)

        # Variable 2 5 8
        bars = np.round([flex_dict[dRate]["Level4"], flex_dict[dRate]["Level5"], flex_dict[dRate]["Level6"]], 1)
        rects = ax[counter][1].bar(["basic", "variable", "smart"], bars, color=['lightblue', 'moccasin', 'lightgreen'], edgecolor='black', zorder=3)
        for rect in rects:
            height = rect.get_height()
            ax[counter][1].text(rect.get_x() + rect.get_width() / 2.,  height, f'{height}', ha='center', va='bottom', fontsize=10, zorder=3)

        # Smart 3 6 9 
        bars = np.round([flex_dict[dRate]["Level7"], flex_dict[dRate]["Level8"], flex_dict[dRate]["Level9"]], 1)
        rects = ax[counter][2].bar(["basic", "variable", "smart"], bars, color=['lightblue', 'moccasin', 'lightgreen'], edgecolor='black', zorder=3)
        for rect in rects:
            height = rect.get_height()
            ax[counter][2].text(rect.get_x() + rect.get_width() / 2.,  height, f'{height}', ha='center', va='bottom', fontsize=10, zorder=3)

        for i in [0, 1, 2]:
            ax[counter][i].set_yticks(np.arange(0, 1401, 200))
        # Remove y-axis labels from all subplots except the first column
        for i in [1, 2]:
            ax[counter][i].set_yticklabels([])  # Remove y-axis labels
            ax[counter][i].tick_params()
        counter += 1

    ax[0][0].set_title('$\mathbf{Fix\ tariff}$', fontsize=10)
    ax[0][1].set_title('$\mathbf{ToU\ tariff}$', fontsize=10)
    ax[0][2].set_title('$\mathbf{RT\ tariff}$', fontsize=10)

    ax[0][0].set_ylabel(r'$\mathbf{dRate\ 30}$' + '\n \nMWh', fontsize=10)
    ax[1][0].set_ylabel(r'$\mathbf{dRate\ 50}$' + '\n \nMWh', fontsize=10)
    ax[2][0].set_ylabel(r'$\mathbf{dRate\ 70}$' + '\n \nMWh', fontsize=10)

    plt.yticks(fontsize=10)
    plt.xticks(fontsize=10)

    fig.tight_layout()
    # plt.show()

    return fig


#%% FIGURE 9

def fig_9():
    
    conn = st.connection('gcs', type=FilesConnection)
    
    dRates = ['dRate_30', 'dRate_50', 'dRate_70']
    boxplot = {}
    for key in dRates:
        boxplot[key] = conn.read(f'vise-d/{key}_boxplot.csv', input_format="csv", ttl=100, header=[0, 1], index_col=[0])
    
    # first dimension = scenario with different penetrations
    # second dimension = Use Case

    dRates = ['dRate_30', 'dRate_50', 'dRate_70']
    Matrix = [[('level1','w/o'), ('level2','w'), ('level3','w')],
            [('level4','w'), ('level5','w'), ('level6','w')],
            [('level7',"w/o"), ('level8','w'), ('level9','w')]]

    cm = 1 / 2.54
    fig, ax = plt.subplots(nrows=3, ncols=2, figsize=(22*cm, 14*cm), sharey=True)

    flierprops = dict(linestyle='none', markeredgewidth=0.5)

    for dRate in [0,1,2]:

        boxprops = [{'facecolor': 'red'}, {'facecolor': 'orange'}, {'facecolor': 'green'}]

        # ToU
        bplot2 = ax[dRate][0].boxplot([boxplot[dRates[dRate]][('level4','w/o')],
                                    boxplot[dRates[dRate]][('level4','w')],
                                    boxplot[dRates[dRate]][('level5','w')],
                                    boxplot[dRates[dRate]][('level5','w')]],
                                    vert=True,  # vertical box alignment
                                    patch_artist=True,  # fill with color,
                                    showfliers=False,
                                    labels=['before', 'basic', 'variable', 'smart'],
                                    flierprops=flierprops,
                                    medianprops=dict(color='black')
                                    )  # will be used to label x-ticks
        ax[dRate][0].set_ylabel(r"$\bf{" +'dRate ' + dRates[dRate][-2:] +"}$\n \n EUR", fontsize=10)
        ax[dRate][0].scatter([1, 1], [np.max(boxplot[dRates[dRate]][('level4','w/o')]), np.min(boxplot[dRates[dRate]][('level4','w/o')])], facecolor='black', marker='x', linewidths=0.5)
        ax[dRate][0].scatter([2, 2], [np.max(boxplot[dRates[dRate]][('level4','w')]), np.min(boxplot[dRates[dRate]][('level4','w')])], facecolor='black', marker='x', linewidths=0.5)
        ax[dRate][0].scatter([3, 3], [np.max(boxplot[dRates[dRate]][('level5','w')]), np.min(boxplot[dRates[dRate]][('level5','w')])], facecolor='black', marker='x', linewidths=0.5)
        ax[dRate][0].scatter([4, 4], [np.max(boxplot[dRates[dRate]][('level5','w')]), np.min(boxplot[dRates[dRate]][('level5','w')])], facecolor='black', marker='x', linewidths=0.5)

        # RTT
        bplot3 = ax[dRate][1].boxplot([boxplot[dRates[dRate]][('level7',"w/o")],
                                    boxplot[dRates[dRate]][('level7',"w")],
                                    boxplot[dRates[dRate]][('level8','w')],
                                    boxplot[dRates[dRate]][('level9','w')]],
                                    vert=True,  # vertical box alignment
                                    patch_artist=True,  # fill with color,
                                    showfliers=False,
                                    labels=['before', 'basic', 'variable', 'smart'],
                                    flierprops=flierprops,
                                    medianprops=dict(color='black')
                                    )  # will be used to label x-ticks
        
        ax[dRate][1].scatter([1, 1], [np.max(boxplot[dRates[dRate]][('level7',"w/o")]), np.min(boxplot[dRates[dRate]][('level7',"w/o")])], facecolor='black', marker='x', linewidths=0.5)
        ax[dRate][1].scatter([2, 2], [np.max(boxplot[dRates[dRate]][('level7',"w")]), np.min(boxplot[dRates[dRate]][('level7',"w")])], facecolor='black', marker='x', linewidths=0.5)
        ax[dRate][1].scatter([3, 3], [np.max(boxplot[dRates[dRate]][('level8','w')]), np.min(boxplot[dRates[dRate]][('level8','w')])], facecolor='black', marker='x', linewidths=0.5)
        ax[dRate][1].scatter([4, 4], [np.max(boxplot[dRates[dRate]][('level9','w')]), np.min(boxplot[dRates[dRate]][('level9','w')])], facecolor='black', marker='x', linewidths=0.5)
        
        colors = ['grey', 'lightblue', 'moccasin','lightgreen']
        for bplot in (bplot2, bplot3):
            for patch, color in zip(bplot['boxes'], colors):
                patch.set_facecolor(color)

        # adding horizontal grid lines
        for j in [0, 1]:
            for i in [0, 1, 2]:
                ax[i][j].yaxis.grid(True)
                ax[i][j].set_ylim((-150, 30))
                ax[i][j].tick_params(axis='both', which='major', labelsize=10)
    
    ax[0][0].set_title(r"$\bf{" + "ToU" + "}$" + " " + r"$\bf{" + "tariff" + "}$", fontsize=10)
    ax[0][1].set_title(r"$\bf{" + "RT" + "}$" + " " + r"$\bf{" + "tariff" + "}$", fontsize=10)

    patches_dict = {"before": Patch(color=colors[0], label="Before curtailment"),
                    "basic": Patch(color=colors[1], label="Basic curtailment"),
                    "variable": Patch(color=colors[2], label="Variable curtailment"),
                    "smart": Patch(color=colors[3], label="Smart curtailment")}

    patches = []
    for pat in patches_dict:
        patches.append(patches_dict[pat])
    #lgd  = fig.legend(handles=patches, loc='lower center', ncol=6, bbox_to_anchor = [0.55, -0.05])

    
    fig.tight_layout()
    # plt.show()
        
    return fig

#%%
if __name__ == '__main__':
    figure_5 = fig_5()
    figure_5.show()
    figure_7 = fig_7()
    figure_7.show()
    figure_8 = fig_8()
    figure_8.show()
    figure_9 = fig_9()
    figure_9.show()
# %%
