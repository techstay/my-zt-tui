import pendulum
from textual import work
from textual.app import App
from textual.containers import Container, Vertical
from textual.screen import Screen
from textual.timer import Timer
from textual.widgets import (
    DataTable,
    Footer,
    Header,
    Input,
    Label,
    TextArea,
)

from my_zt.my_utils import MyZeroTier


class DashboardScreen(Screen):
    timer: Timer

    def compose(self):

        yield Header(
            icon="🎨",
            show_clock=True,
        )

        network_table = DataTable(id="network_property")
        member_table = DataTable(id="member_list")
        yield Container(network_table)
        yield Container(member_table)

        yield Footer()

    async def on_mount(self):
        self.update_network()
        network_table = self.query_one("#network_property", DataTable)
        member_table = self.query_one("#member_list", DataTable)
        network_table.add_columns("Network Property", "Network Information")
        member_table.add_columns(
            "Id",
            "Name",
            "IP Assignments",
            "Last Seen",
            "Client Version",
            "Physical Address",
        )
        self.timer = self.set_interval(10, self.update_network)

    @work(exclusive=True)
    async def update_network(self):
        zt: MyZeroTier = self.app.zt  # type: ignore
        config = zt.load_config()
        if not config.zerotier_token:
            self.log.info("No ZeroTier token configured")
            return

        networks = await zt.get_network_list()
        if not config.preferred_network_id:
            self.log.info("No preferred network configured")
            if len(networks) == 0:
                return
            config.preferred_network_id = networks[0].id
            zt.save_config(config)

        if config.preferred_network_id not in [n.id for n in networks]:
            self.log.error(f"Preferred network {config.preferred_network_id} not found")
            return

        preferred_network = [
            n for n in networks if n.id == config.preferred_network_id
        ][0]

        network_table = self.query_one("#network_property", DataTable)
        network_table.clear()
        network_table.add_rows(
            rows=[
                ("Network Id", preferred_network.id),
                ("Network Name", preferred_network.name),
                ("Description", preferred_network.description),
                ("Members Count", preferred_network.authorized_member_count),
                ("Created Date", preferred_network.createdDate),
            ]
        )
        member_table = self.query_one("#member_list", DataTable)
        member_table.clear()
        for member in await zt.get_member_list(config.preferred_network_id):
            member_table.add_row(
                member.id,
                member.name,
                ", ".join(member.ip_assignments),
                member.lastSeen.diff_for_humans(pendulum.now()),
                member.clientVersion,
                member.physicalAddress,
            )


class SettingsScreen(Screen):
    """Settings screen for configuring ZeroTier token and update interval."""

    def compose(self):
        """Compose the settings screen with configuration options."""
        yield Header(
            icon="⚙️",
            show_clock=True,
        )

        yield Container(
            Vertical(
                Label("ZeroTier Token:"),
                Input(
                    id="token",
                    placeholder="Enter your ZeroTier API token here",
                ),
            )
        )
        yield Container(
            TextArea(
                "Press Esc to return. Press Enter to save config and return.",
                read_only=True,
            )
        )
        yield Footer()

    def on_mount(self) -> None:
        zt: MyZeroTier = self.app.zt  # type: ignore
        config = zt.load_config()
        input = self.query_one("#token", Input)
        if config.zerotier_token:
            input.value = config.zerotier_token

    def key_escape(self):
        self.app.switch_mode("dashboard")

    def key_enter(self):
        input = self.query_one("#token", Input)
        zt: MyZeroTier = self.app.zt  # type: ignore
        try:
            config = zt.load_config()
            config.zerotier_token = input.value
            zt.save_config(config)
            self.log.info("ZeroTier token updated successfully.")
            self.notify(
                "ZeroTier token updated successfully.",
                severity="information",
            )
            self.app.switch_mode("dashboard")

        except Exception as e:
            self.log.error(f"Error updating ZeroTier token: {repr(e)}")
            self.notify(
                title="Error updating ZeroTier token: ",
                message=repr(e),
                severity="error",
            )


class AboutScreen(Screen):
    def compose(self):
        yield Header(
            icon="ℹ️",
            show_clock=True,
        )
        yield TextArea(
            """ \
# My ZeroTier App - ZeroTier Network Management Tool

This is a simple terminal-based application that allows you to view your ZeroTier networks and online members.

""",
            id="about_content",
            language="markdown",
            read_only=True,
        )
        yield Footer()


class MyZeroTierApp(App):
    CSS_PATH = "./css/ui.css"

    zt: MyZeroTier

    BINDINGS = [
        ("d", "switch_mode('dashboard')", "Dashboard"),
        ("s", "switch_mode('settings')", "Settings"),
        ("a", "switch_mode('about')", "About"),
        ("q", "quit", "Quit"),
    ]

    MODES = {
        "dashboard": DashboardScreen,
        "settings": SettingsScreen,
        "about": AboutScreen,
    }

    def __init__(self):
        super().__init__()
        self.zt = MyZeroTier()

    async def on_mount(self) -> None:
        self.title = "My ZeroTier TUI"
        self.sub_title = "show my zerotier clients"
        self.switch_mode("dashboard")
