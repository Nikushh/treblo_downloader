# 🎵 Treblo Downloader Bot

Bot Telegram (basato su [Telethon](https://docs.telethon.dev/)) che scarica le canzoni da **treblo.com** e te le invia direttamente in chat nel formato che preferisci: **MP3, WAV, OGG, FLAC, M4A**.

---

## ✨ Funzionalità

- Download di una o più canzoni inviando i link
- Scelta del formato tramite bottoni inline (MP3, WAV, OGG, FLAC, M4A)
- Download in parallelo (massimo 3 contemporanei)
- Conversione automatica con **ffmpeg**
- Sistema di utenti autorizzati (solo chi è approvato può usare il bot)
- Comandi riservati agli owner per gestire gli accessi
- Log degli errori inviati automaticamente a un canale Telegram

---

## 📋 Requisiti

- **Python 3.8+**
- **ffmpeg** installato e raggiungibile da terminale
- Un bot Telegram creato tramite [@BotFather](https://t.me/BotFather)
- `API_ID` e `API_HASH` ottenibili su [my.telegram.org](https://my.telegram.org)
- Un canale Telegram (privato) dove il bot sia **amministratore**, per i log degli errori

---

## ⚙️ Installazione

### 1. Scarica il progetto

```bash
git clone <url-del-repository>
cd <cartella-del-progetto>
```

### 2. Installa le dipendenze Python

```bash
pip install telethon requests
```

### 3. Installa ffmpeg

**Linux (Debian/Ubuntu):**
```bash
sudo apt install ffmpeg
```

**macOS (Homebrew):**
```bash
brew install ffmpeg
```

**Windows:** scarica ffmpeg da [ffmpeg.org](https://ffmpeg.org/download.html) e aggiungilo al `PATH`.

Verifica l'installazione con:
```bash
ffmpeg -version
```

---

## 🔧 Configurazione

Apri `main.py` e compila questa sezione:

```python
BOT_TOKEN = "123456:ABC-DEF..."     # Token ricevuto da @BotFather
API_ID = 1234567                    # Da my.telegram.org
API_HASH = "abcdef1234567890..."    # Da my.telegram.org

OWNER_IDS = {123456789}             # ID Telegram degli owner (uno o più)
LOG_CHANNEL_ID = -1001234567890     # ID del canale per i log errori
```

### Come trovo il mio ID Telegram?

Avvia il bot e scrivi `/myid`: ti risponde con il tuo ID numerico.
*(Per il primo avvio puoi usare anche bot come @userinfobot.)*

### Come trovo l'ID del canale log?

1. Crea un canale e aggiungi il bot come **amministratore**
2. Ottieni l'ID del canale (formato `-100XXXXXXXXXX`) e inseriscilo in `LOG_CHANNEL_ID`

---

## ▶️ Avvio

```bash
python main.py
```

Se è tutto corretto vedrai:

```
🤖 Bot Telegram (Telethon) avviato e pronto a ricevere link...
```

Lascia il processo in esecuzione. Per tenerlo attivo 24/7 puoi usare `screen`, `tmux`, `systemd` o `pm2`.

---

## 📖 Come si usa

### Per gli utenti

1. Chiedi a un owner di **autorizzarti** (mandagli il tuo ID con `/myid`)
2. Scrivi `/start` al bot
3. Invia uno o più link nel formato:
   ```
   https://treblo.com/song/ID
   ```
   Puoi mandare più link nello stesso messaggio.
4. Scegli il formato dai bottoni che appaiono
5. Ricevi i file in chat appena sono pronti 🎧

> ⚠️ **Nota:** i formati **WAV** e **FLAC** si possono scaricare solo **una traccia alla volta** (file troppo pesanti). Se invii più link, il bot ti proporrà di convertirli in MP3 o M4A.

### Comandi utente

| Comando | Descrizione |
|---|---|
| `/start` o `/help` | Messaggio di benvenuto |
| `/comandi` | Elenco dei comandi |
| `/myid` | Mostra il tuo ID Telegram |

### Comandi owner

| Comando | Descrizione |
|---|---|
| `/autorizza <user_id>` | Autorizza un utente |
| `/rimuovi <user_id>` | Rimuove l'autorizzazione a un utente |
| `/lista` | Mostra gli utenti autorizzati |

Esempio:
```
/autorizza 987654321
```

Gli utenti autorizzati vengono salvati nel file `authorized_users.json`, quindi restano memorizzati anche dopo un riavvio.

---

## 🛠️ Come funziona (in breve)

1. Il bot legge la pagina Treblo e ricava il link audio dal meta tag `og:audio`
2. Scarica il file originale in una cartella temporanea
3. Se il formato richiesto è diverso, lo converte con ffmpeg
4. Invia il file in chat e cancella i file temporanei

---

## ❗ Problemi comuni

| Problema | Soluzione |
|---|---|
| `ffmpeg: command not found` | Installa ffmpeg e controlla che sia nel `PATH` |
| Il bot non risponde | Verifica di essere stato autorizzato (`/autorizza`) |
| "Formato non riconosciuto" | Il link deve essere `https://treblo.com/song/ID` |
| "meta og:audio non trovato" | La canzone non esiste o la pagina non è accessibile |
| "Sessione scaduta" | Reinvia i link e scegli di nuovo il formato |
| Errori non arrivano nel canale | Controlla `LOG_CHANNEL_ID` e che il bot sia admin del canale |

---

## 🔒 Sicurezza

- **Non condividere mai** `BOT_TOKEN`, `API_ID` e `API_HASH`
- Non pubblicare `main.py` con i dati compilati (e non caricare il file `.session` generato)
- Se usi Git, aggiungi al `.gitignore`:
  ```
  *.session
  authorized_users.json
  ```

---

## 📄 Disclaimer

Questo progetto è a scopo educativo. Usalo nel rispetto dei termini di servizio di Treblo e dei diritti d'autore dei contenuti.

---

by. tg: @naplespoiler
