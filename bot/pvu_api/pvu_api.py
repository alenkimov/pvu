from typing import Any

import aiohttp
from eth_account.messages import encode_defunct
from eth_account.account import LocalAccount

from bot._web3 import w3
from bot.logger import logger
from .models import Land, Slot, Location, User, Reward
from .enums import ToolType
from .exceptions import PVUException


def handle_response_data(data: dict):
    status = data["status"]
    if status != 0:
        logger.debug(data)
        raise PVUException(status=status, msg=data["data"])
    return data["data"]


async def request_api(
        session: aiohttp.ClientSession,
        method: str,
        url: str,
        *,
        headers=None,
        params=None,
        payload=None
) -> Any:
    response = await session.request(method, url, headers=headers, params=params, json=payload)
    data = await response.json()
    return handle_response_data(data)


async def get_nonce_to_sign(session: aiohttp.ClientSession, address: str) -> int:
    url = "https://api.plantvsundead.com/users/login"
    querystring = {"publicAddress": address}
    data = await request_api(session, "GET", url, params=querystring)
    return data["nonce"]


async def get_auth_token(session: aiohttp.ClientSession, account: LocalAccount) -> str:
    nonce = await get_nonce_to_sign(session, account.address)
    message_text = f"PVU plantvsundead.com signing: {nonce}"
    message = encode_defunct(text=message_text)
    signed_message = w3.eth.account.sign_message(message, private_key=account.key)
    url = "https://api.plantvsundead.com/users/auth"
    payload = {
        "publicAddress": account.address,
        "signature": signed_message.signature.hex(),
    }
    data = await request_api(session, "POST", url, payload=payload)
    token = data["token"]
    return token


async def get_user_info(session: aiohttp.ClientSession, token: str) -> User:
    url = "https://api.plantvsundead.com/users/userInfo"
    headers = {"authorization": f"bearerHeaderey {token}"}
    data = await request_api(session, "GET", url, headers=headers)
    return User.from_pvu_user_data(data)


async def get_land(session: aiohttp.ClientSession, token: str) -> list[Land]:
    url = "https://api.plantvsundead.com/lands/my-assets/my-slots"
    headers = {"authorization": f"bearerHeaderey {token}"}
    data = await request_api(session, "GET", url, headers=headers)
    lands = []
    for land in data:
        location = Location(x=land["location"][0], y=land["location"][1])
        number_slots = land["numberSlots"]
        lands.append(Land(id=land["_id"], number_slots=number_slots, location=location))
    return lands


async def get_slots_by_location(
        session: aiohttp.ClientSession, token: str, location: Location
) -> list[Slot]:
    url = "https://api.plantvsundead.com/lands/get-by-coordinate"
    querystring = {"x": location.x, "y": location.y}
    headers = {"authorization": f"bearerHeader {token}"}
    data = await request_api(session, "GET", url, headers=headers, params=querystring)
    slots = []
    for slot_data in data[0]["slots"]:
        slots.append(Slot.from_pvu_slot_data(slot_data))
    return slots


async def get_slots(session: aiohttp.ClientSession, token: str) -> list[Slot]:
    lands = await get_land(session, token)
    slots = []
    for land in lands:
        slots.extend(await get_slots_by_location(session, token, land.location))
    return slots


async def buy_tools(
        session: aiohttp.ClientSession,
        token: str,
        tool_type: ToolType,
        quantity: int = 1,
):
    url = "https://api.plantvsundead.com/shops/buy-tools"
    payload = {
        "toolType": tool_type.value,
        "quantity": quantity,
    }
    headers = {"authorization": f"bearerHeader {token}"}
    await request_api(session, "POST", url, payload=payload, headers=headers)


async def buy_water(
        session: aiohttp.ClientSession,
        token: str,
        quantity: int = 1,
):
    await buy_tools(session, token, tool_type=ToolType.WATER, quantity=quantity)


async def buy_scarecrow(
        session: aiohttp.ClientSession,
        token: str,
        quantity: int = 1,
):
    await buy_tools(session, token, tool_type=ToolType.SCARECROW, quantity=quantity)


async def water_plant(
        session: aiohttp.ClientSession,
        token: str,
        slot_id: str,
) -> Reward:
    url = "https://api.plantvsundead.com/farms/water-plant"
    payload = {"slotId": slot_id}
    headers = {"authorization": f"bearerHeader {token}"}
    data = await request_api(session, "POST", url, payload=payload, headers=headers)
    return Reward.from_pvu_reward_data(data)


async def chase_crow(
        session: aiohttp.ClientSession,
        token: str,
        slot_id: str,
) -> Reward:
    url = "https://api.plantvsundead.com/farms/chase-crow"
    payload = {"slotId": slot_id}
    headers = {"authorization": f"bearerHeader {token}"}
    data = await request_api(session, "POST", url, payload=payload, headers=headers)
    return Reward.from_pvu_reward_data(data)


async def chase_good_crow(
        session: aiohttp.ClientSession,
        token: str,
        slot_id: str,
) -> Reward:
    url = "https://api.plantvsundead.com/farms/chase-good-crow"

    payload = {"slotId": slot_id}
    headers = {"authorization": f"bearerHeader {token}"}
    data = await request_api(session, "POST", url, payload=payload, headers=headers)
    return Reward.from_pvu_reward_data(data)


async def harvest_plants(
        session: aiohttp.ClientSession,
        token: str,
        slot_ids: list[str],
) -> Reward:
    url = "https://api.plantvsundead.com/farms/harvest-plant"
    payload = {"slotIds": slot_ids}
    headers = {"authorization": f"bearerHeader {token}"}
    data = await request_api(session, "POST", url, payload=payload, headers=headers)
    return Reward.from_pvu_reward_data(data)
