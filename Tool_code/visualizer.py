# -*- coding: utf-8 -*-
"""
NOT FINISHED- EXAMPLE VISS
Created on Wed Jul 24 11:58:00 2019

@author: galozs
"""

import matplotlib.pyplot as plt
from ucscParser import exons2abs
import matplotlib.patches as mpatches
from matplotlib.collections import PatchCollection

# [tx, cds, exon1, exon2,...,exon_n]
tr = [[(22, 630), (41, 400), (35,79), (105, 234), (350, 422), (460, 489)], 
       [(22, 630), (41, 200), (35,79), (105, 234), (350, 422)],
       [(31, 710), (71, 586), (35,79), (105, 234), (350, 422), (460, 601)]]
dom = [[(20, 55), (190, 210)],
        [(20,55)],
        [(120, 210)]]
shapes = ['Rectangle', 'Circle', 'Wedge', 'Polygon', 'FancyBboxPatch']


fig, ax = plt.subplots(1, 2, figsize=(12, 8))
plt.subplots_adjust(wspace=0.05)
l = len(tr)
ax[0].set_ylim(0, l*5 + 3)
ax[1].set_ylim(0, l*5 + 3)

max_tx = max([t[0][1] for t in tr])
min_tx = min([t[0][0] for t in tr])
ax[0].set_xlim(min_tx - 20, max_tx + 20)
set_stop = 0
t_num = 1
for t in tr:
    y_pos = t_num*5
    ax[0].plot((t[0][0], t[0][1]), (y_pos, y_pos), c='k', zorder=1)
    
    starts = [ex[0] for ex in t[2:]]
    ends = [ex[1] for ex in t[2:]]
    abs_start, abs_stop = exons2abs(starts, ends, t[1], '+')
    abs_start = [pos for pos in abs_start if pos != 0]
    abs_stop = [pos for pos in abs_stop if pos != 0]
    if abs_stop[-1] > set_stop:
        set_stop = abs_stop[-1]
        ax[1].set_xlim(-20, abs_stop[-1] + 20)
    exn = 0
    for ex in t[2:]:
        if ex[1] < t[1][0] or ex[0] > t[1][1]: # entire exon outside of CDS
            ax[0].broken_barh([(ex[0], ex[1] - ex[0] + 1)], (y_pos - 0.25, 0.5), facecolors='C'+ str(exn), zorder=2)
        elif ex[0] < t[1][0] and ex[1] > t[1][0]:
            ax[0].broken_barh([(ex[0], t[1][0] - ex[0])], (y_pos - 0.25, 0.5), facecolors='C'+ str(exn), zorder=2)
            ax[0].broken_barh([(t[1][0], ex[1] - t[1][0] + 1)], (y_pos - 0.5, 1), facecolors='C'+ str(exn), zorder=2)
        elif ex[1] > t[1][1] and ex[0] < t[1][1]:
            ax[0].broken_barh([(ex[0], t[1][1] - ex[0] + 1)], (y_pos - 0.5, 1), facecolors='C'+ str(exn), zorder=2)
            ax[0].broken_barh([(t[1][1] + 1, ex[1] - t[1][1])], (y_pos - 0.25, 0.5), facecolors='C'+ str(exn), zorder=2)
        else:
            ax[0].broken_barh([(ex[0], ex[1] - ex[0] + 1)], (y_pos - 0.5, 1), facecolors='C'+ str(exn), zorder=2)
        if exn < len(abs_start):
            ax[1].broken_barh([(abs_start[exn], abs_stop[exn] - abs_start[exn] + 1)], (y_pos - 0.5, 1), facecolors='C'+ str(exn), zorder=2)
        exn += 1
    
    for do in dom[t_num -1]:
        #ax[1].broken_barh([(do[0], do[1] - do[exn] + 1)], (y_pos - 0.5, 1), facecolors='C'+ str(exn))
        # add a fancy box
        fancybox = mpatches.FancyBboxPatch((do[0], y_pos - 2.5) , do[1] - do[0] + 1, 1,
                                           boxstyle=mpatches.BoxStyle("Round", pad=0.1),fc=(1., .8, 1.),
                                           ec=(1., 0.5, 1.), zorder=2)
        ax[1].add_patch(fancybox)
    t_num += 1

ax[0].grid(True, axis='x')
ax[1].grid(True, axis='x')
ax[0].set_axisbelow(True)
ax[1].set_axisbelow(True)

ytic = [i*5 for i in range(1,l +1)]
ax[0].set_yticks(ytic)
ax[1].set_yticks(ytic)
ax[0].set_yticklabels(['Trancript1', 'Trancript2','Trancript3'])
ax[1].set_yticklabels(['','',''])
ax[0].set_xticks(range(min_tx, max_tx, int((max_tx - min_tx) / 10)))
ax[1].set_xticks(range(0, set_stop +20, int((set_stop + 20)/10)))
ax[0].set_xticklabels(range(min_tx, max_tx, int((max_tx - min_tx) / 10)), rotation = 45)
ax[1].set_xticklabels(range(0, set_stop +20, int((set_stop + 20)/10)), rotation = 45)

plt.show()






