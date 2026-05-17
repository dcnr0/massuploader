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

# --- RENDER HEALTH CHECK KEEP-ALIVE SERVER ---
app = Flask('')

@app.route('/')
def home():
    return "Bot is online and responding to Render health checks."

def run_web_server():
    # Render automatically injects a PORT environment variable
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run_web_server)
    t.daemon = True
    t.start()

# --- CONFIG & ASSETS ---
# SECURE: Pulled from Render Environment Variables dashboard
TOKEN = os.getenv('DISCORD_TOKEN')
if not TOKEN:
    raise ValueError("CRITICAL: DISCORD_TOKEN environment variable is missing!")

# Setup a relative path for Render hosting compatibility
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SEARCH_DIRS = [
    os.path.join(BASE_DIR, "assets")
]

AUTH_DATA = {} 
EMOJI_POOL = list("😀😃😄😁😆😅😂🤣☺️😇🙂🙃😉")

BAIT_MAP = {
    "1": {"files": ["uno.mp3", "dos.mp3"], "type": "sandwich"},
    "2": {"files": ["baitupd.wav"], "type": "start"},
    "3": {"files": ["loud audios.ogg"], "type": "start"},
    "4": {"files": ["past final.mp3"], "type": "start"},
    "5": {"files": ["beep bait.mp3"], "type": "start"},
    "6": {"files": ["bait_output.mp3"], "type": "start"},
    "7": {"files": ["Cinematic 3rd hun_cs bait.mp3"], "type": "start"},
    "8": {"files": ["Cinematic Epic Music by Infraction [No Copyright Music] Action TPOS 211.mp3"], "type": "start"},
    "9": {"files": ["Cinematic Epic Music by Infraction, 2025 THEME BAIT HUN_CS.mp3"], "type": "start"},
    "10": {"files": ["cinema__a_half_louder.mp3"], "type": "start"},
    "11": {"files": ["HUN_Cs's 3rd cinematic bait for hungarian gang.mp3"], "type": "start"},
    "12": {"files": ["SHORTEST BAIT.mp3", "alex_besss-movie-trailer-501295 (1).mp3"], "type": "sandwich"}
}

class ZeptiV77(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        self.session = aiohttp.ClientSession(connector=aiohttp.TCPConnector(limit=0))
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
    if style == "Chaos (Symbols/Letters)": return "".join(random.choice(string.ascii_letters + string.digits + string.punctuation) for _ in range(20))
    if style == "Emoji Heavy": return "".join(random.choice(EMOJI_POOL) for _ in range(15))
    if style == "Uppercase & Lowercase": return "".join(random.choice(string.ascii_letters) for _ in range(20))
    if style == "Numbers Only": return "".join(random.choice(string.digits) for _ in range(15))
    if style == "No Suffix (Clean)": return custom_name
    return f"{custom_name}_{index}"

def scramble_binary(raw_data: bytearray):
    if len(raw_data) > 2000:
        for _ in range(8):
            insert_pos = random.randint(500, len(raw_data) - 500)
            raw_data[insert_pos:insert_pos] = os.urandom(random.randint(4, 16))
    raw_data.extend(os.urandom(random.randint(128, 512)))
    return bytes(raw_data)

def process_audio_bypass(audio_bytes, index, stutter_ms):
    audio = AudioSegment.from_file(io.BytesIO(audio_bytes))
    stutter = audio[:stutter_ms] * index
    audio = stutter + audio
    audio = audio.set_frame_rate(int(audio.frame_rate + random.uniform(-3, 3)))
    buf = io.BytesIO()
    audio.export(buf, format="mp3", bitrate="192k", tags={'comment': os.urandom(8).hex()})
    final = scramble_binary(bytearray(buf.getvalue()))
    del audio; gc.collect()
    return final

# --- BOT COMMANDS ---

@bot.tree.command(name="api")
async def api_setup(interaction: discord.Interaction, key: str, target_id: str, is_group: bool):
    AUTH_DATA[interaction.user.id] = {"apikey": key, "targetId": str(target_id), "isGroup": is_group}
    await interaction.response.send_message(f"✅ Linked to {'Group' if is_group else 'User'} ID: **{target_id}**.", ephemeral=True)

@bot.tree.command(name="method")
async def bypass_method(interaction: discord.Interaction, audio_file: discord.Attachment):
    class MethodSelect(discord.ui.Select):
        async def callback(self, i: discord.Interaction):
            await i.response.defer()
            u = get_uid(); ip, op = f"mi_{u}.mp3", f"mo_{u}.ogg"
            await audio_file.save(ip)
            if self.values[0] == "8d":
                def run():
                    subprocess.run(['ffmpeg', '-i', ip, '-af', "aphaser=in_gain=0.6:out_gain=1:delay=2:decay=0.4:speed=0.5:type=t,apulsator=mode=sine:hz=0.2:amount=1", '-c:a', 'libvorbis', '-q:a', '5', op, '-y'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                await asyncio.get_event_loop().run_in_executor(None, run)
                await i.followup.send(content="**Method Applied: 8D**", file=discord.File(op))
            [os.remove(f) for f in [ip, op] if os.path.exists(f)]

    v = discord.ui.View(); v.add_item(MethodSelect(placeholder="Choose Bypass Method", options=[discord.SelectOption(label="8D Audio", value="8d", description="Title: 8D Effect Bypass")]))
    await interaction.response.send_message("🛠️ Select Method:", view=v, ephemeral=True)

@bot.tree.command(name="mp3")
async def mp3_dl(interaction: discord.Interaction, url: str):
    await interaction.response.defer()
    f = f"m_{get_uid()}.mp3"
    try:
        def dl(): subprocess.run(['yt-dlp', '-x', '--audio-format', 'mp3', '-o', f, url], check=True)
        await asyncio.get_event_loop().run_in_executor(None, dl)
        await interaction.followup.send(file=discord.File(f))
        os.remove(f)
    except Exception as e: await interaction.followup.send(f"❌ Failed: {e}")

@bot.tree.command(name="massupload")
async def massupload(interaction: discord.Interaction, audio_file: discord.Attachment, title: str, style: Literal["Default", "Chaos (Symbols/Letters)", "Emoji Heavy", "Uppercase & Lowercase", "Numbers Only", "No Suffix (Clean)"] = "Default"):
    if interaction.user.id not in AUTH_DATA: return await interaction.response.send_message("❌ Use /api first.", ephemeral=True)
    await interaction.response.defer(); acc = AUTH_DATA[interaction.user.id]; raw = await audio_file.read()
    stut = random.randint(50, 200)
    async def task(idx):
        data = await asyncio.get_event_loop().run_in_executor(None, process_audio_bypass, raw, idx, stut)
        d_name = get_preset_title(style, idx, title); h = {"x-api-key": acc["apikey"]}
        ckey = "groupId" if acc["isGroup"] else "userId"
        for _ in range(100):
            f = aiohttp.FormData(); p = {"assetType": "Audio", "displayName": d_name, "description": "zepti_W", "creationContext": {"creator": {ckey: acc["targetId"]}}}
            f.add_field('request', json.dumps(p), content_type='application/json')
            f.add_field('fileContent', data, filename=f'{get_uid(4)}.mp3', content_type='audio/mpeg')
            async with bot.session.post("https://apis.roblox.com/assets/v1/assets", data=f, headers=h) as r:
                if r.status in [200, 201, 202]: return f"✅ | {d_name}"
                if r.status == 429: await asyncio.sleep(5)
        return f"❌ | {d_name}"
    res = await asyncio.gather(*[task(i) for i in range(1, 11)])
    await interaction.channel.send("```\n" + "\n".join(res) + "```")

@bot.tree.command(name="loudset")
async def loudset(interaction: discord.Interaction, audio_file: discord.Attachment):
    class P(discord.ui.Select):
        async def callback(self, i):
            await i.response.defer()
            u = get_uid(); ip, op = f"li_{u}.mp3", f"lo_{u}.ogg"
            await audio_file.save(ip)
            def proc():
                with AudioFile(ip) as af: rs = get_loud_preset(self.values[0])(af.read(af.frames), af.samplerate)
                tw = f"lt_{u}.wav"
                with AudioFile(tw, 'w', af.samplerate, rs.shape[0]) as o: o.write(rs)
                AudioSegment.from_file(tw).export(op, format="ogg"); os.remove(tw)
            await asyncio.get_event_loop().run_in_executor(None, proc)
            await i.followup.send(file=discord.File(op)); [os.remove(f) for f in [ip, op] if os.path.exists(f)]
    v = discord.ui.View(); v.add_item(P(options=[discord.SelectOption(label=f"Preset {x}", value=str(x)) for x in range(1,14)]))
    await interaction.response.send_message("🔊 Select Preset:", view=v, ephemeral=True)

@bot.tree.command(name="macro")
async def macro(interaction: discord.Interaction, audio_file: discord.Attachment, macro_file: discord.Attachment):
    await interaction.response.defer(); u = get_uid(); ip, op = f"mi_{u}.mp3", f"mo_{u}.ogg"
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
    await asyncio.get_event_loop().run_in_executor(None, run); await interaction.followup.send(file=discord.File(op)); [os.remove(f) for f in [ip, op] if os.path.exists(f)]

@bot.tree.command(name="pitch")
async def pitch(interaction: discord.Interaction, audio_file: discord.Attachment, val: float):
    await interaction.response.defer(); u = get_uid(); ip, op = f"pi_{u}.mp3", f"po_{u}.ogg"; await audio_file.save(ip)
    def run():
        s = AudioSegment.from_file(ip)
        s._spawn(s.raw_data, overrides={'frame_rate': int(s.frame_rate * val)}).set_frame_rate(44100).export(op, format="ogg")
    await asyncio.get_event_loop().run_in_executor(None, run); await interaction.followup.send(file=discord.File(op)); [os.remove(f) for f in [ip, op] if os.path.exists(f)]

@bot.tree.command(name="tpos")
async def tpos(interaction: discord.Interaction, bait: discord.Attachment, main: discord.Attachment):
    await interaction.response.defer(); u = get_uid(); bp, mp, op = f"b_{u}.mp3", f"m_{u}.mp3", f"t_{u}.ogg"
    await bait.save(bp); await main.save(mp)
    def run(): (AudioSegment.from_file(bp) + AudioSegment.from_file(mp)).export(op, format="ogg")
    await asyncio.get_event_loop().run_in_executor(None, run); await interaction.followup.send(file=discord.File(op)); [os.remove(f) for f in [bp, mp, op] if os.path.exists(f)]

@bot.tree.command(name="bait")
async def bait(interaction: discord.Interaction, choice: Literal["1","2","3","4","5","6","7","8","9","10","11","12"], audio_file: discord.Attachment):
    await interaction.response.defer(); u = get_uid(); ip, op = f"bi_{u}.mp3", f"bo_{u}.ogg"; await audio_file.save(ip); cfg = BAIT_MAP[choice]
    def run():
        m = AudioSegment.from_file(ip); b = AudioSegment.from_file(find_file(cfg["files"][0]))
        res = (b + m + AudioSegment.from_file(find_file(cfg["files"][1]))) if cfg["type"] == "sandwich" else (b + m)
        res.export(op, format="ogg")
    await asyncio.get_event_loop().run_in_executor(None, run); await interaction.followup.send(file=discord.File(op)); [os.remove(f) for f in [ip, op] if os.path.exists(f)]

@bot.tree.command(name="decalgen")
async def decalgen(interaction: discord.Interaction, image: discord.Attachment, watermark: Optional[discord.Attachment] = None):
    await interaction.response.defer(); img_d = await image.read(); wm_d = await watermark.read() if watermark else None
    def proc():
        base = Image.open(BytesIO(img_d)); out = BytesIO(); wm = Image.open(BytesIO(wm_d)).convert('RGBA') if wm_d else None
        def apply(f):
            if not wm: return f
            f = f.convert('RGBA').resize((1080,1080), Image.Resampling.LANCZOS)
            s = wm.resize((int(wm.width*(490/wm.width)), int(wm.height*(490/wm.width))), Image.Resampling.LANCZOS)
            f.paste(s, (1080-s.width-10, 1080-s.height-10), s); return f
        if getattr(base, "is_animated", False):
            fs = [apply(fr).convert('P', palette=Image.Palette.ADAPTIVE) for fr in ImageSequence.Iterator(base)]
            fs[0].save(out, format='GIF', save_all=True, append_images=fs[1:], loop=0, optimize=True); return out, f"{get_uid()}.gif"
        res = apply(base); res.save(out, format='PNG', optimize=True); return out, f"{get_uid()}.png"
    buf, name = await asyncio.get_event_loop().run_in_executor(None, proc); buf.seek(0); await interaction.followup.send(file=discord.File(buf, filename=name))

if __name__ == "__main__":
    keep_alive()  # Fires up Flask web server thread for Render compatibility
    bot.run(TOKEN)