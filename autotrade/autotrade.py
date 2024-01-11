from common import get_object_from_list, get_percentage_value, get_formatted_price, write_log
from util import get_stocks_info, create_order_single, get_available_balance


# def start_strategy(props, fyers, strategy):
    #if props.auto_trade_enabled:



    # write_log("\n")
    # strategy_obj = props["first_candle_same_trend_strategy"]
    # stocks_details = get_stocks_info(props, fyers, strategy["symbols"])
    # for symbolObj in stocks_details:
    #     stop_loss = 0
    #     limit_price = 0
    #     profit_booking = 0
    #     # qty = 1
    #     qty = strategy_obj["quantity"]
    #     order_type = 0
    #     side = 0
    #
    #     ltp = symbolObj["v"]["lp"]
    #     obj = get_object_from_list(strategy_obj["symbols"], "symbol", symbolObj["v"]["original_name"])
    #     side_text = obj["side"]
    #     sl_value = get_percentage_value(strategy_obj["stop_loss_percentage"], ltp)
    #     limit_value = get_percentage_value(strategy_obj["limit_percentage"], ltp)
    #
    #     if side_text == "BUY":
    #         side = 1
    #         limit_price = ltp - limit_value
    #         stop_loss = limit_price - sl_value
    #     elif side_text == "SELL":
    #         side = -1
    #         limit_price = ltp + limit_value
    #         stop_loss = limit_price + sl_value
    #
    #     limit_price = get_formatted_price(limit_price)
    #     stop_loss = get_formatted_price(stop_loss)
    #     order_type = strategy_obj["order_type"]
    #
    #     if order_type == "2":  # setting the limit_price=0,if market order
    #         limit_price = 0
    #
    #     balance = get_available_balance(props, fyers, "Available Balance")
    #     available_balance = balance - get_percentage_value(strategy_obj["reserved_balance_percentage"], balance)
    #     # qty = int(available_balance / ltp)
    #     print("qty : ", qty)
    #
    #     create_order_single(props, fyers, symbolObj["n"], qty, order_type, side, limit_price, 0, stop_loss, 0, strategy)
