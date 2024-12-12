import aiohttp
import asyncio
import globals

async def fetch_coin_details(coinType):
	url = f"https://api.raidenx.io/api/v1/sui/tokens/{coinType}"

	async with aiohttp.ClientSession() as session:
		async with session.get(url) as response:
			if response.status == 200:
				coin_details = await response.json()
				# dexes = coin_details.get('dexes')
				# liquidity_usd = sum(float(dex["liquidityUsd"]) for dex in dexes)
				return {
					"symbol": coin_details.get("symbol"),
					"name": coin_details.get("name"),
					"coinType": coin_details.get("address"),
					"decimals": coin_details.get("decimals"),
					"price": coin_details.get("price"),
					"supply": coin_details.get("totalSupply"),
					"dexes": coin_details.get("dexes"),
					# 'liquidity_usd' : liquidity_usd
				}
			else:
				print(f"Error: {response.status}")
				return None


async def fetch_coin_info(coinType):
	url = f"https://api.raidenx.io/api/v1/sui/tokens/{coinType}/infos"

	async with aiohttp.ClientSession() as session:
		async with session.get(url) as response:
			if response.status == 200:
				coin_details = await response.json()
				dexes = coin_details.get("dexes")
				liquidity_usd = sum(float(dex["liquidityUsd"]) for dex in dexes)
				return {
					"symbol": coin_details.get("symbol"),
					"name": coin_details.get("name"),
					"coinType": coin_details.get("address"),
					"decimals": coin_details.get("decimals"),
					# 'price': coin_details.get('price'),
					"supply": coin_details.get("totalSupply"),
					"dexes": coin_details.get("dexes"),
					# 'liquidity_usd' : liquidity_usd
				}
			else:
				print(f"Error: {response.status}")
				return None


async def fetch_coin_dexes(coinType):
	url = f"https://api.raidenx.io/api/v1/sui/tokens/{coinType}/dexes"

	async with aiohttp.ClientSession() as session:
		async with session.get(url) as response:
			if response.status == 200:
				dex_details = await response.json()
				# dexes = coin_details.get('dexes')
				# liquidity_usd = sum(float(dex["liquidityUsd"]) for dex in dexes)
				return dex_details
			else:
				print(f"Error: {response.status}")
				return None


async def fetch_pair_details(pairId):
	url = f"https://api.raidenx.io/api/v1/sui/pairs/{pairId}"

	async with aiohttp.ClientSession() as session:
		async with session.get(url) as response:
			if response.status == 200:
				pair_details = await response.json()
				# return coin_details
				return pair_details
			else:
				print(f"Error: {response.status}")
				return None


async def load_rank_data():
	result_array = []

	for token in globals.global_token_arr:

		pairsOftoken = [
			pair["pairId"]
			for pair in globals.global_pair_arr
			if pair["coinType"] == token["coinType"]
		]

		token_data = {
			"coinType": token["coinType"],
			"symbol": token["symbol"],
			"launchurl" : token["launchURL"],
			"marketCap": 0,
			"holder": 0,
			"liquidity": 0,
			"volume": 0,
			"transaction": 0,
			"maker": 0,
		}

		for pair in pairsOftoken:
			
			pairInfo = await fetch_pair_details(pair)
			token_data["marketCap"] = float(pairInfo["tokenBase"]["priceUsd"]) * int(
				pairInfo["tokenBase"]["totalSupply"]
			)
			token_data["holder"] = int(pairInfo["totalHolders"])
			token_data["liquidity"] += float(pairInfo["liquidity"])
			token_data["volume"] += (
				float(pairInfo["stats"]["volume"]["1h"]) * 24
				+ float(pairInfo["stats"]["volume"]["6h"]) * 1.5
				+ float(pairInfo["stats"]["volume"]["24h"]) * 0.25
			)
			token_data["transaction"] += (
				float(pairInfo["stats"]["totalNumTxn"]["1h"]) * 24
				+ float(pairInfo["stats"]["totalNumTxn"]["6h"]) * 1.5
				+ float(pairInfo["stats"]["totalNumTxn"]["24h"]) * 0.25
			)
			token_data["maker"] += (
				float(pairInfo["stats"]["maker"]["1h"]) * 24
				+ float(pairInfo["stats"]["maker"]["6h"]) * 1.5
				+ float(pairInfo["stats"]["maker"]["24h"]) * 0.25
			)

		result_array.append(token_data)
	return result_array


async def fetch_account_txns(account, amount, start_timestamp):
	url = f"https://api.blockberry.one/sui/v1/accounts/{account}/activity?size=20&orderBy=DESC"
	headers = {"accept": "*/*", "x-api-key": "F9Y7kRMOYmfHycPaRrWBjRNLrIQmx0"}

	async with aiohttp.ClientSession() as session:
		async with session.get(url, headers=headers) as response:
			if response.status == 200:
				res = await response.json()
				txn_detail = res.get("content")
				extracted_data = []
				for item in txn_detail:
					timestamp = item.get("timestamp")
					if timestamp < start_timestamp:
						continue

					coins = (
						item.get("details", {})
						.get("detailsDto", {})
						.get("coins", [{}])[0]
					)
					digest = item.get("digest")
					from_account = item.get("activityWith", [{}])[0].get("id")

					amount_found = coins.get("amount", 0)
					coin_type = coins.get("coinType", "")
					symbol = coins.get("symbol", "")

					new_dict = {
						"account": account,
						"timestamp": timestamp,
						"amount": amount_found,
						"digest": digest,
						"symbol": symbol,
						"coinType": coin_type,
						"fromAccount": from_account,
					}

					if coin_type != "0x2::sui::SUI" or abs(amount_found - amount) > 0.1:
						continue

					extracted_data.append(new_dict)
				return extracted_data
			else:
				print(f"Error fetching transactions: {response.status}")
				return None


async def main():
	coin_type = (
		"0x197aece533dbee36b7698cead0403dfecafa421b3aaa55a15314062a5f640508::ancy::ANCY"
	)


if __name__ == "__main__":
	asyncio.run(main())
