from time import sleep
from datetime import datetime, timezone

import aiohttp

from eth_account import Account
from eth_account.signers.local import LocalAccount

from bot.pvu_api import get_auth_token, get_slots_by_location, get_land, get_user_info, harvest_plants
from bot.pvu_api import water_plant, chase_crow, chase_good_crow
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
            try:
                tokens.update({await get_auth_token(session, account) for account in accounts})
            except:
                logger.error(f"Не удалось запросить токены авторизации")
            for token in tokens:
                try:
                    # Получаем данные о пользователе
                    user = await get_user_info(session, token)
                    logger.info(
                        f"[{user.public_address}]"
                        f" LE={user.le_amount}"
                        f", water={user.watering_tools}"
                        f", scarecrows={user.chase_crow_tools}"
                    )

                    # По умолчанию обрабатываются только растения, принадлежащие пользователю
                    if PROCESS_ONLY_MY_PLANTS:
                        logger.info(
                            f"[{user.public_address}]"
                            f" Обработка растений, принадлежащих пользователю"
                        )
                    else:
                        logger.info(
                            f"[{user.public_address}]"
                            f" Обработка всех растений, включая чужие"
                        )

                    # Получаем данные о землях пользователя
                    lands = await get_land(session, token)
                    for land in lands:
                        # Получаем данные о слотах земли
                        slots = await get_slots_by_location(session, token, land.location)

                        # По умолчанию обрабатываются только растения, принадлежащие пользователю
                        if PROCESS_ONLY_MY_PLANTS:
                            slots = [slot for slot in slots if slot.owner_id == user.public_address]

                        # Подсчет количество ворон и требующих полива растений
                        crow_amount = len(list(filter(lambda slot: slot.action_info.is_have_crow, slots)))
                        need_water_amount = len(list(filter(lambda slot: slot.action_info.is_need_water, slots)))
                        logger.info(
                            f"[{user.public_address}]"
                            f" [land.x={land.location.x}, land.y={land.location.y}]"
                            f" Ворон: {crow_amount}"
                            f", требуют воды: {need_water_amount}"
                        )

                        # Подсчет количества инструментов к покупке
                        chase_crow_tools_to_buy = max(crow_amount - user.chase_crow_tools, 0)
                        watering_tools_to_buy = max(need_water_amount - user.watering_tools, 0)

                        # Проверка на то, хватает ли LE на аккаунте для покупки инструментов
                        if (user.le_amount - (chase_crow_tools_to_buy + watering_tools_to_buy) * 10) < 0:
                            logger.warning(f"[{user.public_address}] Не хватает LE для покупки инструментов!")
                        else:
                            # Покупка инструментов: пугалок и воды
                            if chase_crow_tools_to_buy > 0:
                                await buy_scarecrow(session, token, chase_crow_tools_to_buy)
                                logger.success(
                                    f"[{user.public_address}]"
                                    f" Приобретено пугалок: {chase_crow_tools_to_buy}"
                                )
                            if watering_tools_to_buy > 0:
                                await buy_water(session, token, watering_tools_to_buy)
                                logger.success(
                                    f"[{user.public_address}]"
                                    f" Приобретено воды: {watering_tools_to_buy}"
                                )

                            # Обработка слотов (растений)
                            for slot in slots:
                                if slot.action_info.is_have_crow:
                                    await chase_crow(session, token, slot.id)
                                    logger.success(
                                        f"[{user.public_address}]"
                                        f" [land.x={land.location.x}, land.y={land.location.y}]"
                                        f" [slot.x={slot.location.x}, slot.y={slot.location.y}]"
                                        f" Ворона прогнана!"
                                    )
                                if slot.action_info.is_need_water:
                                    await water_plant(session, token, slot.id)
                                    logger.success(
                                        f"[{user.public_address}]"
                                        f" [land.x={land.location.x}, land.y={land.location.y}]"
                                        f" [slot.x={slot.location.x}, slot.y={slot.location.y}]"
                                        f" Растение полито!"
                                    )
                                if slot.deco_effects is not None:
                                    if slot.deco_effects.is_good_crow is not None and slot.deco_effects.is_good_crow:
                                        await chase_good_crow(session, token, slot.id)
                                        logger.success(
                                            f"[{user.public_address}]"
                                            f" [land.x={land.location.x}, land.y={land.location.y}]"
                                            f" [slot.x={slot.location.x}, slot.y={slot.location.y}]"
                                            f" Добрая ворона прогнана!"
                                        )

                        # Сбор наград
                        now = datetime.utcnow().replace(tzinfo=timezone.utc)
                        slots_to_harvest = []
                        for slot in slots:
                            if slot.harvest_time is not None and now > slot.harvest_time:
                                slots_to_harvest.append(slot)
                        if slots_to_harvest:
                            slot_ids_to_harvest = [slot.id for slot in slots_to_harvest]
                            await harvest_plants(session, token, slot_ids_to_harvest)
                            for slot in slots_to_harvest:
                                logger.success(
                                    f"[{user.public_address}]"
                                    f" [land.x={land.location.x}, land.y={land.location.y}]"
                                    f" [slot.x={slot.location.x}, slot.y={slot.location.y}]"
                                    f" Награда собрана!"
                                )
                except Exception as e:
                    logger.error(f"[{token}] Ну удалось обработать аккаунт")
                    logger.exception(e)
        logger.info(f"Сплю {DELAY} секунд :)")
        sleep(DELAY)
