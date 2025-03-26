import os
from pathlib import Path

import rich
from dotenv import load_dotenv

from my_zt.my_utils import MyZeroTier, MyZeroTierConfigManager

load_dotenv()


def test_my_zerotier_config(tmp_path: Path):
    test_config_path = tmp_path / "my-zt.yaml"
    config_manager = MyZeroTierConfigManager(test_config_path)
    assert config_manager.config.zerotier_token is None

    config_manager.config.zerotier_token = "test"
    config_manager.config.preferred_network_id = "123"
    config_manager.save()
    config_manager.load()
    assert config_manager.config.zerotier_token == "test"
    assert config_manager.config.preferred_network_id == "123"

    config_manager2 = MyZeroTierConfigManager(test_config_path)
    assert config_manager2.config.zerotier_token == "test"
    assert config_manager2.config.preferred_network_id == "123"
    config_manager2._remove_config()
    assert config_manager2.config_path.exists() is False


async def test_my_zerotier_class():
    my_zt = MyZeroTier()
    config = my_zt.load_config()
    config.zerotier_token = os.getenv("ZT_TOKEN") or ""
    my_zt.save_config(config)
    networks = await my_zt.get_network_list()
    print()
    rich.print(networks)

    for n in networks:
        m = await my_zt.get_member_list(n.id)
        rich.print(m)
