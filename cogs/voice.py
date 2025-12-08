import discord
from discord.ext import commands
from discord import app_commands, ui
from .files import Files
from .idle import Idle


class Voice(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.files = Files()
        self.idle_player = Idle()

    @commands.command()
    async def join(self, ctx: commands.Context) -> None:
        print(f"join command called by {ctx.author}")

        if ctx.author.voice is None:
            print("user not in voice channel")
            await ctx.send("you need to be in a voice channel")
            return

        channel = ctx.author.voice.channel
        print(f"attempting to join {channel}")

        try:
            voice_client = await channel.connect()
            print(f"connected successfully: {voice_client}")
            await ctx.send("joined")
            if ctx.guild is not None:
                self.idle_player.start_idle_task(ctx.guild.id, voice_client)
        except Exception as e:
            print(f"failed to connect: {e}")
            await ctx.send(f"couldn't join: {e}")

    @app_commands.command(name="join", description="join your voice channel")
    async def join_slash(self, interaction: discord.Interaction) -> None:
        if interaction.guild is None:
            await interaction.response.send_message(
                "this command can only be used in a server"
            )
            return

        member = interaction.guild.get_member(interaction.user.id)
        if member is None or member.voice is None:
            await interaction.response.send_message("you need to be in a voice channel")
            return

        channel = member.voice.channel

        if channel is None:
            await interaction.response.send_message("you need to be in a voice channel")
            return

        try:
            voice_client = await channel.connect()
            await interaction.response.send_message("joined")
            self.idle_player.start_idle_task(interaction.guild.id, voice_client)
        except Exception as e:
            await interaction.response.send_message(f"couldn't join: {e}")

    @app_commands.command(name="leave", description="leave voice channel")
    async def leave_slash(self, interaction: discord.Interaction) -> None:
        if interaction.guild is None:
            await interaction.response.send_message(
                "this command can only be used in a server"
            )
            return

        voice_client = interaction.guild.voice_client

        if voice_client is None:
            await interaction.response.send_message("not in a voice channel")
            return

        self.idle_player.stop_idle_task(interaction.guild.id)
        await voice_client.disconnect(force=True)
        await interaction.response.send_message("left")

    @app_commands.command(name="upload", description="upload an mp3 to play later")
    async def upload(
        self, interaction: discord.Interaction, file: discord.Attachment
    ) -> None:
        await interaction.response.defer()

        if not self.files.is_valid_audio(file.filename):
            await interaction.followup.send("only audio files please")
            return

        if file.size > 25 * 1024 * 1024:
            await interaction.followup.send("file too big, 25mb max")
            return

        try:
            from pathlib import Path

            filepath = self.files.get_audio_path(file.filename)
            await file.save(Path(filepath))
            await interaction.followup.send(f"saved as {file.filename}")
        except Exception as e:
            await interaction.followup.send(f"failed to save file: {e}")

    @app_commands.command(name="list", description="list uploaded audio files")
    async def list_files(self, interaction: discord.Interaction) -> None:
        files = self.files.list_audio_files()

        if not files:
            await interaction.response.send_message("no files uploaded yet")
            return

        class FilesLayout(ui.LayoutView):
            container = ui.Container(
                ui.Section(
                    ui.TextDisplay("## saved audio files"),
                ),
                ui.Separator(spacing=ui.SeparatorSpacing.small, dividing_line=True),
                accent_color=0x5865F2,
            )

        layout = FilesLayout()

        file_chunks = [files[i : i + 15] for i in range(0, len(files), 15)]

        for chunk in file_chunks:
            file_text = "\n".join(f"• {f}" for f in chunk)
            layout.container.add_item(
                ui.Section(
                    ui.TextDisplay(file_text),
                )
            )
            if chunk != file_chunks[-1]:
                layout.container.add_item(
                    ui.Separator(spacing=ui.SeparatorSpacing.small)
                )

        await interaction.response.send_message(view=layout)

    @app_commands.command(name="playfile", description="play an uploaded file")
    async def playfile(self, interaction: discord.Interaction, filename: str) -> None:
        if interaction.guild is None:
            await interaction.response.send_message(
                "this command can only be used in a server"
            )
            return

        member = interaction.guild.get_member(interaction.user.id)
        if member is None or member.voice is None:
            await interaction.response.send_message("you need to be in a voice channel")
            return

        filepath = self.files.get_audio_path(filename)

        if not self.files.file_exists(filepath):
            await interaction.response.send_message(
                "file not found, use /list to see files"
            )
            return

        queue_cog = self.bot.get_cog("Queue")
        if queue_cog is None:
            await interaction.response.send_message("queue system not loaded")
            return

        metadata = {"title": filename, "artist": "unknown", "album": "unknown"}
        guild_id = interaction.guild.id
        queue_cog.add_to_queue(guild_id, filepath, metadata, False)

        voice_client = interaction.guild.voice_client

        if voice_client is None:
            channel = member.voice.channel
            if channel is None:
                await interaction.response.send_message(
                    "you need to be in a voice channel"
                )
                return
            voice_client = await channel.connect()
            self.idle_player.start_idle_task(guild_id, voice_client)

        if isinstance(voice_client, discord.VoiceClient):
            if not voice_client.is_playing():
                queue_cog.play_next(guild_id, voice_client)
            await interaction.response.send_message(f"added {filename} to queue")
        else:
            await interaction.response.send_message(
                "Failed to play: not connected to a voice channel properly."
            )

    @app_commands.command(name="idle", description="toggle idle background music")
    async def idle_toggle(self, interaction: discord.Interaction, mode: str) -> None:
        if interaction.guild is None:
            await interaction.response.send_message(
                "this command can only be used in a server"
            )
            return

        if mode.lower() not in ["on", "off"]:
            await interaction.response.send_message("use /idle on or /idle off")
            return

        guild_id = interaction.guild.id
        enabled = mode.lower() == "on"
        self.idle_player.set_idle_enabled(guild_id, enabled)

        if enabled:
            await interaction.response.send_message("idle mode enabled")
            voice_client = interaction.guild.voice_client
            if (
                isinstance(voice_client, discord.VoiceClient)
                and not voice_client.is_playing()
            ):
                self.idle_player.update_activity(guild_id)
        else:
            await interaction.response.send_message("idle mode disabled")


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Voice(bot))
