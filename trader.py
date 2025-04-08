from typing import Dict, List
from datamodel import OrderDepth, TradingState, Order
import numpy


class Trader:

    def run(self, state: TradingState) -> tuple[Dict[str, List[Order]], int, str]:
        """
        Main algorithm method. Returns:
        - result: dict of product → list of Order objects
        - conversions: integer (conversion quantity if applicable)
        - traderData: persistent state string
        """
        result = {}

        for product in state.order_depths:
            order_depth = state.order_depths[product]
            orders: List[Order] = []

            # TEMP: Dummy fair value
            acceptable_price = 10

            # Buying logic
            if len(order_depth.sell_orders) > 0:
                best_ask = min(order_depth.sell_orders.keys())
                best_ask_volume = order_depth.sell_orders[best_ask]
                if best_ask < acceptable_price:
                    orders.append(Order(product, best_ask, -best_ask_volume))

            # Selling logic
            if len(order_depth.buy_orders) > 0:
                best_bid = max(order_depth.buy_orders.keys())
                best_bid_volume = order_depth.buy_orders[best_bid]
                if best_bid > acceptable_price:
                    orders.append(Order(product, best_bid, -best_bid_volume))

            result[product] = orders

        # No conversion logic yet, and static traderData
        return result, 0, "SAMPLE"
