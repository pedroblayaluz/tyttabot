from conversation import (
    delete_file, start, record, stop,
    ask_filetype, ask_new_or_existing, ask_filename, give_instructions_and_begin, transcribe_voice,
    list_files, choose_file_to_send, send_file, choose_file_to_delete, delete_file,
    cheat_send_every_file)

from telegram.ext import (
    Application,
    CommandHandler,
    ConversationHandler,
    MessageHandler,
    filters,
)
import os

def main() -> None:
    application = Application.builder().token(os.environ["BOT_TOKEN"]).build()

    application.add_handler(CommandHandler("start", start))

    transcription_handler = ConversationHandler(
        entry_points=[CommandHandler("record", record)],
        states={
            0: [MessageHandler(filters.Regex("^(pt-BR|pt-PT|en-US|es-ES|fr-FR||de-DE)$"), ask_filetype)],
            1: [MessageHandler(filters.Regex("^(spreadsheet|text)$"), ask_new_or_existing)],
            2: [MessageHandler(filters.Regex("^(new|existing)$"), ask_filename)],
            3: [MessageHandler(filters.Regex("(.csv|.txt)$"), give_instructions_and_begin)],
            4: [MessageHandler(filters.VOICE, transcribe_voice)],
            5: [MessageHandler(filters.VOICE, transcribe_voice)]
        },
        fallbacks=[CommandHandler("stop", stop)],
    )
    application.add_handler(transcription_handler)
    application.add_handler(CommandHandler("list_files", list_files))

    send_file_handler = ConversationHandler(
            entry_points=[CommandHandler("send_file", choose_file_to_send)],
            states={
                0: [MessageHandler(filters.Regex("(.csv|.txt)$"), send_file)]
            },
            fallbacks=[CommandHandler("stop", stop)],
    )

    delete_file_handler = ConversationHandler(
            entry_points=[CommandHandler("delete_file", choose_file_to_delete)],
            states={
                0: [MessageHandler(filters.Regex("(.csv|.txt|delete all files)$"), delete_file)]
            },
            fallbacks=[CommandHandler("stop", stop)],
    )
    application.add_handler(send_file_handler)
    application.add_handler(delete_file_handler)
    application.add_handler(CommandHandler("cheat_send_every_file", cheat_send_every_file))

    application.run_polling()


if __name__ == "__main__":
    main()