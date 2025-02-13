from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
import calendar
from datetime import datetime
import asyncio

giorni_settimana_ita = ["Lunedì", "Martedì", "Mercoledì", "Giovedì", "Venerdì", "Sabato", "Domenica"]
mesi_ita = ["Gennaio", "Febbraio", "Marzo", "Aprile", "Maggio", "Giugno", "Luglio", "Agosto", "Settembre", "Ottobre", "Novembre", "Dicembre"]

programmi = {}

BOT_TOKEN = "7513164223:AAEkNwKP87FbRZ84OzzXNV4iXVTOq3G9Pck"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    now = datetime.now()
    context.user_data["mese"] = now.month
    context.user_data["anno"] = now.year
    await mostra_giorni(update, context)

async def mostra_giorni(update: Update, context: ContextTypes.DEFAULT_TYPE, edit=False):
    chat_id = update.message.chat_id if update.message else update.callback_query.message.chat_id
    mese = context.user_data["mese"]
    anno = context.user_data["anno"]
    now = datetime.now()

    if anno < now.year or (anno == now.year and mese < now.month):
        return  

    giorni_nel_mese = calendar.monthrange(anno, mese)[1]
    keyboard = []
    row = []

    for i in range(1, giorni_nel_mese + 1):
        row.append(InlineKeyboardButton(str(i), callback_data=f"giorno_{anno}_{mese}_{i}"))
        if len(row) == 7:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)

    nav_buttons = []
    if not (anno == now.year and mese == now.month):
        nav_buttons.append(InlineKeyboardButton("◀️", callback_data="mese_prev"))
    if anno < 2030 or mese < 12:
        nav_buttons.append(InlineKeyboardButton("▶️", callback_data="mese_next"))

    if nav_buttons:
        keyboard.append(nav_buttons)

    # Bottone aggiunto per "riepilogo programmi"
    keyboard.append([InlineKeyboardButton("Riepilogo Programmi 🏷️", callback_data="riepilogo_programmi")])

    mese_nome = mesi_ita[mese - 1]
    text = f"📅 Mese: {mese_nome} {anno}\nScegli un giorno:"

    if edit and context.user_data.get("message_id"):
        await context.bot.edit_message_text(chat_id=chat_id, message_id=context.user_data["message_id"], text=text, reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        message = await context.bot.send_message(chat_id, text, reply_markup=InlineKeyboardMarkup(keyboard))
        context.user_data["message_id"] = message.message_id

async def riepilogo_programmi(update: Update, context: ContextTypes.DEFAULT_TYPE):
    mese = context.user_data["mese"]
    anno = context.user_data["anno"]
    mese_nome = mesi_ita[mese - 1]

    # Creiamo il riepilogo dei programmi
    programmi_del_mese = []
    
    # Itera su tutti i programmi aggiunti in ogni giorno di ogni mese per ogni anno
    for (anno_programma, mese_programma, giorno_programma), programmi_in_giorno in programmi.items():
        giorno_settimana = giorni_settimana_ita[calendar.weekday(anno_programma, mese_programma, giorno_programma)]
        mese_nome_programma = mesi_ita[mese_programma - 1]
        
        for programma in programmi_in_giorno:
            programma_testo = f"📅 {giorno_settimana} {giorno_programma} {mese_nome_programma} {anno_programma}: {programma}"
            programmi_del_mese.append(programma_testo)

    if not programmi_del_mese:
        programmi_del_mese.append("Nessun programma trovato.")

    # Messaggio di riepilogo con la linea di separazione tra i programmi
    riepilogo_testo = "\n\n" + "\n\n".join(programmi_del_mese)  # Aggiunta riga vuota tra i programmi
    
    # Invia il messaggio di riepilogo
    messaggio_riepilogo = await update.callback_query.message.reply_text(f"Riepilogo Programmi:\n{riepilogo_testo}")
    
    # Attendere 10 secondi e poi cancellare il messaggio
    await asyncio.sleep(10)
    await messaggio_riepilogo.delete()

async def cambia_mese(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    mese = context.user_data["mese"]
    anno = context.user_data["anno"]
    now = datetime.now()

    if query.data == "mese_prev":
        if not (anno == now.year and mese == now.month):  
            if mese > 1:
                mese -= 1
            elif anno > now.year:
                anno -= 1
                mese = 12
    elif query.data == "mese_next":
        if mese < 12:
            mese += 1
        elif anno < 2030:
            anno += 1
            mese = 1

    context.user_data["mese"] = mese
    context.user_data["anno"] = anno

    await mostra_giorni(update, context, edit=True)

async def seleziona_giorno(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    _, anno, mese, giorno = query.data.split("_")
    anno, mese, giorno = int(anno), int(mese), int(giorno)

    mese_nome = mesi_ita[mese - 1]
    giorno_settimana = giorni_settimana_ita[calendar.weekday(anno, mese, giorno)]
    context.user_data["giorno"] = giorno
    context.user_data["mese"] = mese
    context.user_data["anno"] = anno

    chiave = (anno, mese, giorno)
    
    if chiave in programmi:
        programma_testo = "\n".join(programmi[chiave])
    else:
        programma_testo = "Nessun programma aggiunto."

    keyboard = [
        [InlineKeyboardButton("➕ Aggiungi", callback_data="aggiungi")],
        [InlineKeyboardButton("✏️ Modifica", callback_data="modifica")],
        [InlineKeyboardButton("⬅️ Indietro", callback_data="indietro")]
    ]
    
    await query.message.edit_text(f"📅 Programma per {giorno_settimana} {giorno} {mese_nome} {anno}:\n{programma_testo}", reply_markup=InlineKeyboardMarkup(keyboard))

async def aggiungi(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    context.user_data["attesa_input"] = True
    
    messaggio_bot = await query.message.reply_text("Aggiungi un programma:")
    context.user_data["messaggio_bot"] = messaggio_bot

async def ricevi_programma(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if "attesa_input" not in context.user_data:
        return
    
    testo = update.message.text
    giorno, mese, anno = context.user_data["giorno"], context.user_data["mese"], context.user_data["anno"]
    chiave = (anno, mese, giorno)

    programmi.setdefault(chiave, []).append(f"⌛ {testo}")  

    context.user_data.pop("attesa_input", None)

    # Rispondi con il messaggio di conferma
    messaggio_utente = update.message
    messaggio_bot = await update.message.reply_text("✅ Programma salvato con successo!")
    
    # Invia il messaggio di attesa
    messaggio_attesa = await update.message.reply_text("Attendi un attimo, stiamo cancellando i messaggi ⌛")

    await asyncio.sleep(5)

    # Cancelliamo i messaggi dell'utente e il messaggio di conferma
    await messaggio_utente.delete()
    await messaggio_bot.delete()
    await messaggio_attesa.delete()

    if "messaggio_bot" in context.user_data:
        try:
            await context.user_data["messaggio_bot"].delete()
        except:
            pass
        del context.user_data["messaggio_bot"]

    await seleziona_giorno(update, context)

async def modifica_programma(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    giorno, mese, anno = context.user_data["giorno"], context.user_data["mese"], context.user_data["anno"]
    chiave = (anno, mese, giorno)

    if chiave in programmi and programmi[chiave]:
        keyboard = [[InlineKeyboardButton(f"✅ {p}", callback_data=f"rimuovi_{i}")] for i, p in enumerate(programmi[chiave])]
        keyboard.append([InlineKeyboardButton("⬅️ Indietro", callback_data=f"giorno_{anno}_{mese}_{giorno}")])
        await query.message.edit_text("Seleziona un'attività da completare:", reply_markup=InlineKeyboardMarkup(keyboard))

async def rimuovi_programma(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    _, index = query.data.split("_")
    index = int(index)
    
    giorno, mese, anno = context.user_data["giorno"], context.user_data["mese"], context.user_data["anno"]
    chiave = (anno, mese, giorno)

    if chiave in programmi and 0 <= index < len(programmi[chiave]):
        programmi[chiave][index] = programmi[chiave][index].replace("⌛", "✅")

    # Messaggio di conferma modifica
    messaggio_modifica = await query.message.reply_text("✅ Modifica eseguita con successo!")

    # Invia il messaggio di attesa
    messaggio_attesa = await query.message.reply_text("Attendi un attimo, stiamo cancellando i messaggi ⌛")
    
    await asyncio.sleep(5)
    
    # Cancelliamo solo il messaggio di modifica e il messaggio di attesa
    await messaggio_modifica.delete()
    await messaggio_attesa.delete()

    # Non cancelliamo il messaggio principale del calendario
    await seleziona_giorno(update, context)

async def torna_indietro(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await mostra_giorni(update, context, edit=True)

def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(cambia_mese, pattern="mese_"))
    app.add_handler(CallbackQueryHandler(seleziona_giorno, pattern="giorno_"))
    app.add_handler(CallbackQueryHandler(aggiungi, pattern="aggiungi"))
    app.add_handler(CallbackQueryHandler(modifica_programma, pattern="modifica"))
    app.add_handler(CallbackQueryHandler(rimuovi_programma, pattern="rimuovi_"))
    app.add_handler(CallbackQueryHandler(riepilogo_programmi, pattern="riepilogo_programmi"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, ricevi_programma))
    app.add_handler(CallbackQueryHandler(torna_indietro, pattern="indietro"))

    app.run_polling()

if __name__ == "__main__":
    main()
