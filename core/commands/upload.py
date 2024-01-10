import time

import discord
import requests
from discord import SelectOption, app_commands, ui
from discord.ext import commands

from core.config import CONFIG
from core.database import mongo_database
from core.text_manager import TextManager
from core.validator import Validator


class UploadFileCommand(commands.Cog):
    AVAILABLE_FILE_TYPE_DICT = {
        "text/plain": "txt",
        "application/pdf": "pdf",
    }

    def __init__(self, bot):
        self.bot = bot

    def check_file_format(self, file_type) -> bool:
        return file_type in UploadFileCommand.AVAILABLE_FILE_TYPE_DICT

    @app_commands.command(
        name="upload",
        description=TextManager.DEFAULT_LANG_DATA["commands"]["upload"]["description"],
    )
    @app_commands.choices(
        file_scope=[
            app_commands.Choice(name="共享文件", value="shared"),
            app_commands.Choice(name="私人使用", value="private"),
        ]
    )
    async def upload_document(
        self,
        interaction,
        file_scope: str,
        custom_file_name: str,
        attachment: discord.Attachment,
    ):
        text_manager = TextManager()
        LANG_DATA = text_manager.get_selected_language(str(interaction.channel_id))

        if not Validator.in_dm_or_enabled_channel(interaction.channel):
            await interaction.response.send_message(
                f"{LANG_DATA['permission']['dm-or-enabled-channel-only']}"
            )
            return

        async with interaction.channel.typing():
            """
            TODO: check document type, size
            """
            response = requests.get(attachment.url)

            """
            Check file format
            """
            if not self.check_file_format(attachment.content_type):
                return await interaction.response.send_message(
                    LANG_DATA["commands"]["upload"]["invalid-file-type"]
                )

            file_name = attachment.filename
            insert_data = {
                "file_name": file_name,
                "custom_file_name": custom_file_name
                if custom_file_name != ""
                else file_name,
                "file_type": attachment.content_type,
                "file_url": attachment.url,
                "file_time": int(time.time()),
                "file_scope": file_scope,
                "user_id": str(interaction.user.id),
            }
            mongo_database["UserUploadFile"].insert_one(insert_data)

            # get document id from mongo as file name
            # save file to local storage
            file = mongo_database["UserUploadFile"].find_one(insert_data)
            if file is not None:
                file_name = str(file["_id"])

            if attachment.content_type is not None:
                with open(
                    f"{CONFIG['storage_path']}/{file_name}.{UploadFileCommand.AVAILABLE_FILE_TYPE_DICT[attachment.content_type]}",
                    "wb",
                ) as file:
                    file.write(response.content)

        return await interaction.response.send_message(
            LANG_DATA["commands"]["upload"]["success"]
        )

    def cog_check(self, ctx):
        # check if the command is used in a channel that is enabled or in a DM
        return not isinstance(ctx.channel, discord.DMChannel)


async def setup(bot):
    await bot.add_cog(UploadFileCommand(bot))
