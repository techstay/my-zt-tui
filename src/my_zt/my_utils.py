from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar

import pendulum
import yaml
from httpx import AsyncClient
from pydantic import BaseModel


class MyZeroTierConfig(BaseModel):
    zerotier_token: str | None = None
    preferred_network_id: str | None = None


class MyZeroTierConfigManager:
    config_path: Path
    config: MyZeroTierConfig = MyZeroTierConfig()

    def __init__(self, config_path: Path = Path("~/.my-zt.yaml")):
        self.config_path = config_path.expanduser()
        self.load()

    def save(self):
        self._check()
        self.config_path.write_text(yaml.dump(self.config.model_dump()))

    def load(self):
        self._check()
        self.config = MyZeroTierConfig(
            **yaml.load(self.config_path.read_text(), Loader=yaml.Loader)
        )

    def _check(self):
        if not self.config_path.exists():
            self.config_path.touch()
            self.save()

    def _remove_config(self):
        self.config_path.unlink()


@dataclass
class ZeroTierNetwork:
    id: str
    name: str
    authorized_member_count: int
    createdDate: str
    description: str


@dataclass
class ZeroTierMember:
    id: str
    name: str
    description: str
    lastSeen: pendulum.DateTime
    physicalAddress: str
    clientVersion: str
    ip_assignments: list[str]


class MyZeroTier:
    base_url: ClassVar[str] = "https://api.zerotier.com/api/v1"

    def __init__(self):
        self.config_manager = MyZeroTierConfigManager()

    def load_config(self):
        self.config_manager.load()
        return self.config_manager.config

    def save_config(self, new_config: MyZeroTierConfig):
        self.config_manager.config = new_config
        self.config_manager.save()

    async def get_network_list(self) -> list[ZeroTierNetwork]:
        async with AsyncClient() as client:
            response = await client.get(
                f"{MyZeroTier.base_url}/network",
                headers={
                    "Authorization": f"token {self.config_manager.config.zerotier_token}"
                },
            )
            if response.status_code != 200:
                raise Exception(response.text)
            network_list: list[ZeroTierNetwork] = []
            for network in response.json():
                n = ZeroTierNetwork(
                    id=network["id"],
                    name=network["config"]["name"],
                    authorized_member_count=network["authorizedMemberCount"],
                    createdDate=pendulum.from_timestamp(
                        network["config"]["creationTime"] / 1000,
                        tz="local",
                    ).to_date_string(),
                    description=network["description"],
                )
                network_list.append(n)
            return network_list

    async def get_member_list(self, network_id: str) -> list[ZeroTierMember]:
        async with AsyncClient() as client:
            response = await client.get(
                f"{MyZeroTier.base_url}/network/{network_id}/member",
                headers={
                    "Authorization": f"token {self.config_manager.config.zerotier_token}"
                },
            )
            if response.status_code != 200:
                raise Exception(response.text)

            member_list: list[ZeroTierMember] = []
            for member in response.json():
                m = ZeroTierMember(
                    id=member["config"]["id"],
                    name=member["name"],
                    description=member["description"],
                    lastSeen=pendulum.from_timestamp(
                        member["lastSeen"] / 1000,
                        tz="local",
                    ),
                    physicalAddress=member["physicalAddress"],
                    clientVersion=member["clientVersion"],
                    ip_assignments=member["config"]["ipAssignments"],
                )
                member_list.append(m)
            return member_list
