from pyrogram import Client, filters, idle, enums
from pyrogram.types import Message, BotCommand
from pyrogram.handlers import MessageHandler
import sqlite3
import logging
from pyrogram.enums import ParseMode
import asyncio
from transformers import AutoTokenizer, T5ForConditionalGeneration
from sentence_transformers import SentenceTransformer, util
import shelve


# Постоянные переменные
api_id = 26723220
api_hash = 'a4e7684b728360474036a70170cda2ca'
bot_token = '6845584585:AAH-pGB73p83BYPVdgcqn1EOX8T2FxzTZsI'
technical_channel = -1002143414315

dict_lol_test = {'flag': True}
dict_lol = {'flag': True, 'last_post_id': 0}

dbusers = shelve.open('user.txt')
dbusers['all_channels'] = []
dbusers.close()

model_name = 'cointegrated/rubert-tiny2'
embedder = SentenceTransformer(model_name)


# Функция создания красивого вывода постов
def beatiful_post(user_id):
    text = []
    count = 1
    db = sqlite3.connect('data.db')
    cursor = db.cursor()
    dbusers = shelve.open('user.txt')
    print(dbusers[user_id])
    posts_ids = dbusers[user_id][1]
    print(posts_ids)
    for id_ in posts_ids:
        cursor.execute("SELECT selected FROM db_posts WHERE rowid =?", (id_,))
        text_postt = cursor.fetchall()[0]
        text_postt = text_postt[0] # Подчистить данное клоунство
        print(text_postt)
        cursor.execute("SELECT link FROM db_posts WHERE rowid =?", (id_,))
        link_on_post = cursor.fetchall()[0][0]
        link = f'<a href="{link_on_post}">Посмотреть в источнике</a>' # !!!
        text += [f'{count})  {text_postt}\n{link}']
        count += 1
    print(text)
    text_postik = '\n\n'.join(text)
    yaroslav = dbusers[user_id][0]
    dbusers[user_id] = [yaroslav, []]
    db.close()
    return text_postik


# Функция преобразования с помощью Т5
def summarizing_post(post_text_):
    model_name_T5 = "IlyaGusev/rut5_base_headline_gen_telegram"
    tokenizer = AutoTokenizer.from_pretrained(model_name_T5)
    model = T5ForConditionalGeneration.from_pretrained(model_name_T5)
    input_ids = tokenizer([post_text_],  # мб неправильное оформление
                          max_length=600,
                          add_special_tokens=True,
                          padding="max_length",
                          truncation=True,
                          return_tensors="pt"
                          )["input_ids"]
    output_ids = model.generate(input_ids=input_ids)[0]
    headline = tokenizer.decode(output_ids, skip_special_tokens=True)
    print(headline)
    print(1)
    headline = str(headline)
    print(headline)
    return headline


# Функция фиксирования новых постов в выбранных ТГ каналов
async def new_post(client: Client, message: Message):  # добавить проверку на канал
    chat_id = message.chat.id
    dbusers = shelve.open('user.txt')
    source_public_ids = list(map(lambda x: x[0], dbusers['all_channels']))
    users_ids = dbusers.keys()
    if chat_id in source_public_ids:
        db = sqlite3.connect('data.db')
        cursor = db.cursor()

        cursor.execute("""CREATE TABLE IF NOT EXISTS db_posts(
                       id INTEGER PRIMARY KEY AUTOINCREMENT,
                       channel INTEGER, 
                       post TEXT,
                       selected TEXT,
                       link INTEGER
        )""")
        db.commit()
        # ПРОверяем, первый ли наш пост в бд
        cursor.execute("SELECT id FROM db_posts")
        selected_id = cursor.fetchall()

        if len(selected_id) == 0:
            # значит, пост первый. Добавляем его в бд и упрощаем
            prepaired_text = summarizing_post(message.text)

            link_on_post = f'https://t.me/{message.chat.username}/{message.id}'
            adding_db = (message.chat.id, message.text, prepaired_text, link_on_post)  # ! узнать название канала
            print(adding_db)
            cursor.execute("INSERT INTO db_posts (channel, post, selected, link) VALUES(?, ?, ?, ?);", adding_db)
            db.commit()
            for user_id in users_ids:
                if user_id != 'all_channels':
                    user_ids_channels = list(map(lambda x: x[0], dbusers[user_id][0]))
                    print(user_ids_channels)
                    if chat_id in user_ids_channels:
                        posts_id = dbusers[user_id][1]
                        cursor.execute("SELECT id FROM db_posts")
                        last_id = cursor.fetchall()[-1]
                        last_id = int(last_id[0])
                        print(last_id)
                        posts_id.append(last_id)
                        print(posts_id)
                        yaroslav = dbusers[user_id][0]
                        dbusers[user_id] = [yaroslav, posts_id]
                        if len(posts_id) == 3:  # !!! Поменять цфиру
                            await client.send_message(technical_channel, 'u' + str(user_id))

        else:
            cursor.execute("SELECT post FROM db_posts")
            selected_posts = cursor.fetchall()
            print(selected_posts)  # проверка, что все работает :) выбираем оттуда посты ? как оно выводит: в списке? надо в список
            corpus = [el[0] for el in selected_posts]
            corpus_embeddings = embedder.encode(corpus, convert_to_tensor=True)
            # Query sentences:
            queries = [message.text]
            posts_embedding = embedder.encode(queries[0], convert_to_tensor=True)
            hits = util.semantic_search(posts_embedding, corpus_embeddings)
            # Доработать :)
            f = True
            print(hits)
            print()
            print()
            for i in hits:
                for el in i:
                    print(el)
                    print()
                    if el['score'] > 0.8:  # найти число для проеврки семантического поиска (число ближе к 1 , значит этот пост уже повторяет предыдущий)
                        print('говновость')
                        f = False
                if f:
                    print('АХТУУУУНГГГГГ')
                    # Сохраняем текст поста в дб
                    prepaired_text = summarizing_post(message.text)

                    link_on_post = f'https://t.me/{message.chat.username}/{message.id}'
                    adding_db = (message.chat.id, message.text, prepaired_text, link_on_post)  # ! узнать название канала
                    print(adding_db)
                    cursor.execute("INSERT INTO db_posts (channel, post, selected, link) VALUES(?, ?, ?, ?);", adding_db)
                    db.commit()

                    for user_id in users_ids:
                        if user_id != 'all_channels':
                            user_ids_channels = list(map(lambda x: x[0], dbusers[user_id][0]))
                            print(user_ids_channels)
                            if chat_id in user_ids_channels:
                                posts_id = dbusers[user_id][1]
                                cursor.execute("SELECT id FROM db_posts")
                                last_id = cursor.fetchall()[-1]
                                last_id = int(last_id[0])
                                print(last_id)
                                posts_id.append(last_id)
                                print(posts_id)
                                yaroslav = dbusers[user_id][0]
                                dbusers[user_id] = [yaroslav, posts_id]
                                if len(posts_id) == 3: # !!! Поменять цфиру
                                    await client.send_message(technical_channel, 'u' + str(user_id))
                    # await client.send_message(technical_channel, prepaired_text)
        db.close()



# Когда у пользователя обрабатывается N новостей, функция отправляет посты пользователю
async def sending_posts(client: Client, message: Message):
    text = message.text
    if text.startswith('u'):
        user_id = text[1:]
        text_post = beatiful_post(user_id)
        await client.send_message(user_id, text_post, parse_mode=enums.ParseMode.HTML)
        dbusers.close()


# Функция подписки на каналы, отправленные пользователем
async def join_chats(client: Client, message: Message):
    text = message.text
    if text.startswith('s'):
        await client.join_chat(text[1:])


# Создание команд
# /start
async def command_start(client: Client, message: Message):  # !
    mess2 = (f'Привет, {message.from_user.first_name}!\n\n'
             f'Я - новостной бот. Помогу Вам быть в курсе событий со всего мира. Вам не надо будет '
             f'пролистывать каждый канал в поисках нового, достаточно переслать любую запись с Вашего '
             f'избранного канала и я сохраню его в Вашей подборке.')
    await message.reply(mess2)
    user_id = message.from_user.id
    user_idSTR = str(user_id)
    global flag
    if dict_lol_test['flag']:
        # Создание базы данныз с пользователями и их каналами
        dbusers = shelve.open('user.txt')
        dbusers[user_idSTR] = [[], []]
        dict_lol_test['flag'] = False
    else:
        dbusers = shelve.open('user.txt')
        if user_idSTR not in dbusers:
            dbusers[user_idSTR] = [[], []]
    for actor_name, article in dbusers.items(): # поменять
        print(actor_name, article)
    dbusers.close()


# /channels
async def command_channels(client: Client, message: Message):
    dbusers = shelve.open('user.txt')
    usernames_public_curuser = list(map(lambda x: x[1], dbusers[str(message.from_user.id)][0]))
    if not usernames_public_curuser:
        await client.send_message(message.chat.id, "Вы пока не добавили никаких каналов")
    else:
        text = "\n".join(usernames_public_curuser)
        await client.send_message(message.chat.id, f'Список Ваших каналов: {text}')
        print(usernames_public_curuser)
    print(dbusers[str(message.from_user.id)])
    dbusers.close()


# /about
async def command_about(client: Client, message: Message):
    author_id = '@k0tinside'
    await client.send_message(message.chat.id,
                              f'Создатель бота - Михайленко Елена\nПо вопросам обращайтесь: lenamihajlenko28234@gmail.com, {author_id}')


# /digest - высылает новости
async def command_digest(client: Client, message: Message):
    user_id = str(message.chat.id)
    dbusers = shelve.open('user.txt')
    posts_ids = dbusers[user_id][1]
    print(dbusers[user_id])
    if len(posts_ids) != 0:
        text_post = beatiful_post(user_id)
        await client.send_message(user_id, text_post, parse_mode=enums.ParseMode.HTML)
    else:
        await client.send_message(message.chat.id, 'Пока не было добавлено новых новостей!')
    dbusers.close()


# Создание персонального фильтра. Проверка, пересланное сообщение или нет
async def filter_text(_, __, message):
    return message.forward_from_chat is not None
filter_data = filters.create(filter_text)


# Добавление каналов из пересылаемых сообщений
async def handle_forwarded_message(client: Client, message: Message):
    dbusers = shelve.open('user.txt')
    publics_curuser = list(map(lambda x: x, dbusers[str(message.from_user.id)][0]))
    all_channels = dbusers['all_channels']
    forwarded_channel_info = message.forward_from_chat
    channel_id = forwarded_channel_info.id
    channel_username = forwarded_channel_info.username
    about_channel = (channel_id, channel_username)
    print(about_channel)
    await client.send_message(message.chat.id,
                              f"Сообщение переслано из канала {channel_username}")
    if (channel_id, channel_username) not in publics_curuser:
        publics_curuser.append(about_channel)
        all_channels.append(about_channel)
        yaroslav = dbusers[str(message.from_user.id)][1]
        dbusers[str(message.from_user.id)] = [publics_curuser, yaroslav]
        dbusers['all_channels'] = all_channels
        await client.send_message(message.chat.id, f"Канал {channel_username} добавлен")
        await client.send_message(technical_channel, f's@{channel_username}')
    else:
        await client.send_message(message.chat.id, f"Канал {channel_username} уже добавлен")
    print(publics_curuser)
    print(dbusers['all_channels'])
    print(1)
    for actor_name, article in dbusers.items(): # поменять
        print(actor_name, article)
    dbusers.close()


# Основная функция запуска
async def start():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(name)s - %(message)s")
    # Создание клиента для юзер бота
    user_bot = Client(name='user_bot', api_id=api_id, api_hash=api_hash)
    user_bot.add_handler(MessageHandler(join_chats, filters.chat(chats=technical_channel)))
    # Создание клиента для бота
    bot_content = Client(name='bot_content',
                         api_id=api_id,
                         api_hash=api_hash,
                         bot_token=bot_token,
                         parse_mode=ParseMode.HTML)
    user_bot.add_handler(MessageHandler(new_post))
    bot_content.add_handler(MessageHandler(command_start, filters.command(commands='start')))
    bot_content.add_handler(MessageHandler(command_about, filters.command(commands='about')))
    bot_content.add_handler(MessageHandler(command_channels, filters.command(commands='channels')))
    bot_content.add_handler(MessageHandler(command_digest, filters.command(commands='digest')))
    bot_content.add_handler(MessageHandler(handle_forwarded_message, filter_data))
    bot_content.add_handler(MessageHandler(sending_posts, filters.chat(chats=technical_channel)))
    bot_commands = [
        BotCommand(
            command='start',
            description='Get started'
        ),
        BotCommand(
            command='channels',
            description='View my channels'
        ),
        BotCommand(
            command='about',
            description='Get information about author'
        ),
        BotCommand(
            command='digest',
            description='Get latest news'
        )
    ]
    await user_bot.start()
    await bot_content.start()
    await bot_content.set_bot_commands(bot_commands)
    await idle()
    await user_bot.stop()
    await bot_content.stop()


if __name__ == '__main__':
    asyncio.run(start())