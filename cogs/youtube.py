import discord
from discord.ext import commands
from discord import app_commands
import yt_dlp
import os
import hashlib
from typing import Optional, Dict


class YouTube(commands.Cog):
    def __init__(self, bot) -> None:
        self.bot = bot
        self.cache_dir: str = "youtube_cache"
        os.makedirs(self.cache_dir, exist_ok=True)
        self.metadata_cache: Dict[str, Dict[str, str]] = {}

    def get_cache_filename(self, url: str) -> str:
        url_hash = hashlib.md5(url.encode()).hexdigest()
        return os.path.join(self.cache_dir, f"{url_hash}.opus")

    def get_video_metadata(self, url: str) -> Optional[Dict[str, str]]:
        if url in self.metadata_cache:
            return self.metadata_cache[url]

        ydl_opts = {
            "format": "bestaudio/best",
            "quiet": True,
            "no_warnings": True,
            "extract_flat": False,
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                if info:
                    metadata = {
                        "title": info.get("title", "Unknown"),
                        "uploader": info.get("uploader", "Unknown"),
                        "duration": str(info.get("duration", 0)),
                        "thumbnail": info.get("thumbnail", ""),
                        "url": url,
                    }
                    self.metadata_cache[url] = metadata
                    return metadata
        except Exception as e:
            print(f"failed to get metadata: {e}")
            return None

    def download_audio(self, url: str) -> Optional[str]:
        cache_file = self.get_cache_filename(url)

        if os.path.exists(cache_file):
            print(f"using cached file for {url}")
            return cache_file

        ydl_opts = {
            "format": "bestaudio/best",
            "outtmpl": cache_file.replace(".opus", ".%(ext)s"),
            "postprocessors": [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "opus",
                    "preferredquality": "192",
                }
            ],
            "quiet": True,
            "no_warnings": True,
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                print(f"downloading {url}")
                ydl.download([url])
                if os.path.exists(cache_file):
                    return cache_file
                else:
                    print(f"file not found after download: {cache_file}")
                    return None
        except Exception as e:
            print(f"failed to download: {e}")
            return None

    @app_commands.command(name="play", description="play audio from youtube url")
    async def play(self, interaction: discord.Interaction, url: str):
        await interaction.response.defer()

        if interaction.guild is None:
            await interaction.followup.send("only works in servers")
            return

        member = interaction.guild.get_member(interaction.user.id)
        if member is None or member.voice is None:
            await interaction.followup.send("join a voice channel first")
            return

        metadata = self.get_video_metadata(url)
        if metadata is None:
            await interaction.followup.send("couldn't get video info")
            return

        filepath = self.download_audio(url)
        if filepath is None:
            await interaction.followup.send("couldn't download audio")
            return

        queue_cog = self.bot.get_cog("MusicQueue")
        if queue_cog is None:
            await interaction.followup.send("queue system not loaded")
            return

        guild_id = interaction.guild.id
        queue_cog.add_to_queue(guild_id, filepath, metadata, True)

        voice_client = interaction.guild.voice_client

        if voice_client is None:
            channel = member.voice.channel
            if channel is None:
                await interaction.followup.send("join a voice channel first")
                return
            try:
                voice_client = await channel.connect()
            except Exception as e:
                await interaction.followup.send(f"couldn't connect: {e}")
                return

        if isinstance(voice_client, discord.VoiceClient):
            if not voice_client.is_playing():
                queue_cog.play_next(guild_id, voice_client)
            await interaction.followup.send(f"added to queue: {metadata['title']}")
        else:
            await interaction.followup.send("not connected properly")


async def setup(bot):
    await bot.add_cog(YouTube(bot))
