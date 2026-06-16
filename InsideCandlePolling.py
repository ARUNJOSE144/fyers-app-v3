import datetime

import schedule
from colorama import init

from util import *
from datetime import datetime, timedelta, time  # Import after wildcard to avoid shadowing by util's `time` module
import time as time_module

props = {}
LTP_DICT = {}
ACTIVE_POSITIONS = []
TRADE_BOOK = []
ORDER_BOOK = []
EXTERNAL_PENDING_TRADES = []
LOCK = False
trade_gap_counter = 0
fyersWeb = ""

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
write_log(json.dumps(fyers.positions()))
get_available_fund(fyers)

print("Start : ", datetime.now())
SYMBOL = props["consolidation_check_symbol_name"]
CANDLE_COUNT = props["consolidation_check_candle_count"]  # Last 6 candles
PERCENTAGE_THRESHOLD = props["consolidation_check_range_percent"]  # 1% range
CANDLE_TIME = props["consolidation_check_candle_minutes"]

def is_market_open():
    """Returns True if the time is between 9:15 AM and 3:30 PM, else False."""
    now = datetime.now().time()  # Get current time

    market_open = time(9, 15)  # 9:15 AM
    market_close = time(15, 30)  # 3:30 PM

    return market_open <= now <= market_close

def get_last_n_candles(n):
    """Fetch the last n 5-minute candles."""
    now = datetime.now()
    range_from = int((now - timedelta(minutes=n * CANDLE_TIME)).timestamp())  # Start time
    range_to = int(now.timestamp())  # End time

    data = {
        "symbol": SYMBOL,
        "resolution": CANDLE_TIME,
        "date_format": "0",
        "range_from": range_from,
        "range_to": range_to,
        "cont_flag": "1"
    }

    print("Request:", data)

    response = fyers.history(data=data)

    if "candles" in response:
        return response["candles"][-n:]  # Get only the last n candles
    else:
        print("Error fetching candles:", response)
        return None


def check_candles_in_range():
    global props
    global SYMBOL
    global CANDLE_COUNT
    global PERCENTAGE_THRESHOLD
    global CANDLE_TIME
    """Check if the last 6 candles' high-low percentage range is < 1%."""
    props = load_properties()
    SYMBOL = props["consolidation_check_symbol_name"]
    CANDLE_COUNT = props["consolidation_check_candle_count"]  # Last 6 candles
    PERCENTAGE_THRESHOLD = props["consolidation_check_range_percent"]  # 1% range
    CANDLE_TIME = props["consolidation_check_candle_minutes"]

    print("Time : ", datetime.now())
    now = datetime.now()
    if is_market_open():
        if now.minute % CANDLE_TIME == 0:
            candles = get_last_n_candles(CANDLE_COUNT)
            print("candles : ", candles)
        else:
            return
        if not candles or len(candles) < CANDLE_COUNT:
            print("Not enough data to analyze.")
            return
    else:
        print("Market closed...")
        return

    highs = [candle[2] for candle in candles]  # Extract high prices
    lows = [candle[3] for candle in candles]  # Extract low prices

    highest_high = max(highs)
    lowest_low = min(lows)

    # Calculate percentage range
    range_percentage = ((highest_high - lowest_low) / lowest_low) * 100

    print(f"Last {CANDLE_COUNT} candles range: {lowest_low} - {highest_high}")
    print(f"Range Percentage: {range_percentage:.2f}%")

    if range_percentage < PERCENTAGE_THRESHOLD:
        print("✅ The last " + str(CANDLE_COUNT) + " candles are " + str(round(range_percentage, 2)) + "  range ")
        alertUser(INSIDE_CANDLE_FOUND)
    else:
        print("❌ The last " + str(CANDLE_COUNT) + " candles are in " + str(round(range_percentage, 2)) + "range")


# Schedule function to run every 5 minutes
schedule.every(1).minutes.at(":05").do(check_candles_in_range)

print("Inside Candle Checker Running...")
while True:
    schedule.run_pending()
    time_module.sleep(1)



