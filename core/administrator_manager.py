import discord

from core.discord_api import DiscordAPI
from core.utils.config import CONFIG, update_config
from core.utils.text_manager import TextManager


class AdministratorManager:
    def __init__(self):
        self.admin_id_list = CONFIG["admin_user_id_list"]
        self.channel_admin_panel_index_dict = {}

        self.text_manager = TextManager()
        self.discord_api = DiscordAPI()

        self.global_name_cache = {}

    def get_admin_id_list(self):
        return self.admin_id_list

    def get_admin_length(self):
        return len(self.admin_id_list)

    def init_index(self, channel_id):
        self.channel_admin_panel_index_dict[channel_id] = 0

    def update_index(self, channel_id, step):
        if channel_id not in self.channel_admin_panel_index_dict:
            self.channel_admin_panel_index_dict[channel_id] = 0

        self.channel_admin_panel_index_dict[channel_id] += step
        self.channel_admin_panel_index_dict[channel_id] = max(
            0, self.channel_admin_panel_index_dict[channel_id]
        )

        self.channel_admin_panel_index_dict[channel_id] = min(
            self.channel_admin_panel_index_dict[channel_id],
            self.get_admin_length() - 1,
        )

    def get_current_admin(self, channel_id: str):
        current_admin_id = self.admin_id_list[
            self.channel_admin_panel_index_dict[channel_id]
        ]
        # check cache
        if current_admin_id in self.global_name_cache:
            return (
                current_admin_id,
                self.global_name_cache[current_admin_id],
            )

        user_info = self.discord_api.get_user_info(
            self.admin_id_list[self.channel_admin_panel_index_dict[channel_id]]
        )
        global_name = user_info["global_name"]
        self.global_name_cache[current_admin_id] = global_name
        return (
            self.admin_id_list[self.channel_admin_panel_index_dict[channel_id]],
            global_name,
        )

    def get_admin_embed(self, channel_id: str):
        LANG_DATA = self.text_manager.get_selected_language(str(channel_id))

        user_info = self.discord_api.get_user_info(
            self.admin_id_list[self.channel_admin_panel_index_dict[channel_id]]
        )

        if user_info["banner_color"] is None:
            color_int = int("5865F2", 16)
        else:
            color_int = int(user_info["banner_color"].replace("#", ""), 16)

        embed = discord.Embed(
            title=f"{LANG_DATA['commands']['administrator']['administrator']}\
                {self.channel_admin_panel_index_dict[channel_id] + 1}/{self.get_admin_length()}",
            description="",
            colour=color_int,
        )

        embed.add_field(
            name=user_info["global_name"], value=user_info["username"], inline=False
        )
        user_avatar_url = self.discord_api.get_user_avatar(
            str(user_info["id"]), str(user_info["avatar"])
        )
        embed.set_thumbnail(url=user_avatar_url)
        return embed

    def remove_admin(self, channel_id: str):
        current_admin_id = self.admin_id_list[
            self.channel_admin_panel_index_dict[channel_id]
        ]
        self.admin_id_list.remove(current_admin_id)
        CONFIG["admin_user_id_list"] = self.admin_id_list
        update_config()

    def add_admin(self, user_id: str):
        self.admin_id_list.append(user_id)
        CONFIG["admin_user_id_list"] = self.admin_id_list
        update_config()
