import json
from prettytable import PrettyTable


def print_in_table(array):
    table = PrettyTable()
    all_keys = set(key for item in array for key in item.keys())
    table.field_names = list(all_keys)
    for item in array:
        table.add_row([item.get(key, "") for key in all_keys])
    print(table)


# Example usage
# json_data = [{"symbol": "NIFTY", "type": "Arun", "price": 19567}, {"symbol": "BANKNIFTY", "price": 45600}]
# print_in_table(json_data)


