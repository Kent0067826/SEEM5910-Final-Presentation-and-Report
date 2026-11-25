"""Split the door-rule figure (fig_door_rule_deck.png) into two slide figures at its blank column (x = 1216-1225):
fig_door_rule_A.png  (panel A: buffer geometry and switching rule, with its notes)
fig_door_rule_BC.png (panel B: buffer-size sweep; panel C: time budget of one crossing).
The footer lines (rows 956-1026) run across the cut, so both crops stop at row 945; slide 13 restates the rule as text.
Run from the repo root after make_principle_figs.py:  python3 figures/deck/make_crops.py"""
from PIL import Image

src = Image.open("figures/deck/fig_door_rule_deck.png")
w, h = src.size
src.crop((0, 0, 1220, 945)).save("figures/deck/fig_door_rule_A.png")
src.crop((1222, 0, w, 945)).save("figures/deck/fig_door_rule_BC.png")
print("A", (1220, 945), "BC", (w - 1222, 945))
# v34: panel B alone (buffer-size sweep, main talk) and panel C alone (time budget of one crossing, backup slide);
# the blank band between them is rows 474-626 of fig_door_rule_BC.png
bc = Image.open("figures/deck/fig_door_rule_BC.png")
bc.crop((0, 60, bc.size[0], 476)).save("figures/deck/fig_door_rule_B.png")
bc.crop((0, 622, bc.size[0], bc.size[1])).save("figures/deck/fig_door_rule_C.png")
print("B", Image.open("figures/deck/fig_door_rule_B.png").size, "C", Image.open("figures/deck/fig_door_rule_C.png").size)
