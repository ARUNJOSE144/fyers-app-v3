import json
import os
import threading
from datetime import datetime

import mysql.connector
from colorama import Fore, Back
from fyers_api import accessToken
from playsound import playsound
from prettytable import PrettyTable

from common import get_object_from_list, get_comma_separated_symbols, write_log
from constants import *

fyers_copy = {}

connection = None


def load_properties():
    f = open('property.json')
    props = json.load(f)
    f.close()
    return props


def get_access_token(props):
    write_log("\n")
    access_token = ""
    now = datetime.now()
    d = now.strftime("%d-%m-%Y")
    file_name = "access_token/access_token_" + d + ".txt"
    if not os.path.exists(file_name):
        session = accessToken.SessionModel(client_id=props["app_id"], secret_key=props["secret_id"],
                                           redirect_uri=props["redirect_url"],
                                           response_type="code", grant_type="authorization_code")
        response = session.generate_authcode()
        write_log("Login url : " + response)

        auth_code = input("Enter Auth Code : ")
        session.set_token(auth_code)
        access_token = session.generate_token()['access_token']
        with open(file_name, "w")as f:
            f.write(access_token)
    else:
        with open(file_name, "r")as f:
            access_token = f.read()
    write_log("Access Token : " + access_token)
    return access_token


def get_available_balance(props, fyers, title):
    data = fyers.funds()
    write_log("Get Available Funds : Response : " + json.dumps(data))
    obj = get_object_from_list(data["fund_limit"], "title", title)
    return obj["equityAmount"]


def create_order_single(props, fyers, symbol, qty, type, side, limit_price, stop_price, stop_loss, take_profit,
                        strategy):
    request = {
        "symbol": symbol,
        "qty": qty,
        "type": type,
        "side": side,
        "productType": props["productType"],
        "limitPrice": limit_price,
        "stopPrice": stop_price,
        "validity": props["validity"],
        "disclosedQty": props["disclosedQty"],
        "offlineOrder": props["offlineOrder"],
        "stopLoss": stop_loss,
        "takeProfit": take_profit
    }
    retry_count = 1

    response = {}
    while retry_count <= strategy["retry_count_create_order"]:
        write_log("Create Order : Retry_count : " + str(retry_count) + " : Request : " + json.dumps(request))

        response = fyers.place_order(request)
        write_log("Create Order : Retry_count : " + str(retry_count) + " : Response : " + json.dumps(response))
        verify_response("PLACE_ORDER", response)
        retry_count = retry_count + 1
        if response["s"] == SUCCESS:
            print("Order successfully Placed...")
            break
    return response


def get_stocks_info(props, fyers, symbols):
    comma_seperated_symbols = get_comma_separated_symbols(symbols)
    request = {"symbols": comma_seperated_symbols}
    write_log("Get Stock Info : Request : " + json.dumps(request))
    response = fyers.quotes(request)
    write_log("Get Stock Info : Response : " + json.dumps(response))
    return response["d"]


def modify_order(props, fyers, order_id, limit_price, stop_price, qty, type):
    request = {
        "id": order_id
    }
    if limit_price != "NULL":
        request["limitPrice"] = limit_price
    if stop_price != "NULL":
        request["stopPrice"] = stop_price
    if qty != "NULL":
        request["qty"] = qty
    if type != "NULL":
        request["type"] = type

    response = {}
    write_log("Modify order : Request : " + json.dumps(request))
    response = fyers.modify_order(request)
    write_log("Modify order : Response : " + json.dumps(response))
    verify_response("STOP_LOSS_UPDATE", response)


def cancel_order(props, fyers, order_id):
    request = {"id": 'order_id'}
    response = {}
    write_log("Cancel order : Request : " + json.dumps(request))
    response = fyers.cancel_order(request)
    write_log("Cancel order : Response : " + json.dumps(response))
    verify_response("CANCEL_ORDER", response)


def exit_position(props, fyers, order_id):
    request = {}
    if order_id != "NULL":
        request["id"] = order_id

    write_log("Exit Position : Request : " + json.dumps(request))
    response = fyers.exit_positions(request)
    write_log("Exit Position : Response : " + json.dumps(response))
    verify_response("EXIT_POSITION", response)


def verify_response(action_type, response):
    audio = ""
    if action_type == "PLACE_ORDER" and response["s"] == SUCCESS:
        audio = ORDER_PLACED_SUCCESS
    elif action_type == "PLACE_ORDER":
        audio = ORDER_PLACED_FAILURE

    if action_type == "ORDER_MODIFY" and response["s"] == SUCCESS:
        audio = MODIFY_ORDER_SUCCESS
    elif action_type == "ORDER_MODIFY":
        audio = MODIFY_ORDER_FAILURE

    if action_type == "STOP_LOSS_UPDATE" and response["s"] == SUCCESS:
        audio = STOP_LOSS_UPDATED_SUCCESS
    elif action_type == "STOP_LOSS_UPDATE":
        audio = STOP_LOSS_UPDATED_FAILURE

    if action_type == "CANCEL_ORDER" and response["s"] == SUCCESS:
        audio = ORDER_CANCELLED_SUCCESS
    elif action_type == "CANCEL_ORDER":
        audio = ORDER_CANCELLED_FAILURE

    if action_type == "EXIT_POSITION" and response["s"] == SUCCESS:
        audio = ORDER_EXIT_SUCCESS
    elif action_type == "EXIT_POSITION":
        audio = ORDER_EXIT_FAILURE

    # if audio != "":
    #     playsound(audio)


def get_connection():
    # global connection
    # if connection == None:
    connection = mysql.connector.connect(host="10.0.0.85", user="stsuser", password="stsuser@6Dtech",
                                         database="QUESTION_MANAGEMENT")
    return connection


def get_trades(type, props, LTP_DICT):
    connection = get_connection()
    query = "SELECT * FROM TRADE_MASTER "
    if type == "pending":
        query += "where STATUS=1"
    elif type == "trading":
        query += "where STATUS=2"

    if props["show_logs"]:
        print(query)
    mycursor = connection.cursor()
    mycursor.execute(query)
    myresult = mycursor.fetchall()
    trades = []
    for record in myresult:
        trade = {}
        trade["id"] = record[0]
        trade["symbolName"] = record[1]
        trade["strike"] = record[2]
        trade["type"] = record[3]
        trade["side"] = record[4]
        trade["status"] = record[5]
        trade["aboveOrBelow"] = record[6]
        trade["price"] = record[7]
        trade["profitPrice"] = record[8]
        trade["slPrice"] = record[9]
        trade["qty"] = record[10]

        trades.append(trade)

    if props["show_logs"]:
        print("Trades  : ", trades)

    for trade in trades:
        now = datetime.now()
        dt_string = now.strftime("%H:%M:%S.%f")[:-3]
        print(dt_string, " : ", type, "  Strike:", trade["strike"], ", Price:", trade["price"])
        if trade["symbolName"] in LTP_DICT:
            print("Current Price : ", LTP_DICT[trade["symbolName"]])
        else:
            print("Current Price : Not Available")
    return trades


def update_trade_status(status, id):
    connection = get_connection()
    mycursor = connection.cursor()
    sql = "UPDATE TRADE_MASTER SET STATUS = " + str(status) + " WHERE ID = " + str(id)
    print(sql)
    mycursor.execute(sql)
    connection.commit()
    print(mycursor.rowcount, "record(s) affected")


def get_current_active_positions(positions):
    active_positions = []
    for position in positions:
        if position["buyQty"] != position["sellQty"]:
            active_positions.append(position)

    return active_positions


def get_obj_from_array(list, field_name, value):
    for obj in list:
        if obj[field_name] == value:
            return obj
    return ""


def play_audio(file_path):
    try:
        playsound(file_path)
    except Exception as e:
        log_message("Error While playing alert", "WARNING")


def alertUser(file_path):
    audio_thread = threading.Thread(target=play_audio, args=(file_path,))
    audio_thread.start()


# Define your log levels and associated colors
log_levels = {
    'INFO': Fore.BLUE,
    'WARNING': Fore.YELLOW,
    'ERROR': Fore.RED,
    'CRITICAL': Back.RED + Fore.WHITE,
}


def log_message(message, level='INFO'):
    # Get the color for the log level
    color = log_levels.get(level, Fore.RESET)

    # Display the log message with color
    print(f'{color}[{level}] {message}')


def filter_pending_status_rows():
    pending_rows = []
    file_path = "Trade_notepad.txt"

    with open(file_path, 'r') as file:
        lines = file.readlines()
        file.close()

    header = [x.strip() for x in lines[0].replace(" ", "").split('|')]
    for line in lines[1:]:
        parts = [x.strip() for x in line.replace(" ", "").split('|')]
        row = dict(zip(header, parts))
        date_to_check = datetime.strptime(row['date'], "%d-%m-%Y")

        if row['status'] == 'Pending' and date_to_check.date() == datetime.now().date():
            # Convert ID to an integer
            row['id'] = int(row['id'])
            # Remove 'Status' key as it's not needed in the output
            # del row['Status']
            pending_rows.append(row)

    return pending_rows


def update_status_by_id(id_to_update, new_status):
    file_path = "Trade_notepad.txt"
    # Read the text file
    with open(file_path, 'r') as file:
        lines = file.readlines()
        file.close()

    updated_lines = []

    for line in lines:
        parts = line.replace(" ", "").split('|')
        if len(parts) >= 6:
            current_id = parts[0]
            current_status = parts[5]
            if current_id == str(id_to_update):
                parts[5] = new_status
                updated_line = ' | '.join(parts)
                print("Before Update: ", updated_line)
                updated_lines.append(updated_line)
            else:
                updated_lines.append(line)

    # Write the updated content back to the file
    with open(file_path, 'w') as file:
        file.writelines(updated_lines)
        file.close()

    print(f"Updated Status for ID {id_to_update} to '{new_status}'.")


def print_in_table(array):
    table = PrettyTable()
    all_keys = set(key for item in array for key in item.keys())
    table.field_names = list(all_keys)
    for item in array:
        table.add_row([item.get(key, "") for key in all_keys])
    print(table)


def calculate_strike(props, trade, LTP_DATA):
    print("HHH Trade : ", trade)
    print("HHH LTP_DATA : ", LTP_DATA)
    current_price = LTP_DATA[trade["symbol"]]
    symbol_stock_info_list = props["symbol_stock_info"]
    symbol_info = ""
    strike = trade["strike"]
    for symbol_stock_info in symbol_stock_info_list:
        if symbol_stock_info["symbol"] == trade["symbol"]:
            symbol_info = symbol_stock_info

    coieficient = int(current_price / symbol_info["strike_displacement"])

    if trade["operator"] == ">=":
        strike_val = (coieficient - int(trade["from_ATM"])) * symbol_info["strike_displacement"]
        strike += str(strike_val) + "PE"
    elif trade["operator"] == "<=":
        strike_val = (coieficient + int(trade["from_ATM"]) + 1) * symbol_info["strike_displacement"]
        strike += str(strike_val) + "CE"

    print("strike : ", strike)
    return strike
