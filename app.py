#coding:utf-8
import os
import sys
import json
import editdistance

import requests
from flask import Flask, request

app = Flask(__name__)


@app.route('/', methods=['GET'])
def verify():
    # when the endpoint is registered as a webhook, it must echo back
    # the 'hub.challenge' value it receives in the query arguments
    if request.args.get("hub.mode") == "subscribe" and request.args.get("hub.challenge"):
        if not request.args.get("hub.verify_token") == os.environ["VERIFY_TOKEN"]:
            return "Verification token mismatch", 403
        return request.args["hub.challenge"], 200

    return "Hello world", 200


@app.route('/', methods=['POST'])
def webhook():

    # endpoint for processing incoming messaging events

    data = request.get_json()
    log(data)  # you may not want to log every incoming message in production, but it's good for testing

    if data["object"] == "page":

        for entry in data["entry"]:
            for messaging_event in entry["messaging"]:

                if messaging_event.get("message"):  # someone sent us a message

                    sender_id = messaging_event["sender"]["id"]        # the facebook ID of the person sending you the message
                    recipient_id = messaging_event["recipient"]["id"]  # the recipient's ID, which should be your page's facebook ID
                    message_text = messaging_event["message"]["text"]  # the message's text
                    message_text = message_text.encode('utf-8').lower()

                    reply = handle_message( message_text )

                    send_message(sender_id, reply )

                if messaging_event.get("delivery"):  # delivery confirmation
                    pass

                if messaging_event.get("optin"):  # optin confirmation
                    pass

                if messaging_event.get("postback"):  # user clicked/tapped "postback" button in earlier message
                    sender_id = messaging_event["sender"]["id"]        # the facebook ID of the person sending you the message
                    recipient_id = messaging_event["recipient"]["id"]  # the recipient's ID, which should be your page's facebook ID
                    message_text = messaging_event["postback"]["payload"]  # the message's text
                    message_text = message_text.encode('utf-8').lower()
                    reply = handle_message( message_text )
                    send_message(sender_id, reply )

    return "ok", 200

def handle_message(message_text):
    if u'不是我要的答案'.encode("utf8") in message_text :
        return '請您等待專人為您回答'
    # Email
    if u'信'.encode("utf8") in message_text or 'e-mail' in message_text or 'e mail' in message_text or 'email' in message_text :
        if u'進入'.encode("utf8") in message_text or u'登入'.encode("utf8") in message_text :
            return '若無法登入信箱，可以請您嘗試在成功入口介面更改一次密碼，此動作將會同步您的成功入口密碼與個人信箱密碼'
        if u'沒收到'.encode("utf8") in message_text or u'沒有收到'.encode("utf8") in message_text :
            return '若有沒收到的信，有可能是因為被學校信件過濾系統誤判成是垃圾信件，若是使用個人信箱可以登入這個網頁找尋中途被攔截到的信件：http://antispam.ncku.edu.tw/symphony/login.html ，若是公務信箱則登入下面這個：http://eantispam.ncku.edu.tw/symphony/login.html'
        if u'申請'.encode("utf8") in message_text :
            return '若要申請個人信箱，請先登入成功入口後，點選教職員工個人設定裡的個人用電子郵件帳號申請，填入相關資料後便可啟用'
        if 'outlook' in message_text :
            return '可參考計中說明文件 http://cc.ncku.edu.tw/files/11-1255-14653.php?Lang=zh-tw'

    if u'啟動'.encode("utf8") in message_text or u'啟用'.encode("utf8") in message_text or u'授權軟體'.encode("utf8") in message_text  or 'office' in message_text or 'visual studio' in message_text :
        return '若您在學校以外的網路,啟用時必須先啟動vpn,才能進行產品認證'

    if u'成功入口'.encode("utf8") in message_text :
        print(editdistance.eval('成功入口忘記密碼 想要改密碼', message_text ))
        print(type(editdistance.eval('成功入口忘記密碼 想要改密碼', message_text )))
        if u'改'.encode("utf8") in message_text :
            return '若需要修改成功入口密碼,請攜帶雙證件(學生證以及身分證)於上班時間到計算機中心一樓服務台,做更改密碼之服務'

    return message_text


def send_message(recipient_id, message_text):

    log("sending message to {recipient}: {text}".format(recipient=recipient_id, text=message_text))

    params = {
        "access_token": os.environ["PAGE_ACCESS_TOKEN"]
    }
    headers = {
        "Content-Type": "application/json"
    }
    data = json.dumps({
        "recipient": {
            "id": recipient_id
        },
        "message":{
            "attachment":{
                "type":"template",
                "payload":{
                    "template_type":"button",
                    "text": message_text ,
                    "buttons":[
                        {
                        "type":"web_url",
                        "url":"http://myidp.sso2.ncku.edu.tw/nidp/idff/sso?id=3&sid=0&option=credential&sid=0",
                        "title":"成功入口"
                        },
                        {
                        "type":"web_url",
                        "url":"http://cc.ncku.edu.tw/files/11-1255-7637.php?Lang=zh-tw",
                        "title":"SSL VPN服務"
                        },
                        {
                            "type":"postback",
                            "title":"不是我要的答案",
                            "payload":"不是我要的答案"
                        }
                        ]
                }
            }
        }
    })
    r = requests.post("https://graph.facebook.com/v2.6/me/messages", params=params, headers=headers, data=data)
    if r.status_code != 200:
        log(r.status_code)
        log(r.text)


def log(message):  # simple wrapper for logging to stdout on heroku
    print str(message)
    sys.stdout.flush()


if __name__ == '__main__':
    app.run(debug=True)
