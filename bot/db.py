import pymysql
import asyncio

import time
from datetime import datetime, timedelta

# from bot.api import fetch_account_txns
# from bot.api import fetch_coin_dexes

db_config = {
	"host": "autorack.proxy.rlwy.net",
	"user": "root",
	"password": "GbOlKeFDrsnprEQizCkdtfwjxHEhXMav",
	"db": "railway",
	"port": 14715,
}

connection = None


def db_initialize():
	"""Initialize the global database connection."""
	global connection
	if connection is None:
		try:
			print("Connecting to the database...")
			connection = pymysql.connect(**db_config)
			print("Database connected successfully.")
		except pymysql.MySQLError as err:
			print(f"Error connecting to database: {err}")
			connection = None


def get_connection():
	global connection
	"""Retrieve the current database connection."""
	if connection is None:
		db_initialize()
	return connection


def close_connection():
	"""Close the global database connection."""
	global connection
	if connection:
		print("Closing the database connection...")
		connection.close()
		connection = None
		print("Database connection closed.")


def load_tokens():
	"""Load data from tb_tokens into global_token_arr."""
	conn = get_connection()
	if conn:
		try:
			with conn.cursor() as cursor:
				# query = "SELECT id, symbol, name, launchPad, decimals, coinType, supply FROM tb_tokens where allow = 1"
				# query = "SELECT * FROM tb_tokens where allow = 1"
				query = "SELECT * FROM tb_tokens "
				cursor.execute(query)
				results = cursor.fetchall()
				column_names = [desc[0] for desc in cursor.description]

				token_arr = [dict(zip(column_names, row)) for row in results]

				# print("Data loaded successfully:", token_arr)
				return token_arr

			conn.commit()
		except pymysql.MySQLError as err:
			print(f"Error during query: {err}")
	else:
		print("Database connection is not available.")


def load_pairs():
	conn = get_connection()
	if conn:
		try:
			with conn.cursor() as cursor:
				# query = "SELECT symbol, name, launchPad, decimals, coinType, supply FROM tb_tokens where allow = 1"
				# query = "SELECT pairId, coinType FROM tb_tokens INNER JOIN tb_pairs ON tb_tokens.id = tb_pairs.token_id WHERE allow = 1;"
				query = "SELECT pairId, coinType FROM tb_tokens INNER JOIN tb_pairs ON tb_tokens.id = tb_pairs.token_id ;"
				cursor.execute(query)
				result = cursor.fetchall()
				pair_arr = [{"pairId": item[0], "coinType": item[1]} for item in result]
				# print(pair_arr)

				return pair_arr

			conn.commit()
		except pymysql.MySQLError as err:
			print(f"Error during query: {err}")
	else:
		print("Database connection is not available.")

import pymysql

def load_custom_pairs(cointype):
	conn = get_connection()
	if conn:
		try:
			with conn.cursor() as cursor:
				query = """
				            SELECT pairId, coinType 
				            FROM tb_tokens 
				            INNER JOIN tb_pairs ON tb_tokens.id = tb_pairs.token_id 
				            WHERE tb_tokens.allow = 1 AND tb_tokens.coinType = %s;
				        """
				cursor.execute(query, (cointype,))
				result = cursor.fetchall()

				pair_arr = [{"pairId": item[0], "coinType": item[1]} for item in result]

				return pair_arr

			conn.commit()
		except pymysql.MySQLError as err:
			print(f"Error during query: {err}")
	else:
		print("Database connection is not available.")


def fetch_Cointype(coin_type):
	conn = get_connection()
	try:
		with conn.cursor(pymysql.cursors.DictCursor) as cursor:
			query = "SELECT * FROM tb_tokens WHERE coinType = %s LIMIT 1"
			cursor.execute(query, (coin_type,))
			# Fetch result
			record = cursor.fetchone()
			return record
	except Exception as e:
		print(f"Error during retrieval: {e}")
		return []



async def clear_expired_boosts():
	conn = get_connection()
	current_time = int(datetime.now().timestamp() * 1000)
	try :
		with conn.cursor() as cursor:
			query = """
			            DELETE FROM tb_trend_history
			            WHERE end_timestamp < %s
			        """
			cursor.execute(query, (current_time,))
			conn.commit()

	except pymysql.MySQLError as err:
		print(f"Error clearing expired boosts: {err}")


async def fetch_rank_payment():

	conn = get_connection()
	try:
		with conn.cursor(pymysql.cursors.DictCursor) as cursor:
			query = f"SELECT * FROM tb_trend_history"

			cursor.execute(query)

			records = cursor.fetchall()
			return records
	except Exception as e:
		print(f"Error during retrieval: {e}")
		return []


def detect_launchpad(lauchURL):
	if "movepump.com" in lauchURL:
		return "Move Pump"


async def reg_memeToken(token):
	connection = get_connection()
	success = False
	message = None

	try:
		with connection.cursor() as cursor:
			# Insert into tb_tokens if the symbol does not already exist
			query_token = """
			              INSERT INTO tb_tokens (symbol, name, launchpad, launchURL, coinType, decimals, supply)
			              SELECT %s, %s, %s, %s, %s, %s, %s
			              FROM DUAL
			              WHERE NOT EXISTS (
			                  SELECT 1 FROM tb_tokens WHERE symbol = %s
			              );"""
			data_token = (
				token.get("symbol"),
				token.get("name"),
				detect_launchpad(token["launchURL"]),
				token["launchURL"],
				token["coinType"],
				token.get("decimals"),
				token.get("supply"),
				token.get("symbol"), # Match the WHERE clause placeholder
			)
			cursor.execute(query_token, data_token)

			# Check if the row was inserted
			if cursor.rowcount == 0:
				message = f"Token {token.get('symbol')} already exists."
				return (False, message)
			else:
				# Get the inserted token ID
				token_id_query = "SELECT id FROM tb_tokens WHERE symbol = %s;"
				cursor.execute(token_id_query, (token.get("symbol"),))
				token_id = cursor.fetchone()[0]

				# Insert the associated DEX pairs into tb_pairs
				dexes = token.get("dexes", [])
				# dexes = await fetch_coin_dexes(token['coinType'])

				if dexes:
					query_pairs = """
					                  INSERT INTO tb_pairs (token_id, pairId, dexName, liquidityUsd)
					                  VALUES (%s, %s, %s, %s);
					              """
					data_pairs = [
						(
							token_id,
							dex["pairId"],
							dex["dexName"],
							dex.get("liquidityUsd"),
						)
						for dex in dexes
					]
					cursor.executemany(query_pairs, data_pairs)

				connection.commit()
				success = True
				message = f"Token {token.get('symbol')} and its DEX pairs have been successfully added."
				return True, token_id

	except pymysql.MySQLError as e:
		message = (
			f"Failed to add token {token.get('symbol')} or its DEX pairs. Error: {e}"
		)
		connection.rollback()

	return success, message


async def regist_payment(user_data, payment_data):
	current_time_ms = int(datetime.now().timestamp() * 1000)
	period_ms = {
		"12hours": 43200000,
		"24hours": 86400000,
		"48hours": 172800000,
		"3days": 259200000,
		"1week": 604800000,
		"2weeks": 1209600000,
		"3weeks": 1814400000,
		"1month": 2592000000,
		"3hours": 10800000,
		"6hours": 21600000,
	}

	trend_txn_record = {
		"from_account": payment_data["fromAccount"],
		"to_account": payment_data["account"],
		"timestamp": payment_data["timestamp"],
		"sui_amount": payment_data["amount"],
		"digest": payment_data["digest"],
	}
	trend_history_record = {
		"digest": payment_data["digest"],
		"username": user_data["user_name"],
		"token_symbol": user_data["coinInfo"]["symbol"],
		"start_timestamp": current_time_ms,
		"end_timestamp": current_time_ms + period_ms[user_data["period"]],
	}

	connection = get_connection()
	try:
		with connection.cursor() as cursor:

			txn_query = """
			                INSERT INTO tb_trend_txns (from_account, to_account, timestamp, sui_amount, digest)
			                VALUES (%s, %s, %s, %s, %s)
			            """
			cursor.execute(
				txn_query,
				(
					trend_txn_record["from_account"],
					trend_txn_record["to_account"],
					trend_txn_record["timestamp"],
					trend_txn_record["sui_amount"],
					trend_txn_record["digest"],
				),
			)

			history_query = """
			                    INSERT INTO tb_trend_history (digest, username, token_symbol, start_timestamp, end_timestamp)
			                    VALUES (%s, %s, %s, %s, %s)
			                """
			cursor.execute(
				history_query,
				(
					trend_history_record["digest"],
					trend_history_record["username"],
					trend_history_record["token_symbol"],
					trend_history_record["start_timestamp"],
					trend_history_record["end_timestamp"],
				),
			)

		connection.commit()
		print("Records inserted successfully.")

	except pymysql.MySQLError as e:
		print("Error occurred:", e)
		connection.rollback()



async def main():
	account = "0xd6840994167c67bf8063921f5da138a17da41b3f64bb328db1687ddd713c5281"
	timestamp = 1704067200

	current_time = datetime.now()
	time_ahead = current_time - timedelta(minutes=20)
	timestamp_ahead_ms = int(time_ahead.timestamp()) * 1000

	# checked_txns = await fetch_db_payments(account, timestamp_ahead_ms)

	# print('detected from account--------', detected_txns, '\n')
	# print("detected from db ------------", checked_txns, "\n")


if __name__ == "__main__":
	asyncio.run(main())
