#coding:utf-8
import os
import sys
import json
import editdistance
import threading, time

import requests
from flask import Flask, request

app = Flask(__name__)

user_dict = {}
thread_flag = False

def check_user_status():
    global user_dict
    while True :
        for key in user_dict :
            if time.time() - user_dict[key] > 1800 :
                user_dict.pop(key, None)

        time.sleep(1800)



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

    global thread_flag   #only run this thread one time
    global user_dict
    if not thread_flag :
        threading.Thread(target = check_user_status, args = (), name = 'check_thread').start()
        thread_flag = True


    data = request.get_json()
    log(data)  # you may not want to log every incoming message in production, but it's good for testing

    if data["object"] == "page":

        for entry in data["entry"]:
            for messaging_event in entry["messaging"]:

                if messaging_event.get("message"):  # someone sent us a message

                    sender_id = messaging_event["sender"]["id"]        # the facebook ID of the person sending you the message
                    recipient_id = messaging_event["recipient"]["id"]  # the recipient's ID, which should be your page's facebook ID
                    if "text" in messaging_event["message"] :
                        message_text = messaging_event["message"]["text"]  # the message's text
                        message_text = message_text.encode('utf-8').lower()

                        reply = handle_message( message_text, sender_id )

                        if not sender_id in user_dict : # not in time interval
                            send_message( sender_id, reply )
                            if reply == '請您等待專人為您回答' : user_dict[sender_id] = time.time() #使用者待專人回答, chatbot對該使用者暫停30min

                if messaging_event.get("delivery"):  # delivery confirmation
                    pass

                if messaging_event.get("optin"):  # optin confirmation
                    pass

                if messaging_event.get("postback"):  # user clicked/tapped "postback" button in earlier message
                    sender_id = messaging_event["sender"]["id"]        # the facebook ID of the person sending you the message
                    recipient_id = messaging_event["recipient"]["id"]  # the recipient's ID, which should be your page's facebook ID
                    message_text = messaging_event["postback"]["payload"]  # the message's text
                    message_text = message_text.encode('utf-8').lower()
                    reply = handle_message( message_text, sender_id )
                    if not sender_id in user_dict : # not in time interval
                        send_message( sender_id, reply )

    return "ok", 200

def handle_message(message_text, sender_id):
    global user_dict

    if u'不是我要的答案'.encode("utf8") in message_text or 'hello~' in message_text or 'hello～' in message_text :
        return '請您等待專人為您回答'

    if u'你好'.encode("utf8") in message_text or u'請問'.encode("utf8") in message_text or u'嗨'.encode("utf8") in message_text or u'哈囉'.encode("utf8") in message_text or 'hi' in message_text or 'hello' in message_text:
        if len(message_text ) < 10:
            return '你好！請問我能為您做些什麼？'
    # Email
    if u'信'.encode("utf8") in message_text or 'e-mail' in message_text or 'e mail' in message_text or 'email' in message_text or 'mail' in message_text :
        if u'進入'.encode("utf8") in message_text or u'登'.encode("utf8") in message_text or u'使用'.encode("utf8") in message_text or u'密碼錯誤'.encode("utf8") in message_text:
            return '若無法登入信箱，可以請您嘗試在成功入口介面更改一次密碼，此動作將會同步您的成功入口密碼與個人信箱密碼'
        if u'沒收到'.encode("utf8") in message_text or u'沒有收到'.encode("utf8") in message_text or u'垃圾信'.encode("utf8") in message_text :
            return '若有沒收到的信，有可能是因為被學校信件過濾系統誤判成是垃圾信件，若是使用個人信箱可以登入這個網頁找尋中途被攔截到的信件：http://antispam.ncku.edu.tw/symphony/login.html ，若是公務信箱則登入下面這個：http://eantispam.ncku.edu.tw/symphony/login.html'
        if u'申請'.encode("utf8") in message_text :
            return '若要申請個人信箱，請先登入成功入口後，點選教職員工個人設定裡的個人用電子郵件帳號申請，填入相關資料後便可啟用'
        if 'outlook' in message_text :
            return '可參考計中說明文件 http://cc.ncku.edu.tw/files/11-1255-14653.php?Lang=zh-tw'

#====================================================================
    #授權軟體
    if u'軟體'.encode("utf8") in message_text or 'win' in message_text or 'office' in message_text :
        if u'借用'.encode("utf8") in message_text or u'光碟'.encode("utf8") in message_text:
            return '若需要校園授權軟體可參考 http://cc.ncku.edu.tw/files/11-1255-6834-1.php?Lang=zh-tw 或是可以於計網中心服務時間帶一張證件至２樓借用光碟'
        if u'下載'.encode("utf8") in message_text :
            return '您好，校園授權軟體下載有兩種方式:\n1.校園授權網頁下載(需連線校內網路) http://cc.ncku.edu.tw/files/11-1255-6834-1.php?Lang=zh-tw\n2.成功大學mybox(校外網路可下載，但若需要進行啟用授權步驟仍得連進校內網路才能成功啟用，第一次使用mybox需開通。) https://mybox.ncku.edu.tw/ 登入後左邊"共用資料夾"可下載。'
        if u'金鑰'.encode("utf8") in message_text or u'過期'.encode("utf8") in message_text :
            return '您好，windows及office皆為校內網路授權，授權一次為180天，若一直在校外網路待授權期限一到便會出現過期訊息，請連線至校內網路(可使用vpn連回)並重新執行啟用檔再次取得180天授權即可，謝謝。\n校園授權軟體網頁:http://cc.ncku.edu.tw/files/11-1255-6834-1.php?Lang=zh-tw\nssl vpn: http://cc.ncku.edu.tw/files/11-1255-7637.php?Lang=zh-tw\n\n**若需要vpn連線教學請打「vpn連線教學」，謝謝:)'
    if u'啟動'.encode("utf8") in message_text or u'啟用'.encode("utf8") in message_text or u'認證'.encode("utf8") in message_text :
        if u'如何'.encode("utf8") in message_text or u'怎麼'.encode("utf8") in message_text :
            return 'windows或office需至校園授權軟體網頁下載啟用檔，若您在學校以外的網路,啟用授權軟體時必須先啟動vpn,才能進行產品認證 http://cc.ncku.edu.tw/files/11-1255-7637-1.php?Lang=zh-tw \n\n**若需要vpn連線教學請打「vpn連線教學」，謝謝:)'
        if u'無法'.encode("utf8") in message_text or u'失敗'.encode("utf8") in message_text :
            return '您好，若無法啟用，請確認是否已連線校內網路：google 「IP 查詢」→進第一個連結。確認IP為成大IP(140.116.XXX.XXX)。\n若已連線校內網路，請問您的錯誤代碼error code為何?(小黑框裡倒數幾行，類似0xC...，若非一般常見錯誤代碼請等待專人協助或於中心二樓服務台服務時間內攜帶筆電前往詢問)。\n若未連線至校內網路，請使用vpn服務連線至校內網路再作啟用。http://cc.ncku.edu.tw/files/11-1255-7637.php?Lang=zh-tw\n\n**若需要vpn連線教學請打「vpn連線教學」，謝謝:)'
    if '0x80070005' in message_text :
        return '錯誤代碼:0x80070005，未使用系統管理員身份執行，請在啟用檔上按右鍵選擇"以系統管理員身份執行"。\n若按右鍵未出現"以系統管理員身份執行"選項，表示您尚未將下載的啟用壓縮檔解壓縮，請按右鍵解壓縮或是直接將內部檔案拉至桌面亦可，謝謝。'
    if '0XC004F074' in message_text :
        return '錯誤代碼:0XC004F074，1.請確認是否已連線校內網路。google 「IP 查詢」→進第一個連結。確認IP為成大IP(140.116.XXX.XXX)。\n2.請確認電腦右下角時間是否正確。(時區及時間上下午都要對，時區確定為台北+8:00，再使用網路同步時間。)\n3.若您ip已是成大140.116 上述兩項亦沒問題卻認證失敗，請嘗試使用vpn連線後再行認證。\n\n**若需要vpn連線教學請打「vpn連線教學」，謝謝:)'
    if 'script' in message_text :
        return '您好，找不到script可能是以下兩種情形\n1.啟用檔未解壓縮。若在檔案上按右鍵無"以系統管理員身份執行"選項，即可能未解壓縮，請按右鍵解壓縮或是直接將.bat檔拉至桌面亦可。\n2.啟用檔不符合軟體版本。若同一軟體有A.B兩種啟用檔，不知道用哪一個的話，可以兩個都下載下來解壓縮都啟用試試。\nhttp://www.cc.ncku.edu.tw/download/'
    if 'matlab' in message_text :
        if u'下載'.encode("utf8") in message_text or u'單機'.encode("utf8") in message_text :
            return '您好，Matlab單機版不需使用校內網路認證，請前往Mathworks網站(www.mathworks.com)，使用"學校Email"及說明文件裡的cdkey申請一組帳號即可取得授權及下載。\n(以下網址需連線校內網路)\n詳細說明文件: ftp://140.116.249.78/Mathworks/MatlabR2016A/MATLAB_TAH_Single.pdf\nDetailed installation steps: ftp://140.116.249.78/Mathworks/MatlabR2016A/MATLAB_TAH_Single_En.pdf\nhttp://www.cc.ncku.edu.tw/download/matlab.htm'
        if 'license' in message_text or 'network' in message_text :
            return '您好，若您需要license.dat或network.lic表示您目前選擇使用的matlab版本為校園網路版(一開始安裝時有選項可選擇單機版或網路版)，檔案可至http://www.cc.ncku.edu.tw/download/matlab.htm 下載校園網路版連線授權檔(注意事項第三及第四點擇一下載即可)，校園網路版使用時需連線至校內網路才能取得授權。\n若為個人使用建議您改用單機版，單機版使用時無在校內網路使用的限制。若想轉換至單機版請參考:\n(以下網址需連線校內網路)\nftp://140.116.249.78/Mathworks/MatlabR2016A/MATLAB_TAH_Single.pdf\nhttp://www.cc.ncku.edu.tw/download/matlab.htm'
        if 'mac' in message_text or 'linux' in message_text :
            return 'mac 或 linux版本可在申請單機版授權帳號後於matlab官網上登入下載。\n(以下網址需連線校內網路)\n詳細說明文件: ftp://140.116.249.78/Mathworks/MatlabR2016A/MATLAB_TAH_Single.pdf\nDetailed installation steps: ftp://140.116.249.78/Mathworks/MatlabR2016A/MATLAB_TAH_Single_En.pdf\nhttp://www.cc.ncku.edu.tw/download/matlab.htm'
    if 'visual studio' in message_text :
        return '1.visual studio 無限制校內網路，安裝完即可使用。\n2.2013版前無需輸入序號，但2015版需要輸入序號:7DHGB-NW9XQ-Q9GT6-BMGMC-GQ7XY。\nhttp://www.cc.ncku.edu.tw/download/key.htm\n3.2013版可在成大mybox下載(無需校內網路)。'
    if u'網頁'.encode("utf8") in message_text :
        if 'Forbidden' in message_text or 'access denied' in message_text or 'vpn' in message_text or u'校外'.encode("utf8") in message_text or u'拒絕顯示'.encode("utf8") in message_text or u'不能下載'.encode("utf8") in message_text
            or u'無法下載'.encode("utf8") in message_text or u'壞'.encode("utf8") in message_text :
            return '1.請在網路和共用中心的網際網路中IP和DNA皆設定為自動取得，並從新開啟瀏覽器\n2.若無法進入校園授權軟體網頁，請使用vpn服務連線。\n3.若網頁打得開卻無法下載，可能只是打開網頁的暫存檔，同樣需使用vpn服務連線才能下載。\n\n**若需要vpn連線教學請打「vpn連線教學」，謝謝:)'
        if u'開'.encode("utf8") in message_text :
            if u'不'.encode("utf8") in message_text :
                return '1.若無法進入校園授權軟體網頁，請使用vpn服務連線。\n2.若網頁打得開卻無法下載，可能只是打開網頁的暫存檔，同樣需使用vpn服務連線才能下載。\n\n**若需要vpn連線教學請打「vpn連線教學」，謝謝:)'
    if u'vpn'.encode("utf8") in message_text :
        if u'安裝'.encode("utf8") in message_text or u'下載'.encode("utf8") in message_text or u'用'.encode("utf8") in message_text :
            return '請參考http://cc.ncku.edu.tw/files/11-1255-7637.php?Lang=zh-tw 的使用說明'
        if u'連'.encode("utf8") in message_text or u'卡'.encode("utf8") in message_text :
            return '如您是使用網頁版請到http://cc.ncku.edu.tw/files/11-1255-7637.php?Lang=zh-tw 下載連線軟體使用，並參考使用說明進行安裝及連線；若您是使用連線軟體，請先參考http://cc.ncku.edu.tw/files/11-1255-7637.php?Lang=zh-tw 的使用說明，並特別注意VPN使用完畢請登出以免影響下一次登入'
        if u'教學'.encode("utf8") in message_text or u'如何'.encode("utf8") in message_text or u'怎麼'.encode("utf8") in message_text :
            return '1.開啟網頁 http://cc.ncku.edu.tw/files/11-1255-7637-1.php?Lang=zh-tw\n2.\na.網頁方式連線，請參照網頁。\nb.軟體方式連線(推薦)：\n(1)下載ssl vpn連線軟體，解壓縮後安裝。(2)程式集→執行Juniper Network/Network Connect.exe。(3)程式上方輸入登入網址：https://sslvpn9.twaren.net/ncku →執行。(4)輸入成大信箱(成功入口)帳密。登入後右下角圖示顯示已連線。(5)最後確認ip檢查是否連線成功:google 「IP 查詢」→進第一個連結。確認IP為成大IP(140.116.XXX.XXX)。'

#=====================================================================


    #成功入口
    if u'成功入口'.encode("utf8") in message_text :
        if u'改'.encode("utf8") in message_text or u'無法'.encode("utf8") in message_text or u'忘'.encode("utf8") in message_text or u'登'.encode("utf8") in message_text :
            return '若需要修改成功入口密碼,請攜帶雙證件(學生證以及身分證)於上班時間到計算機中心一樓服務台,做更改密碼之服務'

    #mybox
    if 'mybox' in message_text :
        return '若無法連結mybox，可能是mybox帳號尚未開通，請先到mybox系統 (http://mybox.ncku.edu.tw) 啟用你的mybox帳號'

    #畢業
    if u'畢業'.encode("utf8") in message_text :
        return '成功入口僅服務在校學生，故學生畢業後，成功入口帳號即停用。個人mail帳號，則於畢業6個月後停用，而E-portfolio數位學習歷程檔可由該系統原網址登入使用。'

    #成績
    if u'成績'.encode("utf8") in message_text :
        return '請由成功入口進去後，E-portfolio數位學習歷程檔裡就有成績查詢的選項 ， 或由註冊組網頁連到成績查詢網頁。( 註冊組 -> 線上服務 -> 學生 -> 成績查詢 )'

    #dorm
    if u'宿'.encode("utf8") in message_text :
        if u'斷'.encode("utf8") in message_text or u'認證'.encode("utf8") in message_text or u'連'.encode("utf8") in message_text or u'無法使用'.encode("utf8") in message_text:
            return '1.請您使用其他電腦進行交叉測試 2.請您查看是否有被停權，http://www.cc.ncku.edu.tw/dorm/disable/index.php  若依然無法排除問題將請專人為您服務'
        if 'p2p' in message_text :
            return '因使用P2P有侵權問題, 本校校園網路禁止使用P2P, 故本校宿網亦禁止使用P2P, 除非是特殊學術用途之使用, 可另行申請.'
        if u'故障'.encode("utf8") in message_text or u'網路孔壞掉'.encode("utf8") in message_text :
            return '若確認網路有故障，麻煩至http://www.cc.ncku.edu.tw/dorm/ 進行使用者登入後進行故障申告，會由工程師為你處理，請耐心等候'
        if 'authentication failed' in message_text :
            return '出現 "Authentication failed." 訊息, 有二種可能: 1. 帳號或密碼輸入錯誤，請重新輸入再試一下。若不確定是否正確，可借室友電腦登入宿網管理系統看看。 2. 帳號被停用，登入宿網管理系統，查詢登錄資料，若被停用，在最後一項”特殊限制”中，會註明停用原因。'
        return '請參考宿網管理系統 http://www.cc.ncku.edu.tw/dorm/ '

    if u'資安通報'.encode("utf8") in message_text :
        return '需要填寫資安通報，可以先從 https://goo.gl/YzegaO 這裡下載通報檔案，填寫完後直接回傳至security@mail.ncku.edu.tw 這個信箱，或是繳交紙本到計網中心一樓'


    return '請您等待專人為您回答'


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
