import discord
from discord.ext import commands
from discord import app_commands
import aiohttp
import zipfile
from pathlib import Path
import asyncio
from PIL import Image
import io


class Avatars(commands.Cog):
    def __init__(self, bot) -> None:
        self.bot = bot

    @app_commands.command(
        name="avatars", description="download all server avatars as zip"
    )
    async def avatars(self, interaction: discord.Interaction):
        print("=== AVATARS COMMAND STARTED ===")

        await interaction.response.defer()
        print("deferred response")

        if interaction.guild is None:
            await interaction.followup.send("only works in servers")
            return

        print(f"guild: {interaction.guild.name}")
        print(f"members before chunk: {len(interaction.guild.members)}")

        try:
            print("starting chunk with timeout...")
            await asyncio.wait_for(interaction.guild.chunk(), timeout=30.0)
            print("chunk completed")
        except asyncio.TimeoutError:
            print("chunk timed out, using cached members only")
            await interaction.followup.send(
                "using cached members only (some may be missing)"
            )
        except discord.HTTPException as e:
            if e.status == 429:
                print(f"rate limited: {e}")
                await interaction.followup.send(
                    "got rate limited, try again in a minute"
                )
                return
            else:
                print(f"http error during chunk: {e}")
                await interaction.followup.send(f"discord api error: {e}")
                return
        except Exception as e:
            print(f"chunk failed: {e}")
            await interaction.followup.send(f"failed to load members: {e}")
            return

        print(f"members after chunk: {len(interaction.guild.members)}")

        temp_dir = Path("temp_avatars")
        temp_dir.mkdir(exist_ok=True)

        downloaded = 0
        failed = 0

        try:
            async with aiohttp.ClientSession() as session:
                for member in interaction.guild.members:
                    if member.bot:
                        continue

                    print(f"trying to download {member.name}")

                    avatar_url = member.display_avatar.with_size(256).url

                    filename = f"{member.name}_{member.id}.jpg"
                    filepath = temp_dir / filename

                    try:
                        async with session.get(avatar_url) as resp:
                            if resp.status == 200:
                                data = await resp.read()

                                try:
                                    img = Image.open(io.BytesIO(data))
                                    img = img.convert("RGB")
                                    img.save(
                                        filepath, "JPEG", quality=70, optimize=True
                                    )
                                    downloaded += 1
                                    print(f"saved {member.name}")
                                except Exception as e:
                                    print(
                                        f"image processing failed for {member.name}: {e}"
                                    )
                                    failed += 1
                            else:
                                print(f"bad status {resp.status} for {member.name}")
                                failed += 1
                    except Exception as e:
                        print(f"download failed for {member.name}: {e}")
                        failed += 1

            print(f"downloaded: {downloaded}, failed: {failed}")

            if downloaded == 0:
                await interaction.followup.send("couldn't download any avatars")
                temp_dir.rmdir()
                return

            zip_path = Path("server_avatars.zip")
            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
                for file in temp_dir.iterdir():
                    zipf.write(file, file.name)

            file_size = zip_path.stat().st_size
            print(f"zip size: {file_size / (1024 * 1024):.2f}mb")

            if file_size > 25 * 1024 * 1024:
                await interaction.followup.send("zip too big, try with fewer members")
            else:
                await interaction.followup.send(
                    f"got {downloaded} avatars",
                    file=discord.File(zip_path, filename="avatars.zip"),
                )

            for file in temp_dir.iterdir():
                file.unlink()
            temp_dir.rmdir()
            if zip_path.exists():
                zip_path.unlink()

        except Exception as e:
            print(f"overall error: {e}")
            await interaction.followup.send(f"something went wrong: {e}")

            if temp_dir.exists():
                for file in temp_dir.iterdir():
                    file.unlink()
                temp_dir.rmdir()


async def setup(bot):
    await bot.add_cog(Avatars(bot))
