import re
import os
import json
import time
import traceback
import tempfile
import functools
import subprocess
import asyncio
import logging
from telethon import TelegramClient, events, Button

#[span_1](start_span)[span_1](end_span)
TEMP_DIR = tempfile.gettempdir()
os.makedirs(TEMP_DIR, exist_ok=True)

# ============================================================
# CONFIGURAZIONE
# ============================================================

BOT_TOKEN = ""
API_ID = 
API_HASH = ""

OWNER_IDS = {}
AUTHORIZED_FILE = "authorized_users.json"
LOG_CHANNEL_ID = 

client = TelegramClient("treblo_bot_session", API_ID, API_HASH)

user_links = {}

# Limite riportato a 3 come richiesto
LIMITE_CONCORRENZA_GLOBALE = 3
semaforo_globale = asyncio.Semaphore(LIMITE_CONCORRENZA_GLOBALE)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("treblo_bot")


# ============================================================
# GESTIONE LOG ERRORI
# ============================================================

async def invia_log_errore(titolo, dettaglio, contesto=None):
    logger.error("%s\n%s", titolo, dettaglio)

    try:
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        intestazione = f"Errore: {titolo}\nData/ora: {timestamp}\n"
        if contesto:
            intestazione += f"Contesto: {contesto}\n"
        intestazione += "\n" + "=" * 40 + "\n\n"

        contenuto_file = intestazione + dettaglio
        percorso_log = os.path.join(TEMP_DIR, f"errore_{int(time.time() * 1000)}.txt")
        
        with open(percorso_log, "w", encoding="utf-8") as f:
            f.write(contenuto_file)

        messaggio_inviato = await client.send_file(
            LOG_CHANNEL_ID,
            percorso_log,
            caption=f"🐞 **Errore:** `{titolo}`",
            parse_mode="markdown",
        )

        try:
            await client.pin_message(LOG_CHANNEL_ID, messaggio_inviato, notify=False)
        except Exception:
            logger.exception("Impossibile fissare il messaggio di log nel canale.")

        if os.path.exists(percorso_log):
            os.remove(percorso_log)

    except Exception:
        logger.exception("Impossibile inviare il log dell'errore al canale.")


def gestisci_errori(func):
    @functools.wraps(func)
    async def wrapper(event, *args, **kwargs):
        try:
            return await func(event, *args, **kwargs)
        except Exception:
            dettaglio = traceback.format_exc()
            await invia_log_errore(
                titolo=f"Eccezione in {func.__name__}",
                dettaglio=dettaglio,
                contesto=f"chat_id={getattr(event, 'chat_id', '?')}",
            )
    return wrapper


# ============================================================
# GESTIONE UTENTI AUTORIZZATI
# ============================================================

def carica_autorizzati():
    if not os.path.exists(AUTHORIZED_FILE):
        return set()
    try:
        with open(AUTHORIZED_FILE, "r") as f:
            return set(json.load(f))
    except (json.JSONDecodeError, OSError):
        return set()


def salva_autorizzati(autorizzati):
    with open(AUTHORIZED_FILE, "w") as f:
        json.dump(list(autorizzati), f)


authorized_users = carica_autorizzati()

def is_owner(user_id):
    return user_id in OWNER_IDS

def is_authorized(user_id):
    return is_owner(user_id) or user_id in authorized_users


# ============================================================
# LOGICA DI ESTRAZIONE E CONVERSIONE AUDIO
# ============================================================

def estrai_link_diretto(url_pagina):
    import requests
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "it-IT,it;q=0.9,en-US;q=0.8,en;q=0.7",
        "Referer": "https://treblo.com/",
    }
    resp = requests.get(url_pagina, headers=headers, timeout=15)
    resp.raise_for_status()

    match = re.search(
        r'<meta[^>]+property=["\']og:audio["\'][^>]+content=["\']([^"\']+)["\']',
        resp.text
    )
    if not match:
        raise ValueError("Impossibile trovare il link audio nella pagina (meta og:audio non trovato).")

    return match.group(1)


def converti_audio(percorso_input, formato_output):
    percorso_output = percorso_input + f".{formato_output}"
    comando = ["ffmpeg", "-y", "-i", percorso_input, percorso_output]
    risultato = subprocess.run(comando, capture_output=True, text=True)

    if risultato.returncode != 0:
        raise RuntimeError(f"Errore ffmpeg: {risultato.stderr[-500:]}")

    return percorso_output


def scarica_file(url, path):
    import requests
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Referer": "https://treblo.com/",
    }
    resp = requests.get(url, headers=headers, stream=True, timeout=30)
    if resp.status_code != 200:
        raise RuntimeError(f"Risposta del server {resp.status_code}")
    with open(path, "wb") as f:
        for chunk in resp.iter_content(chunk_size=8192):
            f.write(chunk)


# ============================================================
# COMANDI OWNER
# ============================================================

# Aggiunto incoming=True per evitare auto-risposte
@client.on(events.NewMessage(pattern=r"^/autorizza(?:\s+(\d+))?$", incoming=True))
@gestisci_errori
async def autorizza_utente(event):
    if event.chat_id == LOG_CHANNEL_ID or not is_owner(event.sender_id):
        return

    match = event.pattern_match.group(1)
    if not match:
        await event.reply("Uso: `/autorizza <user_id>`", parse_mode="markdown")
        return

    nuovo_id = int(match)
    authorized_users.add(nuovo_id)
    salva_autorizzati(authorized_users)
    await event.reply(f"✅ Utente `{nuovo_id}` autorizzato.", parse_mode="markdown")


@client.on(events.NewMessage(pattern=r"^/rimuovi(?:\s+(\d+))?$", incoming=True))
@gestisci_errori
async def rimuovi_utente(event):
    if event.chat_id == LOG_CHANNEL_ID or not is_owner(event.sender_id):
        return

    match = event.pattern_match.group(1)
    if not match:
        await event.reply("Uso: `/rimuovi <user_id>`", parse_mode="markdown")
        return

    id_da_rimuovere = int(match)
    if id_da_rimuovere in authorized_users:
        authorized_users.remove(id_da_rimuovere)
        salva_autorizzati(authorized_users)
        await event.reply(f"🗑️ Utente `{id_da_rimuovere}` rimosso.", parse_mode="markdown")
    else:
        await event.reply(f"L'utente `{id_da_rimuovere}` non era autorizzato.", parse_mode="markdown")


@client.on(events.NewMessage(pattern=r"^/lista$", incoming=True))
@gestisci_errori
async def lista_utenti(event):
    if event.chat_id == LOG_CHANNEL_ID or not is_owner(event.sender_id):
        return

    if not authorized_users:
        await event.reply("Nessun utente autorizzato al momento (a parte gli owner).")
        return

    testo = "**Utenti autorizzati:**\n" + "\n".join(f"`{uid}`" for uid in sorted(authorized_users))
    await event.reply(testo, parse_mode="markdown")


@client.on(events.NewMessage(pattern=r"^/myid$", incoming=True))
@gestisci_errori
async def mostra_id(event):
    if event.chat_id == LOG_CHANNEL_ID:
        return
    await event.reply(f"Il tuo ID Telegram è: `{event.sender_id}`", parse_mode="markdown")


# ============================================================
# COMANDI UTENTE E LOGICA DI DOWNLOAD
# ============================================================

@client.on(events.NewMessage(pattern=r"^/start$|^/help$", incoming=True))
@gestisci_errori
async def start_command(event):
    if event.chat_id == LOG_CHANNEL_ID or not is_authorized(event.sender_id):
        return

    testo = (
        "🎵 **Benvenuto nel Bot di Download Treblo!** 🎵\n\n"
        "Inviami uno o più link di canzoni per iniziare.\n"
        "I download vengono gestiti in parallelo per massima velocità!\n\n"
        "⚠️ _Nota: I formati WAV e FLAC possono essere scaricati solo inserendo un link alla volta._\n\n"
        "**Formato supportato:**\n`https://treblo.com/song/ID`\n\n"
        "Usa /comandi per vedere l'elenco completo."
    )
    await event.reply(testo, parse_mode="markdown")


@client.on(events.NewMessage(pattern=r"^/comandi$|^/comand$", incoming=True))
@gestisci_errori
async def lista_comandi(event):
    if event.chat_id == LOG_CHANNEL_ID or not is_authorized(event.sender_id):
        return

    testo = (
        "📋 **Comandi disponibili:**\n\n"
        "**Comandi utente:**\n"
        "`/start` oppure `/help` - Messaggio di benvenuto\n"
        "`/myid` - Mostra il tuo ID Telegram\n"
        "`/comandi` - Mostra questo elenco\n\n"
    )
    if is_owner(event.sender_id):
        testo += (
            "**Comandi owner:**\n"
            "`/autorizza <user_id>` - Autorizza un utente\n"
            "`/rimuovi <user_id>` - Rimuove l'autorizzazione a un utente\n"
            "`/lista` - Mostra gli utenti autorizzati"
        )
    await event.reply(testo, parse_mode="markdown")


URL_PATTERN = re.compile(r"https://treblo\.com/song/[A-Za-z0-9_-]+")

# Aggiunto incoming=True al gestore principale per evitare il crash per loop
@client.on(events.NewMessage(incoming=True))
@gestisci_errori
async def handle_treblo_link(event):
    if event.chat_id == LOG_CHANNEL_ID or not is_authorized(event.sender_id):
        return

    testo = event.raw_text or ""
    if testo.startswith("/"):
        return

    urls = URL_PATTERN.findall(testo)
    if not urls:
        await event.reply(
            "Formato non riconosciuto. Inviami uno o più link corretti, ad esempio:\n`https://treblo.com/song/12345`",
            parse_mode="markdown"
        )
        return

    urls = list(dict.fromkeys(urls))
    user_links[event.sender_id] = urls

    bottoni = [
        [Button.inline("MP3", b"fmt_mp3"), Button.inline("WAV", b"fmt_wav")],
        [Button.inline("OGG", b"fmt_ogg"), Button.inline("FLAC", b"fmt_flac")],
        [Button.inline("M4A", b"fmt_m4a")],
    ]

    messaggio_reply = f"✅ Ricevuti **{len(urls)}** link!\nIn quale formato vuoi scaricare i file?"
    await event.reply(messaggio_reply, buttons=bottoni, parse_mode="markdown")


@client.on(events.CallbackQuery(pattern=b"^fmt_"))
@gestisci_errori
async def handle_format_selection(event):
    if event.chat_id == LOG_CHANNEL_ID or not is_authorized(event.sender_id):
        await event.answer()
        return

    formato = event.data.decode().split("_")[1]
    user_id = event.sender_id

    if user_id not in user_links:
        await event.answer("❌ Sessione scaduta. Invia nuovamente i link.", alert=True)
        return

    urls = user_links[user_id]
    totale_tracce = len(urls)

    if totale_tracce > 1 and formato in ["wav", "flac"]:
        bottoni_alternativi = [
            [Button.inline("Converti in MP3", b"fmt_mp3"), Button.inline("Converti in M4A", b"fmt_m4a")]
        ]
        await event.edit(
            f"⚠️ **Attenzione!** I file in formato **{formato.upper()}** devono essere scaricati **una sola traccia alla volta** a causa delle dimensioni elevate.\n\n"
            f"Vuoi continuare il download multiplo di queste {totale_tracce} tracce convertendole in **MP3** o **M4A**?",
            buttons=bottoni_alternativi,
            parse_mode="markdown"
        )
        return

    urls = user_links.pop(user_id)

    status_msg = await event.edit(
        f"⏳ Inizio l'elaborazione di **{totale_tracce}** tracce in formato **{formato.upper()}**...\n_Le riceverai appena pronte._",
        parse_mode="markdown"
    )

    async def elabora_traccia(indice, url_pagina):
        async with semaforo_globale:
            percorso_originale = None
            percorso_convertito = None
            try:
                url_diretto_file = await asyncio.to_thread(estrai_link_diretto, url_pagina)
                estensione_originale = url_diretto_file.split(".")[-1].split("?")[0]
                percorso_originale = os.path.join(TEMP_DIR, f"orig_{user_id}_{indice}.{estensione_originale}")

                await asyncio.to_thread(scarica_file, url_diretto_file, percorso_originale)

                if formato == estensione_originale:
                    percorso_convertito = percorso_originale
                else:
                    percorso_convertito = await asyncio.to_thread(converti_audio, percorso_originale, formato)

                caption_testo = f"✨ **Versione {indice}**\n🎧 Formato: {formato.upper()}\n🔗 `{url_pagina}`"
                await client.send_file(
                    user_id,
                    percorso_convertito,
                    caption=caption_testo,
                    parse_mode="markdown",
                    voice_note=False,
                )

            except Exception as e:
                await client.send_message(user_id, f"❌ Si è verificato un errore con la **Versione {indice}**:\n`{str(e)}`", parse_mode="markdown")
                await invia_log_errore(
                    titolo=f"Errore elaborazione traccia (formato {formato})",
                    dettaglio=traceback.format_exc(),
                    contesto=f"user_id={user_id}, indice={indice}, url={url_pagina}",
                )

            finally:
                for percorso in {percorso_originale, percorso_convertito}:
                    if percorso and os.path.exists(percorso):
                        try:
                            os.remove(percorso)
                        except OSError:
                            pass

    tasks = [elabora_traccia(indice, url) for indice, url in enumerate(urls, start=1)]
    await asyncio.gather(*tasks)
    await status_msg.edit("✅ **Download multiplo completato!** 🎉", parse_mode="markdown")


# ============================================================
# AVVIO BOT
# ============================================================

if __name__ == "__main__":
    print("🤖 Bot Telegram (Telethon) avviato e pronto a ricevere link...")
    print(f"Owner: {OWNER_IDS}")
    print(f"Utenti autorizzati caricati: {authorized_users if authorized_users else 'nessuno'}")
    
    client.start(bot_token=BOT_TOKEN)
    try:
        client.run_until_disconnected()
    except Exception:
        logger.exception("Errore fatale del bot durante l'esecuzione.")
