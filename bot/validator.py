from bot.db import fetch_Cointype

def validate_coinType(coinType: str) -> bool:
    record = fetch_Cointype(coinType)
    print('fetch from database :-------------- ', record)
    if(record) :
        if(record['allow']) :
            return {'val': True, 'text' : 'success'}
        else :
            return {'val': False, 'text' : 'Token is registered, but not allowed!'}
    else :
        return {'val': False, 'text' : 'Token is not registered, regist ahead!'}

def validate_boosting_period(boosting_period) -> bool :
    if boosting_period.isdigit():
        period = int(boosting_period)
        return 1 <= period <= 10  # Valid boosting period if it is between 1 and 10 (inclusive)
    return False  # If not a number, return False

def validate_wallet_address(wallet_address) -> bool :
    return True

