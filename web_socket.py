from fyers_api.Websocket import ws


def run_process_background_symbol_data(access_token):
    data_type = "symbolData"
    symbol = ["NSE:SBIN-EQ", "NSE:ONGC-EQ"]  ##NSE,BSE sample symbols
    #     symbol =["MCX:SILVERMIC21NOVFUT","MCX:GOLDPETAL21SEPFUT"]  ##MCX SYMBOLS
    fs = ws.FyersSocket(access_token=access_token, run_background=True, log_path="/home/Downloads/")
    fs.websocket_data = custom_message
    fs.subscribe(symbol=symbol, data_type=data_type)
    fs.keep_running()


def custom_message(msg):
    print(f"Custom:{msg}")


def main():
    access_token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpc3MiOiJhcGkuZnllcnMuaW4iLCJpYXQiOjE2Nzg1MDY2NzgsImV4cCI6MTY3ODU4MTAxOCwibmJmIjoxNjc4NTA2Njc4LCJhdWQiOlsieDowIiwieDoxIiwieDoyIiwiZDoxIiwiZDoyIiwieDoxIiwieDowIl0sInN1YiI6ImFjY2Vzc190b2tlbiIsImF0X2hhc2giOiJnQUFBQUFCa0NfcTJ1WVNYdzNiOV85dUlxaG5IMWUxLWJlQko1U1QwalJ1dHMwSncyQ2NDeTVrbm1FV3Z5aXo3Wk1SX1FPazZoNVFZR1duY0Ewc0FoTEVWYkQycWhzNm5yeU13Sm9GMWU4aXJrVmtGelY3V01IUT0iLCJkaXNwbGF5X25hbWUiOiJBUlVOIEpPU0UiLCJvbXMiOiJLMSIsImZ5X2lkIjoiWEE0NzczOCIsImFwcFR5cGUiOjEwMCwicG9hX2ZsYWciOiJOIn0.iRlFqUOl4J_bz82TkJInSR6pxoADJyDJaOiSlbM-n8g "
    run_process_background_symbol_data(access_token)


if __name__ == '__main__':
    main()