"""协议第 29 轮：把 17 张图画出来（墙、空地、窄格=门/走廊、各房间编号），看清结构。用法：python show_maps.py 输出目录"""
import sys, json
from pathlib import Path
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'p27'))
import ipfix_account as A
out = Path(sys.argv[1]); out.mkdir(exist_ok=True)
insts = sorted(A.CFG)
fig, axes = plt.subplots(3, 6, figsize=(18, 9.5))
for ax, inst in zip(axes.flat, insts):
    h, w, free = A.load_map(inst); dlab, nd, rlab, apron, F = A.doors_rooms(h, w, free)
    img = np.zeros((h, w, 3))
    for r in range(h):
        for c in range(w):
            if not free[r][c]: img[r, c] = (0.15, 0.15, 0.15)
            elif (r, c) in dlab: img[r, c] = (0.85, 0.1, 0.1)
            elif (r, c) in apron: img[r, c] = (0.95, 0.75, 0.6)
            else: img[r, c] = (1, 1, 1)
    ax.imshow(img, interpolation='nearest'); ax.set_title(f'{inst}  {h}x{w}', fontsize=9); ax.axis('off')
for ax in list(axes.flat)[len(insts):]: ax.axis('off')
plt.tight_layout(); plt.savefig(out / 'all_maps.png', dpi=110)
