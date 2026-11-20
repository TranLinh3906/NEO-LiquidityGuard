# Financial Formula Assumptions

LiquidityGuard measures only the three visible bid and ask levels in a stored snapshot. `bid1` is the best displayed bid and `ask1` is the best displayed ask. BUY simulation consumes ask1→ask3; SELL simulation consumes bid1→bid3. Fees, tax, queue position, hidden liquidity, future amendments, and level four onward are excluded.

The fixture examples treat price as VND/CP and quantity as shares solely to test arithmetic. LIVE output is gated until SSI price and quantity units are verified. The system rejects incomplete/partial snapshots, stale quotes, phases outside `LO`, ATO/ATC, missing or non-positive prices, invalid volume, crossed books, and unverified units.

`spread = ask1 - bid1`; `mid = (ask1 + bid1)/2`; relative spread is `spread/mid`; OBI is `(bid_depth_3 - ask_depth_3)/(bid_depth_3 + ask_depth_3)`. VWAP and slippage are computed only on filled quantity. A partial fill never assumes a fourth price level.
