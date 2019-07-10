import os
import sys
import time
import vk_api
from vk_api.audio import VkAudio
import telebot
import configparser
from telebot.types import InputMediaPhoto
import collections


# Считываем настройки
config_path = os.path.join(sys.path[0], 'settings.ini')
config = configparser.ConfigParser()
config.read(config_path)
ID = config.get('Settings', 'ID')
LAST_ID = config.get('Settings', 'LAST_ID')
LOGIN = config.get('VK', 'LOGIN')
PASSWORD = config.get('VK', 'PASSWORD')
DOMAIN = config.get('VK', 'DOMAIN')
VK_TOKEN = config.get('VK', 'TOKEN', fallback=None)
BOT_TOKEN = config.get('Telegram', 'BOT_TOKEN')
CHANNEL = config.get('Telegram', 'CHANNEL')
INCLUDE_LINK = config.getboolean('Settings', 'INCLUDE_LINK')
PREVIEW_LINK = config.getboolean('Settings', 'PREVIEW_LINK')
TIME_TO_GET_NEW_POST= config.getint('Settings', 'last_time') # in seconds
TIME_BETWEEN_POST = config.getint('Settings', 'between_time') # in seconds

# Символы, на которые можно разбить сообщение
message_breakers = [':', ' ', '\n']
max_message_length = 4091

# Инициализируем телеграмм бота
bot = telebot.TeleBot(BOT_TOKEN)


def setup():
    global LOGIN
    global PASSWORD
    global VK_TOKEN
    global config
    global config_path
    #global vkaudio
    global vk_session
    global vk

    if VK_TOKEN is not None:
        vk_session = vk_api.VkApi(LOGIN, PASSWORD, VK_TOKEN)
        vk_session.auth(token_only=True)
        #vkaudio = VkAudio(vk_session)
    else:
        vk_session = vk_api.VkApi(LOGIN, PASSWORD)
        vk_session.auth()
        #vkaudio = VkAudio(vk_session)

    new_token = vk_session.token['access_token']

    if VK_TOKEN != new_token:
        VK_TOKEN = new_token
        config.set('VK', 'TOKEN', new_token)
        with open(config_path, "w") as config_file:
            config.write(config_file)
    vk = vk_session.get_api()


# Получаем данные из vk.com
def get_data(id_vk):
    # Используем метод wall.getById из документации по API vk.com
    response = vk.wall.getById(posts=DOMAIN+"_"+str(id_vk))
    return response

# проверяем последний ли пост был скопирован
# если нет - продолжаем копировать, если да - получаем новый ID последнего поста
def check_is_last():
    global LAST_ID, ID
    ID = config.get('Settings', 'ID')
    if int(LAST_ID) > int(ID):
        check_posts_vk()
    else:
        # Получаем id последней записи и записываем в файл
        response1 = vk.wall.get(owner_id=DOMAIN, count=1, offset=1)
        response1 = reversed(response1['items'])
        for post in response1:
            if int(post['id']) != int(LAST_ID):
                config.set('Settings', 'LAST_ID', str(post['id']))
                with open(config_path, "w") as config_file:
                    config.write(config_file)
                    config_file.close()
                LAST_ID = config.get('Settings', 'LAST_ID')
                print("new last id = " + LAST_ID)
        print("#################################################################################################")
        print("last id = " + LAST_ID)
        print("the lastest copied id = " + ID)
        print("waiting for new post in vk...\n" + str(TIME_TO_GET_NEW_POST) + " seconds until next request")
        time.sleep(TIME_TO_GET_NEW_POST)


# Проверяем данные по условиям перед отправкой
def check_posts_vk():
    global DOMAIN
    global INCLUDE_LINK
    global ID
    global bot
    global config
    global config_path

    #ID = config.get('Settings', 'ID')
    response = get_data(ID)
    # print(response)
    # response = reversed(response['items'])

    if len(response) != 0:

        print('------------------------------------------------------------------------------------------------')
        print("\nfound not empty response, " + str(TIME_BETWEEN_POST) + " seconds until next post will be copy\n")
        time.sleep(TIME_BETWEEN_POST)

        for post in response:

            # Читаем последний извесный id из файла
            # id = config.get('Settings', 'LAST_ID')

            # Сравниваем id, пропускаем уже опубликованные
            # if int(post['id']) <= int(id):
            #     continue

            print('------------------------------------------------------------------------------------------------')
            print("Copied wall post: https://vk.com/wall"+DOMAIN+"_"+ID)
            print("id = " + ID)
            print("checking next id...")

            # Текст
            text = post['text']

            # Проверяем есть ли что то прикрепленное к посту
            images = []
            links = []
            attachments = []
            if 'attachments' in post:
                attach = post['attachments']
                for add in attach:
                    if add['type'] == 'photo':
                        img = add['photo']
                        images.append(img)
                    elif add['type'] == 'audio':
                        # Все аудиозаписи заблокированы везде, кроме оффицальных приложений
                        continue
                    elif add['type'] == 'video':
                        video = add['video']
                        if 'player' in video:
                            links.append(video['player'])
                    else:
                        for (key, value) in add.items():
                            if key != 'type' and 'url' in value:
                                attachments.append(value['url'])

            # if INCLUDE_LINK:
            #     post_url = "https://vk.com/" + DOMAIN + "?w=wall" + \
            #         str(post['owner_id']) + '_' + str(post['id'])
            #     links.insert(0, post_url)
            # text = '\n'.join([text] + links)
            # #send_posts_text(text)

            # если несколько картинок в посте
            if len(images) > 1:
                image_urls = list(map(lambda img: max(img["sizes"], key=lambda size: size["type"])["url"], images))
                # print(image_urls)
                # отправляем
                first_url = image_urls[0]
                image_urls.pop(0)
                bot.send_media_group(CHANNEL, map(
                    lambda url: InputMediaPhoto(url), image_urls))
                bot.send_photo(CHANNEL, first_url, text)

            # если прикреплена 1 картинка
            if len(images) == 1:
                url = max(images[0]["sizes"], key=lambda size: size["type"])["url"]
                # отправляем
                bot.send_photo(CHANNEL, url, text)
                # print(url)

            # Проверяем есть ли репост другой записи
            # if 'copy_history' in post:
            #     copy_history = post['copy_history']
            #     copy_history = copy_history[0]
            #     print('--copy_history--')
            #     print(copy_history)
            #     text = copy_history['text']
            #     #send_posts_text(text)
            #
            #     # Проверяем есть ли у репоста прикрепленное сообщение
            #     if 'attachments' in copy_history:
            #         copy_add = copy_history['attachments']
            #         copy_add = copy_add[0]
            #
            #         # Если это ссылка
            #         if copy_add['type'] == 'link':
            #             link = copy_add['link']
            #             text = link['title']
            #             #send_posts_text(text)
            #             img = link['photo']
            #             send_posts_img(img)
            #             url = link['url']
            #             #send_posts_text(url)
            #
            #         # Если это картинки
            #         if copy_add['type'] == 'photo':
            #             attach = copy_history['attachments']
            #             for img in attach:
            #                 image = img['photo']
            #                 send_posts_img(image,text)

            # Записываем id в файл

        config.set('Settings', 'ID', str(post['id']+1))
        with open(config_path, "w") as config_file:
            config.write(config_file)
            config_file.close()
    else:
        print('------------------------------------------------------------------------------------------------')
        print(response)
        print("empty response: id = "+ID)
        print("checking next id...")
        # empty response doesn't have own ID
        newID = int(ID) + 1
        config.set('Settings', 'ID', str(newID))
        with open(config_path, "w") as config_file:
            config.write(config_file)
            config_file.close()

# Отправляем посты в телеграмм
#
# # Текст
# def send_posts_text(text):
#     global CHANNEL
#     global PREVIEW_LINK
#     global bot
#
#     if text == '':
#         print('no text')
#     else:
#         # В телеграмме есть ограничения на длину одного сообщения в 4091 символ, разбиваем длинные сообщения на части
#         for msg in split(text):
#             bot.send_message(CHANNEL, msg, disable_web_page_preview=not PREVIEW_LINK)
#
#
# def split(text):
#     global message_breakers
#     global max_message_length
#
#     if len(text) >= max_message_length:
#         last_index = max(
#             map(lambda separator: text.rfind(separator, 0, max_message_length), message_breakers))
#         good_part = text[:last_index]
#         bad_part = text[last_index + 1:]
#         return [good_part] + split(bad_part)
#     else:
#         return [text]
#
#
# # Изображения
# def send_posts_img(img, text1):
#     global bot
#     # Находим картинку с максимальным качеством
#     url = max(img["sizes"], key=lambda size: size["type"])["url"]
#     bot.send_photo(CHANNEL, url, "CAPTION")

# def getAudio():
#     tracks = vkaudio.search(q="Imagine%20Dragons", count=2)
#     for track in tracks:
#     print(track['url'])


if __name__ == '__main__':
    setup()
    check_is_last()
    # getAudio()
    while True:
        check_is_last()
