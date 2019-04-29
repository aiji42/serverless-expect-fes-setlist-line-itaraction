import os
import json
import re
import collections
from bs4 import BeautifulSoup
import urllib.request, urllib.parse, urllib.error
from linebot import (
    LineBotApi, WebhookHandler
)
from linebot.models import (
    MessageEvent, PostbackEvent, TextMessage, TextSendMessage,
    TemplateSendMessage, PostbackAction, ButtonsTemplate
)
from linebot.exceptions import (
    LineBotApiError, InvalidSignatureError
)
import logging

logger = logging.getLogger()
logger.setLevel(logging.ERROR)

line_bot_api = LineBotApi(os.environ["LINE_CHANNEL_ACCESS_TOKEN"])
handler = WebhookHandler(os.environ["LINE_CHANNEL_SECRET"])

def line_intaraction(event, context):
    signature = event["headers"]["X-Line-Signature"]
    body = event["body"]
    body_json = json.loads(body)

    # 初回の疎通テスト用
    if body_json["events"][0]["replyToken"] == "00000000000000000000000000000000":
        return ok_json()

    @handler.add(MessageEvent, message=TextMessage)
    def message(line_event):
        artists = search_artist(line_event.message.text)
        if len(artists) < 1:
            line_bot_api.reply_message(line_event.reply_token, TextSendMessage(text="検索結果が見つかりませんでした。"))
            return ok_json()
        postback_actions = []
        for index, (artist, artist_code) in enumerate(artists):
            # 表示可能なのは4つまで
            if index == 4: break
            # 20文字超えると怒られる
            if len(artist) > 20:
                artist = artist[:19] + "…"
            postback_actions.append(PostbackAction(label=artist, data=artist_code))

        buttons_template = ButtonsTemplate(
            title="検索結果", text="下記の検索結果の中から選んでください。", actions=postback_actions)
        template_message = TemplateSendMessage(alt_text="検索結果だよ", template=buttons_template)
        line_bot_api.reply_message(line_event.reply_token, template_message)

    @handler.add(PostbackEvent)
    def postback(line_event):
        line_bot_api.reply_message(line_event.reply_token, TextSendMessage(text="検索中だよ…"))
        artist_code = line_event.postback.data
        songs = []
        feses = search_fes(artist_code)
        for fes_code, fes_date, fes_title in feses:
            message = "%s %s" % (fes_date, fes_title)
            for index, song in enumerate(setlist(fes_code)):
                songs.append(song)
                message += "\n  %02d %s" % (index, song)
            line_bot_api.push_message(line_event.source.user_id, TextSendMessage(text=message))
        message = "【予測結果】"
        for song, count in collections.Counter(songs).most_common():
            rate = count * 1.0 / len(feses) * 100
            message += "\n{: >3}%({: >2}/{}) {}".format(round(rate), count, len(feses), song)
        line_bot_api.push_message(line_event.source.user_id, TextSendMessage(text=message))

    try:
        handler.handle(body, signature)
    except LineBotApiError as e:
        logger.error("Got exception from LINE Messaging API: %s\n" % e.message)
        for m in e.error.details:
            logger.error("  %s: %s" % (m.property, m.message))
        return error_json()
    except InvalidSignatureError:
        return error_json()

    return ok_json()


def search_artist(keyword):
    html = urllib.request.urlopen("http://www.livefans.jp/search?option=6&keyword=%s&genre=all" % urllib.parse.quote_plus(keyword, encoding="utf-8"))
    soup = BeautifulSoup(html, "html.parser")
    artists = []
    for artist in soup.find_all(class_="artistName"):
        artists.append([artist.string, artist.a.get("href").replace("/artists/", "")])
    return artists


def search_fes(artist_code, page = 1):
    html = urllib.request.urlopen("http://www.livefans.jp/search/artist/%s/page:%d?setlist=on&year=before&sort=e1" % (artist_code, page))
    soup = BeautifulSoup(html, "html.parser")
    feses = []
    if len(soup.find_all(class_="fes")) < 1:
        return feses
    for fes in soup.find_all(class_="rbnFes"):
        fes_url = fes.a.get("href")
        title = soup.find("a", href=fes_url).find_parent().find(class_="artistName").string
        date = soup.find("a", href=fes_url).find_parent().find(class_="date").text[:10]
        event_code = fes_url.replace("/events/", "")
        feses.append([event_code, date, title])
    if len(feses) < 10:
        page += 1
        feses += search_fes(artist_code, page)
    return feses[:10]


def setlist(event_code):
    html = urllib.request.urlopen("http://www.livefans.jp/events/%s" % event_code)
    soup = BeautifulSoup(html, "html.parser")
    songs = []
    for song in soup.find_all(href=re.compile("^/songs")):
        songs.append(song.string)
    return songs


def ok_json():
    return {
        "isBase64Encoded": False,
        "statusCode": 200,
        "headers": {},
        "body": ""
    }


def error_json():
    return {
        "isBase64Encoded": False,
        "statusCode": 403,
        "headers": {},
        "body": "Error"
    }
