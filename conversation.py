import logging
import os
import subprocess
import speech_recognition as sr
from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, Update
from telegram.ext import ContextTypes, ConversationHandler
from glob import glob

logging_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
logging.basicConfig(format=logging_format,
                    level=logging.INFO)
logger = logging.getLogger(__name__)

users = {}
separator_dictionary = {"en-US": "comma",
                        "es-ES": "coma",
                        "fr-FR": "virgule",
                        "de-DE": "komma","pt-BR":"vírgula",
                        "pt-PT": "vírgula"}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        "Hey there! I'm Tytta 🦉 🌙 ✨ \nI will hear voice messages you send me and transcribe them into tables or text documents.\n\n"
        "Here is a list of things you can ask me to do:\n"
        "/record begin a new recording session\n"
        "/stop stop the current recording session or conversation\n"
        "/list\_files list every file\n"
        "/send\_file send you a file\n"
        "/delete\_file delete a file\n\n"
        "If you ever get stuck use /stop",
        parse_mode= "Markdown"
        
    )

def arrange_list_into_equally_sized_sublists(names_list, row_length):
    list_of_equally_sized_lists = [names_list[i:i + row_length] for i in range(0, len(names_list), row_length)]
    return list_of_equally_sized_lists

async def record(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    users[update.message.from_user.id] = {}
    reply_keyboard = arrange_list_into_equally_sized_sublists(list(separator_dictionary.keys()),3)
    await update.message.reply_text(
        "Awesome, lets begin! ✨ \n"
        "I can only read and write english, but I can hear other languages.\n*Which language should I expect you to speak?*\n",
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, input_field_placeholder="Language?"),
        parse_mode= "Markdown"
        
    )
    return 0
    
async def ask_filetype(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    logger.info("%s chose language: %s", update.message.from_user.id, update.message.text)
    users[update.message.from_user.id]["language"] = update.message.text
    user_data = users[update.message.from_user.id]

    reply_keyboard = [["spreadsheet", "text"]]
    await update.message.reply_text(
        f"Ok, so you will be speaking {user_data['language']}!\nAnd would you like me to write what I hear into a spreadsheet or a text document?",
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, input_field_placeholder=".txt/.csv?"
        ),
    )
    return 1

async def ask_new_or_existing(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    logger.info("%s chose to write a %s", update.message.from_user.id, update.message.text)
    users[update.message.from_user.id]["file_type"] = update.message.text

    reply_keyboard = [["new", "existing"]]
    await update.message.reply_text(
        "Do you want to create a *new* file or add to an *existing* one?",
        parse_mode= "Markdown",
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, input_field_placeholder="New or existing?"
        ),
    )
    return 2

async def ask_filename(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    logger.info("%s chose to write to %s file", update.message.from_user.id, update.message.text)
    users[update.message.from_user.id]["file_new_or_existing"] = update.message.text
    user_data = users[update.message.from_user.id]
    
    if user_data["file_type"]=="spreadsheet": extension = ".csv"
    if user_data["file_type"]=="text": extension = ".txt"

    if user_data["file_new_or_existing"] == "existing":
        
        files_list = await get_user_files(update)
        files_list_filtered_by_extension = list(filter(lambda x:x.endswith((extension)), files_list))
        reply_keyboard = arrange_list_into_equally_sized_sublists(files_list_filtered_by_extension, 3)
        
        if len(files_list_filtered_by_extension) == 0: 
            await update.message.reply_text(
            f"No {user_data['file_type']} files were found, how would you like to name your new file? ({user_data['file_type']} file name must end in {extension})",
            reply_markup=ReplyKeyboardRemove()
            )
        else:
            await update.message.reply_text(
                "Choose file",
                reply_markup=ReplyKeyboardMarkup(reply_keyboard,
                    one_time_keyboard=True,
                    input_field_placeholder="Choose file"
                )
            )

    if user_data["file_new_or_existing"] == "new":
        await update.message.reply_text(
            f"How should I name the new file? ({user_data['file_type']} file name should end in {extension})",
            reply_markup=ReplyKeyboardRemove()
        )
    return 3
    
async def give_instructions_and_begin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    logger.info("%s chose the name: %s", update.message.from_user.id, update.message.text)
    users[update.message.from_user.id]["file_name"] = update.message.text
    user_data = users[update.message.from_user.id]

    separator = separator_dictionary[user_data["language"]]
    if user_data["file_type"]=='spreadsheet':
        await update.message.reply_text(
                f"""Starting to take notes 🦉 ✍️.\nSend me the first voice recording!
                
                Every recording you send me will become a new *row* in the *spreadsheet*.\n
                The first recording should contain column names separated by {separator}. Example:\n
                col1 {separator} col2 {separator} col3
                """.replace("    ",''),
        parse_mode= "Markdown"

        )
    if user_data["file_type"]=='text':
        await update.message.reply_text("Let's begin. Send me the first voice recording!\n\nEvery recording you send me will become a nem paragraph on the text document")

    users[update.message.from_user.id]["sent_first_voice_message"] = False #Waiting for the first voice
    return 4

async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    logger.info("User %s canceled the conversation.", update.message.from_user.id)
    await update.message.reply_text(
        "Ok! Stopping this conversation.\n\n"
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
    logger.info("%s Sent an voice", update.message.from_user.id)
    user_data = users[update.message.from_user.id]

    #Create directories for downloading if they don't exists
    recordings_path = "recordings/" + str(update.message.from_user.id)
    documents_path = "transcriptions/" + str(update.message.from_user.id)
    if not user_data["sent_first_voice_message"]:
        os.makedirs(recordings_path, exist_ok=True)
        os.makedirs(documents_path, exist_ok=True)
        users[update.message.from_user.id]["sent_first_voice_message"]=True
    mp3_path = str("recordings/" + str(update.message.from_user.id)+ "/last_voice_message.mp3")
    
    #Download and listen to the file
    await (await context.bot.getFile(update.message.voice.file_id)).download(mp3_path)
    iHeard = convert_mp3_to_str(mp3_path, user_data["language"])
    file_path = documents_path + "/" + user_data["file_name"]
    return iHeard, file_path

async def write_file(update: Update, context: ContextTypes.DEFAULT_TYPE, iHeard, file_path) -> int:
    user_data = users[update.message.from_user.id]


    if user_data["file_type"]=='spreadsheet':
        separator = " " + separator_dictionary[user_data["language"]] + " "
        row = iHeard.replace(separator,",")
        with open(file_path, 'a', newline='') as csv:
            csv.write(row + '\n')
            csv.close()
        await update.message.reply_text(
            "Record voice to add another row, or /stop this session."
        )
    
    if user_data["file_type"]=='text':
        row=iHeard
        with open(file_path,'a', newline='') as txt:
            txt.write(row + '\n')
            txt.close()
        await update.message.reply_text("Record voice to add another paragraph or /stop this session.")
    file_path = str(update.message.from_user.id) + "/" + user_data["file_name"]
    logger.info(f"Wrote:{row}\n to the file {file_path}")
    await update.message.reply_text('Wrote to the file:')
    await update.message.reply_text(row)

async def transcribe_voice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    iHeard, file_path = await download_and_listen(update, context)
    await write_file(update, context, iHeard, file_path)
    return 5

async def get_user_files(update):
    try:
        files_list = os.listdir(str("transcriptions/" + str(update.message.from_user.id)))
    except FileNotFoundError:
        files_list=[]
    if len(files_list) == 0:
        await update.message.reply_text(
            "You don't have any files yet",
            reply_markup=ReplyKeyboardRemove()
        )
    return files_list

async def list_files(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    logger.info("User %s requested files list.", update.message.from_user.id)
    
    files_list = await get_user_files(update)
    files_string = "\n".join(files_list)
    if len(files_list) > 0:
        await update.message.reply_text(
            f"Here is a list of the files you have worked on today:\n{files_string}", reply_markup=ReplyKeyboardRemove()
        )
    return ConversationHandler.END

async def choose_file_to_send(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    logger.info("User %s wants to receive a file.", update.message.from_user.id)
    files_list = await get_user_files(update)
    if len(files_list) > 0:
        files_list = arrange_list_into_equally_sized_sublists(files_list, 3)
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
    logger.info("Sending file %s to %s.", chosen_filename, update.message.from_user.id)

    file_path = str("transcriptions/" + str(update.message.from_user.id)) + "/" + chosen_filename
    file = open(file_path, 'rb')
    await context.bot.send_document(chat_id, file)

    await update.message.reply_text(
        f"Sending {chosen_filename}...",
        reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END


async def choose_file_to_delete(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    logger.info("User %s wants to delete a file.", update.message.from_user.id)

    files_list = await get_user_files(update)

    if len(files_list) > 0:
        files_list = arrange_list_into_equally_sized_sublists(files_list, 3)
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
    logger.info("Deleting file %s from %s.", chosen_filename, update.message.from_user.id)
    if chosen_filename == "delete all files":
        files = glob(str("transcriptions/" + str(update.message.from_user.id)) + "/*")
        for f in files:
            print(f)
            os.remove(f)
    else:
        file_path = str("transcriptions/" + str(update.message.from_user.id)) + "/" + chosen_filename
        os.remove(file_path)

    await update.message.reply_text(
        f"Deleting {chosen_filename.replace('delete ', '')}...",
        reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END
