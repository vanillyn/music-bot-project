import discord
from discord.ext import commands
from discord import app_commands
import aiohttp
import zipfile
from pathlib import Path


class Avatars(commands.Cog):
    def __init__(self, bot) -> None:
        self.bot = bot

    @app_commands.command(
        name="avatars", description="download all server avatars as zip"
    )
    async def avatars(self, interaction: discord.Interaction):
        await interaction.response.defer()

        if interaction.guild is None:
            await interaction.followup.send("only works in servers")
            return

        await interaction.guild.chunk()

        temp_dir = Path("temp_avatars")
        temp_dir.mkdir(exist_ok=True)

        try:
            async with aiohttp.ClientSession() as session:
                for member in interaction.guild.members:
                    if member.bot:
                        continue

                    avatar_url = member.display_avatar.url
                    ext = "png"
                    if avatar_url.endswith(".gif"):
                        ext = "gif"

                    filename = f"{member.name}_{member.id}.{ext}"
                    filepath = temp_dir / filename

                    try:
                        async with session.get(avatar_url) as resp:
                            if resp.status == 200:
                                data = await resp.read()
                                with open(filepath, "wb") as f:
                                    f.write(data)
                    except Exception as e:
                        print(f"failed to download {member.name}: {e}")

            zip_path = Path("server_avatars.zip")
            with zipfile.ZipFile(zip_path, "w") as zipf:
                for file in temp_dir.iterdir():
                    zipf.write(file, file.name)

            await interaction.followup.send(
                file=discord.File(zip_path, filename="avatars.zip")
            )

            for file in temp_dir.iterdir():
                file.unlink()
            temp_dir.rmdir()
            zip_path.unlink()

        except Exception as e:
            await interaction.followup.send(f"something went wrong: {e}")


async def setup(bot):
    await bot.add_cog(Avatars(bot))
