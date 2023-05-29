from datetime import datetime, timezone

from pydantic import BaseModel


class Location(BaseModel):
    x: int
    y: int


class Land(BaseModel):
    location: Location

    id: str
    number_slots: int


class ActionInfo(BaseModel):
    is_have_crow: bool
    is_need_water: bool
    last_crow_time: int
    last_water_time: int
    total_crow_time: int
    total_water_time: int


class DecoEffects(BaseModel):
    is_good_crow: bool or None = None


class Slot(BaseModel):
    action_info: ActionInfo
    location: Location
    deco_effects: DecoEffects or None = None

    id: str
    land_id: str
    type: int
    status: int
    owner_id: str
    harvest_time: datetime or None = None

    @classmethod
    def from_pvu_slot_data(cls, slot_data: dict) -> "Slot":
        location = Location(x=slot_data["location"][0], y=slot_data["location"][1])
        action_info = ActionInfo(
            is_have_crow=slot_data["actionInfos"]["isHaveCrow"],
            is_need_water=slot_data["actionInfos"]["isNeedWater"],
            last_crow_time=slot_data["actionInfos"]["lastCrowTime"],
            last_water_time=slot_data["actionInfos"]["lastWaterTime"],
            total_crow_time=slot_data["actionInfos"]["totalCrowTime"],
            total_water_time=slot_data["actionInfos"]["totalWaterTime"],
        )
        slot = cls(
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
        return slot


class User(BaseModel):
    public_address: str
    le_amount: int
    chase_crow_tools: int
    watering_tools: int
    number_of_boxchain_tickets: int
    number_of_lottery_tickets: int
    number_of_seeds: int = 0

    @classmethod
    def from_pvu_user_data(cls, user_data: dict) -> "User":
        user = cls(
            chase_crow_tools=user_data["chaseCrowTools"],
            watering_tools=user_data["wateringTools"],
            le_amount=user_data["leAmount"],
            number_of_boxchain_tickets=user_data["numberOfBoxchainTickets"],
            number_of_lottery_tickets=user_data["numberOfLotteryTickets"],
            public_address=user_data["publicAddress"],
        )
        if "numberOfSeeds" in user_data:
            user.number_of_seeds = user_data["numberOfSeeds"]
        return user


class Reward(BaseModel):
    le: int = 0
    water: int = 0
    scarecrows: int = 0
    tickets: int = 0
    seeds: int = 0

    @classmethod
    def from_pvu_reward_data(cls, reward_data: list[dict]) -> "Reward":
        le = 0
        tickets = 0
        seeds = 0
        water = 0
        scarecrows = 0
        for reward_info in reward_data:
            if reward_info["name"] == "le":
                le += reward_info["amount"]
            elif reward_info["name"] == "seed":
                seeds += reward_info["amount"]
            elif reward_info["name"] == "ticket":
                tickets += reward_info["amount"]
            elif reward_info["name"] == "water":
                water += reward_info["amount"]
            elif reward_info["name"] == "chase_crow":
                scarecrows += reward_info["amount"]
        return cls(le=le, tickets=tickets, seeds=seeds, water=water, scarecrows=scarecrows)