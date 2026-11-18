import sys, json; sys.path.insert(0,'/home/claude/proj/v10/scripts'); import r10
P='/home/claude/proj/v10/pkg/maps/'; E='/home/claude/proj/v10/maps_ext/'; N='/home/claude/proj/v10/maps_new/'; B='/home/claude/proj/v10/bin/lifelong-v14'
F11=json.load(open('/home/claude/proj/v10/test_freeze_v11b.json'))['methods']; F12=json.load(open('/home/claude/proj/v10/test_freeze_v12.json'))['methods']
INST={'maze40':(P+'maze/maze40.json',40),'warehouse100':(P+'warehouse/warehouse100.json',100),'room200':(P+'room/room200.json',200),
      'room250':(P+'room/room250.json',250),'random200':(P+'random/random200.json',200),'random300':(P+'random/random300.json',300),
      'room300':(E+'room/room300.json',300),'maze60':(E+'maze/maze60.json',60)}
S=json.load(open(N+'instances.json'))
for name,(free,d) in S.items():
    for k,n in d.items(): INST[k]=(N+k+'.json',n)
PRICE={k:v for k,v in F11['C_auto_cheap'].items() if k.startswith('ROBOT_TASK') or k.startswith('ROBOT_WAIT') or k in ('ROBOT_ROUTE_CACHE','ROBOT_OCC_KAPPA','ROBOT_TIE_RULE','ROBOT_ALIGN_BLOCK','ROBOT_ALIGN_SLACK','ROBOT_COMBINE','ROBOT_PRICE_SWITCH','ROBOT_PRICE_LEGS')}
E_=F12['E_credit']
def turn(k,g=None):
    e={'ROBOT_TURN_PEN':str(k)}
    if g is not None: e['ROBOT_TURN_GATE']=str(g)
    return e
