import discord
from discord.ext import commands
from discord import app_commands
from mutagen import File
from typing import Dict


class NowPlaying(commands.Cog):
    def __init__(self, bot) -> None:
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
    async def info(self, interaction: discord.Interaction):
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

        embed = discord.Embed(title="now playing", color=0x5865F2)

        if current.is_youtube:
            embed.add_field(
                name="title", value=metadata.get("title", "unknown"), inline=False
            )
            embed.add_field(
                name="uploader", value=metadata.get("uploader", "unknown"), inline=False
            )

            duration = metadata.get("duration", "0")
            try:
                dur_seconds = int(float(duration))
                minutes = dur_seconds // 60
                seconds = dur_seconds % 60
                embed.add_field(
                    name="duration", value=f"{minutes}:{seconds:02d}", inline=False
                )
            except Exception:
                embed.add_field(name="duration", value="unknown", inline=False)

            thumbnail = metadata.get("thumbnail", "")
            if thumbnail:
                embed.set_thumbnail(url=thumbnail)
        else:
            file_meta = self.get_file_metadata(current.filepath)
            embed.add_field(name="title", value=file_meta["title"], inline=False)
            embed.add_field(name="artist", value=file_meta["artist"], inline=False)
            embed.add_field(name="album", value=file_meta["album"], inline=False)

        embed.add_field(
            name="source",
            value="youtube" if current.is_youtube else "uploaded file",
            inline=False,
        )

        await interaction.response.send_message(embed=embed)


async def setup(bot):
    await bot.add_cog(NowPlaying(bot))
