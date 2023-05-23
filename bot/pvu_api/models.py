from datetime import datetime

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


class Slot(BaseModel):
    action_info: ActionInfo
    location: Location

    id: str
    land_id: str
    type: int
    status: int
    owner_id: str
    harvest_time: datetime or None = None


class User(BaseModel):
    chase_crow_tools: int
    watering_tools: int
    le_amount: int
    number_of_boxchain_tickets: int
    number_of_lottery_tickets: int
    public_address: str
