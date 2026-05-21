import discord
from discord import app_commands
from discord.ext import commands
import os, asyncio, aiohttp, datetime, subprocess, random, string, io, json, re, gc
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
from concurrent.futures import ThreadPoolExecutor

# --- AUTO-INSTALL YT-DLP IF MISSING ---
try:
    import yt_dlp
except ImportError:
    import sys
    subprocess.check_call([sys.executable, "-m", "pip", "install", "yt-dlp"])
    import yt_dlp

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

# --- CRITICAL FFMPEG FIX FOR PYDUB (RENDER COMPATIBLE) ---
FFMPEG_BIN = os.path.join(BASE_DIR, "ffmpeg")
if os.name == 'nt' and not FFMPEG_BIN.endswith('.exe'): 
    FFMPEG_BIN += '.exe'

# Fallback to system-installed paths if the local directory binary is missing
if os.path.exists(FFMPEG_BIN):
    AudioSegment.converter = FFMPEG_BIN
else:
    AudioSegment.converter = "ffmpeg"

AUTH_DATA = {} 
EMOJI_POOL = list("😀😃😄😁😆😅😂🤣☺️😇🙂🙃😉😍😘😗😙😋😛😝😜🤪🤨🧐🤓😎🤩😏😒😞😔😟😕🙁☹️😣😖😫😩😢😭😤😠😡🤬🤯😳😱😨😰😥😓🤗🤔🤭🤫🤥😶😐😑😬🙄😯😦😧😮😲⚠️⚡🔥")

# Fixed Application Emoji Formatting
E_MOD = "<a:mod:1506265969562226738>"
E_LDING = "<a:lding:1506265760631099452>"
E_SUCCESS = "<a:success:1506265759452631082>"
E_FAILED = "<a:failed:1506265787900579994>"

# Dynamic Whitelist & Administrators
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
    "17": {"files": ["LOL1.mp3", "LOL2.mp3"], "type": "sandwich"}
}

class ZeptiV77(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        # Keeps persistent connector live for rapid requests
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
    
    if style == "Chaos (Symbols/Letters)": 
        chars = letters + nums + syms
        return "".join(random.choice(chars) for _ in range(20))
    if style == "Emoji Heavy": 
        return "".join(random.choice(EMOJI_POOL) for _ in range(20))
    if style == "Uppercase & Lowercase": 
        return "".join(random.choice(letters) for _ in range(20))
    if style == "Numbers Only": 
        return "".join(random.choice(nums) for _ in range(15))
    if style == "No Suffix (Clean)": 
        return custom_name
    if style.startswith("withoutnumber-"):
        return style.replace("withoutnumber-", "")
        
    return f"{custom_name}{index}"

def scramble_binary(raw_data: bytearray):
    if len(raw_data) > 2000:
        for _ in range(8):
            insert_pos = random.randint(500, len(raw_data) - 500)
            raw_data[insert_pos:insert_pos] = os.urandom(random.randint(4, 16))
    raw_data.extend(os.urandom(random.randint(128, 512)))
    return bytes(raw_data)

# --- COOLDOWN VARIATIONS WORKER ---
def core_process_worker(base_segment, i, batch_stutter_ms, scramble_enabled):
    try:
        audio = base_segment + 0
        warp = random.uniform(0.99, 1.01)
        audio = audio._spawn(audio.raw_data, overrides={"frame_rate": int(audio.frame_rate * warp)})
        audio = audio.set_frame_rate(44100)

        jitter_val = random.uniform(-5, 5)
        audio = audio.set_frame_rate(int(audio.frame_rate + jitter_val))
        
        stutter = audio[:batch_stutter_ms] * i 
        audio = stutter + audio

        buf = io.BytesIO()
        audio.export(buf, format="mp3", bitrate="192k", tags={'comment': os.urandom(8).hex()})
        raw_data = bytearray(buf.getvalue())
        
        if scramble_enabled:
            raw_data = bytearray(scramble_binary(raw_data))
            
        final_val = bytes(raw_data)
        del audio, raw_data, buf
        gc.collect()
        return final_val
    except Exception as e:
        print(f"[Processing Error] Task {i} failed: {e}")
        return None

# --- FIRE AND FORGET OUTBOUND UPLOADER LOOP ---
async def upload_burst(session, data, name, api_key, target_id, creator_key, idx, live_status_callback):
    url = "https://apis.roblox.com/assets/v1/assets"
    current_delay = 0.25  # Lowered delay for extreme speed boost
    
    for attempt in range(1, 20):
        form = aiohttp.FormData(quote_fields=False)
        form.add_field('request', json.dumps({
            "assetType": "Audio", "displayName": name, "description": "zepti_W",
            "creationContext": {"creator": {creator_key: str(target_id)}}
        }), content_type='application/json')
        form.add_field('fileContent', data, filename=f'{os.urandom(4).hex()}.mp3', content_type='audio/mpeg')

        try:
            async with session.post(url, data=form, headers={'x-api-key': api_key}, timeout=12) as r:
                resp_text = await r.text()
                if r.status in [200, 201, 202]:
                    await live_status_callback(success=True, name=name)
                    return True
                elif r.status == 429:
                    await asyncio.sleep(current_delay)
                    current_delay = min(current_delay * 1.3, 4.0)
                else:
                    try:
                        err_msg = json.loads(resp_text).get("message", resp_text)
                    except:
                        err_msg = resp_text
                    await live_status_callback(success=False, name=name, detail=f"HTTP {r.status}: {err_msg}")
                    if r.status in [401, 403, 400]:
                        return False
        except Exception:
            await asyncio.sleep(0.25)
            
    await live_status_callback(success=False, name=name, detail="Retries Exhausted")
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
        if user.id in ADMIN_IDS:
            return await interaction.followup.send(content=f"{E_FAILED} Cannot remove Admin.", ephemeral=True)
        ALLOWED_EMOJI_USERS.discard(user.id)
        await interaction.followup.send(content=f"{E_SUCCESS} Removed **{user.name}**.", ephemeral=True)

@bot.tree.command(name="emoji", description="Uploads an image or GIF to server's custom emojis")
@app_commands.describe(name="Emoji name", file="File to upload (Max 256KB)")
async def create_server_emoji(interaction: discord.Interaction, name: str, file: discord.Attachment):
    if interaction.user.id not in ALLOWED_EMOJI_USERS:
        return await interaction.response.send_message(content=f"{E_FAILED} Unauthorized.", ephemeral=True)
    if not interaction.guild:
        return await interaction.response.send_message(content=f"{E_FAILED} Run this in a server.", ephemeral=True)
    if file.size > 256000:
         return await interaction.response.send_message(content=f"{E_FAILED} File exceeds max 256KB constraint.")
         
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
    if interaction.user.id not in AUTH_DATA: 
        return await interaction.response.send_message(content=f"{E_FAILED} Use /api first.", ephemeral=True)
    
    try:
        await interaction.response.defer()
    except discord.errors.NotFound:
        return
        
    status_msg = await interaction.followup.send(content=f"{E_LDING} Initializing conversions engine...")
    acc = AUTH_DATA[interaction.user.id]
    
    try:
        raw_audio_bytes = await audio_file.read()
        base_segment = AudioSegment.from_file(io.BytesIO(raw_audio_bytes))
    except Exception as e:
        await status_msg.edit(content=f"{E_FAILED} Pydub failed to decode file source: {e}")
        return

    batch_stutter_ms = random.randint(40, 250)
    loop = asyncio.get_running_loop()
    
    await status_msg.edit(content=f"{E_LDING} Generating audio modifications loop...")
    
    # Speed Optimization: Expanded Thread Pool worker capacity to handle variations layout simultaneously
    with ThreadPoolExecutor(max_workers=10) as pool:
        process_tasks = [
            loop.run_in_executor(pool, core_process_worker, base_segment, idx, batch_stutter_ms, scramble) 
            for idx in range(1, 11)
        ]
        prepared_payload_data = await asyncio.gather(*process_tasks)
    
    payloads = []
    for idx, data in enumerate(prepared_payload_data, 1):
        if data is not None:
            d_name = get_preset_title(style, idx, title)
            payloads.append((d_name, data, idx))
            
    if not payloads:
        await status_msg.edit(content=f"{E_FAILED} Audio variations transformation failed.")
        return

    creator_key = "groupId" if acc["isGroup"] else "userId"
    total_payloads = len(payloads)
    processed_count = 0
    success_count = 0
    status_lines = []
    lock = asyncio.Lock()
    last_ui_update = 0
    
    async def status_update_worker(success: bool, name: str, detail: Optional[str] = None):
        nonlocal processed_count, success_count, last_ui_update
        async with lock:
            processed_count += 1
            if success:
                success_count += 1
                emoji = "<a:success:1506265759452631082>"
                line = f"{emoji} Success! {success_count}/{total_payloads} uploaded! [{name}]"
            else:
                emoji = "<a:failed:1506265787900579994>"
                err_suffix = f" ({detail})" if detail else ""
                line = f"{emoji} Failed! {processed_count - success_count}/{total_payloads} dropped! [{name}]{err_suffix}"
                
            status_lines.append(line)
            
            now = datetime.datetime.now().timestamp()
            if (now - last_ui_update > 1.6) or (processed_count == total_payloads):
                last_ui_update = now
                current_dashboard = (
                    f"**Burst Upload Progression:** ({processed_count}/{total_payloads})\n"
                    + "\n".join(status_lines)
                )
                try:
                    await status_msg.edit(content=current_dashboard)
                except Exception:
                    pass

    # Speed Optimization: Uses global persistent connection framework instead of rebuilding custom instances
    upload_tasks = [
        upload_burst(bot.session, data, d_name, acc["apikey"], acc["targetId"], creator_key, idx, status_update_worker)
        for d_name, data, idx in payloads
    ]
    await asyncio.gather(*upload_tasks)
        
    if success_count > 0:
        await interaction.channel.send(f"✅ Open Cloud Process Complete. Successfully uploaded **{success_count}/{total_payloads}** assets.")
    else:
        await interaction.channel.send(f"❌ Batch Session terminated. All execution processes dropped or rejected.")

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
                    def run_8d():
                        subprocess.run(['ffmpeg', '-i', ip, '-af', "aphaser=in_gain=0.6:out_gain=1:delay=2:decay=0.4:speed=0.5:type=t,apulsator=mode=sine:hz=0.2:amount=1", '-c:a', 'libvorbis', '-q:a', '5', op, '-y'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    await asyncio.get_event_loop().run_in_executor(None, run_8d)
                    if os.path.exists(op):
                        await progress_msg.edit(content=f"{E_MOD} **8D Audio Activated**")
                        await i.followup.send(file=discord.File(op))
                    else:
                        await progress_msg.edit(content=f"{E_FAILED} Method failed.")
                elif self.values[0] == "copyright":
                    def run_copyright():
                        subprocess.run(['ffmpeg', '-i', ip, '-af', "asetrate=48000*0.925,atempo=1.10,atempo=0.92,atempo=1.07,atempo=1.07,atempo=1.07", '-c:a', 'libvorbis', '-q:a', '4', op, '-y'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    await asyncio.get_event_loop().run_in_executor(None, run_copyright)
                    if os.path.exists(op):
                        await progress_msg.edit(content=f"{E_MOD} **Copyright Bypass Activated**")
                        await i.followup.send(file=discord.File(op))
                    else:
                        await progress_msg.edit(content=f"{E_FAILED} Method failed.")
            except Exception:
                await progress_msg.edit(content=f"{E_FAILED} Error running filter.")
            [os.remove(f) for f in [ip, op] if os.path.exists(f)]

    v = discord.ui.View()
    v.add_item(MethodSelect(
        placeholder="Choose Bypass Method", 
        options=[
            discord.SelectOption(label="8D Audio", value="8d"),
            discord.SelectOption(label="Copyright Bypass", value="copyright")
        ]
    ))
    await interaction.followup.send(content=f"{E_MOD} Select Method:", view=v)

@bot.tree.command(name="mp3", description="Downloads web audio links cleanly")
@app_commands.describe(url="Web url link to extract audio from")
async def mp3_dl(interaction: discord.Interaction, url: str):
    await interaction.response.defer()
    status_msg = await interaction.followup.send(content=f"{E_LDING} Processing...")
    uid = get_uid()
    template_path = f"m_{uid}"
    final_filename = f"m_{uid}.mp3"
    
    try:
        def dl():
            ydl_opts = {
                'format': 'bestaudio/best',
                'outtmpl': template_path,
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
                'extractor_args': {
                    'youtubetab': {
                        'skip': ['authcheck']
                    }
                },
                # Fix: Mimics standard web interactions to prevent Render server IP blocking
                'http_headers': {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                    'Accept-Language': 'en-us,en;q=0.5',
                },
                'quiet': True,
                'no_warnings': True
            }
            cookie_file = os.path.join(BASE_DIR, "cookies.txt")
            if os.path.exists(cookie_file): ydl_opts['cookiefile'] = cookie_file
            with yt_dlp.YoutubeDL(ydl_opts) as ydl: ydl.download([url])
                
        await asyncio.get_event_loop().run_in_executor(None, dl)
        if os.path.exists(final_filename):
            await status_msg.edit(content=f"{E_SUCCESS} Successfully downloaded!")
            await interaction.followup.send(file=discord.File(final_filename))
            os.remove(final_filename)
        else:
            await status_msg.edit(content=f"{E_FAILED} Build output missing. Link might be restricted.")
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
                    def bypass_proc():
                        subprocess.run(['ffmpeg', '-y', '-i', ip, '-af', 'volume=35dB,alimiter=level_in=1:level_out=0.99:limit=-0.1dB:attack=5:release=50:aperiodic=1', op], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    await asyncio.get_event_loop().run_in_executor(None, bypass_proc)
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
                else:
                    await progress_msg.edit(content=f"{E_FAILED} File generation failed.")
            except Exception:
                await progress_msg.edit(content=f"{E_FAILED} Processing failed.")
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
    else:
        await status_msg.edit(content=f"{E_FAILED} Macro applied failed.")
    [os.remove(f) for f in [ip, op] if os.path.exists(f)]

@bot.tree.command(name="pitch", description="Shifts playback rate of an audio file")
@app_commands.describe(audio_file="Sound asset to modify", val="Pitch factor multiplier")
async def pitch(interaction: discord.Interaction, audio_file: discord.Attachment, val: float):
    try: await interaction.response.defer()
    except discord.errors.NotFound: return
        
    status_msg = await interaction.followup.send(content=f"{E_LDING} Processing...")
    u = get_uid(); ip, op = f"pi_{u}.mp3", f"po_{u}.ogg"
    await audio_file.save(ip)
    
    def run():
        subprocess.run(['ffmpeg', '-i', ip, '-af', f"asetrate={int(44100*val)},aresample=44100", '-c:a', 'libvorbis', '-q:a', '5', op, '-y'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
    await asyncio.get_event_loop().run_in_executor(None, run)
    if os.path.exists(op):
        await status_msg.edit(content=f"{E_SUCCESS} Shifted Pitch perfectly.")
        await interaction.followup.send(file=discord.File(op))
    else:
        await status_msg.edit(content=f"{E_FAILED} Pitch alteration failed.")
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
    else:
        await status_msg.edit(content=f"{E_FAILED} Injection build failed.")
    [os.remove(f) for f in [bp, mp, op] if os.path.exists(f)]

@bot.tree.command(name="bait", description="Mixes track into pre-existing template option path")
@app_commands.describe(choice="Template choice ID", audio_file="Main audio file")
async def bait(interaction: discord.Interaction, choice: Literal["1","2","3","4","5","6","7","8","9","10","11","12","13","14","15","16","17"], audio_file: discord.Attachment):
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
        else:
            res = bait_track1 + main_track
        res[:419999].export(op, format="ogg")
        
    try:
        await asyncio.get_event_loop().run_in_executor(None, run_bait_mixing)
        if os.path.exists(op):
            await status_msg.edit(content=f"{E_SUCCESS} File mixed cleanly.")
            await interaction.followup.send(file=discord.File(op))
        else:
            await status_msg.edit(content=f"{E_FAILED} Build combination failed.")
    except Exception as e:
        await status_msg.edit(content=f"{E_FAILED} Processing failed: {str(e)}")
    [os.remove(f) for f in [ip, op] if os.path.exists(f)]

if __name__ == "__main__":
    keep_alive()
    bot.run(TOKEN)
