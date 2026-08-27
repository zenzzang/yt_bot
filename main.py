import feedparser
import requests
import json
import os
import csv
import io
from datetime import datetime

SHEET_CSV_URL = "https://docs.google.com/spreadsheets/d/1jaIGjoWuAASDof1FUpE7kYK1Jl4Dmg2u8lfFV65bozs/export?format=csv"
POWER_URL = "https://default91856527a4464990b48e37ca10f2ee.8d.environment.api.powerplatform.com:443/powerautomate/automations/direct/cu/09/workflows/b99e85923f3b421cbcf71e6a38cfc5bd/triggers/manual/paths/invoke?api-version=1&sp=%2Ftriggers%2Fmanual%2Frun&sv=1.0&sig=-mprHiKkXGUwdrOyclY8EzsxwQk0PDWalHoSu7UUOgA"
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

def get_active_channels_from_sheet():
    channels = []
    try:
        response = requests.get(SHEET_CSV_URL)
        response.raise_for_status()
        
        f = io.StringIO(response.text)
        reader = csv.reader(f)
        
        headers = next(reader, None)
        if not headers:
            return channels
            
        id_idx = -1
        active_idx = -1
        
        for idx, h in enumerate(headers):
            h_clean = h.strip()
            if "채널 ID" in h_clean:
                id_idx = idx
            elif "활성 여부" in h_clean:
                active_idx = idx
                
        if id_idx == -1 or active_idx == -1:
            return channels

        for row in reader:
            if not row or len(row) <= max(id_idx, active_idx):
                continue
            channel_id = row[id_idx].strip()
            active = row[active_idx].strip().upper()
            
            if active == "TRUE" and channel_id:
                channels.append(f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}")
    except Exception as e:
        print(f"구글 시트 연동 에러: {e}")
    
    return channels

def format_published_date(published_str):
    """유튜브 RSS 날짜 형식(예: 2026-08-26T04:48:00+00:00)을 YYYY.MM.DD로 변환"""
    try:
        # ISO 형식 파싱 시도
        dt = datetime.fromisoformat(published_str.replace("Z", "+00:00"))
        return dt.strftime("%Y.%m.%d")
    except Exception:
        try:
            # feedparser가 파싱한 구조화된 시간(published_parsed)이 넘어올 경우 대비
            if hasattr(published_str, "__getitem__") and len(published_str) >= 3:
                return f"{published_str[0]:04d}.{published_str[1]:02d}.{published_str[2]:02d}"
        except:
            pass
    # 변환 실패 시 원본 문자열 반환 혹은 앞부분 10자리(YYYY-MM-DD) 추출 후 치환
    clean_str = str(published_str).strip()
    if len(clean_str) >= 10 and clean_str[4] == '-' and clean_str[7] == '-':
        return clean_str[:10].replace('-', '.')
    return clean_str

def send_signal(title, link, thumb, channel, published):
    clean_title = str(title).strip().replace('"', "'")
    clean_channel = str(channel).strip().replace('"', "'")
    clean_link = str(link).strip()
    clean_thumb = str(thumb).strip()
    
    # 게시일시를 YYYY.MM.DD 형태로 변환
    formatted_date = format_published_date(published)

    # 썸네일 바로 밑에 링크 TextBlock을 추가한 적응형 카드 구조
    adaptive_card = {
        "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
        "type": "AdaptiveCard",
        "version": "1.2",
        "body": [
            {
                "type": "TextBlock",
                "text": f"🎬 신규 콘텐츠 알림 [{clean_channel}]",
                "weight": "Bolder",
                "size": "Medium",
                "color": "Accent"
            },
            {
                "type": "TextBlock",
                "text": clean_title,
                "weight": "Bolder",
                "size": "Large",
                "wrap": True
            },
            {
                "type": "Image",
                "url": clean_thumb,
                "size": "Stretch",
                "altText": "유튜브 썸네일",
                "selectAction": {
                    "type": "Action.OpenUrl",
                    "url": clean_link
                }
            },
            {
                "type": "TextBlock",
                "text": f"▶️ [영상 바로보기 링크]({clean_link})",
                "wrap": True,
                "size": "Default",
                "isSubtle": True
            },
            {
                "type": "FactSet",
                "facts": [
                    {
                        "title": "채널",
                        "value": clean_channel
                    },
                    {
                        "title": "게시일시",
                        "value": formatted_date
                    }
                ]
            }
        ],
        "actions": [
            {
                "type": "Action.OpenUrl",
                "title": "▶️ YouTube에서 영상 바로 재생하기",
                "url": clean_link
            },
            {
                "type": "Action.OpenUrl",
                "title": "📊 NC Youtube DashBoard에서 열기",
                "url": "https://nc-nbs.ai.studio/"
            }
        ]
    }

    payload = {
        "adaptiveCard": adaptive_card
    }

    try:
        res = requests.post(
            POWER_URL, 
            data=json.dumps(payload, ensure_ascii=False).encode('utf-8'), 
            headers={"Content-Type": "application/json; charset=utf-8"}
        )
        if res.status_code in [200, 202]:
            print(f"파워 아우토메이트 전송 성공: {clean_title}")
        else:
            print(f"전송 실패 코드: {res.status_code}, 응답: {res.text}")
    except Exception as ex:
        print(f"통신 에러: {ex}")

def run():
    seen = load_seen()
    new_seen = seen.copy()
    
    channel_urls = get_active_channels_from_sheet()
    if not channel_urls:
        print("⚠️ 활성화된 채널이 없습니다.")
        return
    
    for url in channel_urls:
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
