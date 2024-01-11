import datetime

from colorama import init
from fyers_api import fyersModel
from fyers_api.Websocket import ws

from util import *

props = {}
LTP_DICT = {}
ACTIVE_POSITIONS = []
TRADE_BOOK = []
ORDER_BOOK = []
EXTERNAL_PENDING_TRADES = []
LOCK = False
trade_gap_counter = 0

counter = 0
fs = ""
props = load_properties()
# print("props : ", props)

# Initialize colorama
init(autoreset=True)

access_token = get_access_token(props)
fyers = fyersModel.FyersModel(client_id=props["app_id"], token=access_token, log_path="")

SYMBOL_FOR_LTP_MAP = props["SYMBOL_FOR_LTP_MAP"]

write_log(json.dumps(fyers.tradebook()))
write_log(json.dumps(fyers.orderbook()))


def subscribe_to_symbol(symbol):
    global fs
    if fs != "":
        data_type = "symbolData"
        # symbol = ["NSE:NIFTYBANK-INDEX"]
        log_message("Adding symbol: " + str(symbol), 'INFO')
        fs.subscribe(symbol=symbol, data_type=data_type)


def test_web_socekt():
    global counter
    threading.Timer(5, test_web_socekt).start()
    counter = counter + 1
    if counter != 1:
        new_symbol_thread = threading.Thread(target=subscribe_to_symbol)
        new_symbol_thread.start()


# test_web_socekt()


def load_property_from_file():
    global props
    props = load_properties()
    threading.Timer(props["json_reload_interval"], load_property_from_file).start()


def load_pending_trades_from_file(is_repeat):
    global props
    global EXTERNAL_PENDING_TRADES
    if is_repeat:
        threading.Timer(props["file_trades_reload_interval"], lambda: load_pending_trades_from_file(True)).start()

    EXTERNAL_PENDING_TRADES = filter_pending_status_rows()
    if len(EXTERNAL_PENDING_TRADES) > 0:
        print("Pending Trades :")
        print_in_table(EXTERNAL_PENDING_TRADES)


def check_for_the_trade_to_trigger():
    global props
    global EXTERNAL_PENDING_TRADES
    global LTP_DICT
    global LOCK
    global trade_gap_counter
    threading.Timer(props["ltp_match_interval"], check_for_the_trade_to_trigger).start()
    trade_gap_counter -= 1

    if LOCK is False and trade_gap_counter <= 0:
        LOCK = True
        for ext_trade in EXTERNAL_PENDING_TRADES:
            if ext_trade["operator"] == ">=":
                if ext_trade["symbol"] in LTP_DICT and LTP_DICT[ext_trade["symbol"]] >= float(ext_trade["price"]):
                    trade_gap_counter = props["next_trade_gap"]
                    update_status_by_id(ext_trade["id"], "Inprogress")
                    start_trade(ext_trade)

            if ext_trade["operator"] == "<=":
                if ext_trade["symbol"] in LTP_DICT and LTP_DICT[ext_trade["symbol"]] <= float(ext_trade["price"]):
                    trade_gap_counter = props["next_trade_gap"]
                    update_status_by_id(ext_trade["id"], "Inprogress")
                    start_trade(ext_trade)
        LOCK = False


def start_trade(trade):
    global props
    global LOCK
    strike = calculate_strike(props, trade, LTP_DICT)
    response = create_order_single(props, fyers, strike, trade["qty"], 2, 1, 0,
                                   0, 0, 0, {"retry_count_create_order": 1})

    if response["s"] == "ok":
        log_message("Order Placed :  " + trade["symbol"], 'INFO')
        if props["enable_sound"]:
            alertUser(ORDER_PLACED_SUCCESS)
    else:
        log_message("Order Failed :  " + trade["symbol"], 'ERROR')
        if props["enable_sound"]:
            alertUser(ORDER_PLACED_FAILURE)

    load_pending_trades_from_file(False)


load_pending_trades_from_file(True)
load_property_from_file()
check_for_the_trade_to_trigger()


def getSymbolsFromOrderList():
    global SYMBOL_FOR_LTP_MAP
    orders = fyers.orderbook()["orderBook"]

    DYNAMIC_SYMBOLS = []
    for order in orders:
        DYNAMIC_SYMBOLS.append(order["symbol"])

    SYMBOL_FOR_LTP_MAP_UNIQUE = list(set(DYNAMIC_SYMBOLS))
    SYMBOL_FOR_LTP_MAP = SYMBOL_FOR_LTP_MAP + SYMBOL_FOR_LTP_MAP_UNIQUE


getSymbolsFromOrderList()


def getObjFromArray(list, key, value):
    for obj in list:
        if obj[key] == value:
            return obj

    return ""


def getChangePercentage(openingLTP, closingLTP):
    diff = closingLTP - openingLTP
    changePercentage = (diff / openingLTP) * 100
    return changePercentage


def getValueByPercentage(openingLTP, percentage):
    result = (openingLTP / 100) * percentage
    return result


def round_to_nearest_0_05(decimal_value):
    return round(decimal_value * 20) / 20


def manage_Active_Position():
    global ACTIVE_POSITIONS
    # print("LTP_DICT", LTP_DICT)
    threading.Timer(props["active_position_check_interval"], manage_Active_Position).start()
    print("TIME : ", datetime.now().strftime("%H:%M:%S"), " LTP Data : ", LTP_DICT)
    if len(ACTIVE_POSITIONS) > 0:
        # print(" Active Positions Found")
        for position in ACTIVE_POSITIONS:
            chasing_values = props["chasing_values"]
            initial_sl = chasing_values[0]
            initial_displacement = chasing_values[1]
            initial_target = chasing_values[2]
            second_displacement = chasing_values[3]
            if "last_updated_high" in position and position["last_updated_high"] < position["high"]:
                position["last_updated_high"] = position["high"]
                # chasing strategy= 10/15/30/50/100
                change_percentage = getChangePercentage(position["tradedPrice"], position["high"])
                print("Change % : ", change_percentage)

                if change_percentage >= initial_target:
                    print("case 1")
                    current_profit = position["high"] - position["tradedPrice"]
                    stop_price = position["tradedPrice"] + (getValueByPercentage(current_profit, second_displacement))
                elif change_percentage >= initial_displacement - initial_sl:
                    print("case 2")
                    stop_price = position["high"] - getValueByPercentage(position["tradedPrice"], initial_displacement)
                else:
                    print("case 3")
                    stop_price = position["tradedPrice"] - getValueByPercentage(position["tradedPrice"], initial_sl);

                stop_price = round_to_nearest_0_05(stop_price)
                limit_price = round_to_nearest_0_05(stop_price - 0.05)
                if stop_price > position["stop_price"]:
                    modify_order(props, fyers, position["stop_limit_order_id"], limit_price, stop_price,
                                 position["netQty"],
                                 4)
                    position["stop_price"] = stop_price

                    if props["enable_sound"]:
                        alertUser(SL_UPDATED_SUCCESS)
            # else:
            #     print("No PRICE CHANGE")


def get_traded_price(symbol):
    all_trades = fyers.tradebook()["tradeBook"]
    # filter with symbols
    trades_for_the_symbol = []
    for trade in all_trades:
        # print("Trade : ", trade)
        if trade["symbol"] == symbol and trade["tradePrice"] != 0:
            trades_for_the_symbol.append(trade)

    # print("Symbol_Trades : ", trades_for_the_symbol)
    last_trade = {}
    if len(trades_for_the_symbol) >= 1:
        last_trade = trades_for_the_symbol[0]
    for trade in trades_for_the_symbol:
        datetime_format = "%d-%b-%Y %H:%M:%S"

        datetime1 = datetime.strptime(last_trade["orderDateTime"], datetime_format)
        datetime2 = datetime.strptime(trade["orderDateTime"], datetime_format)

        if datetime1 < datetime2:
            last_trade = trade

    if last_trade:
        return last_trade["tradePrice"]
    else:
        return 0


def check_for_new_active_positions():
    global props
    global ACTIVE_POSITIONS
    threading.Timer(props["new_position_time_interval"], check_for_new_active_positions).start()

    # print(ACTIVE_POSITIONS)

    all_positions = fyers.positions()["netPositions"]
    for position in all_positions:
        if position["netAvg"] != 0 and position["netQty"] != 0:
            if getObjFromArray(ACTIVE_POSITIONS, "symbol", position["symbol"]) == "":
                ACTIVE_POSITIONS.append(position)

                # print("New Position Found : ", position["symbol"])
                log_message("New Position Found : " + position["symbol"], 'INFO')
                # playsound(POSITION_FOUND_SUCCESS)
                position["tradedPrice"] = get_traded_price(position["symbol"])
                chasing_values = props["chasing_values"]
                initial_sl = chasing_values[0]
                stop_price = round_to_nearest_0_05(
                    position["tradedPrice"] - getValueByPercentage(position["tradedPrice"], initial_sl))
                limit_price = round_to_nearest_0_05(stop_price - 0.05)
                log_message("limitPrice : " + str(position["symbol"]), 'INFO')
                log_message("stop_price  : " + str(position["symbol"]), 'INFO')
                # print("limitPrice :", limit_price)
                # print("stop_price :", stop_price)

                response = create_order_single(props, fyers, position["symbol"], position["netQty"], 4, -1, limit_price,
                                               stop_price,
                                               0, 0,
                                               {"retry_count_create_order": 1})

                if response["s"] == "ok":
                    position["stop_limit_order_id"] = response["id"]
                    position["last_updated_high"] = position["tradedPrice"]
                    position["high"] = position["tradedPrice"]
                    position["stop_price"] = stop_price
                    if props["enable_sound"]:
                        alertUser(SL_UPDATED_SUCCESS)
                subscribe_to_symbol([position["symbol"]])
            # else:
            #     print("Already Position Found : ", position["symbol"])
        elif position["netAvg"] == 0 and position["netQty"] == 0:
            if getObjFromArray(ACTIVE_POSITIONS, "symbol", position["symbol"]) != "":
                del_index = 0
                for position_del in ACTIVE_POSITIONS:
                    if position_del["symbol"] == position["symbol"]:
                        ACTIVE_POSITIONS.pop(del_index)
                        # print("Position Deleted : ", position["symbol"])
                        log_message("Position Deleted :  " + position["symbol"], 'INFO')
                        if props["enable_sound"]:
                            alertUser(POSITION_DELETED_SUCCESS)
                    del_index = del_index + 1


check_for_new_active_positions()
manage_Active_Position()
pending_sttaus = filter_pending_status_rows()
print(pending_sttaus)
# update_status_by_id(1, "Deleted")

######################## Web Socket #########################

ws_access_token = f"{props['app_id']}:{access_token}"
run_background = False


def update_high_value_for_symbol():
    global ACTIVE_POSITIONS
    global LTP_DICT
    for position in ACTIVE_POSITIONS:
        if 'high' in position:
            if LTP_DICT[position["symbol"]] > position["high"]:
                position["high"] = LTP_DICT[position["symbol"]]
        else:
            position["high"] = LTP_DICT[position["symbol"]]

        # print(ACTIVE_POSITIONS)


def custom_message(response):
    # print("response Map", response)
    LTP_DICT.update({response[0]["symbol"]: response[0]["ltp"]})
    if props["show_logs"]:
        print("LTP Map", LTP_DICT)
    update_high_value_for_symbol()


def run_process_background_symbol_data(access_token):
    global fs
    data_type = "symbolData"
    symbol = SYMBOL_FOR_LTP_MAP
    #symbol=['NSE:NIFTY241112150CE']
    # print("Symbols : ", SYMBOL_FOR_LTP_MAP)
    log_message("Symbols :  " + str(SYMBOL_FOR_LTP_MAP), 'INFO')
    fs = ws.FyersSocket(access_token=access_token, run_background=False, log_path="/logs")
    fs.websocket_data = custom_message
    fs.subscribe(symbol=symbol, data_type=data_type)
    fs.keep_running()


run_process_background_symbol_data(ws_access_token)
