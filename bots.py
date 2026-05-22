import discord
from discord import app_commands
from discord.ext import commands
import os, asyncio, aiohttp, datetime, subprocess, random, string, io, json, re, gc, shutil
from pydub import AudioSegment
from pedalboard import (
    Pedalboard, Compressor, Gain, Limiter, LowShelfFilter, 
    HighShelfFilter, Distortion, Reverb, HighpassFilter, 
    PitchShift, Delay, NoiseGate, Bitcrush, Chorus, Phaser
)
from pedalboard.io import AudioFile
from PIL import Image, ImageSequence
from io import BytesIO
from typing import Literal, Optional
from flask import Flask
from threading import Thread

# --- AUTO-INSTALL DEPENDENCIES IF MISSING ---
try:
    import yt_dlp
except ImportError:
    import sys
    subprocess.check_call([sys.executable, "-m", "pip", "install", "yt-dlp"])
    import yt_dlp

try:
    import spotdl
except ImportError:
    import sys
    subprocess.check_call([sys.executable, "-m", "pip", "install", "spotdl"])

# --- RENDER HEALTH CHECK KEEP-ALIVE SERVER ---
app = Flask('')

@app.route('/')
def home():
    return "Bot is online and responding to Render health checks."

def run_web_server():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run_web_server)
    t.daemon = True
    t.start()

# --- CONFIG & ASSETS ---
TOKEN = os.getenv('DISCORD_TOKEN')
if not TOKEN:
    raise ValueError("CRITICAL: DISCORD_TOKEN environment variable is missing!")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SEARCH_DIRS = [
    os.path.join(d, "assets") if os.path.isdir(os.path.join(BASE_DIR, "assets")) else BASE_DIR for d in [BASE_DIR]
]

FFMPEG_BIN = os.path.join(BASE_DIR, "ffmpeg")
if os.name == 'nt' and not FFMPEG_BIN.endswith('.exe'): 
    FFMPEG_BIN += '.exe'

if os.path.exists(FFMPEG_BIN):
    AudioSegment.converter = FFMPEG_BIN
else:
    AudioSegment.converter = "ffmpeg"

AUTH_DATA = {} 
EMOJI_POOL = list("😀😃😄😁😆😅😂🤣☺️😇🙂🙃😉😍😘😗😙😋😛😝😜🤪🤨🧐🤓😎🤩😏😒😞😔😟😕🙁☹️😣😖😫😩😢😭😤😠😡🤬🤯😳😱😨😰😥😓🤗🤔🤭🤫🤥😶😐😑😬🙄😯😦😧😮😲⚠️⚡🔥")

E_MOD = "<a:mod:1506265969562226738>"
E_LDING = "<a:lding:1506265760631099452>"
E_SUCCESS = "<a:success:1506265759452631082>"
E_FAILED = "<a:failed:1506265787900579994>"

ALLOWED_EMOJI_USERS = {1317324380291862659, 1495521117115256962}
ADMIN_IDS = {1317324380291862659, 1495521117115256962}

BAIT_MAP = {
    "1": {"files": ["uno.mp3", "dos.mp3"], "type": "sandwich"},
    "2": {"files": ["baitupd.mp3"], "type": "start"},
    "3": {"files": ["loud audios.ogg"], "type": "start"},
    "4": {"files": ["past final.mp3"], "type": "start"},
    "5": {"files": ["beep bait.mp3"], "type": "start"},
    "6": {"files": ["bait_output.mp3"], "type": "start"},
    "7": {"files": ["Cinematic 3rd hun_cs bait.mp3"], "type": "start"},
    "8": {"files": ["Cinematic Epic Music by Infraction [No Copyright Music] Action TPOS 211.mp3"], "type": "start"},
    "9": {"files": ["Cinematic Epic Music by Infraction, 2025 THEME BAIT HUN_CS.mp3"], "type": "start"},
    "10": {"files": ["cinema__a_half_louder.mp3"], "type": "start"},
    "11": {"files": ["HUN_Cs's 3rd cinematic bait for hungarian gang.mp3"], "type": "start"},
    "12": {"files": ["SHORTEST BAIT.mp3", "alex_besss-movie-trailer-501295 (1).mp3"], "type": "sandwich"},
    "13": {"files": ["p4w3l bait.mp3"], "type": "start"},
    "14": {"files": ["my bait.mp3"], "type": "start"},
    "15": {"files": ["remember1.mp3", "remember2.mp3"], "type": "sandwich"},
    "16": {"files": ["lofi1.mp3", "lofi2.mp3"], "type": "sandwich"},
    "17": {"files": ["LOL1.mp3", "LOL2.mp3"], "type": "sandwich"},
    "18": {"files": ["acoolbaitHAHA1.mp3", "acoolbaitHAHA2.mp3"], "type": "sandwich"},
    "19": {"files": ["co-1.mp3", "co-2.mp3"], "type": "sandwich"}
}

class ZeptiV77(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        self.session = aiohttp.ClientSession(connector=aiohttp.TCPConnector(limit=0, ttl_dns_cache=300))
        await self.tree.sync()

    async def on_ready(self):
        print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] Zepti_W V77.0: ONLINE")

bot = ZeptiV77()

# --- HELPER FUNCTIONS ---
def get_uid(l=8): return ''.join(random.choices(string.ascii_letters + string.digits, k=l))

def find_file(filename):
    if os.path.exists(filename): return filename
    for d in SEARCH_DIRS:
        p = os.path.join(d, filename)
        if os.path.exists(p): return p
    return None

def get_loud_preset(pid):
    presets = {
        "1": Pedalboard([Compressor(-10, 10), Gain(17.9), LowShelfFilter(250, -6), HighShelfFilter(4000, 3), Gain(2), Limiter(-9.3)]),
        "2": Pedalboard([Gain(10), Distortion(5), Compressor(-20, 4)]),
        "3": Pedalboard([LowShelfFilter(100, 12), Gain(5), Limiter(-1)]),
        "4": Pedalboard([HighpassFilter(300), Gain(15), Distortion(2)]),
        "5": Pedalboard([Bitcrush(8), Gain(10), Limiter(-0.5)]),
        "6": Pedalboard([Reverb(room_size=0.5), Gain(5)]),
        "7": Pedalboard([Phaser(), Chorus(), Gain(8)]),
        "8": Pedalboard([Delay(0.25), Gain(4)]),
        "9": Pedalboard([HighShelfFilter(3000, 10), Gain(12)]),
        "10": Pedalboard([LowShelfFilter(150, 15), Gain(10)]),
        "11": Pedalboard([Compressor(-13.3, 13), Gain(20.8), Gain(26.8)]),
        "12": Pedalboard([NoiseGate(), Compressor(-30, 20), Gain(15)]),
        "13": Pedalboard([Gain(35), Limiter(-0.1), Distortion(10)])
    }
    return presets.get(str(pid), presets["1"])

def get_preset_title(style, index, custom_name):
    letters = string.ascii_letters
    nums = string.digits
    syms = string.punctuation
    if style == "Chaos (Symbols/Letters)": return "".join(random.choice(letters + nums + syms) for _ in range(20))
    if style == "Emoji Heavy": return "".join(random.choice(EMOJI_POOL) for _ in range(20))
    if style == "Uppercase & Lowercase": return "".join(random.choice(letters) for _ in range(20))
    if style == "Numbers Only": return "".join(random.choice(nums) for _ in range(15))
    if style == "No Suffix (Clean)": return custom_name
    if style.startswith("withoutnumber-"): return style.replace("withoutnumber-", "")
    return f"{custom_name}{index}"

async def async_process_ffmpeg(ip, idx, batch_stutter, scramble_enabled):
    u = get_uid()
    op = f"v_out_{u}_{idx}.mp3"
    warp = random.uniform(0.99, 1.01)
    jitter = random.uniform(-5, 5)
    target_rate = int(44100 * warp + jitter)
    
    cmd = [
        'ffmpeg', '-y', '-i', ip,
        '-af', f'asetrate={target_rate},aresample=44100,aloop=loop={idx}:size={int(batch_stutter * 44.1)}:start=0',
        '-b:a', '192k', op
    ]
    
    proc = await asyncio.create_subprocess_exec(*cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    await proc.communicate()
    
    if os.path.exists(op):
        with open(op, 'rb') as f:
            data = bytearray(f.read())
        try: os.remove(op)
        except: pass
        
        if scramble_enabled:
            if len(data) > 2000:
                for _ in range(4):
                    pos = random.randint(500, len(data) - 500)
                    data[pos:pos] = os.urandom(random.randint(4, 12))
            data.extend(os.urandom(random.randint(64, 256)))
        return bytes(data)
    return None

async def upload_burst(session, data, name, api_key, target_id, creator_key, live_status_callback):
    url = "https://apis.roblox.com/assets/v1/assets"
    current_delay = 0.5
    
    for attempt in range(1, 10):
        form = aiohttp.FormData(quote_fields=False)
        form.add_field('request', json.dumps({
            "assetType": "Audio", "displayName": name, "description": "zepti_W",
            "creationContext": {"creator": {creator_key: str(target_id)}}
        }), content_type='application/json')
        form.add_field('fileContent', data, filename='audio.mp3', content_type='audio/mpeg')
        
        try:
            async with session.post(url, data=form, headers={'x-api-key': api_key}, timeout=15) as r:
                resp_text = await r.text()
                if r.status in [200, 201, 202]:
                    if "error" in resp_text.lower():
                        await live_status_callback(success=False, name=name, detail="API Internal Drop", asset_id=None, op_id=None)
                        return False
                        
                    try:
                        parsed = json.loads(resp_text)
                        operation_path = parsed.get("path")
                        op_id = "Unknown Op"
                        if operation_path:
                            match = re.search(r'operations/([a-fA-H0-9\-]+)', operation_path)
                            if match: op_id = match.group(1)

                        if operation_path:
                            op_url = f"https://apis.roblox.com/assets/v1/{operation_path}"
                            asset_id = None
                            
                            for _ in range(12): 
                                await asyncio.sleep(1.5)
                                async with session.get(op_url, headers={'x-api-key': api_key}) as op_r:
                                    if op_r.status == 200:
                                        op_parsed = json.loads(await op_r.text())
                                        
                                        if op_parsed.get("error"):
                                            err_detail = op_parsed.get("error", {}).get("message", "Operation Processing Failed")
                                            await live_status_callback(success=False, name=name, detail=err_detail, asset_id=None, op_id=op_id)
                                            return False
                                            
                                        if op_parsed.get("done") is True:
                                            asset_id = op_parsed.get("response", {}).get("assetId")
                                            if asset_id:
                                                break
                            
                            if not asset_id:
                                asset_id = "Pending Timeout"
                        else:
                            asset_id = parsed.get("assetId", "Unknown ID")
                    except Exception as e:
                        asset_id = "Parsing Error"
                        
                    if asset_id in ["Pending Timeout", "Parsing Error"]:
                        await live_status_callback(success=False, name=name, detail=asset_id, asset_id=None, op_id=op_id)
                        return False
                        
                    await live_status_callback(success=True, name=name, detail=None, asset_id=asset_id, op_id=op_id)
                    return True
                elif r.status == 429:
                    await asyncio.sleep(current_delay)
                    current_delay = min(current_delay * 1.5, 5.0)
                else:
                    try: err_msg = json.loads(resp_text).get("message", resp_text)
                    except: err_msg = resp_text
                    await live_status_callback(success=False, name=name, detail=f"HTTP {r.status}: {err_msg}", asset_id=None, op_id=None)
                    if r.status in [401, 403, 400]: return False
        except:
            await asyncio.sleep(0.5)
            
    await live_status_callback(success=False, name=name, detail="Retries Exhausted", asset_id=None, op_id=None)
    return False

# --- BOT COMMANDS ---

@bot.tree.command(name="emojiwhitelist", description="Manages permission whitelist for the emoji command")
@app_commands.describe(action="Action to perform", user="The target discord user")
async def emoji_whitelist_manager(interaction: discord.Interaction, action: Literal["add", "remove"], user: discord.User):
    if interaction.user.id not in ADMIN_IDS:
        return await interaction.response.send_message(content=f"{E_FAILED} Unauthorized.", ephemeral=True)
    await interaction.response.defer(ephemeral=True)
    if action == "add":
        ALLOWED_EMOJI_USERS.add(user.id)
        await interaction.followup.send(content=f"{E_SUCCESS} Added **{user.name}**.", ephemeral=True)
    elif action == "remove":
        if user.id in ADMIN_IDS: return await interaction.followup.send(content=f"{E_FAILED} Cannot remove Admin.", ephemeral=True)
        ALLOWED_EMOJI_USERS.discard(user.id)
        await interaction.followup.send(content=f"{E_SUCCESS} Removed **{user.name}**.", ephemeral=True)

@bot.tree.command(name="emoji", description="Uploads an image or GIF to server's custom emojis")
@app_commands.describe(name="Emoji name", file="File to upload (Max 256KB)")
async def create_server_emoji(interaction: discord.Interaction, name: str, file: discord.Attachment):
    if interaction.user.id not in ALLOWED_EMOJI_USERS: return await interaction.response.send_message(content=f"{E_FAILED} Unauthorized.", ephemeral=True)
    if not interaction.guild: return await interaction.response.send_message(content=f"{E_FAILED} Run this in a server.", ephemeral=True)
    if file.size > 256000: return await interaction.response.send_message(content=f"{E_FAILED} File exceeds max 256KB constraint.")
    await interaction.response.defer()
    status_msg = await interaction.followup.send(content=f"{E_LDING} Processing image payload...")
    try:
        img_bytes = await file.read()
        new_emoji = await interaction.guild.create_custom_emoji(name=name, image=img_bytes)
        await status_msg.edit(content=f"{E_SUCCESS} Emoji uploaded! {new_emoji}")
    except Exception as e:
        await status_msg.edit(content=f"{E_FAILED} Error: {str(e)}")

@bot.tree.command(name="api", description="Links your Roblox Open Cloud API Key")
@app_commands.describe(key="Roblox Asset API Key", target_id="User or Group ID destination", is_group="Is group ID")
async def api_setup(interaction: discord.Interaction, key: str, target_id: str, is_group: bool):
    await interaction.response.defer(ephemeral=True)
    AUTH_DATA[interaction.user.id] = {"apikey": key, "targetId": str(target_id), "isGroup": is_group}
    await interaction.followup.send(content=f"{E_SUCCESS} Linked to Destination ID: **{target_id}**.", ephemeral=True)

@bot.tree.command(name="massupload", description="Modifies and batch uploads 10 copies concurrently to Roblox")
@app_commands.describe(audio_file="Sound asset to upload", title="Display name prefix", style="Randomizer style pattern", scramble="Enable binary scrambling")
async def massupload(
    interaction: discord.Interaction, 
    audio_file: discord.Attachment, 
    title: str, 
    style: Literal["Default", "Chaos (Symbols/Letters)", "Emoji Heavy", "Uppercase & Lowercase", "Numbers Only", "No Suffix (Clean)"] = "Default",
    scramble: bool = True
):
    if interaction.user.id not in AUTH_DATA: return await interaction.response.send_message(content=f"{E_FAILED} Use /api first.", ephemeral=True)
    try: await interaction.response.defer()
    except discord.errors.NotFound: return
        
    status_msg = await interaction.followup.send(content=f"{E_LDING} Writing temporary source audio configurations...")
    acc = AUTH_DATA[interaction.user.id]
    
    u_init = get_uid()
    tmp_input = f"raw_in_{u_init}.mp3"
    await audio_file.save(tmp_input)

    batch_stutter = random.randint(40, 220)
    await status_msg.edit(content=f"{E_LDING} Building variation array streams safely...")
    
    prepared_payload_data = []
    for idx in range(1, 11):
        variant = await async_process_ffmpeg(tmp_input, idx, batch_stutter, scramble)
        if variant:
            prepared_payload_data.append(variant)
    
    try: os.remove(tmp_input)
    except: pass

    payloads = []
    for idx, data in enumerate(prepared_payload_data, 1):
        payloads.append((get_preset_title(style, idx, title), data))
            
    if not payloads:
        await status_msg.edit(content=f"{E_FAILED} Audio variant transformations dropped or collapsed.")
        return

    creator_key = "groupId" if acc["isGroup"] else "userId"
    total_payloads = len(payloads)
    processed_count = success_count = failed_count = 0
    status_lines = []
    accepted_assets_summary = []
    lock = asyncio.Lock()
    last_ui_update = 0
    
    async def status_update_worker(success: bool, name: str, detail: Optional[str] = None, asset_id: Optional[str] = None, op_id: Optional[str] = None):
        nonlocal processed_count, success_count, failed_count, last_ui_update
        async with lock:
            processed_count += 1
            if success:
                success_count += 1
                line = f"<a:success:1506265759452631082> Fully Pended! [{name}]"
                accepted_assets_summary.append({"name": name, "asset_id": asset_id, "op_id": op_id})
            else:
                failed_count += 1
                err_suffix = f" ({detail})" if detail else ""
                line = f"<a:failed:1506265787900579994> Failed! [{name}]{err_suffix}"
                
            status_lines.append(line)
            now = datetime.datetime.now().timestamp()
            if (now - last_ui_update > 2.0) or (processed_count == total_payloads):
                last_ui_update = now
                try: await status_msg.edit(content=f"**Processing Dispatch Array:** ({processed_count}/{total_payloads})\n" + "\n".join(status_lines))
                except: pass

    await status_msg.edit(content=f"{E_LDING} Burst dispatching and tracking operations pipeline (This takes a moment)...")
    
    upload_tasks = []
    for d_name, data in payloads:
        upload_tasks.append(upload_burst(bot.session, data, d_name, acc["apikey"], acc["targetId"], creator_key, status_update_worker))
        await asyncio.sleep(0.15)
        
    await asyncio.gather(*upload_tasks)
        
    if success_count == 0:
        await interaction.channel.send(f"{E_FAILED} All variations failed processing filters.")
    else:
        summary_lines = [
            f"**__Mass Upload Session Finalization Stats__**",
            f"📊 `Total: {total_payloads}` | ✅ `Success: {success_count}` | ❌ `Dropped: {failed_count}` | 📈 `Pass: {int((success_count/total_payloads)*100)}%`",
            f"\n**__Accepted Asset Inventory Details:__**"
        ]
        
        for idx, item in enumerate(accepted_assets_summary, 1):
            summary_lines.append(
                f"**{idx}.** `{item['name']}` 🔗 **ID:** `{item['asset_id']}` 🛠️ **Op:** `{item['op_id']}`"
            )
        
        await interaction.channel.send("\n".join(summary_lines))

@bot.tree.command(name="method", description="Processes audio through complex phase loops")
@app_commands.describe(audio_file="The source sound asset")
async def bypass_method(interaction: discord.Interaction, audio_file: discord.Attachment):
    try: await interaction.response.defer(ephemeral=True)
    except discord.errors.NotFound: return
    class MethodSelect(discord.ui.Select):
        async def callback(self, i: discord.Interaction):
            await i.response.defer()
            progress_msg = await i.followup.send(content=f"{E_LDING} Processing...")
            u = get_uid(); ip, op = f"mi_{u}.mp3", f"mo_{u}.ogg"
            await audio_file.save(ip)
            try:
                if self.values[0] == "8d":
                    cmd = ['ffmpeg', '-y', '-i', ip, '-af', "aphaser=in_gain=0.6:out_gain=1:delay=2:decay=0.4:speed=0.5:type=t,apulsator=mode=sine:hz=0.2:amount=1", '-c:a', 'libvorbis', '-q:a', '5', op]
                    proc = await asyncio.create_subprocess_exec(*cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    await proc.communicate()
                    if os.path.exists(op):
                        await progress_msg.edit(content=f"{E_MOD} **8D Audio Activated**")
                        await i.followup.send(file=discord.File(op))
                    else: await progress_msg.edit(content=f"{E_FAILED} Method failed.")
                elif self.values[0] == "copyright":
                    cmd = ['ffmpeg', '-y', '-i', ip, '-af', "asetrate=48000*0.925,atempo=1.10,atempo=0.92,atempo=1.07,atempo=1.07,atempo=1.07", '-c:a', 'libvorbis', '-q:a', '4', op]
                    proc = await asyncio.create_subprocess_exec(*cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    await proc.communicate()
                    if os.path.exists(op):
                        await progress_msg.edit(content=f"{E_MOD} **Copyright Bypass Activated**")
                        await i.followup.send(file=discord.File(op))
                    else: await progress_msg.edit(content=f"{E_FAILED} Method failed.")
            except: await progress_msg.edit(content=f"{E_FAILED} Error running filter.")
            [os.remove(f) for f in [ip, op] if os.path.exists(f)]
    v = discord.ui.View(); v.add_item(MethodSelect(placeholder="Choose Bypass Method", options=[discord.SelectOption(label="8D Audio", value="8d"), discord.SelectOption(label="Copyright Bypass", value="copyright")]))
    await interaction.followup.send(content=f"{E_MOD} Select Method:", view=v)

@bot.tree.command(name="mp3", description="Downloads web audio links cleanly (Bypasses Spotify DRM with spotdl)")
@app_commands.describe(url="Web url link to extract audio from")
async def mp3_dl(interaction: discord.Interaction, url: str):
    await interaction.response.defer()
    status_msg = await interaction.followup.send(content=f"{E_LDING} Stream scraping audio streams (Optimized)...")
    uid = get_uid()
    
    if "spotify.com" in url.lower():
        try:
            tmp_spot_dir = f"spot_{uid}"
            os.makedirs(tmp_spot_dir, exist_ok=True)
            
            cmd = ['spotdl', 'download', url, '--output', f"{tmp_spot_dir}/track.mp3"]
            proc = await asyncio.create_subprocess_exec(*cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            try:
                await asyncio.wait_for(proc.communicate(), timeout=40)
            except asyncio.TimeoutError:
                proc.kill()
                raise asyncio.TimeoutError("Spotify extraction timed out.")

            expected_file = f"{tmp_spot_dir}/track.mp3"
            if os.path.exists(expected_file):
                await status_msg.edit(content=f"{E_SUCCESS} Downloaded and wrapped Spotify track format.")
                await interaction.followup.send(file=discord.File(expected_file))
                os.remove(expected_file)
                os.rmdir(tmp_spot_dir)
            else:
                await status_msg.edit(content=f"{E_FAILED} Output structural build dropped by spotdl search.")
                if os.path.exists(tmp_spot_dir):
                    shutil.rmtree(tmp_spot_dir)
        except Exception as e:
            await status_msg.edit(content=f"{E_FAILED} Failed SpotDL: {e}")
            if os.path.exists(f"spot_{uid}"):
                shutil.rmtree(f"spot_{uid}")
            
    else:
        template_path = f"m_{uid}"
        final_filename = f"m_{uid}.mp3"
        try:
            async def run_with_timeout():
                def dl():
                    ydl_opts = {
                        'format': 'ba/w',
                        'outtmpl': template_path,
                        'postprocessors': [{
                            'key': 'FFmpegExtractAudio',
                            'preferredcodec': 'mp3',
                            'preferredquality': '128',
                        }],
                        'extractor_args': {'youtubetab': {'skip': ['authcheck']}},
                        'http_headers': {
                            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
                        },
                        'quiet': True,
                        'no_warnings': True
                    }
                    cookie_file = os.path.join(BASE_DIR, "cookies.txt")
                    if os.path.exists(cookie_file): ydl_opts['cookiefile'] = cookie_file
                    with yt_dlp.YoutubeDL(ydl_opts) as ydl: ydl.download([url])
                await asyncio.get_event_loop().run_in_executor(None, dl)

            await asyncio.wait_for(run_with_timeout(), timeout=40)
            
            if os.path.exists(final_filename):
                await status_msg.edit(content=f"{E_SUCCESS} Downloaded and wrapped target track format.")
                await interaction.followup.send(file=discord.File(final_filename))
                os.remove(final_filename)
            else: 
                await status_msg.edit(content=f"{E_FAILED} Output structural build dropped by extractor.")
        except asyncio.TimeoutError:
            await status_msg.edit(content=f"{E_FAILED} Extraction timed out. Server IP is currently restricted by platform provider.")
        except Exception as e: 
            await status_msg.edit(content=f"{E_FAILED} Failed: {e}")

@bot.tree.command(name="loudset", description="Alters audio using mastering presets")
@app_commands.describe(audio_file="The sound asset to master")
async def loudset(interaction: discord.Interaction, audio_file: discord.Attachment):
    try: await interaction.response.defer(ephemeral=True)
    except discord.errors.NotFound: return
    class P(discord.ui.Select):
        async def callback(self, i):
            await i.response.defer()
            progress_msg = await i.followup.send(content=f"{E_LDING} Processing...")
            u = get_uid(); ip, op = f"li_{u}.mp3", f"lo_{u}.ogg"
            await audio_file.save(ip)
            try:
                if self.values[0] == "13":
                    cmd = ['ffmpeg', '-y', '-i', ip, '-af', 'volume=35dB,alimiter=level_in=1:level_out=0.99:limit=-0.1dB:attack=5:release=50:aperiodic=1', op]
                    proc = await asyncio.create_subprocess_exec(*cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    await proc.communicate()
                else:
                    def proc():
                        with AudioFile(ip) as af: rs = get_loud_preset(self.values[0])(af.read(af.frames), af.samplerate)
                        tw = f"lt_{u}.wav"
                        with AudioFile(tw, 'w', af.samplerate, rs.shape[0]) as o: o.write(rs)
                        AudioSegment.from_file(tw).export(op, format="ogg"); os.remove(tw)
                    await asyncio.get_event_loop().run_in_executor(None, proc)
                if os.path.exists(op):
                    await progress_msg.edit(content=f"{E_MOD} **Loud Preset {self.values[0]} Processed**")
                    await i.followup.send(file=discord.File(op))
                else: await progress_msg.edit(content=f"{E_FAILED} File generation failed.")
            except: await progress_msg.edit(content=f"{E_FAILED} Processing failed.")
            [os.remove(f) for f in [ip, op] if os.path.exists(f)]
    v = discord.ui.View(); v.add_item(P(options=[discord.SelectOption(label=f"Preset {x}", value=str(x)) for x in range(1,14)]))
    await interaction.followup.send(content=f"{E_MOD} Select Preset:", view=v)

@bot.tree.command(name="macro", description="Parses raw exported Audacity macro TXT settings")
@app_commands.describe(audio_file="Target asset file", macro_file="The macro text file (.txt)")
async def macro(interaction: discord.Interaction, audio_file: discord.Attachment, macro_file: discord.Attachment):
    try: await interaction.response.defer()
    except discord.errors.NotFound: return
    status_msg = await interaction.followup.send(content=f"{E_LDING} Processing...")
    u = get_uid(); ip, op = f"mi_{u}.mp3", f"mo_{u}.ogg"
    macro_text = (await macro_file.read()).decode('utf-8', errors='ignore'); await audio_file.save(ip)
    effects = []
    if 'Compressor:' in macro_text:
        m = re.search(r'Threshold="(-?\d+)"', macro_text)
        effects.append(Compressor(threshold_db=float(m.group(1)) if m else -30.0, ratio=10.0))
    if 'Sc4:' in macro_text:
        m = re.search(r'Makeup_gain_\(dB\)="(\d+\.?\d*)"', macro_text)
        effects.append(Gain(gain_db=float(m.group(1)) if m else 14.0))
    if 'High-passFilter:' in macro_text:
        m = re.search(r'FREQUENCY="(\d+)"', macro_text)
        effects.append(HighpassFilter(cutoff_frequency_hz=float(m.group(1)) if m else 120.0))
    def run():
        with AudioFile(ip) as af: pr = Pedalboard(effects)(af.read(af.frames), af.samplerate)
        tw = f"mt_{u}.wav"
        with AudioFile(tw, 'w', af.samplerate, pr.shape[0]) as o: o.write(pr)
        subprocess.run(['ffmpeg', '-i', tw, '-c:a', 'libvorbis', '-q:a', '0', op, '-y'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL); os.remove(tw)
    await asyncio.get_event_loop().run_in_executor(None, run)
    if os.path.exists(op):
        await status_msg.edit(content=f"{E_SUCCESS} Macro applied.")
        await interaction.followup.send(file=discord.File(op))
    else: await status_msg.edit(content=f"{E_FAILED} Macro applied failed.")
    [os.remove(f) for f in [ip, op] if os.path.exists(f)]

@bot.tree.command(name="pitch", description="Shifts playback rate of an audio file")
@app_commands.describe(audio_file="Sound asset to modify", val="Pitch factor multiplier")
async def pitch(interaction: discord.Interaction, audio_file: discord.Attachment, val: float):
    try: await interaction.response.defer()
    except discord.errors.NotFound: return
    status_msg = await interaction.followup.send(content=f"{E_LDING} Processing...")
    u = get_uid(); ip, op = f"pi_{u}.mp3", f"po_{u}.ogg"
    await audio_file.save(ip)
    def run(): subprocess.run(['ffmpeg', '-i', ip, '-af', f"asetrate={int(44100*val)},aresample=44100", '-c:a', 'libvorbis', '-q:a', '5', op, '-y'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    await asyncio.get_event_loop().run_in_executor(None, run)
    if os.path.exists(op):
        await status_msg.edit(content=f"{E_SUCCESS} Shifted Pitch perfectly.")
        await interaction.followup.send(file=discord.File(op))
    else: await status_msg.edit(content=f"{E_FAILED} Pitch alteration failed.")
    [os.remove(f) for f in [ip, op] if os.path.exists(f)]

@bot.tree.command(name="tpos", description="Conjoins a bait segment cleanly in front of main track")
@app_commands.describe(bait="Introductory sound asset", main="Primary track asset")
async def tpos(interaction: discord.Interaction, bait: discord.Attachment, main: discord.Attachment):
    try: await interaction.response.defer()
    except discord.errors.NotFound: return
    status_msg = await interaction.followup.send(content=f"{E_LDING} Processing...")
    u = get_uid(); bp, mp, op = f"b_{u}.mp3", f"m_{u}.mp3", f"t_{u}.ogg"
    await bait.save(bp); await main.save(mp)
    def run(): (AudioSegment.from_file(bp) + AudioSegment.from_file(mp)).export(op, format="ogg")
    await asyncio.get_event_loop().run_in_executor(None, run)
    if os.path.exists(op):
        await status_msg.edit(content=f"{E_SUCCESS} Track structured cleanly.")
        await interaction.followup.send(file=discord.File(op))
    else: await status_msg.edit(content=f"{E_FAILED} Injection build failed.")
    [os.remove(f) for f in [bp, mp, op] if os.path.exists(f)]

@bot.tree.command(name="bait", description="Mixes track into pre-existing template option path")
@app_commands.describe(choice="Template choice ID", audio_file="Main audio file")
async def bait(
    interaction: discord.Interaction, 
    choice: Literal["1","2","3","4","5","6","7","8","9","10","11","12","13","14","15","16","17","18","19"], 
    audio_file: discord.Attachment
):
    try: await interaction.response.defer()
    except discord.errors.NotFound: return
    status_msg = await interaction.followup.send(content=f"{E_LDING} Processing...")
    u = get_uid(); ip, op = f"bi_{u}.mp3", f"bo_{u}.ogg"
    await audio_file.save(ip)
    cfg = BAIT_MAP[choice]
    def run_bait_mixing():
        main_track = AudioSegment.from_file(ip)
        bait1_path = find_file(cfg["files"][0])
        if not bait1_path: raise FileNotFoundError(f"Missing base template asset: {cfg['files'][0]}")
        bait_track1 = AudioSegment.from_file(bait1_path)
        if cfg.get("type") == "sandwich":
            bait2_path = find_file(cfg["files"][1])
            if not bait2_path: raise FileNotFoundError(f"Missing end template asset: {cfg['files'][1]}")
            bait_track2 = AudioSegment.from_file(bait2_path)
            res = bait_track1 + main_track + bait_track2
        else: res = bait_track1 + main_track
        res[:419999].export(op, format="ogg")
    try:
        await asyncio.get_event_loop().run_in_executor(None, run_bait_mixing)
        if os.path.exists(op):
            await status_msg.edit(content=f"{E_SUCCESS} File mixed cleanly.")
            await interaction.followup.send(file=discord.File(op))
        else: await status_msg.edit(content=f"{E_FAILED} Build combination failed.")
    except Exception as e: await status_msg.edit(content=f"{E_FAILED} Processing failed: {str(e)}")
    [os.remove(f) for f in [ip, op] if os.path.exists(f)]

if __name__ == "__main__":
    keep_alive()
    bot.run(TOKEN)
