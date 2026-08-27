def get_active_channels_from_sheet():
    """구글 시트에서 활성 여부가 정확히 TRUE인 채널 RSS URL 목록만 동적으로 가져옵니다."""
    channels = []
    try:
        response = requests.get(SHEET_CSV_URL)
        response.raise_for_status()
        
        # CSV 데이터 파싱
        f = io.StringIO(response.text)
        reader = csv.DictReader(f)
        
        for row in reader:
            # 공백을 제거하고 대문자로 변환하여 비교 ("TRUE" 또는 "true" 대응)
            active = str(row.get("활성여부", "")).strip().upper()
            channel_id = str(row.get("채널ID", "")).strip()
            channel_url = str(row.get("채널URL", "")).strip()
            
            # 정확히 TRUE일 때만 추가
            if active == "TRUE":
                if channel_id:
                    channels.append(f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}")
                elif channel_url:
                    channels.append(channel_url)
        
        print(f"[{len(channels)}개] 활성(TRUE) 채널 로드 완료")
    except Exception as e:
        print(f"구글 시트 연동 에러: {e}")
    
    return channels
