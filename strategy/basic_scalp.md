# if abs(position) > max_position:
close all position


# No Orders , No Position
place two order: 
BUY qty @ price - (fee_bps + bps*3) 
SELL qty @ price + (fee_bps + bps*3)

# One order 
if BUY order filled, place SELL order at price + (fee_bps + 10*3)
if SELL order filled, place BUY order at price - (fee_bps + 10*3) 



