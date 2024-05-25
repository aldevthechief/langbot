import telebot
from server import keep_alive
from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup
from time import sleep

import googletrans
import langcodes
import random
from wonderwords import RandomWord

import os
import json
from git import Repo

bot_token = os.environ.get('bot_token')
git_username = os.environ.get('git_username')
git_token = os.environ.get('git_token')

bot = telebot.TeleBot(bot_token)

gitlink = f'https://{git_username}:{git_token}@github.com/aldevthechief/langbot-data.git'
datadir = os.path.join(os.getcwd(), 'data')
try: 
    repo = Repo(datadir)
except: 
    repo = Repo.clone_from(gitlink, datadir, branch='data')
    
wordmsgdict = {}
mistakes = {}
transdict = {}
filedir = os.path.join(datadir, 'transdata.json')
with open(filedir, 'r') as file:
    try:
        transdict = json.load(file)
    except json.JSONDecodeError:
        pass
        
trans = googletrans.Translator()
wordgen = RandomWord()

dictationbutton = telebot.types.BotCommand('startquiz', 'проверить знание слов')
wordsbutton = telebot.types.BotCommand('changewords', 'изменить список слов')
languagebutton = telebot.types.BotCommand('swaplang', 'изменить язык перевода')
bot.set_my_commands([dictationbutton, wordsbutton, languagebutton])
        
def gitpush():
    repo.index.add('transdata.json')
    repo.index.commit('current user data')
    repo.remote().push()
        

@bot.message_handler(commands=['start'])
def bot_startup(msg):
    bot.send_message(msg.chat.id, 'привет, я твой личный помощник в изучении языков😄')
    ctx = bot.send_message(msg.chat.id, 'чтобы начать наше обучение, пришли мне список слов для изучения😉', reply_markup=wordgen_markup())
    bot.register_next_step_handler(ctx, get_destination_language)
    
    
@bot.message_handler(commands=['changewords'])
def new_words(msg):
    ctx = bot.send_message(msg.chat.id, 'пришли мне новый список слов для изучения🙈', reply_markup=wordgen_markup())
    bot.register_next_step_handler(ctx, get_destination_language)
    

def generate_words(msg):
    transdict.setdefault(str(msg.chat.id), [[], ''])[0].clear()
    words = wordgen.random_words(random.randint(15, 20))
    for word in words:
        transdict[str(msg.chat.id)][0].append(word)
    
    ctx = bot.send_message(msg.chat.id, 'хорошо, тогда напиши мне язык перевода🙃')
    bot.register_next_step_handler(ctx, translate_words, words)
   
    
@bot.message_handler(commands=['swaplang'])
def change_destination_language(msg):
    if not transdict.get(str(msg.chat.id), [[]])[0]:
        ctx = bot.send_message(msg.chat.id, 'для начала пришли мне свой список слов для изучения🙈', reply_markup=wordgen_markup())
        bot.register_next_step_handler(ctx, get_destination_language)
    else:
        ctx = bot.send_message(msg.chat.id, 'напиши мне язык перевода🙃')
        bot.register_next_step_handler(ctx, translate_words, transdict[str(msg.chat.id)][0])
    

def get_destination_language(msg):
    transdict.setdefault(str(msg.chat.id), [[], ''])[0].clear()
    words = [x.strip() for x in msg.text.split('\n')]
    for word in words:
        transdict[str(msg.chat.id)][0].append(word)
        
    ctx = bot.send_message(msg.chat.id, 'а теперь напиши мне язык перевода🙃')
    bot.register_next_step_handler(ctx, translate_words, words)
    

def translate_words(langmsg, wordlist = None):
    wronginput = False
    try:
        destlangcode = langcodes.find(langmsg.text).language
    except:
        wronginput = True
        ctx = bot.send_message(langmsg.chat.id, 'не удалось распознать язык, отправь еще раз🙏')
        bot.register_next_step_handler(ctx, translate_words, wordlist)
    
    googlelangs = googletrans.LANGUAGES.keys()
    if destlangcode not in googlelangs: 
        try:
            destlangcode = [lang for lang in googlelangs if destlangcode in lang][0]
        except:
            wronginput = True
            ctx = bot.send_message(langmsg.chat.id, 'не удалось распознать язык, отправь еще раз🙏')
            bot.register_next_step_handler(ctx, translate_words, wordlist)
        
    if wronginput: return
        
    transdict[str(langmsg.chat.id)][1] = destlangcode
    
    restext = ''
    if wordlist is not None:
        for word in wordlist:
            bot.send_chat_action(langmsg.chat.id, 'typing')
            transresult = trans.translate(word, dest=destlangcode)
            restext += f'{word} - {transresult.text}\n'
        wordmsg = bot.send_message(langmsg.chat.id, f'отлично, вот твой список слов💅:\n\n{restext}', reply_markup=base_markup())
        wordmsgdict[langmsg.chat.id] = wordmsg
        
    with open(filedir, 'w') as file:
        json.dump(transdict, file)
        
    gitpush()


def return_to_wordlist(msg, editmsg = False):
    refmsg = wordmsgdict.get(msg.chat.id, None)
    if refmsg is not None:
        if editmsg: 
            bot.edit_message_text(refmsg.text.strip('отлично, '), msg.chat.id, msg.message_id, reply_markup=base_markup())
        else:
            bot.send_message(msg.chat.id, refmsg.text.strip('отлично, '), reply_markup=base_markup())
        return
    
    restext = ''
    destlangcode = transdict[str(msg.chat.id)][1]
    for word in transdict[str(msg.chat.id)][0]:
        bot.send_chat_action(msg.chat.id, 'typing')
        transresult = trans.translate(word, dest=destlangcode)
        restext += f'{word} - {transresult.text}\n'
    bot.send_message(msg.chat.id, f'вот твой список слов💅:\n\n{restext}', reply_markup=base_markup())
        

@bot.message_handler(commands=['startquiz'])
def start_dictation(msg):
    if not transdict.get(str(msg.chat.id), [[]])[0]:
        bot.send_message(msg.chat.id, 'для начала настрой список слов для изучения🤦‍♂️ /changewords')
        return
    bot.send_message(msg.chat.id, 'выбери режим изучения слов👇', reply_markup=dict_mode_markup())
    
    
def get_dict_wordcount(msg, guessword):
    if msg.text in ['/start', '/startquiz', '/changewords', '/swaplang']:
        break_quiz(msg)
        return
    
    wronginput = False
    try:
        wordcount = int(msg.text)
    except ValueError:
        wronginput = True
        ctx = bot.send_message(msg.chat.id, 'не удалось распознать число, отправь еще раз🙏')
        bot.register_next_step_handler(ctx, get_dict_wordcount, guessword)
    
    maxcount = len(transdict.get(str(msg.chat.id), [[]])[0])
    if not 1 <= wordcount <= maxcount:
        wronginput = True
        ctx = bot.send_message(msg.chat.id, f'можно проверить до {maxcount} слов, отправь другое количество🤨')
        bot.register_next_step_handler(ctx, get_dict_wordcount, guessword)
        
    if wronginput: return
    guess_word_dict(msg, wordcount) if guessword else guess_meaning_dict(msg, wordcount)
    

def break_quiz(msg):
    match msg.text:
        case '/start':
            bot_startup(msg)
        case '/startquiz':
            start_dictation(msg)
        case '/changewords':
            new_words(msg)
        case '/swaplang':
            change_destination_language(msg)
    
    
def guess_word_dict(msg, wordcount = None, words = None, answer = None, question = None):
    if msg.text in ['/start', '/startquiz', '/changewords', '/swaplang']:
        break_quiz(msg)
        return
    
    if words is None and wordcount is not None:
        mistakes[msg.chat.id] = []
        
        words = {}
        randchoice = random.sample(transdict[str(msg.chat.id)][0], wordcount)
        for word in randchoice:
            bot.send_chat_action(msg.chat.id, 'typing')
            
            lang = transdict[str(msg.chat.id)][1]
            translation = trans.translate(word, dest=lang).text
            words[word] = translation
        bot.send_message(msg.chat.id, 'хорошо, тогда я буду диктовать тебе слова, а ты мне будешь кидать их перевод😘👌')
        sleep(2)
            
    if answer is not None and msg.text.strip().lower() != answer.lower():
        bot.send_message(msg.chat.id, f'ты ошибся, правильно - *{answer}*', parse_mode='Markdown')
        bot.send_chat_action(msg.chat.id, 'typing')
        mistakes[msg.chat.id].append(f'*{answer}* - *{question}*')
        sleep(2)
    else: words.pop(answer, None)
        
    if words: 
        chosenword, chosentrans = random.choice(list(words.items()))
        ctx = bot.send_message(msg.chat.id, chosentrans)
        bot.register_next_step_handler(ctx, guess_word_dict, wordcount, words, chosenword, chosentrans)
    else:
        rightpercentage = round((1 - len(mistakes[msg.chat.id]) / (wordcount + len(mistakes[msg.chat.id]))) * 100)
        
        if rightpercentage == 100:
            congratstr =  f'отличная работа! 👏\n{100}% правильных ответов\n'
            mistakestr = '\nты не допустил ошибки ни в одном из слов'
        else:
            congratstr = f'хорошая работа! 👏\n{rightpercentage}% правильных ответов\n'
            mistakestr = f'\nвот те слова, в которых ты ошибся:\n' + '\n'.join(set(mistakes[msg.chat.id]))
            
        bot.send_message(msg.chat.id, congratstr + mistakestr, reply_markup=break_dict_markup(), parse_mode='Markdown')


def guess_meaning_dict(msg, wordcount = None, words = None, answer = None, question = None): 
    if msg.text in ['/start', '/startquiz', '/changewords', '/swaplang']:
        break_quiz(msg)
        return
    
    if words is None and wordcount is not None:
        mistakes[msg.chat.id] = []
        
        words = {}
        randchoice = random.sample(transdict[str(msg.chat.id)][0], wordcount)
        for word in randchoice:
            bot.send_chat_action(msg.chat.id, 'typing')
            
            lang = transdict[str(msg.chat.id)][1]
            translation = trans.translate(word, dest=lang).text
            words[translation] = word
        bot.send_message(msg.chat.id, 'хорошо, тогда я буду диктовать тебе слова, а ты мне будешь кидать их перевод😘👌')
        sleep(2)
            
    if answer is not None and msg.text.strip().lower() != answer.lower():
        bot.send_message(msg.chat.id, f'ты ошибся, правильно - *{answer}*', parse_mode='Markdown')
        bot.send_chat_action(msg.chat.id, 'typing')
        mistakes[msg.chat.id].append(f'*{answer}* - *{question}*')
        sleep(2)
    else: words.pop(answer, None)
        
    if words: 
        chosenword, chosentrans = random.choice(list(words.items()))
        ctx = bot.send_message(msg.chat.id, chosentrans)
        bot.register_next_step_handler(ctx, guess_word_dict, wordcount, words, chosenword, chosentrans)
    else:
        rightpercentage = round((1 - len(mistakes[msg.chat.id]) / (wordcount + len(mistakes[msg.chat.id]))) * 100)
        
        if rightpercentage == 100:
            congratstr =  f'отличная работа! 👏\n{100}% правильных ответов\n'
            mistakestr = '\nты не допустил ошибки ни в одном из слов'
        else:
            congratstr = f'хорошая работа! 👏\n{rightpercentage}% правильных ответов\n'
            mistakestr = f'\nвот те слова, в которых ты ошибся:\n' + '\n'.join(set(mistakes[msg.chat.id]))
            
        bot.send_message(msg.chat.id, congratstr + mistakestr, reply_markup=break_dict_markup(), parse_mode='Markdown')

    
@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    chatid = call.message.chat.id
    bot.edit_message_reply_markup(chatid, call.message.message_id, '')
    
    match call.data:
        case 'new_lang':
            change_destination_language(call.message)
        case 'new_wordlist':
            new_words(call.message)
        case 'dictation':
            wordmsgdict[chatid] = call.message
            start_dictation(call.message)
        case 'repeat_dictation':
            start_dictation(call.message)
        case 'guess_word': 
            bot.delete_message(chatid, call.message.message_id)
            ctx = bot.send_message(chatid, 'сколько слов ты хочешь изучить?🤔')
            bot.register_next_step_handler(ctx, get_dict_wordcount, guessword=True)
        case 'guess_meaning':
            bot.delete_message(chatid, call.message.message_id)
            ctx = bot.send_message(chatid, 'сколько слов ты хочешь изучить?🤔')
            bot.register_next_step_handler(ctx, get_dict_wordcount, guessword=False)
        case 'return_to_list': 
            return_to_wordlist(call.message)
        case 'return_to_prev_list':
            return_to_wordlist(call.message, True)
        case 'gen_words':
            bot.clear_step_handler_by_chat_id(chatid)
            generate_words(call.message)
    
    
def base_markup():
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(InlineKeyboardButton('изучить слова', callback_data='dictation'))
    markup.add(InlineKeyboardButton('изменить слова', callback_data='new_wordlist'),
               InlineKeyboardButton('изменить язык', callback_data='new_lang'))
    return markup


def dict_mode_markup():
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(InlineKeyboardButton('угадать слово по переводу', callback_data='guess_word'),
               InlineKeyboardButton('угадать перевод слова', callback_data='guess_meaning'),
               InlineKeyboardButton('вернуться к списку слов', callback_data='return_to_prev_list'))
    return markup


def break_dict_markup():
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(InlineKeyboardButton('изучить еще слова', callback_data='repeat_dictation'),
               InlineKeyboardButton('вернуться к списку слов', callback_data='return_to_list'))
    return markup


def wordgen_markup():
    return InlineKeyboardMarkup([[InlineKeyboardButton('сгенерировать список слов на английском', callback_data='gen_words')]])
    
    
while True:
    keep_alive()
    try:
        bot.infinity_polling()
    except Exception as error:
        print(error)
        sleep(15)
