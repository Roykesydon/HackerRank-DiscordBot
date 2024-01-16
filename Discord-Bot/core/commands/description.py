import discord
from core.config import LANG_DATA
from core.validator import Validator
from discord import app_commands
from discord.ext import commands


class DescriptionCommand(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="description",
        description=LANG_DATA["commands"]["description"]["description"],
    )
    async def show_description(self, interaction):
        if not Validator.in_dm_or_enabled_channel(interaction.channel):
            await interaction.response.send_message(
                f"{LANG_DATA['permission']['dm-or-enabled-channel-only']}"
            )
            return

        async with interaction.channel.typing():
            logo = discord.File("./assets/logo.png")
            description = LANG_DATA["description"]

            await interaction.response.send_message(description, file=logo)


async def setup(bot):
    await bot.add_cog(DescriptionCommand(bot))
