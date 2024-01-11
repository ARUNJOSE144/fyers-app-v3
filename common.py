from datetime import date
from datetime import datetime
from time import strftime


def get_object_from_list(list, key, value):
    # print("list", list)
    for obj in list:
        # print("obj", obj)
        # print("key", key)
        # print("value", value)
        if obj[key] == value:
            return obj


def get_comma_separated_symbols(list):
    comma_separated_symbols = ""
    for symbolObj in list:
        if comma_separated_symbols == "":
            comma_separated_symbols += symbolObj["symbol"]
        else:
            comma_separated_symbols += "," + symbolObj["symbol"]

    return comma_separated_symbols


def get_percentage_value(percentage, value):
    return (percentage / 100) * value


def get_formatted_price(x):
    g = float("{:.3f}".format(x))
    mod = g % 1
    number = int(g / 1)
    result = 0
    array = [.0, .05, .1, .15, .2, .25, .3, .35, .4, .45, .5, .55, .6, .65, .7, .75, .8, .85, .9, .95]
    for i in array:
        if mod >= .95:
            result = .95

        if i == mod:
            result = i
            break

        if i < mod:
            continue
        else:
            result = i
            break
    result = float(number) + float(result)
    return result


def write_log(content):
    now = datetime.now()
    dt_string = now.strftime("%d/%m/%Y %H:%M:%S.%f")[:-3]
    d = now.strftime("%d-%m-%Y")

    print(content)
    with open('LOGS/log_' + d + '.txt', 'a') as f:
        f.write("\n" + dt_string + "    " + content)
