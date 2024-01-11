import threading
from encodings import undefined

from fyers_api import fyersModel
from fyers_api.Websocket import ws
# import ws from fyers_api.websocket
from autotrade.afterPosition import handleAfterPosition
from strategy_10_min.strategy import start_strategy
from util import *

props = {}
LTP_DICT = {}
ACTIVE_POSITIONS = []
ACTIVE_TRADES_IN_DB = []
PENDING_TRADES_IN_DB = []
TRADE_BOOK = []
ORDER_BOOK = []

props = load_properties()
# print("props : ", props)

is_busy = False

access_token = get_access_token(props)
fyers = fyersModel.FyersModel(client_id=props["app_id"], token=access_token, log_path="")

SYMBOL_FOR_LTP_MAP = props["SYMBOL_FOR_LTP_MAP"]


# print("Positions : ", fyers.positions())
# print("Trade Book : ", fyers.tradebook())
# print("All orders : ", fyers.orderbook())


# get_trades("pending")
# print("ACTIVE_TRADES_IN_DB : ", ACTIVE_TRADES_IN_DB)


# update_trade_status(2, 1)


def load_property_from_file():
    global props
    props = load_properties()
    threading.Timer(props["json_reload_interval"], load_property_from_file).start()


def check_for_active_positions():
    global props
    all_positions = fyers.positions()

    threading.Timer(props["json_reload_interval"], check_for_active_positions).start()


def load_trades_from_db():
    global ACTIVE_TRADES_IN_DB
    global PENDING_TRADES_IN_DB
    ACTIVE_TRADES_IN_DB = get_trades("trading", props, LTP_DICT)
    PENDING_TRADES_IN_DB = get_trades("pending", props, LTP_DICT)
    threading.Timer(props["db_trade_reload_interval"], load_trades_from_db).start()


def sync_positions():
    global props
    global ACTIVE_POSITIONS
    global TRADE_BOOK
    global ORDER_BOOK
    threading.Timer(props["position_reload_interval"], sync_positions).start()

    ACTIVE_POSITIONS = get_current_active_positions(fyers.positions()["netPositions"])
    # print("Active Positions : ", ACTIVE_POSITIONS)
    TRADE_BOOK = fyers.tradebook()["tradeBook"]
    # print("TRADE_BOOK : ", TRADE_BOOK)
    ORDER_BOOK = fyers.orderbook()["orderBook"]
    # print("ORDER_BOOK : ", ORDER_BOOK)


def check_for_time_event():
    threading.Timer(1.0, check_for_time_event).start()
    now = datetime.now()
    current_time = now.strftime("%H:%M:%S")
    # print("Current Time =", current_time)
    if props["first_candle_same_trend_strategy"]["time"] == current_time:
        strategy = props["first_candle_same_trend_strategy"]
        if strategy != undefined and strategy["not_traded"] == True and len(strategy["symbols"]) > 0:
            # print("Trade about to start")
            start_strategy(props, fyers, strategy)

    # if props["blind_trading_at_9_15"]["time"] == current_time:
    #     strategy = props["first_candle_same_trend_strategy"]
    #     if strategy != undefined and strategy["not_traded"] == True and len(strategy["symbols"]) > 0:
    #         # print("Trade about to start")
    #         start_strategy(props, fyers, strategy)


# check_for_time_event()
load_property_from_file()


# load_trades_from_db()
# sync_positions()


def manage_trades():
    global ACTIVE_POSITIONS
    global TRADE_BOOK
    global ACTIVE_TRADES_IN_DB
    global LTP_DICT
    global ORDER_BOOK
    global is_busy

    threading.Timer(2.0, manage_trades).start()

    if len(ACTIVE_POSITIONS) > 0 and not is_busy:
        is_busy = True
        for active_position in ACTIVE_POSITIONS:
            strike = active_position["symbol"]
            db_record = get_obj_from_array(ACTIVE_TRADES_IN_DB, "strike", strike)
            if db_record:
                symbol = db_record["symbolName"]
                if symbol in LTP_DICT:
                    if db_record["type"] == "CALL":
                        if db_record["side"] == "BUY":
                            if db_record["profitPrice"] <= LTP_DICT[symbol] or db_record["slPrice"] >= LTP_DICT[symbol]:
                                print("In CALL Exit")
                                order = get_obj_from_array(ORDER_BOOK, "symbol", symbol)
                                exit_position(props, fyers, "NULL")
                                update_trade_status(3, db_record["id"])
                                ACTIVE_TRADES_IN_DB = get_trades("trading", props, LTP_DICT)

                    if db_record["type"] == "PUT":
                        if db_record["side"] == "BUY":
                            if db_record["profitPrice"] >= LTP_DICT[symbol] or db_record["slPrice"] <= LTP_DICT[symbol]:
                                print("In PUT Exit")
                                order = get_obj_from_array(ORDER_BOOK, "symbol", symbol)
                                exit_position(props, fyers, "NULL")
                                update_trade_status(3, db_record["id"])
                                ACTIVE_TRADES_IN_DB = get_trades("trading", props, LTP_DICT)

        is_busy = False


manage_trades()


def tradePositionsFromTable():
    global PENDING_TRADES_IN_DB
    global is_busy
    threading.Timer(2.0, tradePositionsFromTable).start()
    trades = PENDING_TRADES_IN_DB
    if len(trades) > 0 and not is_busy:
        is_busy = True
        for trade in trades:
            if trade["symbolName"] in LTP_DICT:
                qty = trade["qty"]
                order_type = 2
                side = 1
                strategy = {"retry_count_create_order": 1}
                instrument_name = trade["symbolName"]
                if trade["strike"] != "NULL":
                    instrument_name = trade["strike"]
                if trade["aboveOrBelow"] == "ABOVE" and LTP_DICT[trade["symbolName"]] >= trade["price"]:
                    print("1 c")
                    create_order_single(props, fyers, instrument_name, qty, order_type, side, 0, 0, 0, 0,
                                        strategy)
                    update_trade_status(2, trade["id"])
                    PENDING_TRADES_IN_DB = get_trades("pending", props, LTP_DICT)

                elif trade["aboveOrBelow"] == "BELOW" and LTP_DICT[trade["symbolName"]] <= trade["price"]:
                    print("1 d")
                    create_order_single(props, fyers, instrument_name, qty, order_type, side, 0, 0, 0, 0,
                                        strategy)
                    update_trade_status(2, trade["id"])
                    PENDING_TRADES_IN_DB = get_trades("pending", props, LTP_DICT)

        is_busy = False


tradePositionsFromTable()
######################## Web Socket #########################

ws_access_token = f"{props['app_id']}:{access_token}"
run_background = False


def custom_message(response):
    # print("response Map", response)
    LTP_DICT.update({response[0]["symbol"]: response[0]["ltp"]})
    if props["show_logs"]:
        print("LTP Map", LTP_DICT)


def run_process_background_symbol_data(access_token):
    data_type = "symbolData"
    symbol = SYMBOL_FOR_LTP_MAP
    fs = ws.FyersSocket(access_token=access_token, run_background=False, log_path="/logs")
    fs.websocket_data = custom_message
    fs.subscribe(symbol=symbol, data_type=data_type)
    fs.keep_running()


def getSymbolsFromOrderList():
    global SYMBOL_FOR_LTP_MAP
    orders = fyers.orderbook()["orderBook"]

    DYNAMIC_SYMBOLS = []
    for order in orders:
        DYNAMIC_SYMBOLS.append(order["symbol"])
        print("Order : ", order)

    SYMBOL_FOR_LTP_MAP_UNIQUE = list(set(DYNAMIC_SYMBOLS))
    SYMBOL_FOR_LTP_MAP = SYMBOL_FOR_LTP_MAP + SYMBOL_FOR_LTP_MAP_UNIQUE
    # print(" After SYMBOL_FOR_LTP_MAP : ", SYMBOL_FOR_LTP_MAP)


getSymbolsFromOrderList()

# def custom_message_order(msg):
#     global ACTIVE_POSITIONS
#     global TRADE_BOOK
#     ACTIVE_POSITIONS = get_current_active_positions(fyers.positions()["netPositions"])
#     print("Active Positions : ", ACTIVE_POSITIONS)
#     TRADE_BOOK = fyers.tradebook()["tradeBook"]
#     print("TRADE_BOOK : ", TRADE_BOOK)


# def run_process_background_order_data(access_token):
#     data_type = "orderUpdate"
#     fs_order_data = ws.FyersSocket(access_token=access_token, run_background=False, log_path="/logs")
#     fs_order_data.websocket_data = custom_message_order
#     fs_order_data.subscribe(data_type=data_type)
#     fs_order_data.keep_running()


run_process_background_symbol_data(ws_access_token)

handleAfterPosition(fyers, LTP_DICT)
# run_process_background_order_data(ws_access_token)
