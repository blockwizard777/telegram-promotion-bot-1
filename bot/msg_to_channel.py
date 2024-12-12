import os
from math import log10
import datetime

from telegram.constants import ParseMode
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from bot.api import fetch_pair_details, fetch_coin_info
from bot.db import load_custom_pairs 

import globals

IMAGE_PATH = "ancy.jpg" 

async def send_pay_state(bot, chat_id, user_data, payment_data) -> None:
	# Check if the image file exists
	if not os.path.exists(IMAGE_PATH):
		print(f"Error: The file {IMAGE_PATH} does not exist.")
		return

	pairdatas = load_custom_pairs(user_data["coinInfo"]["coinType"])
	fetched_datas = await fetch_pair_details(pairdatas[0]["pairId"])

	marketCap = float(fetched_datas["tokenBase"]["priceUsd"]) * int(
		fetched_datas["tokenBase"]["totalSupply"]
	)

	message_text = (
		f"🍒 {user_data['user_name']} Is Looking Entered [AncyTrending](https://t.me/suitrending_boost)! 🍒\n\n"
		f"🟢 {user_data['coinInfo']['symbol']} | {format_number(marketCap)}K MC | {payment_data['symbol']}\n\n"
	)

	try:
		with open(IMAGE_PATH, "rb") as image_file:
			# Add 'await' here to ensure this async call is awaited
			await bot.send_photo(
				chat_id=chat_id,
				photo=image_file,
				caption=message_text,
				parse_mode=ParseMode.MARKDOWN
			)
	except FileNotFoundError:
		print(f"Error: File {IMAGE_PATH} not found.")
	except IOError as e:
		print(f"Error: Could not open file {IMAGE_PATH}. {str(e)}")


async def send_tracking_token(bot, chat_id: str, txn_info) -> None:
	# print(txn_info)
	coin_symbol = txn_info.get('token').split('::')[-1]
	search_coinType = txn_info.get('token')
	selected_token = next((item for item in globals.global_token_arr if item['coinType'] == search_coinType), None)

	api_coin_info = await fetch_coin_info(search_coinType)
	api_coin_dexes = api_coin_info.get('dexes',[])
	# api_coin_dexes = await fetch_coin_dexes(search_coinType)
	api_pair_data = await fetch_pair_details(txn_info['pairId'])

	liquidity_usd = sum(float(dex["liquidityUsd"]) for dex in api_coin_dexes)
	price_vari_6h = float(api_pair_data.get('stats','New').get('percent','New').get('6h','New'))

	if float(price_vari_6h)<0 :
		price_vari_6h = ""
	else :
		price_vari_6h = f"+{price_vari_6h:.2f}%"
	print('channel_board_add')

	img_cnt = int(log10(float(txn_info['quoteAmount']) + 1) * 10) + 1
	image_particles = "🟢" * img_cnt 

	message = (
		f"<b>${coin_symbol} :  {txn_info['tradingType']}!</b>\n\n"
		f"{image_particles}\n\n" 
		f"➡️ <b>{float(txn_info['quoteAmount']):.2f} SUI</b> (${float(txn_info['totalUsd']):.2f})\n" 
		f"⬅️ <b>{int(float(txn_info['baseAmount'])):,} </b> ${coin_symbol}\n\n" 
		f"👤 <a href='https://suiscan.xyz/mainnet/account/{txn_info['maker'].get('address')}/activity'>0x{txn_info['maker'].get('address')[:2]}...{txn_info['maker'].get('address')[-3:]}</a>: {price_vari_6h} <a href='https://suiscan.xyz/mainnet/tx/{txn_info['hash']}'>TXN</a>\n"

		f"💧 <b>Liquidity:</b> ${int(liquidity_usd):,}\n"
		f"🏛️ <b>Market Cap: $</b> {int(float(txn_info.get('priceUsd'))*selected_token['supply']):,}\n\n"
		f"<b>TRENDING </b> #{1} on @Ancy Trending\n\n"

		f"🏆<a href='{globals.pinned_trending_url}'>Trending</a> | 👁️<a href='{selected_token['launchURL']}'>{selected_token['launchPad']}</a>" 
	)
	keyboard = [
		[InlineKeyboardButton(f"Buy {coin_symbol} on {selected_token['launchPad']}", url=f"{selected_token['launchURL']}")]
	]
	reply_markup = InlineKeyboardMarkup(keyboard)

	await bot.send_message(
		chat_id=chat_id,
		text=message,
		parse_mode=ParseMode.HTML,
		reply_markup=reply_markup,
		disable_web_page_preview=True
	)


def format_number(num):
	if num >= 1_000_000_000: # Billions
		return f"{num / 1_000_000_000:.2f}B"
	elif num >= 1_000_000: # Millions
		return f"{num / 1_000_000:.2f}M"
	elif num >= 1_000: # Thousands
		return f"{num / 1_000:.2f}K"
	else: # Less than 1,000
		return f"{num:.2f}"

async def send_ranking(bot, chat_id: str, rank_score) -> None: 
	rankingIcons = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
	formatted_tokens = []

	for index, token in enumerate(rank_score):
		rankIcon = rankingIcons[index] if index < len(rankingIcons) else "🔘" 
		coin_symbol = token["symbol"]
		launchPad = token.get("launchPad", "No URL") 
		marketCap = token.get("marketCap", 0) 
		formatted_tokens.append(f"{rankIcon} {coin_symbol} | {format_number(marketCap)} MCap")

	rank_paragraph = "\n\n".join(formatted_tokens)

	utc_time = datetime.datetime.now(datetime.timezone.utc)
	formatted_utc_time = utc_time.strftime("%H:%M:%S UTC")

	message_text = (
		f"🍒 <b>Ancy's Trending:</b> SUI, Move Pump, PUMPFUN, MOONSHOT ...\n\n\n" 
		f"{rank_paragraph}\n\n\n"
		f"📅 Update time: <code>{formatted_utc_time}</code>"
	)

	keyboard = [
		[InlineKeyboardButton("✅Book Trending", url="https://t.me/suiTokenPromote_bot?start=1")]
	]
	reply_markup = InlineKeyboardMarkup(keyboard)

	# Send the message and pin it in the channel
	message = await bot.send_message(
		chat_id=chat_id,
		text=message_text,
		parse_mode=ParseMode.HTML,
		reply_markup=reply_markup,
		disable_web_page_preview=True
	)

	globals.pinned_msgID = message.message_id
	globals.pinned_trending_url = f"https://t.me/suitrending_boost/{message.message_id}"

	try:
		await bot.unpin_all_chat_messages(chat_id=chat_id)
		print("All pinned messages unpinned successfully.")
		await bot.pin_chat_message(chat_id=chat_id, message_id=message.message_id)
		print("Add recent trending dashlead.")
	except Exception as e:
		print(f"Error unpinning messages: {e}")
