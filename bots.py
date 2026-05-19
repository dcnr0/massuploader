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
    os.path.join(BASE_DIR, "assets")
]

AUTH_DATA = {} 
EMOJI_POOL = list("😀😃😄😁😆😅😂🤣☺️😇🙂🙃😉")

# Fixed Application Emoji Formatting (Using App Emoji syntax)
E_MOD = "<a:mod:1506265969562226738>"
E_LDING = "<a:lding:1506265760631099452>"
E_SUCCESS = "<a:success:1506265759452631082>"
E_FAILED = "<a:failed:1506265787900579994>"

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
    "16": {"files": ["lofi1.mp3", "lofi2.mp3"], "type": "sandwich"}
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
    await interaction.response.defer(ephemeral=True)
    AUTH_DATA[interaction.user.id] = {"apikey": key, "targetId": str(target_id), "isGroup": is_group}
    await interaction.followup.send(content=f"{E_SUCCESS} Linked to {'Group' if is_group else 'User'} ID: **{target_id}**.", ephemeral=True)

@bot.tree.command(name="method")
async def bypass_method(interaction: discord.Interaction, audio_file: discord.Attachment):
    try:
        await interaction.response.defer(ephemeral=True)
    except discord.errors.NotFound:
        return

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
                        await progress_msg.edit(content=f"{E_FAILED} Method failed to generate output.")
                    
                elif self.values[0] == "copyright":
                    def run_copyright():
                        subprocess.run(['ffmpeg', '-i', ip, '-af', "asetrate=48000*0.925,atempo=1.10,atempo=0.92,atempo=1.07,atempo=1.07,atempo=1.07", '-c:a', 'libvorbis', '-q:a', '4', op, '-y'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    await asyncio.get_event_loop().run_in_executor(None, run_copyright)
                    if os.path.exists(op):
                        await progress_msg.edit(content=f"{E_MOD} **Copyright Bypass Activated**")
                        await i.followup.send(file=discord.File(op))
                    else:
                        await progress_msg.edit(content=f"{E_FAILED} Method failed to generate output.")
            except Exception:
                await progress_msg.edit(content=f"{E_FAILED} Error running dropdown filter.")
                
            [os.remove(f) for f in [ip, op] if os.path.exists(f)]

    v = discord.ui.View()
    v.add_item(MethodSelect(
        placeholder="Choose Bypass Method", 
        options=[
            discord.SelectOption(label="8D Audio", value="8d", description="8D Phaser Effect Bypass"),
            discord.SelectOption(label="Copyright Bypass", value="copyright", description="Multi-stage Asetrate/Atempo Shift")
        ]
    ))
    await interaction.followup.send(content=f"{E_MOD} Select Method:", view=v)

@bot.tree.command(name="mp3")
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
                'quiet': True
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
                
        await asyncio.get_event_loop().run_in_executor(None, dl)
        
        if os.path.exists(final_filename):
            await status_msg.edit(content=f"{E_SUCCESS} Successfully downloaded!")
            await interaction.followup.send(file=discord.File(final_filename))
            os.remove(final_filename)
        else:
            await status_msg.edit(content=f"{E_FAILED} Conversion finished but output file could not be found.")
            
    except Exception as e: 
        await status_msg.edit(content=f"{E_FAILED} Failed: {e}")

@bot.tree.command(name="massupload")
async def massupload(interaction: discord.Interaction, audio_file: discord.Attachment, title: str, style: Literal["Default", "Chaos (Symbols/Letters)", "Emoji Heavy", "Uppercase & Lowercase", "Numbers Only", "No Suffix (Clean)"] = "Default"):
    if interaction.user.id not in AUTH_DATA: 
        return await interaction.response.send_message(content=f"{E_FAILED} Use /api first.", ephemeral=True)
    
    try:
        await interaction.response.defer()
    except discord.errors.NotFound:
        return
        
    status_msg = await interaction.followup.send(content=f"{E_LDING} Massuploading...")
    acc = AUTH_DATA[interaction.user.id]
    raw = await audio_file.read()
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
                if r.status in [200, 201, 202]: return f"{E_SUCCESS} | {d_name}"
                if r.status == 429: await asyncio.sleep(5)
        return f"{E_FAILED} | {d_name}"
        
    res = await asyncio.gather(*[task(i) for i in range(1, 11)])
    await status_msg.edit(content=f"{E_SUCCESS} Batch completed.")
    await interaction.channel.send("```\n" + "\n".join([r.replace(E_SUCCESS, "✅").replace(E_FAILED, "❌") for r in res]) + "```")

@bot.tree.command(name="loudset")
async def loudset(interaction: discord.Interaction, audio_file: discord.Attachment):
    try:
        await interaction.response.defer(ephemeral=True)
    except discord.errors.NotFound:
        return
    
    class P(discord.ui.Select):
        async def callback(self, i):
            await i.response.defer()
            progress_msg = await i.followup.send(content=f"{E_LDING} Processing...")
            u = get_uid(); ip, op = f"li_{u}.mp3", f"lo_{u}.ogg"
            await audio_file.save(ip)
            
            try:
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

@bot.tree.command(name="macro")
async def macro(interaction: discord.Interaction, audio_file: discord.Attachment, macro_file: discord.Attachment):
    try:
        await interaction.response.defer()
    except discord.errors.NotFound:
        return
        
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
        await status_msg.edit(content=f"{E_SUCCESS} Macro applied successfully.")
        await interaction.followup.send(file=discord.File(op))
    else:
        await status_msg.edit(content=f"{E_FAILED} Macro application failed.")
    [os.remove(f) for f in [ip, op] if os.path.exists(f)]

@bot.tree.command(name="pitch")
async def pitch(interaction: discord.Interaction, audio_file: discord.Attachment, val: float):
    try:
        await interaction.response.defer()
    except discord.errors.NotFound:
        return
        
    status_msg = await interaction.followup.send(content=f"{E_LDING} Processing...")
    u = get_uid(); ip, op = f"pi_{u}.mp3", f"po_{u}.ogg"
    await audio_file.save(ip)
    
    def run():
        input_rate = 44100
        new_rate = int(input_rate * val)
        subprocess.run([
            'ffmpeg', '-i', ip, 
            '-af', f"asetrate={new_rate},aresample={input_rate}", 
            '-c:a', 'libvorbis', '-q:a', '5', op, '-y'
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
    await asyncio.get_event_loop().run_in_executor(None, run)
    if os.path.exists(op):
        await status_msg.edit(content=f"{E_SUCCESS} Shifted Pitch and Speed perfectly.")
        await interaction.followup.send(file=discord.File(op))
    else:
        await status_msg.edit(content=f"{E_FAILED} Pitch alteration failed.")
    [os.remove(f) for f in [ip, op] if os.path.exists(f)]

@bot.tree.command(name="tpos")
async def tpos(interaction: discord.Interaction, bait: discord.Attachment, main: discord.Attachment):
    try:
        await interaction.response.defer()
    except discord.errors.NotFound:
        return
        
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

@bot.tree.command(name="bait")
async def bait(interaction: discord.Interaction, choice: Literal["1","2","3","4","5","6","7","8","9","10","11","12","13","14","15","16"], audio_file: discord.Attachment):
    try:
        await interaction.response.defer()
    except discord.errors.NotFound:
        return
        
    status_msg = await interaction.followup.send(content=f"{E_LDING} Processing...")
    u = get_uid(); ip, op = f"bi_{u}.mp3", f"bo_{u}.ogg"
    await audio_file.save(ip)
    
    cfg = BAIT_MAP[choice]
    
    # Thread-safe async file loader and mixer
    def run_bait_mixing():
        main_track = AudioSegment.from_file(ip)
        
        # Resolving bait filepaths
        bait1_path = find_file(cfg["files"][0])
        if not bait1_path:
            raise FileNotFoundError(f"Missing base template asset: {cfg['files'][0]}")
        bait_track1 = AudioSegment.from_file(bait1_path)
        
        if cfg.get("type") == "sandwich":
            bait2_path = find_file(cfg["files"][1])
            if not bait2_path:
                raise FileNotFoundError(f"Missing end template asset: {cfg['files'][1]}")
            bait_track2 = AudioSegment.from_file(bait2_path)
            res = bait_track1 + main_track + bait_track2
        else:
            res = bait_track1 + main_track
            
        # Hard limits lengths cleanly to avoid oversized payloads
        res = res[:419999]
        res.export(op, format="ogg")
        
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

@bot.tree.command(name="decalgen")
async def decalgen(interaction: discord.Interaction, image: discord.Attachment, watermark: Optional[discord.Attachment] = None):
    try:
        await interaction.response.defer()
    except discord.errors.NotFound:
        return
        
    status_msg = await interaction.followup.send(content=f"{E_LDING} Processing...")
    img_d = await image.read(); wm_d = await watermark.read() if watermark else None
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
    buf, name = await asyncio.get_event_loop().run_in_executor(None, proc); buf.seek(0)
    
    await status_msg.edit(content=f"{E_SUCCESS} Asset rendered successfully.")
    await interaction.followup.send(file=discord.File(buf, filename=name))

if __name__ == "__main__":
    keep_alive()
    bot.run(TOKEN)
