import discord
from discord.ext import commands
from discord import app_commands, ui
from mutagen import File
from typing import Dict


class NowPlaying(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    def get_file_metadata(self, filepath: str) -> Dict[str, str]:
        try:
            audio = File(filepath)
            if audio is None:
                return {"title": "unknown", "artist": "unknown", "album": "unknown"}

            title = "unknown"
            artist = "unknown"
            album = "unknown"

            if audio.tags:
                if "title" in audio.tags:
                    title = str(audio.tags["title"][0])
                elif "TIT2" in audio.tags:
                    title = str(audio.tags["TIT2"])

                if "artist" in audio.tags:
                    artist = str(audio.tags["artist"][0])
                elif "TPE1" in audio.tags:
                    artist = str(audio.tags["TPE1"])

                if "album" in audio.tags:
                    album = str(audio.tags["album"][0])
                elif "TALB" in audio.tags:
                    album = str(audio.tags["TALB"])

            return {"title": title, "artist": artist, "album": album}
        except Exception as e:
            print(f"error reading metadata: {e}")
            return {"title": "unknown", "artist": "unknown", "album": "unknown"}

    @app_commands.command(name="info", description="show info about current song")
    async def info(self, interaction: discord.Interaction) -> None:
        if interaction.guild is None:
            await interaction.response.send_message("only works in servers")
            return

        queue_cog = self.bot.get_cog("Queue")
        if queue_cog is None:
            await interaction.response.send_message("queue system not loaded")
            return

        guild_id = interaction.guild.id
        current = queue_cog.current.get(guild_id)

        if current is None:
            await interaction.response.send_message("nothing playing right now")
            return

        metadata = current.metadata

        class InfoLayout(ui.LayoutView):
            container = ui.Container(
                ui.Section(
                    ui.TextDisplay("## now playing"),
                ),
                ui.Separator(spacing=ui.SeparatorSpacing.small, dividing_line=True),
                accent_color=0x5865F2,
            )

        layout = InfoLayout()

        if current.is_youtube:
            title = metadata.get("title", "unknown")
            uploader = metadata.get("uploader", "unknown")

            duration_str = "unknown"
            duration = metadata.get("duration", "0")
            try:
                dur_seconds = int(float(duration))
                minutes = dur_seconds // 60
                seconds = dur_seconds % 60
                duration_str = f"{minutes}:{seconds:02d}"
            except Exception:
                pass

            layout.container.add_item(
                ui.Section(
                    ui.TextDisplay(
                        f"**{title}**\n{uploader}\n\nduration: {duration_str}\nsource: youtube"
                    ),
                )
            )

            thumbnail = metadata.get("thumbnail", "")
            if thumbnail:
                try:
                    layout.container.add_item(
                        ui.MediaGallery(ui.MediaGalleryItem(thumbnail))
                    )
                except Exception:
                    pass
        else:
            file_meta = self.get_file_metadata(current.filepath)
            layout.container.add_item(
                ui.Section(
                    ui.TextDisplay(
                        f"**{file_meta['title']}**\n{file_meta['artist']}\n\nalbum: {file_meta['album']}\nsource: uploaded file"
                    ),
                )
            )

        await interaction.response.send_message(view=layout)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(NowPlaying(bot))
