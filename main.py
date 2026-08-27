import feedparser
import requests
import json
import os

CHANNEL_URLS = [
    "https://www.youtube.com/feeds/videos.xml?channel_id=UCbiqc9mdIz3XEH6LG5nCeMg",
    "https://www.youtube.com/feeds/videos.xml?channel_id=UC3a5gHVMzpdhmNj9JefvTzw",
    "https://www.youtube.com/feeds/videos.xml?channel_id=UC6EcdZPLwHRoJbFWl0LeDaw",
    "https://www.youtube.com/feeds/videos.xml?channel_id=UCYhAwwDOx16I_yAenTr3Y_A",
    "https://www.youtube.com/feeds/videos.xml?channel_id=UC8_FRgynMX8wlGsU6Jh3zKg",
    "https://www.youtube.com/feeds/videos.xml?channel_id=UCs4zYuMKbsEjRultr9J51rA",
    "https://www.youtube.com/feeds/videos.xml?channel_id=UCTo4YrH1vEFbDqtaaQhIpCA",
    "https://www.youtube.com/feeds/videos.xml?channel_id=UCStqutAFFfXUFLeo1htewhg",
    "https://www.youtube.com/feeds/videos.xml?channel_id=UCbsEahPqZ6WrRqQ0wqLAZdg",
    "https://www.youtube.com/feeds/videos.xml?channel_id=UC8fO3ZAsmI2dMogK5Mojq2g",
    "https://www.youtube.com/feeds/videos.xml?channel_id=UCQcL_ooESP8rvQa8ogtKkvQ",
    "https://www.youtube.com/feeds/videos.xml?channel_id=UCJdQeF_krqVXnRsMeLiFVKA",
    "https://www.youtube.com/feeds/videos.xml?channel_id=UCLSnC5HDvLzV-X_ar_QkZsg",
    "https://www.youtube.com/feeds/videos.xml?channel_id=UCEsHrY4O-6PpFjSiZNWp-EQ",
    "https://www.youtube.com/feeds/videos.xml?channel_id=UCqh_gleuOIleCy5Qmbo2j1Q",
    "https://www.youtube.com/feeds/videos.xml?channel_id=UC4GQLyXDkw2NIS7GAW7Uwbg",
    "https://www.youtube.com/feeds/videos.xml?channel_id=UCOl67W1YI0sWHiVfymbqmew",
    "https://www.youtube.com/feeds/videos.xml?channel_id=UCkDvh4ai4BKo98lJd-ZGqDA",
    "https://www.youtube.com/feeds/videos.xml?channel_id=UCWGs7lFiEdbThvEW4LogTTw",
    "https://www.youtube.com/feeds/videos.xml?channel_id=UCPAyM_GHKKKd9jnnuPNQZCQ",
    "https://www.youtube.com/feeds/videos.xml?channel_id=UCGgOgKxwYoi3SAYwMVbglbw",
    "https://www.youtube.com/feeds/videos.xml?channel_id=UCHiWCN5LEWCPC0G0I8TPT-g",
    "https://www.youtube.com/feeds/videos.xml?channel_id=UCEpd2-cNQYNY_-fNZpfsyUQ",
    "https://www.youtube.com/feeds/videos.xml?channel_id=UCJ1pgwGj3mFYgWT5cSbhq0Q",
    "https://www.youtube.com/feeds/videos.xml?channel_id=UCC1A0EJmrU3gIkk35ZotUxg",
    "https://www.youtube.com/feeds/videos.xml?channel_id=UC0mZxgRoyTFIsycsqqaAqow",
    "https://www.youtube.com/feeds/videos.xml?channel_id=UC6alabHLrFrxup0R3Z-BmlQ",
    "https://www.youtube.com/feeds/videos.xml?channel_id=UCQ4RpXaydDFrDeVdbk537ag",
    "https://www.youtube.com/feeds/videos.xml?channel_id=UCoOAmAJ83x93BwGAz8IgrfQ",
    "https://www.youtube.com/feeds/videos.xml?channel_id=UCREI1IrOmyrfY1hWIpmT1Wg",
    "https://www.youtube.com/feeds/videos.xml?channel_id=UC0aZSIcBfnpWLXAnDQPhjmQ",
    "https://www.youtube.com/feeds/videos.xml?channel_id=UCs6vXCK1qs2Q35IOmi3OZaw",
    "https://www.youtube.com/feeds/videos.xml?channel_id=UCGl9Jqn5Wnh4ihPKER2hYkA",
    "https://www.youtube.com/feeds/videos.xml?channel_id=UCnzF9FKfXUrz_syAy1PRREw",
    "https://www.youtube.com/feeds/videos.xml?channel_id=UCo-9ovAJ6Ffo2mEI85nw6jg"
]

POWER_URL = "https://default91856527a4464990b48e37ca10f2ee.8d.environment.api.powerplatform.com:443/powerautomate/automations/direct/cu/02/workflows/1f012f272d9041b3ab0c4a7031ffab2e/triggers/manual/paths/invoke?api-version=1&sp=%2Ftriggers%2Fmanual%2Frun&sv=1.0&sig=wFnhf1VLP2r9WLu7nTHZKFHhvPRARZIQ_PD9AB3Uqy8"
SEEN_FILE = "seen_videos.json"

def load_seen():
    if os.path.exists(SEEN_FILE):
        with open(SEEN_FILE, "r") as f:
            try: return json.load(f)
            except: return []
    return []

def save_seen(lst):
    with open(SEEN_FILE, "w") as f:
        json.dump(lst[-200:], f)

def send_signal(title, link, thumb, channel, published):
    payload = {
        "title": title,
        "link": link,
        "thumbnail_url": thumb,
        "channel_name": channel,
        "published": published
    }
    try:
        res = requests.post(POWER_URL, data=json.dumps(payload), headers={"Content-Type": "application/json"})
        if res.status_code in [200, 202]:
            print(f"파워 아우토메이트 전송 성공: {title}")
        else:
            print(f"전송 실패 코드: {res.status_code}")
    except Exception as ex:
        print(f"통신 에러: {ex}")

def run():
    seen = load_seen()
    new_seen = seen.copy()
    
    for url in CHANNEL_URLS:
        try:
            feed = feedparser.parse(url)
            if feed.entries:
                latest = feed.entries[0]
                vid = latest.get("yt_videoid", "")
                title = latest.title
                link = latest.link
                published = latest.get("published", "시간 정보 없음")
                channel = feed.feed.get("title", "유튜브 채널")
                
                if not vid and "v=" in link:
                    vid = link.split("v=")[1].split("&")[0]
                elif not vid and "shorts/" in link:
                    vid = link.split("shorts/")[1].split("?")[0]
                
                thumb = f"https://img.youtube.com/vi/{vid}/hqdefault.jpg" if vid else ""
                
                if vid and vid not in seen:
                    print(f"[신규 전송] {channel} - {title}")
                    send_signal(title, link, thumb, channel, published)
                    new_seen.append(vid)
                else:
                    print(f"[스킵] {channel} - {title}")
        except Exception as e:
            print(f"채널 파싱 에러 ({url}): {e}")
            
    save_seen(new_seen)

if __name__ == "__main__":
    run()
