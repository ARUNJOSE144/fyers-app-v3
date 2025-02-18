import datetime

import schedule
from colorama import init
from datetime import datetime, timedelta  # Import timedelta separately


from util import *
import time

props = {}
LTP_DICT = {}
ACTIVE_POSITIONS = []
TRADE_BOOK = []
ORDER_BOOK = []
EXTERNAL_PENDING_TRADES = []
LOCK = False
trade_gap_counter = 0
fyersWeb = ""
CANDLE_TIME=1

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
alertUser(INSIDE_CANDLE_FOUND)

print("Start : ", datetime.now())
SYMBOL = "NSE:NIFTY50-INDEX"
CANDLE_COUNT = 25  # Last 6 candles
PERCENTAGE_THRESHOLD = .15  # 1% range


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

    response = fyers.history(data=data)

    if "candles" in response:
        return response["candles"][-n:]  # Get only the last n candles
    else:
        print("Error fetching candles:", response)
        return None


def check_candles_in_range():
    """Check if the last 6 candles' high-low percentage range is < 1%."""
    print("Time : ", datetime.now())
    now = datetime.now()
    if now.minute % CANDLE_TIME == 0:
        candles = get_last_n_candles(CANDLE_COUNT)
        print("candles : ", candles)
    else:
        return
    if not candles or len(candles) < CANDLE_COUNT:
        print("Not enough data to analyze.")
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
        print("❌ The last " + str(CANDLE_COUNT) + " candles are not in " + str(round(range_percentage, 2)) + "range")

# Schedule function to run every 5 minutes
schedule.every(1).minutes.at(":05").do(check_candles_in_range)

print("Inside Candle Checker Running...")
while True:
    schedule.run_pending()
    time.sleep(1)
