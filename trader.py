from typing import Dict, List
from datamodel import Order, OrderDepth, TradingState
import collections
import copy

empty_dict = {'KELP': 0, 'RAINFOREST_RESIN': 0, 'SQUID_INK': 0}


class Trader:
    window = 4
    kelp_historical_price = collections.deque()
    squid_historical_price = collections.deque()
    position = copy.deepcopy(empty_dict)

    POSITION_LIMIT = {"KELP": 50, "RAINFOREST_RESIN": 50, "SQUID_INK": 50}

    def compute_orders(self, product, order_depth, acc_bid, acc_ask, LIMIT):
        orders: list[Order] = []

        osell = collections.OrderedDict(sorted(order_depth.sell_orders.items()))
        obuy = collections.OrderedDict(sorted(order_depth.buy_orders.items(), reverse=True))

        sell_vol, best_sell_pr = self.values_extract(osell)
        buy_vol, best_buy_pr = self.values_extract(obuy, 1)

        cpos = self.position[product]

        for ask, vol in osell.items():
            if ((ask <= acc_bid) or ((self.position[product] < 0) and (ask == acc_bid + 1))) and cpos < LIMIT:
                order_for = min(-vol, LIMIT - cpos)
                cpos += order_for
                assert (order_for >= 0)
                orders.append(Order(product, ask, order_for))

        undercut_buy = best_buy_pr + 1
        undercut_sell = best_sell_pr - 1

        bid_pr = min(undercut_buy, acc_bid)
        sell_pr = max(undercut_sell, acc_ask)

        if cpos < LIMIT:
            num = LIMIT - cpos
            orders.append(Order(product, bid_pr, num))
            cpos += num

        cpos = self.position[product]

        for bid, vol in obuy.items():
            if ((bid >= acc_ask) or ((self.position[product] > 0) and (bid + 1 == acc_ask))) and cpos > -LIMIT:
                order_for = max(-vol, -LIMIT - cpos)
                cpos += order_for
                assert (order_for <= 0)
                orders.append(Order(product, bid, order_for))

        if cpos > -LIMIT:
            num = -LIMIT - cpos
            orders.append(Order(product, sell_pr, num))
            cpos += num

        return orders

    def calc_next_price_kelp(self):
        coef = [0.20581442, 0.20492715, 0.2609162, 0.32744102]
        intercept = 1.826096406050283
        nxt_price = intercept
        for i, val in enumerate(self.kelp_historical_price):
            nxt_price += val * coef[i]

        return int(round(nxt_price))

    def run(self, state: TradingState):
        result: Dict[str, List[Order]] = {}

        for key, val in state.position.items():
            self.position[key] = val

        POSITION_LIMIT = 50
        FAIR_PRICE = 10000

        for product in state.order_depths:
            order_depth = state.order_depths[product]
            orders: List[Order] = []

            if product == "RAINFOREST_RESIN":
                orders = self.compute_orders(product, order_depth, FAIR_PRICE - 2, FAIR_PRICE + 2, self.POSITION_LIMIT[product])
                result[product] = orders

            if product == "KELP":
                if len(self.kelp_historical_price) == self.window:
                    self.kelp_historical_price.popleft()

                _, bs_kelp = self.values_extract(collections.OrderedDict(sorted(order_depth.sell_orders.items())))
                _, bb_kelp = self.values_extract(collections.OrderedDict(sorted(order_depth.buy_orders.items(), reverse=True)), 1)

                self.kelp_historical_price.append((bs_kelp + bb_kelp) / 2)

                kelp_lb = -1e9
                kelp_ub = 1e9

                if len(self.kelp_historical_price) == self.window:
                    kelp_lb = self.calc_next_price_kelp() - 1
                    kelp_ub = self.calc_next_price_kelp() + 1

                orders = self.compute_orders(product, order_depth, kelp_lb, kelp_ub, self.POSITION_LIMIT[product])
                result[product] = orders

            if product == "SQUID_INK":
                orders = self.handle_squid(product, state, {})
                result[product] = orders

        traderData = "SAMPLE"
        conversions = None
        return result, conversions, traderData

    def handle_squid(self, product: str, state: TradingState, memory: dict) -> List[Order]:
        orders = []
        order_depth = state.order_depths[product]
        position = state.position.get(product, 0)

        best_bid = max(order_depth.buy_orders, default=None)
        best_ask = min(order_depth.sell_orders, default=None)

        if best_bid is None or best_ask is None:
            return []

        spread = best_ask - best_bid

        if spread >= 2:
            bid_price = best_bid + 1
            ask_price = best_ask - 1
            bid_volume = self.cap_volume(10, position, product)
            ask_volume = self.cap_volume(10, -position, product)

            if bid_volume > 0:
                orders.append(Order(product, bid_price, bid_volume))
            if ask_volume > 0:
                orders.append(Order(product, ask_price, -ask_volume))

        return orders

    def cap_volume(self, intended_volume: int, current_position: int, product: str) -> int:
        max_allowed = self.POSITION_LIMIT[product] - current_position if intended_volume > 0 else self.POSITION_LIMIT[product] + current_position
        return max(0, min(abs(intended_volume), abs(max_allowed))) * (1 if intended_volume > 0 else -1)

    def values_extract(self, order_dict, buy=0):
        tot_vol = 0
        best_val = -1
        mxvol = -1

        for ask, vol in order_dict.items():
            if (buy == 0):
                vol *= -1
            tot_vol += vol
            if tot_vol > mxvol:
                mxvol = vol
                best_val = ask

        return tot_vol, best_val
