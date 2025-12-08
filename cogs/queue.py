import discord
from discord.ext import commands
from discord import app_commands, ui
from collections import deque
from typing import Dict, Deque, Optional
import random


class QueueItem:
    def __init__(self, filepath: str, metadata: Dict[str, str], is_youtube: bool):
        self.filepath: str = filepath
        self.metadata: Dict[str, str] = metadata
        self.is_youtube: bool = is_youtube


class Queue(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.queues: Dict[int, Deque[QueueItem]] = {}
        self.current: Dict[int, Optional[QueueItem]] = {}
        self.history: Dict[int, Deque[QueueItem]] = {}
        self.loop_mode: Dict[int, str] = {}
        self.shuffle_enabled: Dict[int, bool] = {}

    def get_queue(self, guild_id: int) -> Deque[QueueItem]:
        if guild_id not in self.queues:
            self.queues[guild_id] = deque()
        return self.queues[guild_id]

    def get_history(self, guild_id: int) -> Deque[QueueItem]:
        if guild_id not in self.history:
            self.history[guild_id] = deque()
        return self.history[guild_id]

    def add_to_queue(
        self, guild_id: int, filepath: str, metadata: Dict[str, str], is_youtube: bool
    ) -> None:
        queue = self.get_queue(guild_id)
        item = QueueItem(filepath, metadata, is_youtube)
        queue.append(item)

    def get_next(self, guild_id: int) -> Optional[QueueItem]:
        queue = self.get_queue(guild_id)
        loop = self.loop_mode.get(guild_id, "off")

        if loop == "single" and guild_id in self.current and self.current[guild_id]:
            return self.current[guild_id]

        if not queue:
            if loop == "queue" and guild_id in self.history:
                history = self.history[guild_id]
                if history:
                    queue.extend(history)
                    history.clear()

        if not queue:
            return None

        if self.shuffle_enabled.get(guild_id, False):
            idx = random.randint(0, len(queue) - 1)
            items = list(queue)
            item = items.pop(idx)
            queue.clear()
            queue.extend(items)
            return item
        else:
            return queue.popleft()

    def play_next(self, guild_id: int, voice_client: discord.VoiceClient) -> None:
        if self.current.get(guild_id) is not None:
            history = self.get_history(guild_id)
            current_item = self.current[guild_id]
            if current_item is not None:
                history.append(current_item)
                if len(history) > 50:
                    history.popleft()

        next_item = self.get_next(guild_id)
        if next_item is None:
            self.current[guild_id] = None
            return

        self.current[guild_id] = next_item

        def after_playing(error: Optional[Exception]) -> None:
            if error:
                print(f"playback error: {error}")
            self.play_next(guild_id, voice_client)

        voice_client.play(
            discord.FFmpegPCMAudio(next_item.filepath), after=after_playing
        )

    @app_commands.command(name="queue", description="show current queue")
    async def show_queue(self, interaction: discord.Interaction) -> None:
        if interaction.guild is None:
            await interaction.response.send_message("only works in servers")
            return

        guild_id = interaction.guild.id
        queue = self.get_queue(guild_id)
        current = self.current.get(guild_id)

        if current is None and len(queue) == 0:
            await interaction.response.send_message("queue is empty")
            return

        class QueueLayout(ui.LayoutView):
            container = ui.Container(
                ui.Section(
                    ui.TextDisplay("## music queue"),
                ),
                ui.Separator(spacing=ui.SeparatorSpacing.small, dividing_line=True),
                accent_color=0x5865F2,
            )

        layout = QueueLayout()

        if current:
            current_title = current.metadata.get("title", "unknown")
            layout.container.add_item(
                ui.Section(
                    ui.TextDisplay(f"**now playing**\n{current_title}"),
                )
            )
            layout.container.add_item(
                ui.Separator(spacing=ui.SeparatorSpacing.small, dividing_line=True)
            )

        if queue:
            queue_text = "**up next**\n"
            for i, item in enumerate(list(queue)[:10], 1):
                title = item.metadata.get("title", "unknown")
                queue_text += f"{i}. {title}\n"

            if len(queue) > 10:
                queue_text += f"\n... and {len(queue) - 10} more"

            layout.container.add_item(
                ui.Section(
                    ui.TextDisplay(queue_text.strip()),
                )
            )
            layout.container.add_item(
                ui.Separator(spacing=ui.SeparatorSpacing.small, dividing_line=True)
            )

        loop = self.loop_mode.get(guild_id, "off")
        shuffle = self.shuffle_enabled.get(guild_id, False)

        layout.container.add_item(
            ui.Section(
                ui.TextDisplay(
                    f"loop: {loop}  •  shuffle: {'on' if shuffle else 'off'}"
                ),
            )
        )

        await interaction.response.send_message(view=layout)

    @app_commands.command(name="skip", description="skip to next song")
    async def skip(self, interaction: discord.Interaction) -> None:
        if interaction.guild is None:
            await interaction.response.send_message("only works in servers")
            return

        voice_client = interaction.guild.voice_client
        if voice_client is None or not isinstance(voice_client, discord.VoiceClient):
            await interaction.response.send_message("not playing anything")
            return

        if voice_client.is_playing():
            voice_client.stop()

        await interaction.response.send_message("skipped")

    @app_commands.command(name="stop", description="stop playing but dont leave")
    async def stop(self, interaction: discord.Interaction) -> None:
        if interaction.guild is None:
            await interaction.response.send_message("only works in servers")
            return

        voice_client = interaction.guild.voice_client
        if voice_client is None or not isinstance(voice_client, discord.VoiceClient):
            await interaction.response.send_message("not playing anything")
            return

        if voice_client.is_playing():
            voice_client.stop()

        guild_id = interaction.guild.id
        self.current[guild_id] = None

        await interaction.response.send_message("stopped")

    @app_commands.command(name="previous", description="go back to previous song")
    async def previous(self, interaction: discord.Interaction) -> None:
        if interaction.guild is None:
            await interaction.response.send_message("only works in servers")
            return

        guild_id = interaction.guild.id
        history = self.get_history(guild_id)

        if not history:
            await interaction.response.send_message("no previous song")
            return

        prev_item = history.pop()

        if self.current.get(guild_id) is not None:
            queue = self.get_queue(guild_id)
            current_item = self.current[guild_id]
            if current_item is not None:
                queue.appendleft(current_item)

        voice_client = interaction.guild.voice_client
        if voice_client is None or not isinstance(voice_client, discord.VoiceClient):
            await interaction.response.send_message("not connected to voice")
            return

        self.current[guild_id] = prev_item

        def after_playing(error: Optional[Exception]) -> None:
            if error:
                print(f"playback error: {error}")
            self.play_next(guild_id, voice_client)

        if voice_client.is_playing():
            voice_client.stop()

        voice_client.play(
            discord.FFmpegPCMAudio(prev_item.filepath), after=after_playing
        )
        await interaction.response.send_message(
            f"playing: {prev_item.metadata.get('title', 'unknown')}"
        )

    @app_commands.command(name="shuffle", description="toggle shuffle mode")
    async def shuffle(self, interaction: discord.Interaction, mode: str) -> None:
        if interaction.guild is None:
            await interaction.response.send_message("only works in servers")
            return

        if mode.lower() not in ["on", "off"]:
            await interaction.response.send_message("use /shuffle on or /shuffle off")
            return

        guild_id = interaction.guild.id
        enabled = mode.lower() == "on"
        self.shuffle_enabled[guild_id] = enabled

        await interaction.response.send_message(
            f"shuffle {'enabled' if enabled else 'disabled'}"
        )

    @app_commands.command(name="loop", description="set loop mode (single, queue, off)")
    async def loop(self, interaction: discord.Interaction, mode: str) -> None:
        if interaction.guild is None:
            await interaction.response.send_message("only works in servers")
            return

        mode_lower = mode.lower()
        if mode_lower not in ["single", "queue", "off"]:
            await interaction.response.send_message(
                "use /loop single, /loop queue, or /loop off"
            )
            return

        guild_id = interaction.guild.id
        self.loop_mode[guild_id] = mode_lower

        await interaction.response.send_message(f"loop mode: {mode_lower}")


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Queue(bot))
