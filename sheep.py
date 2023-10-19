"""
A python script which reads uses env variables to connect to a Trello board,
receiving user input and returning the requested data in a brief readable format.
"""

import re
import sys
import json
import calendar
import requests
from requests.exceptions import ConnectionError
from datetime import datetime,timedelta


# GLOBAL VARIABLES
HELP_PROMPT = "Use ?help for instructions."
HELP_STR = """Replace the text in caps with its corresponding value.
Every Person has a name and description.
Every List has a name and may contain one or more Persons. 

?info (NAME)
Returns the description for a given Person.

?names (LIST NAME)
Returns all Person names in one list.

?lists
Returns every List name

?allnames
Returns all Person names across all Lists

?update (NAME) (DESCRIPTION TEXT)
Adds onto the existing description text for a given Person."""
BAD_CONN_STR = "Could not establish a connection to retrieve any data."
CLE = "ca465cd986c77caac5dfb3cd1c6e52b9"
TOK = "ATTAf4b0a022aa89f2c19ba5ce2696f641551d26004ead21f366583ed3d42fef478e89B13555"
BOARD_ID = "NpRJdfe4"
QUERY = {
  'key': CLE,
  'token': TOK
}
HEADERS = {
  "Accept": "application/json"
}

# FUNCTION DECLARATIONS
def create_response_err(method: str, code: int):
  return {
    "user_msg": f"Err: Bad {method} request. Code {code}.",
    "usable": False,
  }
def create_custom_err(custom_msg: str):
  if not custom_msg.endswith("."):
    custom_msg = f"{custom_msg}."
  return {
    "user_msg": custom_msg,
    "usable": False,
  }

def get_all_list_names():
  """
  Returns all of the list names
  """
  url = f"https://api.trello.com/1/boards/{BOARD_ID}/lists"
  try:
      response = requests.request("GET", url, params=QUERY)
  except ConnectionError as e:
      return create_custom_err(BAD_CONN_STR)
  if response.status_code != 200:
    return create_response_err("GET", response.status_code)
  all_lists = response.json()
  list_names = "\n".join([single_list.get("name") for single_list in all_lists if "name" in single_list])
  return {
    "user_msg": list_names,
    "usable": True,
    "return_data": all_lists,
  }

def find_list_id_by_name(list_name: str):
  """
  Returns the ID of a single list by providing the name of the list.
  """
  url = f"https://api.trello.com/1/boards/{BOARD_ID}/lists"
  try:
    response = requests.request("GET", url, params=QUERY)
  except ConnectionError as e:
    return create_custom_err(BAD_CONN_STR)
  if response.status_code != 200:
    return create_response_err("GET", response.status_code)
  all_lists = response.json()
  for single_list in all_lists:
    if single_list.get("name").lower() == list_name.lower():
      return {
        "user_msg": f"Found the List ID for {list_name}.",
        "usable": True,
        "return_data": single_list.get("id"),
      }
  return create_custom_err(f"No List exists by the name '{list_name}'")

def get_all_cards_in_list(list_id):
  """
  Returns all cards of a single list by providing the ID of the list.
  """
  url = f"https://api.trello.com/1/lists/{list_id}/cards"
  try:
      response = requests.request("GET", url, headers=HEADERS, params=QUERY)
  except ConnectionError as e:
      return create_custom_err(BAD_CONN_STR)
  if response.status_code != 200:
    return create_response_err("GET", response.status_code)
  all_people_in_list = response.json()
  names = "\n".join([person.get("name") for person in all_people_in_list if "name" in person])
  return {
    "user_msg": names,
    "usable": True,
    "return_data": all_people_in_list
  }

def get_all_names():
  """
  Returns all people across every list on the board.
  """
  url = f"https://api.trello.com/1/boards/{BOARD_ID}/cards"
  try:
    response = requests.request("GET", url, headers=HEADERS, params=QUERY)
  except ConnectionError as e:
    return create_custom_err(BAD_CONN_STR)
  if response.status_code != 200:
    return create_response_err("GET", response.status_code)
  all_people = response.json()
  names = "\n".join([person.get("name") for person in all_people if "name" in person])
  return {
    "user_msg": names,
    "usable": True,
    "return_data": all_people
  }

def get_card_by_name(person_name):
  """
  Returns full details for a Person via their name.
  """
  all_cards = get_all_names()
  if not all_cards.get("usable"):
    return create_custom_err("Err: Could not get all names.")
  persons_card = {}
  for card in all_cards.get("return_data"):
    if person_name.lower() in card.get('name').lower():
      persons_card = card
      break
  if not persons_card:
    return create_custom_err("Name does not exist")
  card_name = persons_card.get("name")
  card_id = persons_card.get("id")
  card_desc = persons_card.get("desc")
  raw_lastupd = persons_card.get("dateLastActivity")
  try:
    card_dt = datetime.strptime(raw_lastupd, "%Y-%m-%dT%H:%M:%S.%fZ")
    card_dt = card_dt - timedelta(hours=5)
    card_date = f"{card_dt.day} {calendar.month_abbr[card_dt.month]} {card_dt.year}"
  except Exception as e:
    card_date = "N/A"
  list_id = persons_card.get("idList")
  url = f"https://api.trello.com/1/lists/{list_id}"
  query = {
    'key': CLE,
    'token': TOK,
    'fields': 'name'
  }
  try:
    response = requests.request("GET", url, headers=HEADERS, params=query)
  except ConnectionError as e:
    return create_custom_err(BAD_CONN_STR)
  if response.status_code != 200:
    return create_response_err("GET", response.status_code)
  list_name = response.json().get("name")
  result_str = f"Name: {card_name}\nList: {list_name}\nDescription: {card_desc}\nLast updated: {card_date}"
  return {
    "user_msg": result_str,
    "usable": True,
    "return_data": card_id
  }

def append_card_desc_by_id(id: str, desc_str: str):
  url = f"https://api.trello.com/1/cards/{id}"
  query = {
    'key': CLE,
    'token': TOK,
    'fields': 'desc'
  }
  try:
    response = requests.request("GET", url, headers=HEADERS, params=query)
  except ConnectionError as e:
    return create_custom_err(BAD_CONN_STR)
  if response.status_code != 200:
    return create_response_err("GET", response.status_code)

  # Append the new description
  old_desc = response.json().get('desc')
  if isinstance(old_desc, str):
    if not old_desc:
      new_desc = f"{desc_str}"
    else:
      new_desc = f"{old_desc}\n\n{desc_str}"
  else:
    return create_custom_err("Err: The existing data could not be parsed.")

  # Send off the new description
  query = {
    'key': CLE,
    'token': TOK,
    'desc': new_desc
  }
  try:
      response = requests.request("PUT", url, headers=HEADERS, params=query)
  except ConnectionError as e:
      return create_custom_err(BAD_CONN_STR)
  if response.status_code != 200:
    return create_response_err("PUT", response.status_code)
  return {
    "user_msg": "Successfully updated the description.",
    "usable": True,
  }

# FUTURE DEVELOPMENT
def set_card_desc_by_id(id, desc_str):
  url = f"https://api.trello.com/1/cards/{id}"
  query = {
    'key': CLE,
    'token': TOK,
    'desc': desc_str
  }
  response = requests.request(
    "PUT",
    url,
    headers=HEADERS,
    params=query
  )
  if response.status_code != 200:
    return create_response_err("PUT", response.status_code)
  return {
    "user_msg": "Successfully updated the description.",
    "usable": True,
  }

def command_call(user_entry: str):
  """
  Returns the requested data based on user input.
  """
  # Separate the cmd from the input
  split_entry = user_entry.split(maxsplit=1)
  if not split_entry[0].startswith("?"):
    return "Commands begin with '?'. "
  cmd = split_entry[0]

  # Select the command
  if cmd == "?help":
    return HELP_STR

  if cmd == "?info":
    args = re.findall(r'\(([^)]+)\)', user_entry)
    if len(args) != 1:
      return f"Wrong usage. {HELP_PROMPT}"
    return get_card_by_name(args[0]).get("user_msg")

  if cmd == "?names":
    args = re.findall(r'\(([^)]+)\)', user_entry)
    if len(args) != 1:
      return f"Wrong usage. {HELP_PROMPT}"
    list_id = find_list_id_by_name(args[0])
    if not list_id.get("usable"):
      return list_id.get("user_msg")
    return get_all_cards_in_list(list_id.get("return_data")).get("user_msg")

  if cmd == "?lists":
    return get_all_list_names().get("user_msg")

  if cmd == "?allnames":
    return get_all_names().get("user_msg")

  if cmd == "?update":
    args = re.findall(r'\(([^)]+)\)', user_entry)
    if len(args) != 2:
      return f"Wrong usage. {HELP_PROMPT}"
    name = args[0]
    text = args[1]
    card_id = get_card_by_name(name)
    if not card_id.get("usable"):
      return card_id.get("user_msg")
    return append_card_desc_by_id(card_id.get("return_data"), text).get("user_msg")

  return f"Invalid command. {HELP_PROMPT}"

def main():
  try:
    [args] = sys.argv[1:]
  except Exception:
    print("Failing to process user input.")
    return
  print(command_call(args))
  return

# MAIN
if __name__ == '__main__':
  main()

# DEV USAGE TESTING AREA

# full = get_all_names()
# print(full.get("user_msg"))
# list_id = find_list_id_by_name("Important people")
# gotten_id = get_card_by_name("Politicians")
# theOG = "making promises of sorts"
# nonOG = "test desc"
# append_card_desc_by_id(gotten_id, nonOG)
