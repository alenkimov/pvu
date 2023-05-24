from datetime import datetime, timezone

import aiohttp
from eth_account.messages import encode_defunct
from eth_account.account import LocalAccount

from bot._web3 import w3
from .models import Land, Slot, Location, ActionInfo, User, DecoEffects
from .enums import ToolType


async def get_nonce_to_sign(session: aiohttp.ClientSession, address: str) -> int:
    url = "https://api.plantvsundead.com/users/login"
    querystring = {"publicAddress": address}
    response = await session.request("GET", url, params=querystring)
    data = await response.json()
    nonce = data["data"]["nonce"]
    return nonce


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
    response = await session.request("POST", url, json=payload)
    data = await response.json()
    token = data["data"]["token"]
    return token


async def get_user_info(session: aiohttp.ClientSession, token: str) -> User:
    url = "https://api.plantvsundead.com/users/userInfo"
    headers = {"authorization": f"bearerHeaderey {token}"}
    response = await session.request("GET", url, headers=headers)
    data = await response.json()
    data = data["data"]
    user = User(
        chase_crow_tools=data["chaseCrowTools"],
        watering_tools=data["wateringTools"],
        le_amount=data["leAmount"],
        number_of_boxchain_tickets=data["numberOfBoxchainTickets"],
        number_of_lottery_tickets=data["numberOfLotteryTickets"],
        public_address=data["publicAddress"],
    )
    return user


async def get_land(session: aiohttp.ClientSession, token: str) -> list[Land]:
    url = "https://api.plantvsundead.com/lands/my-assets/my-slots"
    headers = {"authorization": f"bearerHeaderey {token}"}
    response = await session.request("GET", url, headers=headers)
    data = await response.json()
    lands = []
    for land in data["data"]:
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
    response = await session.request("GET", url, headers=headers, params=querystring)
    data = await response.json()
    slots = []
    for slot_data in data["data"][0]["slots"]:
        location = Location(x=slot_data["location"][0], y=slot_data["location"][1])
        action_info = ActionInfo(
            is_have_crow=slot_data["actionInfos"]["isHaveCrow"],
            is_need_water=slot_data["actionInfos"]["isNeedWater"],
            last_crow_time=slot_data["actionInfos"]["lastCrowTime"],
            last_water_time=slot_data["actionInfos"]["lastWaterTime"],
            total_crow_time=slot_data["actionInfos"]["totalCrowTime"],
            total_water_time=slot_data["actionInfos"]["totalWaterTime"],
        )
        slot = Slot(
            location=location,
            action_info=action_info,
            id=slot_data["_id"],
            land_id=slot_data["landId"],
            type=slot_data["type"],
            status=slot_data["status"],
            owner_id=slot_data["ownerId"],
        )
        if "harvestTime" in slot_data:
            slot.harvest_time = datetime.fromtimestamp(slot_data["harvestTime"] // 1000, timezone.utc)
        if "decoEffects" in slot_data:
            slot.deco_effects = DecoEffects()
            if "isGoodCrow" in slot_data["decoEffects"]:
                slot.deco_effects.is_good_crow = slot_data["decoEffects"]["isGoodCrow"]
        slots.append(slot)
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
    await session.request("POST", url, json=payload, headers=headers)


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
):
    url = "https://api.plantvsundead.com/farms/water-plant"
    payload = {"slotId": slot_id}
    headers = {"authorization": f"bearerHeader {token}"}
    response = await session.request("POST", url, json=payload, headers=headers)
    # data = await response.json()
    # le = sum([_data["amount"] for _data in data["data"]])
    # return le


async def chase_crow(
        session: aiohttp.ClientSession,
        token: str,
        slot_id: str,
):
    url = "https://api.plantvsundead.com/farms/chase-crow"
    payload = {"slotId": slot_id}
    headers = {"authorization": f"bearerHeader {token}"}
    response = await session.request("POST", url, json=payload, headers=headers)
    # data = await response.json()
    # le = sum([_data["amount"] for _data in data["data"]])
    # return le


async def chase_good_crow(
        session: aiohttp.ClientSession,
        token: str,
        slot_id: str,
):
    url = "https://api.plantvsundead.com/farms/chase-good-crow"

    payload = {"slotId": slot_id}
    headers = {"authorization": f"bearerHeader {token}"}
    response = await session.request("POST", url, json=payload, headers=headers)


async def harvest_plants(
        session: aiohttp.ClientSession,
        token: str,
        slot_ids: list[str],
):
    url = "https://api.plantvsundead.com/farms/harvest-plant"
    payload = {"slotIds": slot_ids}
    headers = {"authorization": f"bearerHeader {token}"}
    response = await session.request("POST", url, json=payload, headers=headers)
