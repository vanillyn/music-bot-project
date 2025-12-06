import discord
from discord.ext import commands
from discord import app_commands
import os


class Voice(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.audio_dir = "audio_files"
        os.makedirs(self.audio_dir, exist_ok=True)

    @commands.command()
    async def join(self, ctx):
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
        except Exception as e:
            print(f"failed to connect: {e}")
            await ctx.send(f"couldn't join: {e}")

    @app_commands.command(name="join", description="join your voice channel")
    async def join_slash(self, interaction: discord.Interaction):
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

        try:
            voice_client = await channel.connect()
            await interaction.response.send_message("joined")
        except Exception as e:
            await interaction.response.send_message(f"couldn't join: {e}")

    @commands.command()
    async def leave(self, ctx):
        if ctx.voice_client is None:
            await ctx.send("not in a voice channel")
            return

        await ctx.voice_client.disconnect()
        await ctx.send("left")

    @app_commands.command(name="leave", description="leave voice channel")
    async def leave_slash(self, interaction: discord.Interaction):
        voice_client = interaction.guild.voice_client

        if voice_client is None:
            await interaction.response.send_message("not in a voice channel")
            return

        await voice_client.disconnect()
        await interaction.response.send_message("left")

    @commands.command()
    async def play(self, ctx, *, filepath: str):
        if ctx.voice_client is None:
            await ctx.send("not in a voice channel, use !join first")
            return

        if not os.path.exists(filepath):
            await ctx.send("file not found")
            return

        if ctx.voice_client.is_playing():
            ctx.voice_client.stop()

        ctx.voice_client.play(discord.FFmpegPCMAudio(filepath))
        await ctx.send("playing")

    @app_commands.command(name="upload", description="upload an mp3 to play later")
    async def upload(self, interaction: discord.Interaction, file: discord.Attachment):
        await interaction.response.defer()

        if not file.filename.endswith((".mp3", ".wav", ".ogg", ".m4a")):
            await interaction.followup.send("only audio files please")
            return

        if file.size > 25 * 1024 * 1024:
            await interaction.followup.send("file too big, 25mb max")
            return

        safe_name = os.path.basename(file.filename)
        filepath = os.path.join(self.audio_dir, safe_name)

        try:
            await file.save(filepath)
        except Exception as e:
            await interaction.followup.send(f"failed to save file: {e}")
            return

        await interaction.followup.send(f"saved as {safe_name}")

    @app_commands.command(name="list", description="list uploaded audio files")
    async def list_files(self, interaction: discord.Interaction):
        files = [
            f
            for f in os.listdir(self.audio_dir)
            if f.endswith((".mp3", ".wav", ".ogg", ".m4a"))
        ]

        if not files:
            await interaction.response.send_message("no files uploaded yet")
            return

        file_list = "\n".join(files)
        await interaction.response.send_message(
            f"available files:\n```\n{file_list}\n```"
        )

    @app_commands.command(name="playfile", description="play an uploaded file")
    async def playfile(self, interaction: discord.Interaction, filename: str):
        if interaction.guild is None:
            await interaction.response.send_message(
                "this command can only be used in a server"
            )
            return

        member = interaction.guild.get_member(interaction.user.id)
        if member is None or member.voice is None:
            await interaction.response.send_message("you need to be in a voice channel")
            return

        filepath = os.path.join(self.audio_dir, filename)

        if not os.path.exists(filepath):
            await interaction.response.send_message(
                "file not found, use /list to see files"
            )
            return

        voice_client = interaction.guild.voice_client

        if voice_client is None:
            channel = member.voice.channel
            if channel is None:
                await interaction.response.send_message(
                    "you need to be in a voice channel"
                )
                return
            voice_client = await channel.connect()

        if voice_client.is_playing():
            voice_client.stop()

        voice_client.play(discord.FFmpegPCMAudio(filepath))
        await interaction.response.send_message(f"playing {filename}")


async def setup(bot):
    await bot.add_cog(Voice(bot))
