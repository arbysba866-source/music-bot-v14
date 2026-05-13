from __future__ import annotations

import re
import asyncio
import requests

from discord import Embed, Intents, Activity, Status, Color, ActivityType
from discord import FFmpegOpusAudio, Message, utils
from discord.ext import commands
from yt_dlp import YoutubeDL
from youtube_search import YoutubeSearch
 
from discord import VoiceClient, Member, VoiceState
from typing import TYPE_CHECKING , Union , Optional

if TYPE_CHECKING:
    from discord.ext.commands import Bot

from os import getenv

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#   AWS SERVICES — PURPLE NEON MUSIC BOT
#   Embed color: Deep Purple
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

EMBED_COLOR = 0x7B2FBE  # Deep purple matching the design

# ── Waveform bar made of block chars (animated-looking) ──
WAVEFORM = "▂▃▅▆▇▆▅▇▆▅▃▂▁▂▃▅▆▇█▇▆▅▃▂▁▂▃▅▇▆▅▃▂"

bot = commands.Bot(
    command_prefix='!',
    intents=Intents.all(),
    activity=Activity(type=ActivityType.listening, name="AWS Services 🎵"),
    status=Status.idle,
    help_command=None
)


ytdl_format_options = {
    'format': 'worstaudio',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'http_headers': {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'},
    'cookiefile': 'cookies.txt',  
    'source_address': '0.0.0.0'
}

def is_youtube_link(message_content):
    pattern = [
        r'https?://(?:www\.)?youtu\.be/([^/?]+)',
        r'https?://(?:www\.)?youtube\.com/watch\?v=([^&]+)'
    ]
    for valid_url in pattern:
        if re.match(valid_url, message_content):
            return True
    return False


def is_link_valid(url):
    try:
        response = requests.head(url, allow_redirects=True)
        return response.status_code == 200
    except:
        return False
    

def get_duration(time):
    if time is None:
        return "🔴 LIVE"
    hours   = int(time // 3600)
    minutes = int((time % 3600) // 60)
    seconds = int(time % 60)
    if hours > 0:
        return f"{hours}:{minutes:02d}:{seconds:02d}"
    return f"{minutes:02d}:{seconds:02d}"


def build_now_playing_embed(data: dict, url: str, requester) -> Embed:
    """
    Builds the purple neon 'Now Playing' embed
    matching the AWS Services visual style.
    """
    title    = data.get('title', 'Unknown')
    duration = get_duration(data.get('duration'))
    thumb    = data.get('thumbnail', '')

    # ── Waveform progress bar visual ──
    progress_bar = f"```\n{WAVEFORM}\n```"

    embed = Embed(
        color=EMBED_COLOR
    )

    # Header row
    embed.set_author(
        name="▶  NOW PLAYING",
        icon_url="https://cdn.discordapp.com/attachments/1467293992478838805/1503604157083422760/AWS.png?ex=6a049cbe&is=6a034b3e&hm=77cacdfa8a74465d92ae8e3b772e63bcb4e06989028063b5520a377c8711f1f2&"  # fallback icon
    )

    # Song info block
    embed.add_field(
        name=f"🎵  {title}",
        value=(
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"{WAVEFORM}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"`0:00` ◉━━━━━━━━━━━━━━━━━━ `{duration}`\n"
            f"\n"
            f"🔀  ⏮  ⏸  ⏭  🔁"
        ),
        inline=False
    )

    # Footer row: requester + volume
    embed.set_footer(
        text=f"Requested by  {requester.name}   🔊 100%",
        icon_url=requester.display_avatar.url
    )

    if thumb:
        embed.set_thumbnail(url=thumb)

    return embed


def build_simple_embed(description: str, color: int = EMBED_COLOR) -> Embed:
    return Embed(description=description, color=color)


class Music(commands.Cog):
    def __init__(self, bot):
        self.bot: Bot = bot
        self.voice_client: Union[VoiceClient, None] = None
        self.isloop = False
        self.skip   = False
        self.data: dict = {}

    def get_data(self, url: str, ctx: commands.Context) -> dict:
        ytdl      = YoutubeDL(ytdl_format_options)
        ytdl_info = ytdl.extract_info(url, download=False)
        return {
            'user':      ctx.author,
            'title':     ytdl_info.get('title', 'Unknown'),
            'url':       ytdl_info.get('url'),
            'duration':  ytdl_info.get('duration'),
            'thumbnail': ytdl_info.get('thumbnail')
        }

    # ── Ready ──────────────────────────────────────────────
    @commands.Cog.listener()
    async def on_ready(self):
        print(f"✅  Connected as {self.bot.user.name}")

    # ── Repeat ────────────────────────────────────────────
    @commands.command(name='repeat', aliases=['r', 'loop'])
    async def repeat_command(self, ctx: commands.Context):
        if ctx.author.voice is None:
            return
        if ctx.guild.get_member(self.bot.user.id) not in ctx.author.voice.channel.members:
            return

        if self.voice_client.is_playing() or self.voice_client.is_paused():
            if not self.data:
                await ctx.reply(embed=build_simple_embed("**⚠️  An error occurred. Please contact the developer.**"))
                return

            if self.data['user'] and self.data['user'] != ctx.author:
                await ctx.reply(embed=build_simple_embed(
                    f"**:x:  Only the music requester ({self.data['user'].mention}) can use this command.**",
                    color=0xFF4757
                ))
            elif self.isloop:
                self.isloop = False
                await ctx.reply(embed=build_simple_embed(
                    f"**▶️  Playing  —  {self.data['title']}  (`{get_duration(self.data['duration'])}`)**"
                ))
            else:
                self.isloop = True
                await ctx.reply(embed=build_simple_embed(
                    f"**🔁  Repeating  —  {self.data['title']}  (`{get_duration(self.data['duration'])}`)**"
                ))
        else:
            await ctx.reply(embed=build_simple_embed("**:x:  No song is currently playing.**", color=0xFF4757))

    # ── Play ──────────────────────────────────────────────
    @commands.command(name='play', aliases=['p', 'ش'])
    async def play_command(self, ctx: commands.Context, *, message: Optional[str]):
        if ctx.author.voice is None:
            await ctx.reply(embed=build_simple_embed(
                "**:x:  You need to be in a voice channel to use this command.**",
                color=0xFF4757
            ))
            return

        if message is None:
            await ctx.reply(embed=build_simple_embed(
                f"**`{self.bot.command_prefix}play <song name | URL>`**"
            ))
            return

        if not ctx.voice_client:
            self.voice_client = await ctx.author.voice.channel.connect(self_deaf=True)
        elif self.voice_client.is_playing() or self.voice_client.is_paused():
            await ctx.reply(embed=build_simple_embed(
                "**:x:  Music Bot is currently in use. Please wait. ⏱️**",
                color=0xFF4757
            ))
            return
        elif self.voice_client.channel != ctx.author.voice.channel:
            await ctx.voice_client.move_to(ctx.author.voice.channel)

        async with ctx.typing():
            if not is_youtube_link(message):
                try:
                   search_result = YoutubeSearch(message, max_results=1).to_dict()
                except:
                    await ctx.reply(embed=build_simple_embed(
                        f"**:x:  Could not find a song named `{message}`.**",
                        color=0xFF4757
                    ))
                    return
                if len(search_result) <= 0:
                    await ctx.reply(embed=build_simple_embed(
                        f"**:x:  Could not find a song named `{message}`.**",
                        color=0xFF4757
                    ))
                    return
                url = "https://youtube.com" + search_result[0]['url_suffix']
            else:
                if is_link_valid(message):
                    url = message
                else:
                    await ctx.reply(embed=build_simple_embed("**:x:  The link you entered is invalid.**", color=0xFF4757))
                    return

        self.data = self.get_data(url=url, ctx=ctx)

        if self.data['url'] is None:
            await ctx.reply(embed=build_simple_embed("**:x:  Cannot fetch this song.**", color=0xFF4757))
            return

        # ── Send the purple neon Now Playing embed ──
        embed = build_now_playing_embed(self.data, url, ctx.author)
        await ctx.send(embed=embed)

        while True:
            fresh = self.get_data(url=url, ctx=ctx)
            self.voice_client.play(FFmpegOpusAudio(fresh['url'], before_options='-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5', options='-vn'))
            while self.voice_client.is_playing() or self.voice_client.is_paused():
                await asyncio.sleep(0.1)
                if self.skip:
                    self.voice_client.stop()
                    self.skip = False
            if self.isloop:
                continue
            self.data = {}
            return

    # ── Skip ──────────────────────────────────────────────
    @commands.command(name='skip', aliases=['s'])
    async def skip_command(self, ctx: commands.Context):
        if ctx.author.voice is None:
            return
        if ctx.guild.get_member(self.bot.user.id) not in ctx.author.voice.channel.members:
            return

        if self.voice_client.is_playing() or self.voice_client.is_paused():
            if not self.data:
                await ctx.reply(embed=build_simple_embed("**⚠️  An error occurred.**"), delete_after=10)
            else:
                if self.data['user'] and (
                    self.data['user'] != ctx.author
                    and self.data['user'] in ctx.author.voice.channel.members
                ):
                    await ctx.reply(embed=build_simple_embed(
                        f"**:x:  Only the music requester ({self.data['user'].mention}) can use this command.**",
                        color=0xFF4757
                    ))
                else:
                    self.skip   = True
                    self.isloop = False
                    await ctx.reply(embed=build_simple_embed(
                        f"**⏭  Skipped  —  {self.data['title']}  (`{get_duration(self.data['duration'])}`)**"
                    ))
        else:
            await ctx.reply(embed=build_simple_embed("**:x:  There is no song to skip.**", color=0xFF4757))

    # ── Stop ──────────────────────────────────────────────
    @commands.command(name='stop', aliases=['leave', 'disconnect'])
    async def stop_command(self, ctx: commands.Context):
        if ctx.author.voice is None:
            return
        if ctx.guild.get_member(self.bot.user.id) not in ctx.author.voice.channel.members:
            return

        if self.voice_client.is_playing() or self.voice_client.is_paused():
            if not self.data:
                await ctx.reply(embed=build_simple_embed("**⚠️  An error occurred.**"), delete_after=10)
            else:
                if self.data['user'] and (
                    self.data['user'] != ctx.author
                    and self.data['user'] in ctx.author.voice.channel.members
                ):
                    await ctx.reply(embed=build_simple_embed(
                        f"**:x:  Only the music requester ({self.data['user'].mention}) can use this command.**",
                        color=0xFF4757
                    ))
                else:
                    await self.voice_client.disconnect()
                    self.skip   = False
                    self.isloop = False
                    await ctx.reply(embed=build_simple_embed("**👋  Goodbye!**"))
        else:
            if self.voice_client:
                await self.voice_client.disconnect()
                self.skip   = False
                self.isloop = False
                await ctx.reply(embed=build_simple_embed("**👋  Goodbye!**"))
            else:
                await ctx.reply(embed=build_simple_embed(
                    "**:x:  I'm not connected to a voice channel.**",
                    color=0xFF4757
                ))

    # ── Voice state listener ───────────────────────────────
    @commands.Cog.listener()
    async def on_voice_state_update(self, member: Member, before: VoiceState, after: VoiceState):
        if member.id == self.bot.user.id:
            if after.channel is None:
                self.voice_client = None
                self.data = {}
            else:
                self.voice_client = utils.get(self.bot.voice_clients, guild=member.guild)


# ── Setup & run ───────────────────────────────────────────

async def on_setup():
    await bot.add_cog(Music(bot))

bot.setup_hook = on_setup

bot.run(getenv("DISCORD_TOKEN")) 