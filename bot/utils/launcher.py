import asyncio
import argparse
import json
import os
from pyrogram import Client

from bot.config import settings
from bot.utils import logger
from bot.core.tapper import run_tapper
from bot.core.query import run_query_tapper
from bot.core.registrator import register_sessions
from bot.utils.scripts import get_session_names, get_proxies, get_user_agent, get_proxy, fetch_username

options = """
Select an action:

    1. Run clicker (Session)
    2. Create session
    3. Run clicker (Query)
"""


global tg_clients

async def get_tg_clients() -> list[Client]:
    global tg_clients

    session_names = get_session_names()

    if not session_names:
        raise FileNotFoundError("Not found session files")

    if not settings.API_ID or not settings.API_HASH:
        raise ValueError("API_ID and API_HASH not found in the .env file.")

    tg_clients = [
        Client(
            name=session_name,
            api_id=settings.API_ID,
            api_hash=settings.API_HASH,
            workdir="sessions/",
            plugins=dict(root="bot/plugins"),
        )
        for session_name in session_names
    ]

    return tg_clients

def get_chq_chr(user_name):
    with open("profiles.json", "r") as f:
        data = json.load(f)

    if user_name not in list(data.keys()):
        logger.info(f"Created new profile for {user_name} in profiles.json, follow tutorial to edit it!")
        data.update({user_name: {
                "chq": "",
                "chr": 1
            }
        })
        with open("profiles.json", "w") as f:
            json.dump(data, f, indent=4)

        return "", 1
    else:
        return data[user_name]['chq'], data[user_name]['chr']


async def process() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("-a", "--action", type=int, help="Action to perform")

    logger.info(f"Detected {len(get_session_names())} sessions | {len(get_proxies())} proxies")

    action = parser.parse_args().action

    if not os.path.exists("user_agents.json"):
        with open("user_agents.json", 'w') as file:
            file.write("{}")
        logger.info("User agents file created successfully")

    if not action:
        print(options)

        while True:
            action = input("> ")

            if not action.isdigit():
                logger.warning("Action must be number")
            elif action not in ["1", "2", "3"]:
                logger.warning("Action must be 1, 2 or 3")
            else:
                action = int(action)
                break

    if action == 1:
        tg_clients = await get_tg_clients()

        await run_tasks(tg_clients=tg_clients)
    elif action == 2:
        await register_sessions()
    elif action == 3:
        with open("data.txt", "r") as f:
                query_ids = [line.strip() for line in f.readlines()]
        await run_tasks_query(query_ids)

async def run_tasks_query(query_ids: list[str]):
    lock = asyncio.Lock()
    wait = True if len(query_ids) > 3 else False
    accounts_gap = {}
    for query in query_ids:
        chq, chr = get_chq_chr(fetch_username(query))
        if chq == "":
            query_ids.remove(query)
        else:
            accounts_gap.update({fetch_username(query): {
                "chq": chq,
                "chr": chr
            }})

    tasks = [
        asyncio.create_task(
            run_query_tapper(
                query=query,
                proxy=await get_proxy(fetch_username(query)),
                lock=lock,
                ua=await get_user_agent(fetch_username(query)),
                wait=wait,
                account_gap=accounts_gap.get(fetch_username(query))
            )
        )
        for query in query_ids
    ]

    await asyncio.gather(*tasks)

async def run_tasks(tg_clients: list[Client]):
    lock = asyncio.Lock()
    wait = True if len(tg_clients) > 3 else False

    accounts_gap = {}

    for tg_client in tg_clients:
        chq, chr = get_chq_chr(tg_client.name)
        if chq == "":
            tg_clients.remove(tg_client)
        else:
            accounts_gap.update({tg_client.name: {
                "chq": chq,
                "chr": chr
            }})


    tasks = [
        asyncio.create_task(
            run_tapper(
                tg_client=tg_client,
                proxy=await get_proxy(tg_client.name),
                lock=lock,
                ua=await get_user_agent(tg_client.name),
                wait=wait,
                account_gap=accounts_gap.get(tg_client.name)
            )
        )
        for tg_client in tg_clients
    ]

    await asyncio.gather(*tasks)
