from time import sleep
from datetime import datetime, timezone

import aiohttp

from eth_account import Account
from eth_account.signers.local import LocalAccount

from bot.pvu_api import get_auth_token, get_slots, get_user_info, harvest_plants
from bot.pvu_api import water_plant, chase_crow
from bot.pvu_api import buy_water, buy_scarecrow
from bot.paths import PRIVATE_KEYS_TXT, TOKENS_TXT
from bot.logger import logger
from bot.config import DELAY, PROCESS_ONLY_MY_PLANTS


for filepath in [PRIVATE_KEYS_TXT, TOKENS_TXT]:
    if not filepath.exists():
        with open(filepath, "w"):
            pass


async def work():
    while True:
        with open(PRIVATE_KEYS_TXT, "r") as file:
            accounts: set[LocalAccount] = {Account.from_key(key.strip()) for key in file.readlines() if key != "\n"}
        tokens: set[str] = set()
        with open(TOKENS_TXT, "r") as file:
            for token in file.readlines():
                token = token.strip()
                if token == "\n":
                    continue
                if token.startswith("bearerHeader "):
                    token = token.split()[1]
                tokens.add(token)
        async with aiohttp.ClientSession() as session:
            tokens.update({await get_auth_token(session, account) for account in accounts})
            for token in tokens:
                user = await get_user_info(session, token)
                logger.info(
                    f"[{user.public_address}]"
                    f" LE={user.le_amount}"
                    f" water={user.watering_tools}"
                    f" scarecrows={user.chase_crow_tools}"
                )

                slots = await get_slots(session, token)

                if PROCESS_ONLY_MY_PLANTS:
                    slots = [slot for slot in slots if slot.owner_id == user.public_address]

                crow_amount = len(list(filter(lambda slot: slot.action_info.is_have_crow, slots)))
                need_water_amount = len(list(filter(lambda slot: slot.action_info.is_need_water, slots)))

                chase_crow_tools_to_buy = max(crow_amount - user.chase_crow_tools, 0)
                watering_tools_to_buy = max(need_water_amount - user.watering_tools, 0)

                if (user.le_amount - (chase_crow_tools_to_buy + watering_tools_to_buy) * 10) < 0:
                    logger.warning(f"[{user.public_address}] Not enough LE to buy tools!")
                else:
                    if chase_crow_tools_to_buy > 0:
                        await buy_scarecrow(session, token, chase_crow_tools_to_buy)
                        logger.success(f"[{user.public_address}] Bought {chase_crow_tools_to_buy} chase crow tools!")
                    if watering_tools_to_buy > 0:
                        await buy_water(session, token, watering_tools_to_buy)
                        logger.success(f"[{user.public_address}] Bought {watering_tools_to_buy} watering tools!")
                    for slot in slots:
                        if slot.action_info.is_have_crow:
                            await chase_crow(session, token, slot.id)
                            logger.success(
                                f"[{user.public_address}] [{slot.location.x}, {slot.location.y}] chased!"
                            )
                        if slot.action_info.is_need_water:
                            await water_plant(session, token, slot.id)
                            logger.success(
                                f"[{user.public_address}] [{slot.location.x}, {slot.location.y}] watered!"
                            )
                    now = datetime.utcnow().replace(tzinfo=timezone.utc)
                    slot_ids_to_harvest = []
                    for slot in slots:
                        if slot.harvest_time is not None and now > slot.harvest_time:
                            slot_ids_to_harvest.append(slot.id)
                    await harvest_plants(session, token, slot_ids_to_harvest)

        logger.info(f"Sleep {DELAY} secs :)")
        sleep(DELAY)
