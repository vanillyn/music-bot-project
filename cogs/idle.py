import asyncio
import random
import discord
from typing import Dict, Any
from .files import Files


class Idle:
    def __init__(self) -> None:
        self.files: Files = Files()
        self.idle_enabled: Dict[int, bool] = {}
        self.idle_tasks: Dict[int, asyncio.Task[Any]] = {}
        self.last_activity: Dict[int, float] = {}

    def set_idle_enabled(self, guild_id: int, enabled: bool) -> None:
        self.idle_enabled[guild_id] = enabled

    def update_activity(self, guild_id: int) -> None:
        self.last_activity[guild_id] = asyncio.get_event_loop().time()

    def start_idle_task(self, guild_id: int, voice_client: discord.VoiceClient) -> None:
        if guild_id not in self.idle_tasks or self.idle_tasks[guild_id].done():
            self.idle_enabled.setdefault(guild_id, True)
            self.update_activity(guild_id)
            self.idle_tasks[guild_id] = asyncio.create_task(
                self.idle_loop(guild_id, voice_client)
            )

    def stop_idle_task(self, guild_id: int) -> None:
        if guild_id in self.idle_tasks:
            self.idle_tasks[guild_id].cancel()

    async def idle_loop(self, guild_id: int, voice_client: discord.VoiceClient) -> None:
        while True:
            try:
                await asyncio.sleep(5)

                if not voice_client.is_connected():
                    break

                if not self.idle_enabled.get(guild_id, True):
                    continue

                if voice_client.is_playing():
                    self.update_activity(guild_id)
                    continue

                current_time = asyncio.get_event_loop().time()
                time_since_activity = current_time - self.last_activity.get(
                    guild_id, current_time
                )

                if time_since_activity >= 30:
                    bg_files = self.files.list_bg_music_files()

                    if bg_files:
                        track = random.choice(bg_files)
                        filepath = self.files.get_bg_music_path(track)
                        voice_client.play(discord.FFmpegPCMAudio(filepath))
                        print(f"playing idle track: {track}")
                        self.update_activity(guild_id)

            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"error in idle loop: {e}")
                await asyncio.sleep(10)
