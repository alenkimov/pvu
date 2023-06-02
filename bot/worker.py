from time import sleep
from datetime import datetime, timezone
import asyncio
from random import uniform, shuffle

import aiohttp

from eth_account import Account
from eth_account.signers.local import LocalAccount

from bot.pvu_api import get_auth_token, get_slots_by_location, get_land, get_user_info, harvest_plants
from bot.pvu_api import water_plant, chase_crow, chase_good_crow
from bot.pvu_api import buy_water, buy_scarecrow
from bot.pvu_api.exceptions import PVUException
from bot.paths import INPUT_DIR, PRIVATE_KEYS_TXT, TOKENS_TXT
from bot.logger import logger
from bot.config import SLEEP_TIME, PROCESS_ONLY_MY_PLANTS, PROCESS_DELAY


if not INPUT_DIR.exists():
    INPUT_DIR.mkdir(exist_ok=True)
    logger.info(f"Создал папку для входных данных {INPUT_DIR}")


for filepath in [PRIVATE_KEYS_TXT, TOKENS_TXT]:
    if not filepath.exists():
        with open(filepath, "w"):
            pass
        logger.info(f"Создал файл {filepath}")


async def work():
    # По умолчанию обрабатываются только растения, принадлежащие пользователю
    if PROCESS_ONLY_MY_PLANTS:
        logger.info(f"Обработка растений, принадлежащих пользователю")
    else:
        logger.info(f"Обработка всех растений, включая чужие")

    while True:
        tokens: set[str] = set()

        # Подгружаем приватные ключи
        with open(PRIVATE_KEYS_TXT, "r") as file:
            accounts: set[LocalAccount] = {Account.from_key(key.strip()) for key in file.readlines() if key != "\n"}

        # Подгружаем токены
        with open(TOKENS_TXT, "r") as file:
            for token in file.readlines():
                token = token.strip()
                if token == "\n":
                    continue
                if token.startswith("bearerHeader "):
                    token = token.split()[1]
                tokens.add(token)

        async with aiohttp.ClientSession() as session:
            # Запрашиваем токены по приватным ключам
            try:
                tokens.update({await get_auth_token(session, account) for account in accounts})
            except PVUException as e:
                logger.error(f" Не удалось запросить токены авторизации: {e.msg}")
            except Exception:
                logger.error(f"Не удалось запросить токены авторизации: неизвестная ошибка")
            if not tokens:
                logger.warning(
                    f"Для работы скрипта требуется хотя бы один токен авторизации или приватный ключ!"
                    f"\nКак получить токен авторизации: https://github.com/AlenKimov/pvu#о-токене-авторизации"
                    f"\nВнесите токены авторизации в файл {TOKENS_TXT}"
                    f"\nИли внесите приватные ключи в файл {PRIVATE_KEYS_TXT}"
                )
                break

            # Обрабатываем токены
            for token in tokens:
                # Получаем данные о землях пользователя
                try:
                    lands = await get_land(session, token)
                except PVUException as e:
                    logger.error(
                        f"[token={token[:4]}...{token[-4:]}]"
                        f" Не удалось получить данные о землях пользователя: {e}"
                    )
                    continue
                except Exception:
                    logger.error(
                        f"[token={token[:4]}...{token[-4:]}]"
                        f" Не удалось получить данные о землях пользователя: неизвестная ошибка"
                    )
                    continue

                for land in lands:
                    # Получаем актуальные данные о пользователе
                    try:
                        user = await get_user_info(session, token)
                    except:
                        logger.error(
                            f"[token={token[:4]}...{token[-4:]}]"
                            f" Не удалось получить данные о пользователе"
                        )
                        continue

                    # Получаем данные о слотах земли
                    try:
                        slots = await get_slots_by_location(session, token, land.location)
                    except PVUException as e:
                        logger.error(
                            f"[{user.public_address}]"
                            f" [land.x={land.location.x}, land.y={land.location.y}]"
                            f" Не удалось получить данные о слотах (растениях): {e}"
                        )
                        continue
                    except Exception:
                        logger.error(
                            f"[{user.public_address}]"
                            f" [land.x={land.location.x}, land.y={land.location.y}]"
                            f" Не удалось получить данные о слотах (растениях): неизвестная ошибка"
                        )
                        continue

                    # По умолчанию обрабатываются только растения, принадлежащие пользователю
                    if PROCESS_ONLY_MY_PLANTS:
                        slots = [slot for slot in slots if slot.owner_id == user.public_address]

                    # Подсчет количество ворон и требующих полива растений
                    crow_amount = len(list(filter(lambda slot: slot.action_info.is_have_crow, slots)))
                    need_water_amount = len(list(filter(lambda slot: slot.action_info.is_need_water, slots)))
                    if not (crow_amount and need_water_amount):
                        logger.info(
                            f"[{user.public_address}]"
                            f" [land.x={land.location.x}, land.y={land.location.y}]"
                            f" Обработка не требуется"
                        )
                    else:
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
                            try:
                                await buy_scarecrow(session, token, chase_crow_tools_to_buy)
                                logger.success(
                                    f"[{user.public_address}]"
                                    f" [land.x={land.location.x}, land.y={land.location.y}]"
                                    f" Приобретено пугалок: {chase_crow_tools_to_buy}"
                                )
                            except PVUException as e:
                                logger.error(
                                    f"[{user.public_address}]"
                                    f" [land.x={land.location.x}, land.y={land.location.y}]"
                                    f" Не удалось купить пугалки: {e.msg}"
                                )
                                continue
                            except Exception:
                                logger.error(
                                    f"[{user.public_address}]"
                                    f" [land.x={land.location.x}, land.y={land.location.y}]"
                                    f" Не удалось купить пугалки: неизвестная ошибка"
                                )
                                continue
                        if watering_tools_to_buy > 0:
                            try:
                                await buy_water(session, token, watering_tools_to_buy)
                                logger.success(
                                    f"[{user.public_address}]"
                                    f" [land.x={land.location.x}, land.y={land.location.y}]"
                                    f" Приобретено воды: {watering_tools_to_buy}"
                                )
                            except PVUException as e:
                                logger.error(
                                    f"[{user.public_address}]"
                                    f" [land.x={land.location.x}, land.y={land.location.y}]"
                                    f" Не удалось купить воду: {e.msg}"
                                )
                                continue
                            except Exception:
                                logger.error(
                                    f"[{user.public_address}]"
                                    f" [land.x={land.location.x}, land.y={land.location.y}]"
                                    f" Не удалось купить воду: неизвестная ошибка"
                                )
                                continue

                    # Перемешиваем слоты
                    shuffle(slots)

                    # Обработка слотов (растений)
                    # -- Прогон ворон
                    for slot in slots:
                        if slot.action_info.is_have_crow:
                            try:
                                await asyncio.sleep(uniform(*PROCESS_DELAY))
                                rewards = await chase_crow(session, token, slot.id)
                                logger.success(
                                    f"[{user.public_address}]"
                                    f" [land.x={land.location.x}, land.y={land.location.y}]"
                                    f" [slot.x={slot.location.x}, slot.y={slot.location.y}]"
                                    f" Ворона прогнана! Награды: {rewards}"
                                )
                            except PVUException as e:
                                logger.error(
                                    f"[{user.public_address}]"
                                    f" [land.x={land.location.x}, land.y={land.location.y}]"
                                    f" [slot.x={slot.location.x}, slot.y={slot.location.y}]"
                                    f" Не удалось прогнать ворону: {e.msg}"
                                )
                            except Exception:
                                logger.error(
                                    f"[{user.public_address}]"
                                    f" [land.x={land.location.x}, land.y={land.location.y}]"
                                    f" [slot.x={slot.location.x}, slot.y={slot.location.y}]"
                                    f" Не удалось прогнать ворону: неизвестная ошибка"
                                )
                    # -- Поливка
                    for slot in slots:
                        if slot.action_info.is_need_water:
                            try:
                                await asyncio.sleep(uniform(*PROCESS_DELAY))
                                rewards = await water_plant(session, token, slot.id)
                                logger.success(
                                    f"[{user.public_address}]"
                                    f" [land.x={land.location.x}, land.y={land.location.y}]"
                                    f" [slot.x={slot.location.x}, slot.y={slot.location.y}]"
                                    f" Растение полито! Награды: {rewards}"
                                )
                            except PVUException as e:
                                logger.error(
                                    f"[{user.public_address}]"
                                    f" [land.x={land.location.x}, land.y={land.location.y}]"
                                    f" [slot.x={slot.location.x}, slot.y={slot.location.y}]"
                                    f" Не удалось полить растение: {e.msg}"
                                )
                            except Exception:
                                logger.error(
                                    f"[{user.public_address}]"
                                    f" [land.x={land.location.x}, land.y={land.location.y}]"
                                    f" [slot.x={slot.location.x}, slot.y={slot.location.y}]"
                                    f" Не удалось полить растение: неизвестная ошибка"
                                )
                    # -- Прогон добрых ворон
                    for slot in slots:
                        if slot.deco_effects is not None:
                            if slot.deco_effects.is_good_crow is not None and slot.deco_effects.is_good_crow:
                                # Добрых ворон может отгонять только владелец растения
                                if slot.owner_id == user.public_address:
                                    try:
                                        await asyncio.sleep(uniform(*PROCESS_DELAY))
                                        rewards = await chase_good_crow(session, token, slot.id)
                                        logger.success(
                                            f"[{user.public_address}]"
                                            f" [land.x={land.location.x}, land.y={land.location.y}]"
                                            f" [slot.x={slot.location.x}, slot.y={slot.location.y}]"
                                            f" Добрая ворона прогнана! Награды: {rewards}"
                                        )
                                    except PVUException as e:
                                        logger.error(
                                            f"[{user.public_address}]"
                                            f" [land.x={land.location.x}, land.y={land.location.y}]"
                                            f" [slot.x={slot.location.x}, slot.y={slot.location.y}]"
                                            f" Не удалось прогнать ворону: {e.msg}"
                                        )
                                    except Exception:
                                        logger.error(
                                            f"[{user.public_address}]"
                                            f" [land.x={land.location.x}, land.y={land.location.y}]"
                                            f" [slot.x={slot.location.x}, slot.y={slot.location.y}]"
                                            f" Не удалось прогнать добрую ворону: неизвестная ошибка"
                                        )
                    # -- Сбор наград
                    for slot in slots:
                        now = datetime.utcnow().replace(tzinfo=timezone.utc)
                        if slot.harvest_time is not None and now > slot.harvest_time:
                            # Собирать награды можно только со своих растений
                            if slot.owner_id == user.public_address:
                                await asyncio.sleep(uniform(*PROCESS_DELAY))
                                try:
                                    rewards = await harvest_plants(session, token, (slot.id, ))
                                    logger.success(
                                        f"[{user.public_address}]"
                                        f" [land.x={land.location.x}, land.y={land.location.y}]"
                                        f" [slot.x={slot.location.x}, slot.y={slot.location.y}]"
                                        f" Награда собрана: {rewards}"
                                    )
                                except PVUException as e:
                                    logger.error(
                                        f"[{user.public_address}]"
                                        f" [land.x={land.location.x}, land.y={land.location.y}]"
                                        f" [slot.x={slot.location.x}, slot.y={slot.location.y}]"
                                        f" Не удалось собрать награду: {e.msg}"
                                    )
                                except Exception:
                                    logger.error(
                                        f"[{user.public_address}]"
                                        f" [land.x={land.location.x}, land.y={land.location.y}]"
                                        f" Не удалось собрать награду: неизвестная ошибка"
                                    )
                else:
                    logger.info(
                        f"[{user.public_address}]"
                        f" [land.x={land.location.x}, land.y={land.location.y}]"
                        f" Итого:"
                        f" le={user.le_amount}"
                        f" water={user.watering_tools}"
                        f" scarecrows={user.chase_crow_tools}"
                        f" tickets={user.number_of_lottery_tickets}"
                        f" seeds={user.number_of_seeds}"
                    )

        logger.info(f"Сплю {SLEEP_TIME} секунд :)")
        sleep(SLEEP_TIME)
