import asyncio
import socketio

import signal
import sys
from threading import Event

from datetime import datetime, timedelta

from bot.utils import classify_token_input, generate_launchpad_url

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    ContextTypes,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
)
from bot.config import BOT_TOKEN, CHAT_ID


from bot.msg_to_channel import send_tracking_token, send_ranking, send_pay_state

from bot.api import (
    fetch_coin_info,
    load_rank_data,
    fetch_account_txns,
)

from bot.db import (
    db_initialize,
    close_connection,
    clear_expired_boosts,
    fetch_rank_payment,
    regist_payment,
    reg_memeToken,
)

import atexit

import globals

application = None

sio = socketio.AsyncClient()
stop_event = Event()  # Event to signal when to stop

front_msg_id = ""
front_chat_id = ""

# Store timers for each user to allow cancellation upon verification success
verification_timers = {}

paying_account_arr = []


def get_trendReceiveAccount():
    return "0xd6840994167c67bf8063921f5da138a17da41b3f64bb328db1687ddd713c5281"


async def check_vaild_payment(
    amount,
    server_account="0xd6840994167c67bf8063921f5da138a17da41b3f64bb328db1687ddd713c5281",
):
    amount = float(amount)
    current_time = datetime.now()
    time_ahead = current_time - timedelta(minutes=15)
    timestamp_ahead = int(time_ahead.timestamp() * 1000)

    detected_txns = await fetch_account_txns(server_account, amount, timestamp_ahead)

    # digests = await fetch_db_payments(server_account, timestamp_ahead)
    # print("detected_txns", detected_txns, "\n")
    # print("db_txns", digests, "\n")

    # digest_set = {item["digest"] for item in digests}
    # filtered_detected_txns = [
    #     item for item in detected_txns if item["digest"] not in digest_set
    # ]
    # print("filtered_txns", filtered_detected_txns)

    return detected_txns


def update_tokens_pairs(token_id, tokenInfo):

    globals.global_token_arr.append(
        {
            "id": token_id,
            "symbol": tokenInfo["symbol"],
            "name": tokenInfo["name"],
            "coinType": tokenInfo["coinType"],
            "launchPad": "Move Pump",
            "launchURL": tokenInfo["launchURL"],
            "decimals": tokenInfo["decimals"],
            "supply": int(tokenInfo["supply"]),
            "allow": 1,
        }
    )

    for dex in tokenInfo["dexes"]:
        globals.global_pair_arr.append(
            {"pairId": dex["pairId"], "coinType": tokenInfo["coinType"]}
        )


async def delete_user_message(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    try:
        await context.bot.delete_message(
            chat_id=update.effective_chat.id, message_id=update.message.message_id
        )
    except Exception as e:
        print(f"Failed to delete user message: {e}")


async def summaryView(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_data = context.user_data

    period = user_data["period"]
    cost = user_data["cost"]

    server_account = get_trendReceiveAccount()
    user_data["server_account"] = server_account

    coinInfo = user_data.get("coinInfo", [])

    message_text = (
        "⚡ <b>ANCY Trending Boost</b> ⚡\n\n"
        f"<b>Top Trending  for {period}</b>\n\n"
        f"<b>Token Name: </b>{coinInfo['name']}\n"
        f"<b>Token Symbol: </b>{coinInfo['symbol']}\n\n"
        # "<b>Telegram:</b> https://t.me/AncyPeosiPortal\n\n"
        f"🔗 <b>Activate the boost by sending {cost} SUI to:</b>\n"
        f"<code>{server_account}</code>\n\n"
        f"<b>Step 1:</b> Send {cost} SUI\n"
        "<b>Step 2:</b> Click Verify Payment to verify the transaction\n"
        "<b>Step 3:</b> Watch ANCY soar to the Top trending shortly!\n\n"
        "🚀 <i>Get ready for a double dose of trending power!</i> 🚀\n\n"
    )
    keyboard = [
        [InlineKeyboardButton("✅ Verify Payment", callback_data="verify_payment")],
        [InlineKeyboardButton("🔙 Back", callback_data="period_select")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if update.message:
        await update.message.edit_text(
            text=message_text, reply_markup=reply_markup, parse_mode="HTML"
        )
    elif update.callback_query:
        await update.callback_query.edit_message_text(
            text=message_text, reply_markup=reply_markup, parse_mode="HTML"
        )


async def handle_period_selection(context, user_data, query=None, update=None):
    """
    Handles the period selection logic for both msgHandler and route.
    """
    message_text = (
        "<b>⚡Trending Boost⚡</b>\n"
        "Trending boost guarantees your token on Multichain Trending\n\n"
        "<b>Select the Period:</b>"
    )
    keyboard = [
        [
            InlineKeyboardButton("3 Hours | 25 SUI", callback_data="boost_3hours_25"),
            InlineKeyboardButton("3 days | 180 SUI", callback_data="boost_3days_180"),
        ],
        [
            InlineKeyboardButton("6 Hours | 35 SUI", callback_data="boost_6hours_35"),
            InlineKeyboardButton("1 week | 350 SUI", callback_data="boost_1week_350"),
        ],
        [
            InlineKeyboardButton("12 Hours | 45 SUI", callback_data="boost_12hours_45"),
            InlineKeyboardButton("2 weeks | 600 SUI", callback_data="boost_2weeks_600"),
        ],
        [
            InlineKeyboardButton("24 Hours | 75 SUI", callback_data="boost_24hours_75"),
            InlineKeyboardButton("3 weeks | 800 SUI", callback_data="boost_3weeks_800"),
        ],
        [
            InlineKeyboardButton(
                "48 Hours | 125 SUI", callback_data="boost_48hours_125"
            ),
            InlineKeyboardButton(
                "1 month | 1000 SUI", callback_data="boost_1month_1000"
            ),
        ],
        [InlineKeyboardButton("🔙 Back", callback_data="toStartMenu")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Use `query` if it's a callback query, otherwise use `update.message`.
    if query:
        await query.edit_message_text(
            text=message_text, reply_markup=reply_markup, parse_mode="HTML"
        )
    elif update:
        bot_message_id = user_data.get("bot_message_id")
        if bot_message_id:
            try:
                await context.bot.edit_message_text(
                    chat_id=update.effective_chat.id,
                    message_id=bot_message_id,
                    text=message_text,
                    parse_mode="HTML",
                    reply_markup=reply_markup,
                )
            except Exception as e:
                print(f"Failed to edit bot message: {e}")
        else:
            bot_message = await update.message.reply_text(
                text=message_text, parse_mode="HTML", reply_markup=reply_markup
            )
            user_data["bot_message_id"] = bot_message.message_id


async def show_token_confirmation(
    context: ContextTypes.DEFAULT_TYPE,
    user_data: dict,
    chat_id: int,
    bot_message_id: int = None,
    query=None,
) -> None:

    coin_info = user_data.get("coinInfo", {})
    message_text = (
        f"Add {coin_info.get('symbol')} token Confirmation:\n\n"
        f"Name : {coin_info.get('name')}\n"
        f"Symbol : {coin_info.get('symbol')}\n"
        f"LuanchPad : 💸{coin_info.get('launchPad')}💸\n"
        f"LaunchPad URL: {coin_info.get('launchURL')}\n\n"
        f"CA:<code>{coin_info.get('coinType')}</code>"
    )

    reply_keyboard = [
        [
            InlineKeyboardButton("❌ Close", callback_data="close"),
            InlineKeyboardButton("✅ Add Confirm", callback_data="add_token_confirm"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(reply_keyboard)

    try:
        if bot_message_id:
            # Edit the existing bot message
            await context.bot.edit_message_text(
                chat_id=chat_id,
                message_id=bot_message_id,
                text=message_text,
                parse_mode="HTML",
                reply_markup=reply_markup,
                disable_web_page_preview=True,
            )
        elif query:
            # Edit the callback query message
            await query.edit_message_text(
                text=message_text,
                parse_mode="HTML",
                reply_markup=reply_markup,
                disable_web_page_preview=True,
            )
    except Exception as e:
        print(f"Failed to update confirmation message: {e}")


async def boost_callback_handler(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    query = update.callback_query
    await query.answer()

    user_data = context.user_data
    if not user_data.get("user_id", None):
        return
    print(query.from_user.id, user_data["user_id"])
    if query.from_user.id != user_data["user_id"]:
        return

    callback_data = query.data
    if callback_data.startswith("boost_"):

        period, cost = callback_data.split("_")[1:3]
        context.user_data["period"] = period
        context.user_data["cost"] = cost
        await summaryView(update, context)

        return


async def handle_invalid_token_input(update, context, user_data, response=None):
    invalid_message = await update.message.reply_text(
        f"Invalid token input: {response or 'Invalid input'}!"
    )

    await update.message.delete()

    bot_message_id = user_data.get("bot_message_id")
    if bot_message_id:
        try:
            await context.bot.delete_message(
                chat_id=update.effective_chat.id, message_id=bot_message_id
            )
        except Exception as e:
            print(f"Failed to delete bot message: {e}")

    message_text = (
        "❔ Send me token's Contract Address(coinType) or LaunchPad/PresaleUrl :\n\n"
        "Supported chains: Sui\n"
        "Supported Launches: move.pump | turbos.fun | hop.fun \n"
    )
    bot_message = await invalid_message.reply_text(text=message_text, parse_mode="HTML")
    user_data["bot_message_id"] = bot_message.message_id


async def msgHandler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # global input_seq
    input_text = update.message.text

    user_data = context.user_data  # Unique to each user
    input_seq = user_data.get("input_seq", None)  # Get user-specific state

    if not user_data.get("user_id"):
        return
    if update.message.from_user.id != user_data["user_id"]:
        return
    # Validate coin type
    user_message_id = update.message.message_id  # Get the user's message ID
    bot_message_id = user_data.get("bot_message_id")

    if user_data["user_id"] and input_seq == "input_token":
        inputType, response = classify_token_input(input_text.strip())
        print(inputType, response)
        if inputType == "invalid":
            await handle_invalid_token_input(update, context, user_data, response)
            return
        coinType = response["coinType"]
        selected_token = next(
            (
                token
                for token in globals.global_token_arr
                if token["coinType"] == coinType
            ),
            None,
        )

        if selected_token:
            user_data["coinInfo"] = selected_token
            user_data["input_seq"] = "period_select"
            await delete_user_message(update, context)
            await handle_period_selection(context, user_data, update=update)
            return

        # Delete the user message using the helper

        coinInfo = await fetch_coin_info(coinType)

        if coinInfo:
            user_data["coinInfo"] = coinInfo
        else:
            await handle_invalid_token_input(
                update, context, user_data, "There's no such token in SUI blockchain!"
            )
            return

        # new token Input Case
        if inputType == "launchURL":
            print("launchURL_response", response)
            user_data["coinInfo"]["launchPad"] = response["launchPad"]
            user_data["coinInfo"]["launchURL"] = response["launchURL"]

            # Delete the user's message
            await delete_user_message(update, context)

            # Show the confirmation message
            await show_token_confirmation(
                context=context,
                user_data=user_data,
                chat_id=update.effective_chat.id,
                bot_message_id=bot_message_id,
            )
            return

        elif inputType == "coinType":
            # Process the launch URL (response is a dictionary with launchPad and launchURL)
            message_text = "<b>Select launchPad</b>\n\n"

            # Define the inline keyboard with multiple buttons in a grid format
            keyboard = [
                [
                    InlineKeyboardButton("move.pump", callback_data="sel_move_pump"),
                    InlineKeyboardButton("turbos.fun", callback_data="sel_turbos_fun"),
                    InlineKeyboardButton("hop.fun", callback_data="sel_hop_fun"),
                ],
                [InlineKeyboardButton("❌ Close", callback_data="toStartMenu")],
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await update.message.delete()

            user_data["input_seq"] = "input_launchPad"

            bot_message_id = user_data.get("bot_message_id")
            if bot_message_id:
                try:
                    # Edit the bot message with the new content and inline keyboard
                    await context.bot.edit_message_text(
                        chat_id=update.effective_chat.id,
                        message_id=bot_message_id,
                        text=message_text,
                        parse_mode="HTML",
                        reply_markup=reply_markup,  # Add the reply_markup to show the keyboard
                    )
                except Exception as e:
                    print(f"Failed to edit bot message: {e}")
            else:
                # If there's no bot_message_id, send a new message instead
                bot_message = await update.message.reply_text(
                    text=message_text, parse_mode="HTML", reply_markup=reply_markup
                )
                user_data["bot_message_id"] = (
                    bot_message.message_id
                )  # Save the new message ID


async def route(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_data = context.user_data  # Unique to each user
    query = update.callback_query
    await query.answer()

    print(f"here ROUTE!-----{query.data}\n")

    if not user_data.get("user_id", None):
        return
    print(query.from_user.id, user_data["user_id"])
    if query.from_user.id != user_data["user_id"]:
        return

    if query.data == "cancel":
        await query.message.delete()

    if query.data == "input_token":
        user_data["input_seq"] = "input_token"

        message_text = (
            "❔ Send me token's Contract Address(coinType) or LaunchPad/PresaleUrl :\n\n"
            "Supported chains: Sui\n"
            "Supported Launches : move.pump | turbos.fun | hop.fun \n"
        )
        await query.edit_message_text(text=message_text, parse_mode="HTML")
    if query.data in ["sel_move_pump", "sel_turbos_fun", "sel_hop_fun"]:
        if query.data == "sel_move_pump":
            user_data["coinInfo"]["launchPad"] = "move.pump"
        elif query.data == "sel_turbos_fun":
            user_data["coinInfo"]["launchPad"] = "turbos.fun"
        elif query.data == "sel_hop_fun":
            user_data["coinInfo"]["launchPad"] = "sel_hop_fun"
        user_data["coinInfo"]["launchURL"] = generate_launchpad_url(
            user_data["coinInfo"]["launchPad"], user_data["coinInfo"]["coinType"]
        )

        print(user_data["coinInfo"])
        user_data["input_seq"] = "addTokenConfirm"

        await show_token_confirmation(
            context=context,
            user_data=user_data,
            chat_id=query.message.chat_id,
            query=query,
        )
        return
    if query.data == "add_token_confirm":
        print("add_token_confirmation : ", user_data["coinInfo"])
        res, res_message = await reg_memeToken(context.user_data["coinInfo"])

        if not res:
            await query.edit_message_text(text=f"Failt to regist! {res_message}")
            return

        token_id = res_message
        await query.edit_message_text(
            text=f"You've succeeded to regist! {user_data['coinInfo']['symbol']}{res_message}"
        )
        update_tokens_pairs(token_id, context.user_data["coinInfo"])
        await asyncio.sleep(1)

        user_data["input_seq"] = "period_select"
        await handle_period_selection(context, user_data, query=query)

    if query.data == "period_select":
        user_data["input_seq"] = "coinType"
        await handle_period_selection(context, user_data, query=query)

    if query.data == "verify_payment":

        await query.edit_message_text(text="Validating Purchase ...")

        valid_payment = await check_vaild_payment(
            context.user_data["cost"], context.user_data["server_account"]
        )

        if valid_payment:
            await query.edit_message_text(
                text="Congratulations! You succeeded in Trend boosting! 👍 Your trend boost will be applied immediately."
            )

            await regist_payment(context.user_data, valid_payment[0])
            await send_pay_state(
                context.bot, CHAT_ID, context.user_data, valid_payment[0]
            )
            await run_ranking()

        else:
            await query.edit_message_text(
                text="⚠️ Payment not detected! If already sent, try again in a minute."
            )
            await asyncio.sleep(5)
            await summaryView(update, context)  # Return to summary if payment

    if query.data == "toStartMenu":
        user_data["input_seq"] = None  # Reset state
        await start_menu(query, context)

    if query.data == "close":
        await query.message.delete()
        user_data["input_seq"] = None  # Reset state
        await start_menu(query, context)


async def start_menu(update_or_callback, context: ContextTypes.DEFAULT_TYPE):
    # Initial message
    message_text = (
        "⚡ <b>Trending Boost</b> ⚡\n\n"
        "📌 <b>Guaranteed Listing on</b> <a href='https://t.me/suitrending_boost'>Ancy's Trending</a>\n"
        "✅ Large favorability on our algorithm\n"
        "✅ And more common pump alerts for your token\n"
        "🚀 Enjoy the volume boost that comes with your Trending purchase\n\n"
        "🚀 <b>Click the button below to start</b>"
    )
    reply_markup = InlineKeyboardMarkup(
        [[InlineKeyboardButton("🚀 Start Now", callback_data="input_token")]]
    )

    if isinstance(update_or_callback, Update):
        user = update_or_callback.message.from_user
        context.user_data["user_id"] = user.id  # Store the user ID
        context.user_data["user_name"] = user.username  # Store the username

        sent_message = await update_or_callback.message.reply_text(
            text=message_text,
            parse_mode="HTML",
            reply_markup=reply_markup,
            disable_web_page_preview=True,
        )
        context.user_data["bot_message_id"] = sent_message.message_id
        # print('bot_message_id', context.user_data['bot_message_id'])
    else:
        # print('bot_message_id', context.user_data['bot_message_id'])
        await update_or_callback.edit_message_text(
            text=message_text,
            parse_mode="HTML",
            reply_markup=reply_markup,
            disable_web_page_preview=True,
        )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "I can respond to:\n/start - Start trend\n /add - add memeToken\n /help - Show this help message"
    )


async def add_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_data = context.user_data
    user_data["input_seq"] = "add_meme_token"
    await update.message.reply_text(
        "❔ Send me the token's exact coinType \nSupported Chains: SUI\n\n ex) 0x197aece533dbee36b7698cead0403dfecafa421b3aaa55a15314062a5f640508::ancy::ANCY"
    )


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await start_menu(update, context)


async def on_connect():
    print("Connected to WebSocket!")
    for pair_item in globals.global_pair_arr:
        await sio.emit(
            "SUBSCRIBE_REALTIME_TRANSACTION", {"pairId": pair_item.get("pairId")}
        )
        # print(f"Emitted subscription for pairId: {pair_item.get('pairId')}")

    # await sio.emit("SUBSCRIBE_REALTIME_TRANSACTION", {
    #     'pairId': 'fd08ebdeb69d67541aa6f0b07cc98a9752516c5667f559367e329de4f5d77356',
    # })

    # await sio.emit('SUBSCRIBE_REALTIME_PAIR_STATS_CHANGED', {
    #     'pairId': 'fd08ebdeb69d67541aa6f0b07cc98a9752516c5667f559367e329de4f5d77356'
    # })


@sio.event
async def connect():
    print("Socket connected!")
    await on_connect()


@sio.event
async def connect_error(data):
    print(f"Connection failed with error: {data}")


@sio.event
async def disconnect():
    print("Disconnected from WebSocket!")


@sio.on("TRANSACTION")
async def handle_transaction(data):
    global application
    try:
        if data.get("tradingType") == "BUY" and float(data.get("quoteAmount")) >= 12:
            await send_tracking_token(application.bot, CHAT_ID, data)

    except Exception as e:
        print(f"Error processing transaction: {e}")


async def handle_pair(data):
    print("Pair stats changed::")
    print(data, "\n")


async def track_transactions():
    SOCKET_URL = "wss://ws-sui.raidenx.io"
    try:
        await sio.connect(SOCKET_URL)
        print("Attempting to connect to WebSocket server...")
        await sio.wait()
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        await sio.disconnect()


def stop_gracefully(signal_received, frame):
    stop_event.set()
    sio.disconnect()
    sys.exit(0)


async def calc_rank_score(rank_data):
    weights = {
        "marketCap": 0.2,
        "holder": 0.15,
        "liquidity": 0.15,
        "volume": 0.2,
        "transaction": 0.15,
        "maker": 0.15,
    }

    paid_data = await fetch_rank_payment()

    parameters = ["marketCap", "holder", "liquidity", "volume", "transaction", "maker"]

    max_min_values = {
        param: {"max": float("-inf"), "min": float("inf")} for param in parameters
    }

    for item in rank_data:
        for param in parameters:
            value = item[param]
            if value > max_min_values[param]["max"]:
                max_min_values[param]["max"] = value
            if value < max_min_values[param]["min"]:
                max_min_values[param]["min"] = value

    rank_scores = []
    current_time_ms = int(datetime.now().timestamp() * 1000)

    for item in rank_data:
        normalized_scores = {}
        for param in parameters:
            max_val = max_min_values[param]["max"]
            min_val = max_min_values[param]["min"]

            if max_val != min_val:
                normalized_scores[param] = (
                    (item[param] - min_val) / (max_val - min_val) * 100
                )
            else:
                normalized_scores[param] = 0

        rank_score = sum(
            normalized_scores[param] * weights[param] for param in parameters
        )

        for paid_item in paid_data:
            if (
                item["symbol"] == paid_item["token_symbol"]
                and current_time_ms < paid_item["end_timestamp"]
            ):
                rank_score *= 4

        rank_scores.append(
            {
                "symbol": item["symbol"],
                "coinType": item["coinType"],
                "marketCap": item["marketCap"],
                "score": rank_score,
            }
        )

    sorted_rank_scores = sorted(rank_scores, key=lambda x: x["score"], reverse=True)

    for i, item in enumerate(sorted_rank_scores, start=1):
        item["rank"] = i

    return sorted_rank_scores


async def run_ranking():
    global application

    try:
        rank_data = await load_rank_data()

        rank_score = await calc_rank_score(rank_data)

        await send_ranking(application.bot, CHAT_ID, rank_score[:15])

    except Exception as e:
        print(f"Error in run_ranking: {e}")


async def schedule_ranking_task():

    while True:
        await clear_expired_boosts()
        await run_ranking()
        await asyncio.sleep(30 * 60)


async def run_polling(application):
    await application.initialize()
    await application.start()
    await application.updater.start_polling()

    while True:
        await asyncio.sleep(0.1)


async def main():
    global application

    db_initialize()

    signal.signal(signal.SIGINT, stop_gracefully)
    atexit.register(close_connection)
    atexit.register(globals.save_globals)

    globals.load_globals()

    application = (
        Application.builder()
        .token(BOT_TOKEN)
        .read_timeout(40)
        .write_timeout(40)
        .build()
    )

    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("add", add_command))

    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, msgHandler))

    application.add_handler(
        CallbackQueryHandler(
            route,
            pattern="^(input_token|add_token_confirm|sel_move_pump|sel_turbos_fun|sel_hop_fun|cancel|confirm_add|coinType|period_select|toStartMenu|verify_payment|confirm|ack_to_main|close)$",
        )
    )
    application.add_handler(
        CallbackQueryHandler(boost_callback_handler, pattern=r"^boost_")
    )

    asyncio.create_task(track_transactions())
    asyncio.create_task(schedule_ranking_task())

    await run_polling(application)


if __name__ == "__main__":
    asyncio.run(main())
