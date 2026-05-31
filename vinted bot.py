"""
🤖 VintedBot — Telegram Bot do Resell
=====================================
Funkcje:
- /marza - kalkulator marży
- /kupno - zapisz zakup
- /sprzedaz - zapisz sprzedaż
- /stan - podsumowanie finansów
- /historia - lista transakcji
- /przypomnienie - ustaw przypomnienie o odświeżaniu
- /szablony - gotowe opisy do ogłoszeń
- Automatyczne podsumowanie o 22:00

Instalacja:
    pip install python-telegram-bot apscheduler

Uruchomienie:
    1. Stwórz bota przez @BotFather na Telegramie → dostaniesz TOKEN
    2. Wpisz TOKEN poniżej (BOT_TOKEN)
    3. python vinted_bot.py
"""

import json
import os
import logging
from datetime import datetime, time
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, ContextTypes,
    CallbackQueryHandler, MessageHandler, filters, ConversationHandler
)
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# ============================================================
# KONFIGURACJA — wpisz swój token od @BotFather
# ============================================================
BOT_TOKEN = "WPISZ_TUTAJ_TOKEN"
# ============================================================

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DATA_FILE = "transakcje.json"
REMINDERS_FILE = "przypomnienia.json"

SHIPPING_COST = 14  # domyślny koszt wysyłki InPost

# ===================== DANE =====================

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"transakcje": [], "aktywne": []}

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def load_reminders():
    if os.path.exists(REMINDERS_FILE):
        with open(REMINDERS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_reminders(data):
    with open(REMINDERS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# ===================== KOMENDY =====================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tekst = (
        "👋 Cześć! Jestem Twoim botem do resell na Vinted!\n\n"
        "📋 *Co umiem:*\n"
        "💰 /marza [koszt] [sprzedaż] — kalkulator marży\n"
        "🛒 /kupno [nazwa] [cena] — zapisz zakup\n"
        "✅ /sprzedaz [nazwa] [cena] — zapisz sprzedaż\n"
        "📊 /stan — podsumowanie finansów\n"
        "📝 /historia — lista transakcji\n"
        "⏰ /przypomnienie [co ile godzin] — przypomnienie o odświeżaniu\n"
        "📄 /szablony — gotowe opisy ogłoszeń\n"
        "❓ /pomoc — ta wiadomość\n\n"
        "🚀 Zacznij od `/marza 40 90` żeby sprawdzić zysk!"
    )
    await update.message.reply_text(tekst, parse_mode="Markdown")

async def marza(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args

    if len(args) < 2:
        await update.message.reply_text(
            "❌ Użycie: `/marza [koszt_zakupu] [cena_sprzedaży]`\n"
            "Przykład: `/marza 45 90`\n\n"
            "Opcjonalnie z własnym kosztem wysyłki:\n"
            "`/marza 45 90 12`",
            parse_mode="Markdown"
        )
        return

    try:
        koszt = float(args[0])
        sprzedaz = float(args[1])
        wysylka = float(args[2]) if len(args) > 2 else SHIPPING_COST

        zysk = sprzedaz - koszt - wysylka
        procent = (zysk / koszt * 100) if koszt > 0 else 0

        if zysk > 0:
            emoji = "✅" if procent > 30 else "⚠️"
        else:
            emoji = "❌"

        ocena = ""
        if procent >= 50:
            ocena = "🔥 Świetna okazja!"
        elif procent >= 30:
            ocena = "👍 Dobra marża"
        elif procent >= 10:
            ocena = "😐 Słaba marża"
        else:
            ocena = "🚫 Nie warto"

        tekst = (
            f"{emoji} *Kalkulator marży*\n\n"
            f"🛒 Koszt zakupu: `{koszt:.2f} zł`\n"
            f"💵 Cena sprzedaży: `{sprzedaz:.2f} zł`\n"
            f"📦 Koszt wysyłki: `{wysylka:.2f} zł`\n"
            f"{'─' * 25}\n"
            f"💰 Zysk netto: `{zysk:.2f} zł`\n"
            f"📈 Marża: `{procent:.1f}%`\n\n"
            f"{ocena}"
        )
        await update.message.reply_text(tekst, parse_mode="Markdown")

    except ValueError:
        await update.message.reply_text("❌ Podaj liczby! Przykład: `/marza 45 90`", parse_mode="Markdown")

async def kupno(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args

    if len(args) < 2:
        await update.message.reply_text(
            "❌ Użycie: `/kupno [nazwa] [cena]`\n"
            "Przykład: `/kupno \"Nike Air Force\" 45`",
            parse_mode="Markdown"
        )
        return

    try:
        cena = float(args[-1])
        nazwa = " ".join(args[:-1])

        data = load_data()
        transakcja = {
            "id": len(data["transakcje"]) + 1,
            "nazwa": nazwa,
            "koszt": cena,
            "status": "aktywne",
            "data_zakupu": datetime.now().strftime("%d.%m.%Y %H:%M"),
            "cena_sprzedazy": None,
            "data_sprzedazy": None
        }
        data["transakcje"].append(transakcja)
        data["aktywne"].append(transakcja["id"])
        save_data(data)

        await update.message.reply_text(
            f"✅ *Zakup zapisany!*\n\n"
            f"🏷️ Produkt: `{nazwa}`\n"
            f"💸 Zapłacono: `{cena:.2f} zł`\n"
            f"📅 Data: {transakcja['data_zakupu']}\n"
            f"🔖 ID: `#{transakcja['id']}`\n\n"
            f"Gdy sprzedasz użyj: `/sprzedaz {nazwa} [cena]`",
            parse_mode="Markdown"
        )
    except ValueError:
        await update.message.reply_text("❌ Błąd! Przykład: `/kupno Nike 45`", parse_mode="Markdown")

async def sprzedaz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args

    if len(args) < 2:
        await update.message.reply_text(
            "❌ Użycie: `/sprzedaz [nazwa lub ID] [cena]`\n"
            "Przykład: `/sprzedaz Nike 90` lub `/sprzedaz #3 90`",
            parse_mode="Markdown"
        )
        return

    try:
        cena_sprzedazy = float(args[-1])
        identyfikator = " ".join(args[:-1])

        data = load_data()
        znaleziono = None

        for t in data["transakcje"]:
            if t["status"] == "aktywne":
                if identyfikator.startswith("#"):
                    if t["id"] == int(identyfikator[1:]):
                        znaleziono = t
                        break
                else:
                    if identyfikator.lower() in t["nazwa"].lower():
                        znaleziono = t
                        break

        if not znaleziono:
            await update.message.reply_text(
                f"❌ Nie znaleziono aktywnego zakupu: `{identyfikator}`\n"
                "Sprawdź `/historia` żeby zobaczyć wszystkie produkty.",
                parse_mode="Markdown"
            )
            return

        znaleziono["status"] = "sprzedane"
        znaleziono["cena_sprzedazy"] = cena_sprzedazy
        znaleziono["data_sprzedazy"] = datetime.now().strftime("%d.%m.%Y %H:%M")
        if znaleziono["id"] in data["aktywne"]:
            data["aktywne"].remove(znaleziono["id"])
        save_data(data)

        zysk = cena_sprzedazy - znaleziono["koszt"] - SHIPPING_COST
        procent = (zysk / znaleziono["koszt"] * 100) if znaleziono["koszt"] > 0 else 0

        await update.message.reply_text(
            f"🎉 *Sprzedaż zapisana!*\n\n"
            f"🏷️ Produkt: `{znaleziono['nazwa']}`\n"
            f"🛒 Kupiono za: `{znaleziono['koszt']:.2f} zł`\n"
            f"💵 Sprzedano za: `{cena_sprzedazy:.2f} zł`\n"
            f"📦 Wysyłka: `{SHIPPING_COST:.2f} zł`\n"
            f"{'─' * 25}\n"
            f"💰 Zysk: `{zysk:.2f} zł` ({procent:.1f}%)\n\n"
            f"{'🔥 Świetna sprzedaż!' if procent > 40 else '👍 Niezłe!'}",
            parse_mode="Markdown"
        )
    except ValueError:
        await update.message.reply_text("❌ Błąd! Przykład: `/sprzedaz Nike 90`", parse_mode="Markdown")

async def stan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = load_data()
    transakcje = data["transakcje"]

    sprzedane = [t for t in transakcje if t["status"] == "sprzedane"]
    aktywne = [t for t in transakcje if t["status"] == "aktywne"]

    total_zysk = sum(
        t["cena_sprzedazy"] - t["koszt"] - SHIPPING_COST
        for t in sprzedane
        if t["cena_sprzedazy"]
    )
    total_zainwestowane = sum(t["koszt"] for t in aktywne)
    total_wydane = sum(t["koszt"] for t in sprzedane)

    tekst = (
        f"📊 *Twoje statystyki*\n\n"
        f"✅ Sprzedanych produktów: `{len(sprzedane)}`\n"
        f"🛒 Aktywnych ogłoszeń: `{len(aktywne)}`\n"
        f"{'─' * 25}\n"
        f"💰 Łączny zysk: `{total_zysk:.2f} zł`\n"
        f"📦 Zamrożony kapitał: `{total_zainwestowane:.2f} zł`\n\n"
    )

    if aktywne:
        tekst += "🏷️ *Aktywne ogłoszenia:*\n"
        for t in aktywne[:5]:
            tekst += f"• #{t['id']} {t['nazwa']} — `{t['koszt']:.2f} zł`\n"
        if len(aktywne) > 5:
            tekst += f"_...i {len(aktywne) - 5} więcej_\n"

    await update.message.reply_text(tekst, parse_mode="Markdown")

async def historia(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = load_data()
    transakcje = data["transakcje"]

    if not transakcje:
        await update.message.reply_text("📭 Brak transakcji. Dodaj pierwszą przez `/kupno`!", parse_mode="Markdown")
        return

    ostatnie = transakcje[-10:][::-1]
    tekst = "📝 *Ostatnie transakcje:*\n\n"

    for t in ostatnie:
        if t["status"] == "sprzedane":
            zysk = t["cena_sprzedazy"] - t["koszt"] - SHIPPING_COST
            tekst += f"✅ #{t['id']} *{t['nazwa']}*\n"
            tekst += f"   {t['koszt']}→{t['cena_sprzedazy']} zł | zysk: `{zysk:.2f} zł`\n\n"
        else:
            tekst += f"🔄 #{t['id']} *{t['nazwa']}* — `{t['koszt']:.2f} zł` (aktywne)\n\n"

    await update.message.reply_text(tekst, parse_mode="Markdown")

async def przypomnienie(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    user_id = str(update.effective_user.id)

    if not args:
        reminders = load_reminders()
        if user_id in reminders:
            co_ile = reminders[user_id]["co_ile_godzin"]
            await update.message.reply_text(
                f"⏰ Masz ustawione przypomnienie co *{co_ile}h*\n\n"
                f"Aby zmienić: `/przypomnienie [godziny]`\n"
                f"Aby wyłączyć: `/przypomnienie 0`",
                parse_mode="Markdown"
            )
        else:
            await update.message.reply_text(
                "⏰ Brak przypomnienia.\n"
                "Ustaw: `/przypomnienie 3` (co 3 godziny)\n"
                "Opcje: 2, 3, 4, 6, 8, 12 godzin",
                parse_mode="Markdown"
            )
        return

    try:
        co_ile = int(args[0])
        reminders = load_reminders()

        if co_ile == 0:
            if user_id in reminders:
                del reminders[user_id]
                save_reminders(reminders)
            await update.message.reply_text("🔕 Przypomnienia wyłączone.")
            return

        if co_ile not in [1, 2, 3, 4, 6, 8, 12, 24]:
            await update.message.reply_text("❌ Podaj: 1, 2, 3, 4, 6, 8, 12 lub 24 godziny")
            return

        reminders[user_id] = {
            "co_ile_godzin": co_ile,
            "chat_id": update.effective_chat.id,
            "ostatnie": datetime.now().isoformat()
        }
        save_reminders(reminders)

        await update.message.reply_text(
            f"✅ Przypomnienie ustawione!\n\n"
            f"⏰ Co *{co_ile} godziny* przypomnę Ci o odświeżeniu ogłoszeń na Vinted 🔄",
            parse_mode="Markdown"
        )
    except ValueError:
        await update.message.reply_text("❌ Przykład: `/przypomnienie 3`", parse_mode="Markdown")

async def szablony(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("👟 Buty", callback_data="szablon_buty")],
        [InlineKeyboardButton("👕 Ubrania", callback_data="szablon_ubrania")],
        [InlineKeyboardButton("🎮 Elektronika", callback_data="szablon_elektronika")],
        [InlineKeyboardButton("👜 Torebki/Plecaki", callback_data="szablon_torby")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("📄 Wybierz kategorię szablonu:", reply_markup=reply_markup)

async def szablon_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    szablony_dict = {
        "szablon_buty": (
            "👟 *Szablon — Buty*\n\n"
            "```\n"
            "✅ Stan: [idealny/bardzo dobry/dobry]\n"
            "📏 Rozmiar: [XX] EU — mierzone przeze mnie\n"
            "🔍 Opis: [marka, model, kolor]\n"
            "📦 Wysyłka: 24h po płatności, InPost\n"
            "❓ Pytania? Chętnie odpowiem!\n"
            "```"
        ),
        "szablon_ubrania": (
            "👕 *Szablon — Ubrania*\n\n"
            "```\n"
            "✅ Stan: [idealny/bardzo dobry/dobry]\n"
            "📏 Rozmiar: [XS/S/M/L/XL] — wymiary na zdjęciu\n"
            "🏷️ Marka: [nazwa]\n"
            "🔍 Kolor: [kolor]\n"
            "📦 Wysyłka: 24h po płatności\n"
            "🔄 Możliwa wymiana: tak/nie\n"
            "```"
        ),
        "szablon_elektronika": (
            "🎮 *Szablon — Elektronika*\n\n"
            "```\n"
            "✅ Stan: [używany/bardzo dobry]\n"
            "⚙️ Działa: w 100%\n"
            "📦 Zawartość: [co w zestawie]\n"
            "🔋 Bateria: [X%] pojemności\n"
            "📅 Rok zakupu: [rok]\n"
            "🚫 Bez iCloud / bez blokad\n"
            "📦 Wysyłka: zadbane pakowanie, 24h\n"
            "```"
        ),
        "szablon_torby": (
            "👜 *Szablon — Torebki/Plecaki*\n\n"
            "```\n"
            "✅ Stan: [idealny/bardzo dobry]\n"
            "📐 Wymiary: [szer x wys x głęb] cm\n"
            "🏷️ Marka: [nazwa] (oryginał)\n"
            "🔍 Kolor: [kolor]\n"
            "🧹 Czyszczona: tak/nie\n"
            "📦 Wysyłka: 24h, zapakowane w folię\n"
            "```"
        ),
    }

    tekst = szablony_dict.get(query.data, "❌ Nieznany szablon")
    await query.edit_message_text(tekst, parse_mode="Markdown")

async def pomoc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await start(update, context)

# ===================== SCHEDULER =====================

async def wyslij_przypomnienia(application):
    reminders = load_reminders()
    teraz = datetime.now()

    for user_id, info in reminders.items():
        ostatnie = datetime.fromisoformat(info["ostatnie"])
        co_ile = info["co_ile_godzin"]
        roznica = (teraz - ostatnie).total_seconds() / 3600

        if roznica >= co_ile:
            try:
                await application.bot.send_message(
                    chat_id=info["chat_id"],
                    text=(
                        "🔔 *Czas odświeżyć ogłoszenia na Vinted!*\n\n"
                        "📱 Wejdź w swoje ogłoszenia i kliknij 'Odśwież'\n"
                        "⏰ Najlepszy czas: teraz!\n\n"
                        "_Aktywne ogłoszenia są wyżej w wynikach_ 🚀"
                    ),
                    parse_mode="Markdown"
                )
                reminders[user_id]["ostatnie"] = teraz.isoformat()
            except Exception as e:
                logger.error(f"Błąd wysyłania przypomnienia: {e}")

    save_reminders(reminders)

async def wyslij_podsumowanie_dnia(application):
    reminders = load_reminders()
    data = load_data()
    dzisiaj = datetime.now().strftime("%d.%m.%Y")

    sprzedane_dzis = [
        t for t in data["transakcje"]
        if t["status"] == "sprzedane" and t.get("data_sprzedazy", "").startswith(dzisiaj)
    ]
    aktywne = [t for t in data["transakcje"] if t["status"] == "aktywne"]
    zysk_dzis = sum(
        t["cena_sprzedazy"] - t["koszt"] - SHIPPING_COST
        for t in sprzedane_dzis
        if t.get("cena_sprzedazy")
    )

    chat_ids = set(info["chat_id"] for info in reminders.values())

    for chat_id in chat_ids:
        try:
            await application.bot.send_message(
                chat_id=chat_id,
                text=(
                    f"🌙 *Podsumowanie dnia — {dzisiaj}*\n\n"
                    f"✅ Sprzedaży dziś: `{len(sprzedane_dzis)}`\n"
                    f"💰 Zysk dziś: `{zysk_dzis:.2f} zł`\n"
                    f"🛒 Aktywnych ogłoszeń: `{len(aktywne)}`\n\n"
                    f"{'🔥 Dobry dzień!' if zysk_dzis > 0 else '😴 Jutro będzie lepiej!'}\n\n"
                    f"💡 Pamiętaj odświeżyć ogłoszenia rano!"
                ),
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.error(f"Błąd podsumowania: {e}")

# ===================== MAIN =====================

def main():
    if BOT_TOKEN == "WPISZ_TUTAJ_TOKEN":
        print("❌ BŁĄD: Wpisz token bota w zmiennej BOT_TOKEN!")
        print("   1. Napisz do @BotFather na Telegramie")
        print("   2. Wpisz /newbot i postępuj zgodnie z instrukcją")
        print("   3. Skopiuj token i wklej w BOT_TOKEN")
        return

    app = Application.builder().token(BOT_TOKEN).build()

    # Handlery komend
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("pomoc", pomoc))
    app.add_handler(CommandHandler("marza", marza))
    app.add_handler(CommandHandler("kupno", kupno))
    app.add_handler(CommandHandler("sprzedaz", sprzedaz))
    app.add_handler(CommandHandler("stan", stan))
    app.add_handler(CommandHandler("historia", historia))
    app.add_handler(CommandHandler("przypomnienie", przypomnienie))
    app.add_handler(CommandHandler("szablony", szablony))
    app.add_handler(CallbackQueryHandler(szablon_callback, pattern="^szablon_"))

    # Scheduler
    scheduler = AsyncIOScheduler()

    # Sprawdzaj przypomnienia co 30 minut
    scheduler.add_job(
        wyslij_przypomnienia,
        "interval",
        minutes=30,
        args=[app]
    )

    # Podsumowanie dnia o 22:00
    scheduler.add_job(
        wyslij_podsumowanie_dnia,
        "cron",
        hour=22,
        minute=0,
        args=[app]
    )

    scheduler.start()

    print("✅ Bot uruchomiony!")
    print("📱 Napisz /start na Telegramie żeby zacząć")
    print("⏹️  Ctrl+C aby zatrzymać\n")

    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
