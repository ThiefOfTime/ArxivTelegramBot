from telegram.ext import Updater, CommandHandler
import requests
from bs4 import BeautifulSoup
import pickle
from os.path import isfile, isdir
from os import sep

general_topics = None
sub_topics = None
sub_topics_links = None
subscribe_dict = {}
global_url = 'https://arxiv.org'
sep_top = "\n\t- "
user_data = {}


def update_user_data():
    global pickle_path
    pickle.dump(user_data, open(pickle_path, "wb"))


def get_cur_state(username):
    global pickle_path
    global user_data
    global subscribe_dict
    user_data = pickle.load(open(pickle_path, "rb"))
    if username in user_data.keys():
        subscribe_dict = user_data[username]["subs"]


def get_topics_with_links():
    url = global_url
    page = requests.get(url)
    soup = BeautifulSoup(page.text, "html.parser")
    h2 = soup.find_all("h2")
    h2 = list(map(lambda x: x.get_text(), h2))[:-1]
    a = soup.find_all("a", id=lambda x: x and x.startswith('main-'))
    a_dict = {x.get_text(): x.get("id").split("-", 1)[1] for x in a}
    a_links_dict = {}
    for id in a_dict.values():
        links = soup.find_all("a", id=lambda x: x and x.startswith(id))
        a_links_dict[id] = {x.get_text(): url + x.get("href") for x in links}
    return h2, a_dict, a_links_dict


def get_papers(subscrition):
    url = subscribe_dict[subscrition]
    soup = BeautifulSoup(requests.get(url).text, "html.parser")
    names = list(map(lambda x: x.get_text().strip().split(' ', 1)[1], soup.find_all("div", class_="list-title mathjax")))
    span_elems = soup.find_all("span", class_="list-identifier")
    return {n: {'name': elem.find_all("a")[0].get_text(), 'abstract': global_url + elem.find_all("a")[0].get("href"),
                 'pdf': global_url + elem.find_all("a")[1].get("href")} for n, elem in zip(names, span_elems)}


def start(update, context):
    global general_topics
    global sub_topics
    global sub_topics_links
    user_data[update.message.from_user.first_name] = {"subs": {}}
    update_user_data()
    general_topics, sub_topics, sub_topics_links = get_topics_with_links()
    update.message.reply_text(
        f'Hello {update.message.from_user.first_name}')


def list_topics(update, context):
    global general_topics
    global sub_topics
    global sub_topics_links
    general_topics, sub_topics, sub_topics_links = get_topics_with_links()
    for topic in sub_topics:
        if len(sub_topics_links[sub_topics[topic]]) > 0:
            update.message.reply_text(f'{topic}:\n\t- {sep_top.join(sub_topics_links[sub_topics[topic]].keys())}')


def subscribe(update, context):
    get_cur_state(update.message.from_user.first_name)
    sub = update.message.text.split(" ", 1)[1]
    for category in sub_topics_links.values():
        if sub in category.keys():
            subscribe_dict[sub] = category[sub]
            update.message.reply_text(f'You subscribed to {sub}')
            user_data[update.message.from_user.first_name]["subs"] = subscribe_dict
            update_user_data()
            break
    else:
        update.message.reply_text('The category you want to subscribe to does not exist.')


def list_subscritions(update, context):
    get_cur_state(update.message.from_user.first_name)
    if len(subscribe_dict.keys()) > 0:
        update.message.reply_text(f'Your subscriptions are:\n\t- {sep_top.join(subscribe_dict.keys())}')
    else:
        update.message.reply_text(f'You did not subscribed to anything so far.')


def get_new_papers_for_subscritions(update, context):
    get_cur_state(update.message.from_user.first_name)
    user_inp = update.message.text.split(" ", 1)[-1]
    version = "abstract" if user_inp not in ["pdf", 'abstract'] else user_inp
    sep_papers = '\n\t\t'
    for sub in subscribe_dict.keys():
        papers = get_papers(sub)
        update.message.reply_text(f'Papers for {sub}:\n\t- '
                                  f'{sep_top.join(sep_papers.join([n, x["name"], x[version]]) for n, x in papers.items())}')


def unsubscribe(update, context):
    get_cur_state(update.message.from_user.first_name)
    user_inp = update.message.text.split(" ", 1)[1]
    if user_inp in subscribe_dict.keys():
        del subscribe_dict[user_inp]
        user_data[update.message.from_user.first_name]["subs"] = subscribe_dict
        update_user_data()
        update.message.reply_text(f'You successfully unsubscribed from {user_inp}')
    else:
        update.message.reply_text('The subscription you provided was not found.')


def help(update, context):
    update.message.reply_text('The following commands are implemented:\n'
                              '\t- /start  Starts the bot and resets the user data\n'
                              '\t- /listtopics  Lists all topics available\n'
                              '\t- /subscribe [name of the subtopic]  Subscribes you to the topic\n'
                              '\t- /listsubs  Lists all of your subs\n'
                              '\t- /pullnew [pdf/default=abstract]  Pulls the newest papers according to your subscriptions\n'
                              '\t- /unsubscribe [name of the subscription]  Unsubscribes you from the topic')


with open("conf", "r") as config:
    pickle_path = config.readline().split(":", 1)[-1].strip()
    key = config.readline().split(":", 1)[-1].strip()

if isfile(pickle_path):
    user_data = pickle.load(open(pickle_path, "rb"))
else:
    user_data = {}
    if isdir(pickle_path.rsplit(sep, 1)[0]):
        pickle.dump(user_data, open(pickle_path.rsplit(sep, 1)[0] + "/user_data.p", "wb"))
    else:
        pickle_path = "user_data.p"
        pickle.dump(user_data, open("user_data.p", "wb"))

general_topics, sub_topics, sub_topics_links = get_topics_with_links()

updater = Updater(key, use_context=True)

updater.dispatcher.add_handler(CommandHandler('start', start))
updater.dispatcher.add_handler(CommandHandler('help', help))
updater.dispatcher.add_handler(CommandHandler('listtopics', list_topics))
updater.dispatcher.add_handler(CommandHandler('subscribe', subscribe))
updater.dispatcher.add_handler(CommandHandler('listsubs', list_subscritions))
updater.dispatcher.add_handler(CommandHandler('pullnew', get_new_papers_for_subscritions))
updater.dispatcher.add_handler(CommandHandler('unsubscribe', unsubscribe))

updater.start_polling()
updater.idle()