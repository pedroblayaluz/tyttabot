import logging
import os
import subprocess
import speech_recognition as sr
from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, Update
from telegram.ext import ContextTypes, ConversationHandler
from glob import glob

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

USER_ID, LANGUAGE, FILE_TYPE, NEW_OR_EXISTING, FILE_NAME, SENT_FIRST_VOICE, VOICE = range(7)
user_data = {}
separator_dictionary = {"en-US":"comma", "es-ES":"coma", "fr-FR":"virgule", "de-DE":"komma","pt-BR":"vírgula", "pt-PT":"vírgula"}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_data[USER_ID] = update.message.from_user.id
    await update.message.reply_text(
        "Hey there! I'm Tytta 🦉 🌙 ✨ \nI will hear voice messages you send me and transcribe them into tables or text documents.\n\n"
        "Here is a list of things you can ask me to do:\n"
        "/record begin a new recording session\n"
        "/stop stop the current recording session\n"
        "/list\_files list every file\n"
        "/send\_file send you a file\n"
        "/delete\_file delete a file\n\n",
        parse_mode= "Markdown"
        
    )

async def record(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_data[USER_ID] = update.message.from_user.id
    reply_keyboard = [["pt-BR", "pt-PT", "en-US"], ["es-ES", "fr-FR", "de-DE"]]
    await update.message.reply_text(
        "Awesome, lets begin! ✨ \n"
        "I can only read and write english, but I can hear other languages.\n*Which language should I expect you to speak?*\n",
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, input_field_placeholder="Language?"),
        parse_mode= "Markdown"
        
    )
    return LANGUAGE

async def ask_filetype(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    logger.info("%s chose language: %s", user_data[USER_ID], update.message.text)
    user_data[LANGUAGE] = update.message.text
    reply_keyboard = [["spreadsheet", "text"]]
    await update.message.reply_text(
        f"Ok, so you will be speaking {user_data[LANGUAGE]}!\nAnd would you like me to write what I hear into a spreadsheet or a text document?",
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, input_field_placeholder=".txt/.csv?"
        ),
    )
    return FILE_TYPE

async def ask_new_or_existing(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    logger.info("%s chose to write a %s", user_data[USER_ID], update.message.text)
    user_data[FILE_TYPE] = update.message.text
    reply_keyboard = [["new", "existing"]]
    await update.message.reply_text(
        "Do you want to create a *new* file or add to an *existing* one?",
        parse_mode= "Markdown",
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, input_field_placeholder="New or existing?"
        ),
    )
    return NEW_OR_EXISTING


async def ask_filename(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    logger.info("%s chose to write to %s file", user_data[USER_ID], update.message.text)
    user_data[NEW_OR_EXISTING] = update.message.text

    if user_data[FILE_TYPE]=="spreadsheet": extension = ".csv"
    if user_data[FILE_TYPE]=="text": extension = ".txt"

    if user_data[NEW_OR_EXISTING] == "existing":
        
        files_list = os.listdir(str("transcriptions/" + str(user_data[USER_ID])))
        files_list_filtered_by_extension = list(filter(lambda x:x.endswith((extension)), files_list))
        files_list_arranged_in_rows_of_3 = [files_list_filtered_by_extension[i:i + 3] for i in range(0, len(files_list_filtered_by_extension), 3)]
        
        if len(files_list_filtered_by_extension) == 0: 
            await update.message.reply_text(
            f"No {user_data[FILE_TYPE]} files were found, how would you like to name your new file? ({user_data[FILE_TYPE]} file name must end in {extension}",
            reply_markup=ReplyKeyboardRemove()
            )
        else:
            await update.message.reply_text(
                "Choose file",
                reply_markup=ReplyKeyboardMarkup(files_list_arranged_in_rows_of_3,
                    one_time_keyboard=True,
                    input_field_placeholder="Choose file"
                )
            )

    if user_data[NEW_OR_EXISTING] == "new":
        await update.message.reply_text(
            f"How should I name the new file? ({user_data[FILE_TYPE]} file name should end in {extension})",
            reply_markup=ReplyKeyboardRemove()
        )
    return FILE_NAME
    
async def give_instructions_and_begin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    logger.info("%s chose the name: %s", user_data[USER_ID], update.message.text)
    user_data[FILE_NAME] = update.message.text
    separator = separator_dictionary[user_data[LANGUAGE]]
    if user_data[FILE_TYPE]=='spreadsheet':
        await update.message.reply_text(
                f"""Starting to take notes 🦉 ✍️.\nSend me the first voice recording!
                
                Every recording you send me will become a new *row* in the *spreadsheet*.\n
                The first recording should contain column names separated by {separator}. Example:\n
                col1 {separator} col2 {separator} col3
                """.replace("    ",''),
        parse_mode= "Markdown"

        )
    if user_data[FILE_TYPE]=='text':
        await update.message.reply_text("Let's begin. Send me the first voice recording!\n\nEvery recording you send me will become a nem paragraph on the text document")
    user_data[SENT_FIRST_VOICE] = False #Waiting for the first voice
    return SENT_FIRST_VOICE

async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    logger.info("User %s canceled the conversation.", user_data[USER_ID])
    await update.message.reply_text(
        "Ok! Stopping this recording session.\n\n"
        "Here is a list of things you can ask me to do:\n"
        "/record begin a new recording session\n"
        "/list_files list every file\n"
        "/send_file send you a file\n"
        "/delete_file delete a file\n\n", reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END

def convert_mp3_to_str(mp3_path, language):
    #MP3 to WAV:
    subprocess.run(["ffmpeg", "-y", "-i", mp3_path, mp3_path.replace('mp3','wav')], 
        stdout=subprocess.DEVNULL,
        stderr=subprocess.STDOUT)
    #Recognize speech
    r = sr.Recognizer()
    with sr.AudioFile(mp3_path.replace('mp3','wav')) as source:
        voice = r.record(source)
    try:
        s = r.recognize_google(voice,language=language)
        print("Text: "+ s)
    except Exception as e:
        print("Exception: "+ str(e))
    return s

async def download_and_listen(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    logger.info("%s Sent an voice", user_data[USER_ID])

    #Create directories for downloading if they don't exists
    recordings_path = "recordings/" + str(user_data[USER_ID])
    documents_path = "transcriptions/" + str(user_data[USER_ID])
    if not user_data[SENT_FIRST_VOICE]:
        os.makedirs(recordings_path, exist_ok=True)
        os.makedirs(documents_path, exist_ok=True)
        user_data[SENT_FIRST_VOICE]=True
    mp3_path = str("recordings/" + str(user_data[USER_ID])+ "/last_voice_message.mp3")
    
    #Download and listen to the file
    await (await context.bot.getFile(update.message.voice.file_id)).download(mp3_path)
    iHeard = convert_mp3_to_str(mp3_path, user_data[LANGUAGE])
    file_path = documents_path + "/" + user_data[FILE_NAME]
    return iHeard, file_path

async def write_file(update: Update, context: ContextTypes.DEFAULT_TYPE, iHeard, file_path) -> int:

    if user_data[FILE_TYPE]=='spreadsheet':
        separator = " " + separator_dictionary[user_data[LANGUAGE]] + " "
        row = iHeard.replace(separator,",")
        with open(file_path, 'a', newline='') as csv:
            csv.write(row + '\n')
            csv.close()
        await update.message.reply_text(
            "Record voice to add another row, or /stop this session."
        )
    
    if user_data[FILE_TYPE]=='text':
        row=iHeard
        with open(file_path,'a', newline='') as txt:
            txt.write(row + '\n')
            txt.close()
        await update.message.reply_text("Record voice to add another paragraph or /stop this session.")
    file_path = str(user_data[USER_ID]) + "/" + user_data[FILE_NAME]
    logger.info(f"Wrote:{row}\n to the file {file_path}")
    await update.message.reply_text('Wrote to the file:')
    await update.message.reply_text(row)

async def transcribe_voice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    iHeard, file_path = await download_and_listen(update, context)
    await write_file(update, context, iHeard, file_path)
    return VOICE

async def list_files(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    logger.info("User %s requested files list.", user_data[USER_ID])
    
    files_list = os.listdir(str("transcriptions/" + str(user_data[USER_ID])))
    files_string = "\n".join(files_list)
    await update.message.reply_text(
        f"Here is a list of the files you have worked on today:\n {files_string}", reply_markup=ReplyKeyboardRemove()
    )


async def choose_file_to_send(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    logger.info("User %s wants to receive a file.", user_data[USER_ID])

    files_list = os.listdir(str("transcriptions/" + str(user_data[USER_ID])))
    files_list = [files_list[i:i + 3] for i in range(0, len(files_list), 3)]

    await update.message.reply_text(
        "Choose file",
        reply_markup=ReplyKeyboardMarkup(files_list,
            one_time_keyboard=True,
            input_field_placeholder="send file"
        )
    )
    return 0


async def send_file(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    chat_id = update.message.chat_id
    chosen_filename = update.message.text
    logger.info("Sending file %s to %s.", chosen_filename, user_data[USER_ID])

    file_path = str("transcriptions/" + str(user_data[USER_ID])) + "/" + chosen_filename
    file = open(file_path, 'rb')
    await context.bot.send_document(chat_id, file)

    await update.message.reply_text(
        f"Sending {chosen_filename}...",
        reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END


async def choose_file_to_delete(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    logger.info("User %s wants to delete a file.", user_data[USER_ID])

    files_list = os.listdir(str("transcriptions/" + str(user_data[USER_ID])))
    files_list = [files_list[i:i + 3] for i in range(0, len(files_list), 3)]
    files_list.insert(0, ["delete all files"])
    await update.message.reply_text(
        "Choose file to delete",
        reply_markup=ReplyKeyboardMarkup(files_list,
            one_time_keyboard=True,
            input_field_placeholder="delete file"
        )
    )
    return 0


async def delete_file(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    chosen_filename = update.message.text
    logger.info("Deleting file %s from %s.", chosen_filename, user_data[USER_ID])
    if chosen_filename == "delete all files":
        files = glob(str("transcriptions/" + str(user_data[USER_ID])) + "/*")
        for f in files:
            print(f)
            os.remove(f)
    else:
        file_path = str("transcriptions/" + str(user_data[USER_ID])) + "/" + chosen_filename
        os.remove(file_path)

    await update.message.reply_text(
        f"Deleting {chosen_filename}...",
        reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END