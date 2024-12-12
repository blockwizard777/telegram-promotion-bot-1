
import json
import os
from bot.db import load_tokens, load_pairs 
# from bot.api import load_rank_data

FILENAME = os.path.join(os.path.dirname(__file__), "global_data.json")

global_token_arr = []
global_pair_arr = []
global_rank_arr = []

unit_coin_price = 2.0
pinned_trending_url = "https://t.me/suitrending_boost/571"
pinned_msgID = 571
total_account_arr = ['0xd6840994167c67bf8063921f5da138a17da41b3f64bb328db1687ddd713c5281']

def load_globals():
    global global_token_arr, global_pair_arr, global_rank_arr, unit_coin_price, pinned_trending_url, pinned_msgID

    global_token_arr = load_tokens() #load from db
    global_pair_arr = load_pairs()
    # rank_src_data = load_rank_data(global_pair_arr)

    # print(global_token_arr, "\n", global_pair_arr)
    
    try:
        with open(FILENAME, "r") as f:
            data = json.load(f)
            unit_coin_price = data.get("unit_coin_price", 2.0)
            pinned_trending_url = data.get("pinned_trending_url")
            pinned_msgID = data.get("pinned_msgID")

            if not global_token_arr :
                global_token_arr = data.get("global_token_arr")
            if not global_pair_arr :
                global_pair_arr = data.get("global_pair_arr")
    except FileNotFoundError:
        print(f"Warning: {FILENAME} not found. Using default values.")
        
# Function to save current global values to JSON file
def save_globals():
    global global_token_arr, global_pair_arr, unit_coin_price, pinned_trending_url, pinned_msgID
    data = {
        "global_token_arr": global_token_arr,
        "global_pair_arr": global_pair_arr,
        "global_rank_arr": global_rank_arr,
        "unit_coin_price": unit_coin_price,
        "pinned_trending_url": pinned_trending_url,
        "pinned_msgID": pinned_msgID,
    }
    with open(FILENAME, "w") as f:
        json.dump(data, f)

# Initialize globals on import
