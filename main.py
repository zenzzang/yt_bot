import feedparser
import requests
import json
import os
import csv
import io
from datetime import datetime

SHEET_CSV_URL = "https://docs.google.com/spreadsheets/d/1jaIGjoWuAASDof1FUpE7kYK1Jl4Dmg2u8lfFV65bozs/export?format=csv"
POWER_URL = "https://default91856527a4464990b48e37ca10f2ee.8d.environment.api.powerplatform.com:443/powerautomate/automations/direct/cu/02/workflows/1f012f272d9041b3ab0c4a7031ffab2e/triggers/manual/paths/invoke?api-version=1&sp=%2Ftriggers%2Fmanual%2Frun&sv=1.0&sig=wFnhf1VLP2r9WLu7nTHZKFHhvPRARZIQ_PD9AB3Uqy8"
SEEN_FILE = "seen_videos.json"

def load_seen():
    """seen_videos.json 로드 (기존의 단순 문자열 리스트와 새로운 딕셔너리 형태 모두 호환)"""
    if os.path.exists(SEEN_FILE):
        with open(SEEN_FILE, "r", encoding="utf-8") as f:
            try: 
                data = json.load(f)
                # 기존 데이터가 단순 ID 문자열 리스트인 경우를 대비한 예외 처리
                normalized = []
                for item in data:
                    if isinstance(item, str):
                        normalized.append({"vid": item, "title": "", "channel": "", "link": ""})
                    elif isinstance(item, dict):
                        normalized.append(item)
                return normalized
            except: 
                return []
    return []

def save_seen(lst):
    """최신 200개의 기록만 유지하여 저장"""
    with open(SEEN_FILE, "w", encoding="utf-8") as f:
        json.dump(lst[-200:], f, ensure_ascii=False, indent=2)

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
    """유튜브 RSS 날짜 형식을 YYYY.MM.DD HH:MM:SS 형식으로 변환"""
    try:
        dt = datetime.fromisoformat(published_str.replace("Z", "+00:00"))
        return dt.strftime("%Y.%m.%d %H:%M:%S")
    except Exception:
        try:
            if hasattr(published_str, "__getitem__") and len(published_str) >= 6:
                return f"{published_str[0]:04d}.{published_str[1]:02d}.{published_str[2]:02d} {published_str[3]:02d}:{published_str[4]:02d}:{published_str[5]:02d}"
        except:
            pass
    clean_str = str(published_str).strip()
    return clean_str

def send_signal(title, link, thumb, channel, published, vid):
    clean_title = str(title).strip().replace('"', "'")
    clean_channel = str(channel).strip().replace('"', "'")
    clean_link = str(link).strip()
    clean_thumb = str(thumb).strip()
    
    formatted_date = format_published_date(published)
    dashboard_url = f"https://nc-nbs.ai.studio/?video={vid}" if vid else "https://nc-nbs.ai.studio/"

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
                "text": f"'{clean_title}' 영상이 새로 업로드되었습니다.",
                "wrap": True,
                "size": "Default"
            },
            {
                "type": "FactSet",
                "facts": [
                    {
                        "title": "링크",
                        "value": clean_link
                    },
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
                "url": dashboard_url
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
    
    # 이미 본 영상들의 비디오 ID 집합(Set) 생성
    seen_vids = {item["vid"] for item in seen}
    
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
                
                if vid and vid not in seen_vids:
                    print(f"[신규 전송] {channel} - {title}")
                    send_signal(title, link, thumb, channel, published, vid)
                    # 비디오 ID뿐만 아니라 채널명, 제목, 링크를 함께 기록
                    new_seen.append({
                        "vid": vid,
                        "title": title,
                        "channel": channel,
                        "link": link
                    })
                    seen_vids.add(vid)
                else:
                    print(f"[스킵] {channel} - {title}")
        except Exception as e:
            print(f"채널 파싱 에러 ({url}): {e}")
            
    save_seen(new_seen)

if __name__ == "__main__":
    run()
