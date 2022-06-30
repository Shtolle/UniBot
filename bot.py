from config import TOKEN


# from qrtools.qrtools import QR


from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from pytube import YouTube

from urllib import request
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from moviepy.editor import VideoFileClip

import requests
import cv2 
import ssl
import os
import time
import qrcode
import json

ssl._create_default_https_context = ssl._create_unverified_context


class YtDownload(StatesGroup):
    link = State()
    format = State()
    quality = State()

class QrCode(StatesGroup):
    text= State()
    photo= State()



storage = MemoryStorage()
bot = Bot(token=TOKEN)
dp = Dispatcher(bot, storage=storage)


mp4Btn = KeyboardButton("MP4")
mp3Btn = KeyboardButton("MP3")
quality144 = KeyboardButton("144")
quality240 = KeyboardButton("240")
quality360 = KeyboardButton("360")
quality720 = KeyboardButton("720")
youtubeBtn = KeyboardButton("/youtube")
qrCodeBtn = KeyboardButton("/qrCode")
closeBtn = KeyboardButton("close")
decodeBtn = KeyboardButton("/encode")
encodeBtn = KeyboardButton("/decode")



actionKbd = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True, row_width=2).row(youtubeBtn, qrCodeBtn)
formatKbd = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True).row(mp4Btn, mp3Btn,closeBtn)
qualityKbd = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True).row(quality144, quality240,quality360, quality720,closeBtn)
qrKbrd = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True).row(decodeBtn, encodeBtn,closeBtn)


det = cv2.QRCodeDetector()

@dp.message_handler(commands=['start'])
async def process_hello(message: types.Message):
    await bot.send_message(message.from_user.id,  "Heey, how can I help?", reply_markup = actionKbd)


async def yt_video_download(message,link, format, quality):
    name = time.time()
    try:
        if link.find("https://www.youtube.com/watch") != -1 or link.find("https://youtu.be/") != -1 :
            if format =="MP4":
                await bot.send_message(message.from_user.id,"Trying to access...", reply_markup=actionKbd )
                yt = YouTube(link)
                mp4_files = yt.streams.filter(file_extension="mp4")
                file = mp4_files.get_by_resolution(f"{quality}p")

                await bot.send_message(message.from_user.id,"Downloading..." )

                file.download(output_path= "Videos", filename=f"{name}.mp4")

                await bot.send_message(message.from_user.id,"Finished, sending...")
                file_size = os.path.getsize(f'Videos/{name}.mp4')
                file_size = file_size/1000000
                if file_size > 50:
                    await bot.send_message(message.from_user.id,"It looks like your file is too large, we will send the cropped version (might take a while)")
                    data = cv2.VideoCapture(f'Videos/{name}.mp4')
                    # count the number of frames
                    frames = data.get(cv2.CAP_PROP_FRAME_COUNT)
                    fps = int(data.get(cv2.CAP_PROP_FPS))
                    # calculate duration of the video
                    duration = int(frames / fps)
                    #trimming
                    trimmedClip = VideoFileClip(f'Videos/{name}.mp4').subclip(0, 400 if quality=="720" else 1200)
                    trimmedClip.write_videofile(f'Videos/{name}copy.mp4')
                    await bot.send_message(message.from_user.id,"Trimmed, uploading")
                    files={'video': open(f'Videos/{name}copy.mp4','rb')}
                    print("Got your files")
                    values={'chat_id' : message.chat.id, "width":1280, "height":720}
                    response = requests.post(f"https://api.telegram.org/bot{TOKEN}/sendVideo", files=files, data=values)

                else:
                    files={'video': open(f'Videos/{name}.mp4','rb')}
                    values={'chat_id' : message.chat.id, "width":1280, "height":720}
                    response = requests.post(f"https://api.telegram.org/bot{TOKEN}/sendVideo", files=files, data=values)
                    data = json.loads(response.content)
                    if data["error_code"]==413:
                        await bot.send_message(message.from_user.id,"The file is too large - sending in separate files")
                        trimmedClip = VideoFileClip('Videos/{name}.mp4').subclip(0, 360)
                        files={'video': open(trimmedClip,'rb')}
                        print("Got your files")
                        values={'chat_id' : message.chat.id}
                        response = requests.post(f"https://api.telegram.org/bot{TOKEN}/sendVideo", files=files, data=values)
                        print(response.content)
                    return
            else: 
                await bot.send_message(message.from_user.id,"Trying to access...",reply_markup=actionKbd )
                yt = YouTube(link)
                mp3_file = yt.streams.filter(only_audio=True).first()

                await bot.send_message(message.from_user.id,"Downloading..." )


                out_file = mp3_file.download(output_path= "Audios", filename=f"{name}.mp3")
                base, ext = os.path.splitext(out_file)
                new_file = base + '.mp3'
                os.rename(out_file, new_file)


                await bot.send_message(message.from_user.id,"Finished, sending...")
                files={'audio': open(f'Audios/{name}.mp3','rb')}
                values={'chat_id' : message.chat.id}
                requests.post(f"https://api.telegram.org/bot{TOKEN}/sendAudio", files=files, data=values)

                
                return
        else: 
            await bot.send_message(message.from_user.id,"Your link doesn't look right try again")
            return False
    except Exception:
         print(Exception)
         await bot.send_message(message.from_user.id,"Something went wrong, check your link or try another quality option")
         pass
    

@dp.message_handler(commands=['qrCode'])
async def process_qrDec(message: types.Message):
    await bot.send_message(message.from_user.id, "Do you want to decode or encode?", reply_markup=qrKbrd)


@dp.message_handler(commands=['decode'])
async def process_qrDec(message: types.Message):
  try:
    await bot.send_message(message.from_user.id, "Send your image below", reply_markup=qrKbrd)

    if  message.photo :
        image_id = message.photo[-1].file_id
        file= await bot.get_file(image_id)
        request.urlretrieve( f"https://api.telegram.org/file/bot{TOKEN}/{file.file_path}", "qcode.png")
        val, points, straight_qrcode = det.detectAndDecode(cv2.imread("qcode.png"))

        if val != "":
            await message.answer(val)
        
        else :
            await message.answer("Couldn't detect QR code")
    else :
         await message.answer("Please send me a photo")

  except Exception:
      print(Exception)
      pass


@dp.message_handler(commands=['encode'], state= None)
async def process_qrEnc(message: types.Message):
    await QrCode.text.set()
    await message.reply("Send me your text")
  




@dp.message_handler( content_types=['text'], state=QrCode.text  )
async def create_qr(message: types.Message, state:FSMContext):
    if message.text != "close":
        try:
            await bot.send_message(message.from_user.id, "Generating...")
            img = qrcode.make(message.text)
            img.save(f"Photos/{message.text}.jpg")
            await bot.send_message(message.from_user.id, "Sending...")
            files={'photo': open(f'Photos/{message.text}.jpg','rb')}
            values={'chat_id' : message.chat.id}
            requests.post(f"https://api.telegram.org/bot{TOKEN}/sendPhoto", files=files, data=values)
            await state.finish()
        except Exception:
            print(Exception)
            await bot.send_message(message.from_user.id, "Something went wrong")
            pass
    else :
        await state.finish()
        await bot.send_message(message.from_user.id, "How can I help?", reply_markup=actionKbd)


@dp.message_handler(commands=['youtube'], state=None)
async def send_yt_video(message: types.Message):
    await YtDownload.link.set()
    await message.reply("Send me your link")

@dp.message_handler(commands=['close'])
async def close_kbrd(message: types.Message):

    markup = types.ReplyKeyboardRemove(selective=False)
    await bot.send_message(message.from_user.id, "Good bye.\nSee you soon!", reply_markup=markup)



@dp.message_handler( content_types=['text'], state=YtDownload.link  )
async def set_link(message: types.Message, state:FSMContext):
    if message.text.find("https://www.youtube.com/watch" or "https://youtu.be/") != -1:
        async with state.proxy() as data:
            data["link"] = message.text 
        await YtDownload.next()
        await bot.send_message(message.from_user.id,"Choose between MP3 and MP4" , reply_markup = formatKbd)
    elif message.text=="close":
        await state.finish()
        await bot.send_message(message.from_user.id, "How can I help?", reply_markup=actionKbd)
    else:
        await bot.send_message(message.from_user.id,"Please provide a valid YouTube link")


@dp.message_handler( content_types=['text'], state=YtDownload.format  )
async def set_link(message: types.Message, state:FSMContext):
    if message.text == "MP3" or message.text =="MP4" :
        async with state.proxy() as data:
            data["format"] = message.text 
        await YtDownload.next()
        await bot.send_message(message.from_user.id,"Choose a video quality" , reply_markup = qualityKbd)
    elif message.text=="close":
            await state.finish()
            await bot.send_message(message.from_user.id, "How can I help?", reply_markup=actionKbd)
    else :
        await bot.send_message(message.from_user.id,"Please provide a valid format (MP3 or MP4)")

    @dp.message_handler( content_types=['text']  )
    async def close(message: types.Message ):
        if message.text == "close":
            await bot.send_message(message.from_user.id, "How can I help?", reply_markup=actionKbd)

@dp.message_handler( content_types=['text'], state=YtDownload.quality  )
async def set_link(message: types.Message, state:FSMContext):
    if message.text == ("144" or "240" or "360" or "720"):
        async with state.proxy() as data:
            data["quality"] = message.text 
        data = await state.get_data()
        quality = data.get("quality")
        format = data.get("format")
        link = data.get("link")
        await yt_video_download(message,link, format, quality)
        await state.finish()
    elif message.text=="close":
        await state.finish()
        await bot.send_message(message.from_user.id, "How can I help?", reply_markup=actionKbd)
    else :
     await bot.send_message(message.from_user.id,"Please provide a valid video quality (144/240/360/720)")


@dp.message_handler( content_types=['photo'] )
async def load_photo(message: types.Message):
    image_id = message.photo[-1].file_id
    file= await bot.get_file(image_id)
    request.urlretrieve( f"https://api.telegram.org/file/bot{TOKEN}/{file.file_path}", "qcode.png")
    val, points, straight_qrcode = det.detectAndDecode(cv2.imread("qcode.png"))

    if val != "":
        await message.answer(val)
    
    else :
        await message.answer("Couldn't detect QR code")


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True,)
