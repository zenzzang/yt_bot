def get_active_channels_from_sheet():
    """구글 시트의 컬럼 구조((H)활성 여부, (D)채널 ID)에 맞춰 활성(TRUE) 채널만 가져옵니다."""
    channels = []
    try:
        response = requests.get(SHEET_CSV_URL)
        response.raise_for_status()
        
        # CSV 데이터 파싱
        f = io.StringIO(response.text)
        reader = csv.DictReader(f)
        
        for row in reader:
            # 띄어쓰기가 포함된 실제 시트 헤더 이름 ('활성 여부', '채널 ID') 사용
            active = str(row.get("활성 여부", "")).strip().upper()
            channel_id = str(row.get("채널 ID", "")).strip()
            channel_url = str(row.get("채널 URL", "")).strip()
            
            # 활성 여부가 TRUE이고 채널 ID가 존재할 경우 RSS URL 생성
            if active == "TRUE":
                if channel_id:
                    channels.append(f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}")
                elif channel_url and "channel_id=" in channel_url:
                    channels.append(channel_url)
        
        print(f"[{len(channels)}개] 활성(TRUE) 채널 로드 완료")
    except Exception as e:
        print(f"구글 시트 연동 에러: {e}")
    
    return channels
