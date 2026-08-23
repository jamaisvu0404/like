"""
プライズ重心情報（Merry✩An、831生活、あかり、もぐらクレーン）2026年分 収集＆HTML生成スクリプト
"""

import os
import sys
import re
import json
import time
import requests
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

# 実行ディレクトリ
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_JSON_PATH = os.path.join(BASE_DIR, "gravity_data.json")
OUTPUT_HTML_PATH = os.path.join(BASE_DIR, "gravity.html")
PRIZE_HTML_PATH = os.path.join(BASE_DIR, "prize_gravity_viewer.html")

SUPABASE_URL = "https://cguiwksdixdgxaebbwye.supabase.co"

# 対象アカウント（ユーザー名・スクリーンネーム判定用）
TARGET_AUTHORS = {
    "merry": {
        "name": "Merry☆An",
        "screen_names": ["6es8jm4ynjppa2d"],
        "keywords": ["merry", "みりあん"]
    },
    "831": {
        "name": "831生活",
        "screen_names": ["831suky"],
        "keywords": ["831生活", "831suky"]
    },
    "akari": {
        "name": "あかり",
        "screen_names": ["yohane150"],
        "keywords": ["yohane150", "あかり"]
    },
    "mogura": {
        "name": "もぐらクレーン",
        "screen_names": ["mogurakurenn"],
        "keywords": ["mogurakurenn", "もぐらクレーン"]
    }
}

def identify_author(user_name, screen_name):
    """投稿者の識別"""
    u_lower = (user_name or "").lower()
    s_lower = (screen_name or "").lower()
    
    for key, info in TARGET_AUTHORS.items():
        if s_lower in info["screen_names"]:
            return info["name"]
        for kw in info["keywords"]:
            if kw in u_lower or kw in s_lower:
                return info["name"]
    return None

def get_supabase_key():
    """crane-labのJSチャンクからSupabaseの匿名キーを自動取得"""
    try:
        r = requests.get("https://crane-lab.com/center-of-gravity", timeout=10)
        chunks = re.findall(r'src="(/_next/static/chunks/[^"]+)"', r.text)
        for c in chunks:
            if "center-of-gravity" in c or "page" in c or "layout" in c:
                res = requests.get(f"https://crane-lab.com{c}", timeout=10)
                keys = re.findall(r'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9\.[a-zA-Z0-9_\-\.]+', res.text)
                if keys:
                    return keys[0]
    except Exception as e:
        print(f"Warning: Failed to auto-extract Supabase key: {e}")
    return "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImNndWl3a3NkaXhkZ3hhZWJid3llIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MjgzMDUyMzksImV4cCI6MjA0Mzg4MTIzOX0.N-J1oMhK49g2vW9uW-K4Ff0bS5X8Z9"

def fetch_anime_titles(headers):
    """作品タイトルマスタの取得"""
    print("作品タイトルマスタを取得中...")
    anime_map = {}
    try:
        r = requests.get(f"{SUPABASE_URL}/rest/v1/anime_titles?select=id,title,sub_title,reading_kana&limit=2000", headers=headers, timeout=15)
        if r.status_code == 200:
            for item in r.json():
                anime_map[item['id']] = item
            print(f"-> {len(anime_map)} 件の作品タイトルを取得しました。")
    except Exception as e:
        print(f"Error fetching anime titles: {e}")
    return anime_map

def fetch_all_cog_records(headers, limit_total=None):
    """center_of_gravity テーブルからレコードインデックスを取得"""
    print("重心情報レコードのインデックスを取得中...")
    all_records = []
    page_size = 1000
    offset = 0
    
    while True:
        url = f"{SUPABASE_URL}/rest/v1/center_of_gravity?select=*&order=id.desc&limit={page_size}&offset={offset}"
        try:
            r = requests.get(url, headers=headers, timeout=15)
            if r.status_code != 200:
                print(f"Error fetching page at offset {offset}: status {r.status_code}")
                break
            items = r.json()
            if not items:
                break
            all_records.extend(items)
            print(f"-> {len(all_records)} 件取得済み...")
            if limit_total and len(all_records) >= limit_total:
                all_records = all_records[:limit_total]
                break
            if len(items) < page_size:
                break
            offset += page_size
        except Exception as e:
            print(f"Exception during pagination: {e}")
            break
            
    print(f"合計 {len(all_records)} 件のレコードインデックスを取得しました。")
    return all_records

def clean_url_or_text(s):
    if not s:
        return ""
    cleaned = re.sub(r'https?://t\.co/[a-zA-Z0-9]+', '', s).strip()
    return cleaned

def parse_tweet_content(text, author_name, anime_title=""):
    """各投稿者のフォーマットに合わせて構造化データをパース"""
    if not text:
        return {}
    
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    
    prize_name = ""
    fig_size = ""
    box_weight = ""
    box_size = ""
    gravity_details = []
    condition_details = []
    tags = set()

    # --- 景品名の抽出 ---
    name_candidates = []
    for line in lines:
        if any(line.startswith(prefix) for prefix in ['＃重心情報', '#重心情報', '重心情報', '#cranity', '#クレーンゲーム']):
            continue
        if any(line.startswith(prefix) for prefix in ['🔶', '【', '🟨', 'http', '※', '★', '☆', '・']):
            break
        if '重心情報:' in line or '重心情報：' in line:
            break
        cleaned = clean_url_or_text(line)
        # 『』「」を除去
        cleaned = re.sub(r'^[『「【](.*?)[』」】]$', r'\1', cleaned)
        if cleaned:
            name_candidates.append(cleaned)

    prize_name = ' '.join(name_candidates).strip()
    if not prize_name:
        # 代替として1行目またはアニメタイトル
        for line in lines:
            c = clean_url_or_text(line)
            if c and not any(c.startswith(p) for p in ['#', '＃', '【', '🟨', '🔶']):
                prize_name = re.sub(r'^[『「【](.*?)[』」】]$', r'\1', c)
                break
    if not prize_name:
        prize_name = anime_title or "プライズ景品"

    # クレンジング
    prize_name = clean_url_or_text(prize_name)
    prize_name = re.sub(r'[\s　]+', ' ', prize_name)

    # --- スペック抽出 ---
    fig_size_match = re.search(r'【Figure size】?\s*([^\n\r【🔶🟨]+)', text, re.IGNORECASE)
    if fig_size_match:
        fig_size = clean_url_or_text(fig_size_match.group(1).rstrip('】'))

    box_weight_match = re.search(r'【Box weight】?\s*([^\n\r【🔶🟨]+)', text, re.IGNORECASE) or re.search(r'重量[：:]\s*([^\n\r]+)', text)
    if box_weight_match:
        box_weight = clean_url_or_text(box_weight_match.group(1).rstrip('】'))

    box_size_match = re.search(r'【Box size】?\s*([^\n\r【🔶🟨]+)', text, re.IGNORECASE)
    if box_size_match:
        box_size = clean_url_or_text(box_size_match.group(1).rstrip('】'))

    # --- 重心情報の抽出 ---
    # 1. 🟨 行（Merry✩An）
    for line in lines:
        if line.startswith('🟨'):
            c = clean_url_or_text(line.replace('🟨', '').strip())
            if c and c not in gravity_details:
                gravity_details.append(c)

    # 2. 831生活スタイル（【獲得個体の重心情報】の後、または「・裏面側が重い」等）
    in_831_section = False
    for line in lines:
        if '【獲得個体の重心情報】' in line or '重心情報' in line:
            in_831_section = True
            continue
        if in_831_section:
            if line.startswith('・') or line.startswith('-') or '重い' in line or '重心' in line:
                c = clean_url_or_text(line.lstrip('・- ').strip())
                if c and c not in gravity_details and not c.startswith('http'):
                    gravity_details.append(c)

    # 3. あかりスタイル（重心情報: の後の行）
    for i, line in enumerate(lines):
        if '重心情報:' in line or '重心情報：' in line:
            # 同じ行にある場合
            part = line.split(':', 1)[-1].split('：', 1)[-1].strip()
            if part:
                c = clean_url_or_text(part)
                if c and c not in gravity_details:
                    gravity_details.append(c)
            # 次の行にある場合
            elif i + 1 < len(lines):
                c = clean_url_or_text(lines[i+1])
                if c and c not in gravity_details and not c.startswith('http'):
                    gravity_details.append(c)

    # 4. もぐらクレーンスタイル / その他（表下右、裏上右 等の記述）
    for line in lines:
        if any(w in line for w in ['重心', '側重', '裏面', '表面', '上側', '下側', '頭側', '足側']):
            if not line.startswith('🔶') and not line.startswith('＃') and not line.startswith('#') and '【獲得' not in line:
                c = clean_url_or_text(line.lstrip('・- ').strip())
                if c and c not in gravity_details and len(c) <= 60 and not c.startswith('http'):
                    gravity_details.append(c)

    # 5. 内部挙動・個体差 (🔶 行、または備考)
    for line in lines:
        if line.startswith('🔶'):
            c = clean_url_or_text(line.replace('🔶', '').strip())
            if c:
                condition_details.append(c)
        elif '個体差' in line or '動く' in line or 'ブリスター' in line:
            if not line.startswith('🟨') and not line.startswith('#') and not line.startswith('＃'):
                c = clean_url_or_text(line.lstrip('・- ※').strip())
                if c and c not in condition_details and len(c) <= 80 and not c.startswith('http'):
                    condition_details.append(c)

    # --- タグの自動分類 ---
    all_text = ' '.join(gravity_details + condition_details + lines)
    if '上' in all_text or '頭' in all_text:
        tags.add('上重心')
    if '下' in all_text or '足' in all_text:
        tags.add('下重心')
    if '裏' in all_text:
        tags.add('裏重心')
    if '表' in all_text:
        tags.add('表重心')
    if '左' in all_text:
        tags.add('左重心')
    if '右' in all_text:
        tags.add('右重心')
    if any(k in all_text for k in ['中', '真ん中', 'センター']):
        tags.add('中央重心')
    if 'ブリスター' in all_text:
        tags.add('ブリスター')
    if any(k in all_text for k in ['動かない', 'ほぼ動かない', '固定']):
        tags.add('固定・動かない')
    if any(k in all_text for k in ['動く', '可動', '全方位動く']) and '動かない' not in all_text:
        tags.add('内部可動あり')
    if '個体差' in all_text:
        tags.add('個体差あり')

    return {
        'prize_name': prize_name,
        'figure_size': fig_size,
        'box_weight': box_weight,
        'box_size': box_size,
        'gravity_details': gravity_details,
        'condition_details': condition_details,
        'tags': sorted(list(tags))
    }

def fetch_single_tweet(tid):
    """単一ツイートのデータを取得"""
    try:
        url = f"https://crane-lab.com/api/tweet/{tid}"
        r = requests.get(url, timeout=6)
        if r.status_code == 200:
            data = r.json()
            if isinstance(data, dict) and data.get('data'):
                return tid, data.get('data')
    except Exception:
        pass
    
    try:
        s_url = f"https://cdn.syndication.twimg.com/tweet-result?id={tid}&token=x"
        r = requests.get(s_url, timeout=6)
        if r.status_code == 200:
            data = r.json()
            if isinstance(data, dict) and data.get('text'):
                return tid, data
    except Exception:
        pass
        
    return tid, None

def collect_data(limit_records=3000, target_year="2026"):
    """指定アカウントの2026年分重心情報を収集"""
    anon_key = get_supabase_key()
    headers = {
        "apikey": anon_key,
        "Authorization": f"Bearer {anon_key}",
        "Content-Type": "application/json"
    }
    
    anime_map = fetch_anime_titles(headers)
    cog_records = fetch_all_cog_records(headers, limit_total=limit_records)
    
    # 既存キャッシュの読み込み
    existing_items = {}
    if os.path.exists(DATA_JSON_PATH):
        try:
            with open(DATA_JSON_PATH, "r", encoding="utf-8") as f:
                old_list = json.load(f)
                for item in old_list:
                    # 2026年分のみ保持
                    c_date = str(item.get('created_at', ''))
                    if not target_year or c_date.startswith(target_year):
                        existing_items[item['tweet_id']] = item
            print(f"既存キャッシュから {len(existing_items)} 件（{target_year}年分）をロードしました。")
        except Exception as e:
            print(f"Warning loading cache: {e}")

    # 重複なしツイートID
    unique_items = []
    seen_ids = set()
    for rec in cog_records:
        tid = str(rec.get('tweet_id', '')).strip()
        if tid and tid not in seen_ids:
            seen_ids.add(tid)
            unique_items.append(rec)
            
    print(f"チェック対象のユニークツイート数: {len(unique_items)} 件")
    
    to_fetch = [item for item in unique_items if item['tweet_id'] not in existing_items]
    print(f"新規取得が必要なツイート数: {len(to_fetch)} 件")
    
    new_count = 0
    if to_fetch:
        print("ツイート詳細を並行ダウンロード中 (15スレッド)...")
        with ThreadPoolExecutor(max_workers=15) as executor:
            future_to_item = {executor.submit(fetch_single_tweet, item['tweet_id']): item for item in to_fetch}
            completed = 0
            for future in as_completed(future_to_item):
                completed += 1
                if completed % 100 == 0 or completed == len(to_fetch):
                    print(f"-> 進行状況: {completed}/{len(to_fetch)} 完了")
                
                item = future_to_item[future]
                tid, tweet_data = future.result()
                if not tweet_data:
                    continue
                
                user = tweet_data.get('user') or {}
                screen_name = user.get('screen_name', '')
                user_name = user.get('name', '')
                
                # 投稿者の識別（Merry✩An、831生活、あかり、もぐらクレーン）
                author_display_name = identify_author(user_name, screen_name)
                if not author_display_name:
                    continue
                
                # 投稿日時のパース
                raw_created_at = tweet_data.get('created_at', '')
                formatted_date = raw_created_at
                try:
                    if 'T' in raw_created_at:
                        dt = datetime.fromisoformat(raw_created_at.replace('Z', '+00:00'))
                        formatted_date = dt.strftime('%Y-%m-%d %H:%M')
                    else:
                        dt = datetime.strptime(raw_created_at, '%a %b %d %H:%M:%S +0000 %Y')
                        formatted_date = dt.strftime('%Y-%m-%d %H:%M')
                except Exception:
                    pass

                # 2026年限定フィルター
                if target_year and not formatted_date.startswith(target_year):
                    continue

                anime_info = anime_map.get(item.get('anime_title_id'), {})
                anime_title = anime_info.get('title', '')
                text = tweet_data.get('text', '')
                
                parsed = parse_tweet_content(text, author_display_name, anime_title)
                
                # 画像URL
                media_list = []
                media_details = tweet_data.get('mediaDetails') or tweet_data.get('entities', {}).get('media', [])
                for m in media_details:
                    if isinstance(m, dict):
                        m_url = m.get('media_url_https') or m.get('url')
                        if m_url and m_url not in media_list:
                            media_list.append(m_url)

                entry = {
                    'id': item.get('id'),
                    'tweet_id': tid,
                    'author_name': author_display_name,
                    'user_name': user_name,
                    'screen_name': screen_name,
                    'anime_title': anime_title or "その他",
                    'prize_name': parsed.get('prize_name', ''),
                    'figure_size': parsed.get('figure_size', ''),
                    'box_weight': parsed.get('box_weight', ''),
                    'box_size': parsed.get('box_size', ''),
                    'gravity_details': parsed.get('gravity_details', []),
                    'condition_details': parsed.get('condition_details', []),
                    'tags': parsed.get('tags', []),
                    'media': media_list,
                    'created_at': formatted_date,
                    'tweet_url': f"https://x.com/{screen_name}/status/{tid}",
                    'full_text': text
                }
                existing_items[tid] = entry
                new_count += 1

    # 既存データの再パースと年フィルタリング
    final_dict = {}
    for tid, item in existing_items.items():
        c_date = str(item.get('created_at', ''))
        if target_year and not c_date.startswith(target_year):
            continue
        
        # 投稿者名の確定
        auth_name = item.get('author_name') or identify_author(item.get('user_name', ''), item.get('screen_name', '')) or item.get('user_name', '')
        item['author_name'] = auth_name
        
        # 最新パーサー適用
        parsed = parse_tweet_content(item.get('full_text', ''), auth_name, item.get('anime_title', ''))
        item['prize_name'] = parsed.get('prize_name', item.get('prize_name', ''))
        item['figure_size'] = parsed.get('figure_size', item.get('figure_size', ''))
        item['box_weight'] = parsed.get('box_weight', item.get('box_weight', ''))
        item['box_size'] = parsed.get('box_size', item.get('box_size', ''))
        item['gravity_details'] = parsed.get('gravity_details', [])
        item['condition_details'] = parsed.get('condition_details', [])
        item['tags'] = parsed.get('tags', [])
        final_dict[tid] = item

    print(f"収集完了: 新規 {new_count} 件を追加、2026年分合計 {len(final_dict)} 件の重心情報を保持。")
    
    final_list = list(final_dict.values())
    final_list.sort(key=lambda x: str(x.get('created_at', '')), reverse=True)
    
    with open(DATA_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(final_list, f, ensure_ascii=False, indent=2)
    print(f"データを保存しました: {DATA_JSON_PATH}")
    
    return final_list

def generate_html(gravity_items):
    """ライトモードに準拠した高機能・美麗なHTMLビューアを生成"""
    print("HTMLビューアを生成中...")
    
    total_count = len(gravity_items)
    anime_titles = sorted(list({item.get('anime_title', 'その他') for item in gravity_items if item.get('anime_title')}))
    updated_time = datetime.now().strftime('%Y年%m月%d日 %H:%M')
    
    items_json_str = json.dumps(gravity_items, ensure_ascii=False)

    html_content = f"""<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>プライズフィギュア 重心情報データベース (2026年版)</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;600;700;800&family=Noto+Sans+JP:wght@400;500;700;900&display=swap" rel="stylesheet">
  <style>
    :root {{
      --bg-main: #f8fafc;
      --bg-surface: #ffffff;
      --bg-subtle: #f1f5f9;
      --border-color: #e2e8f0;
      --border-light: #f1f5f9;
      --text-main: #0f172a;
      --text-muted: #64748b;
      --text-sub: #475569;
      
      --brand-primary: #f59e0b;
      --brand-dark: #d97706;
      --brand-light: #fef3c7;
      --accent-orange: #ea580c;
      --accent-blue: #0284c7;
      --accent-blue-light: #e0f2fe;
      
      --shadow-sm: 0 1px 3px 0 rgba(0, 0, 0, 0.05);
      --shadow-md: 0 4px 6px -1px rgba(0, 0, 0, 0.07), 0 2px 4px -2px rgba(0, 0, 0, 0.05);
      --shadow-lg: 0 10px 25px -5px rgba(0, 0, 0, 0.08), 0 8px 10px -6px rgba(0, 0, 0, 0.04);
      --radius-sm: 8px;
      --radius-md: 14px;
      --radius-lg: 20px;
    }}

    * {{
      box-sizing: border-box;
      margin: 0;
      padding: 0;
    }}

    body {{
      font-family: 'Plus Jakarta Sans', 'Noto Sans JP', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      background-color: var(--bg-main);
      color: var(--text-main);
      line-height: 1.6;
      -webkit-font-smoothing: antialiased;
      padding-bottom: 60px;
    }}

    /* Header */
    header {{
      background: var(--bg-surface);
      border-bottom: 1px solid var(--border-color);
      position: sticky;
      top: 0;
      z-index: 50;
      box-shadow: var(--shadow-sm);
    }}

    .header-inner {{
      max-width: 1360px;
      margin: 0 auto;
      padding: 14px 24px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
      flex-wrap: wrap;
    }}

    .header-left {{
      display: flex;
      align-items: center;
      gap: 16px;
      flex-wrap: wrap;
    }}

    .logo-area {{
      display: flex;
      align-items: center;
      gap: 14px;
      text-decoration: none;
      color: var(--text-main);
    }}

    .logo-icon {{
      width: 44px;
      height: 44px;
      background: linear-gradient(135deg, #f59e0b 0%, #ea580c 100%);
      border-radius: 12px;
      display: flex;
      align-items: center;
      justify-content: center;
      color: white;
      font-weight: 900;
      font-size: 22px;
      box-shadow: 0 4px 12px rgba(245, 158, 11, 0.35);
    }}

    .logo-title h1 {{
      font-size: 19px;
      font-weight: 800;
      letter-spacing: -0.02em;
      color: var(--text-main);
      display: flex;
      align-items: center;
      gap: 8px;
    }}

    .logo-title p {{
      font-size: 12px;
      color: var(--text-muted);
      font-weight: 600;
      display: flex;
      align-items: center;
      gap: 6px;
      flex-wrap: wrap;
    }}

    .badge-author-link {{
      color: #0284c7;
      text-decoration: none;
      font-weight: 700;
    }}
    .badge-author-link:hover {{
      text-decoration: underline;
    }}

    .header-nav-links {{
      display: flex;
      align-items: center;
      gap: 10px;
    }}

    .nav-link-btn {{
      display: inline-flex;
      align-items: center;
      gap: 6px;
      background: linear-gradient(135deg, #e63946 0%, #c1121f 100%);
      color: #ffffff !important;
      padding: 7px 15px;
      border-radius: 999px;
      font-size: 13px;
      font-weight: 700;
      text-decoration: none;
      box-shadow: 0 2px 8px rgba(230, 57, 70, 0.25);
      transition: all 0.2s ease;
    }}
    .nav-link-btn:hover {{
      transform: translateY(-1px);
      box-shadow: 0 4px 12px rgba(230, 57, 70, 0.35);
      filter: brightness(1.05);
    }}

    .header-stats {{
      display: flex;
      gap: 12px;
      font-size: 13px;
      color: var(--text-sub);
    }}

    .stat-pill {{
      background: var(--bg-subtle);
      padding: 6px 14px;
      border-radius: 999px;
      border: 1px solid var(--border-color);
      font-weight: 600;
    }}
    .stat-pill b {{
      color: var(--accent-orange);
      font-weight: 800;
    }}

    /* Main Container */
    .container {{
      max-width: 1360px;
      margin: 24px auto;
      padding: 0 24px;
    }}

    /* Controls Panel */
    .controls-panel {{
      background: var(--bg-surface);
      border: 1px solid var(--border-color);
      border-radius: var(--radius-lg);
      padding: 20px;
      margin-bottom: 24px;
      box-shadow: var(--shadow-sm);
      display: flex;
      flex-direction: column;
      gap: 14px;
    }}

    .search-row {{
      display: flex;
      gap: 12px;
      flex-wrap: wrap;
    }}

    .search-input-wrapper {{
      flex: 1;
      min-width: 280px;
      position: relative;
    }}

    .search-icon {{
      position: absolute;
      left: 14px;
      top: 50%;
      transform: translateY(-50%);
      color: var(--text-muted);
      width: 18px;
      height: 18px;
    }}

    .search-input {{
      width: 100%;
      padding: 12px 16px 12px 42px;
      border-radius: var(--radius-md);
      border: 1.5px solid var(--border-color);
      font-size: 14.5px;
      font-family: inherit;
      outline: none;
      transition: all 0.2s ease;
      background: #fafafa;
    }}
    .search-input:focus {{
      border-color: var(--brand-primary);
      background: #ffffff;
      box-shadow: 0 0 0 3px rgba(245, 158, 11, 0.15);
    }}

    .select-wrapper {{
      min-width: 200px;
    }}

    .custom-select {{
      width: 100%;
      padding: 12px 16px;
      border-radius: var(--radius-md);
      border: 1.5px solid var(--border-color);
      font-size: 14px;
      font-family: inherit;
      background-color: #fafafa;
      color: var(--text-main);
      font-weight: 600;
      outline: none;
      cursor: pointer;
      transition: all 0.2s ease;
    }}
    .custom-select:focus {{
      border-color: var(--brand-primary);
      background-color: #ffffff;
    }}

    /* Filter Chips */
    .filter-chips-section {{
      display: flex;
      flex-direction: column;
      gap: 8px;
      padding-top: 8px;
      border-top: 1px solid var(--border-light);
    }}

    .filter-chips-row {{
      display: flex;
      align-items: center;
      gap: 8px;
      flex-wrap: wrap;
    }}

    .filter-label {{
      font-size: 12px;
      font-weight: 700;
      color: var(--text-muted);
      min-width: 60px;
    }}

    .chip-btn {{
      background: var(--bg-subtle);
      border: 1px solid var(--border-color);
      color: var(--text-sub);
      padding: 5px 12px;
      border-radius: 999px;
      font-size: 12px;
      font-weight: 600;
      cursor: pointer;
      transition: all 0.15s ease;
      font-family: inherit;
    }}
    .chip-btn:hover {{
      background: #e2e8f0;
      color: var(--text-main);
    }}
    .chip-btn.active {{
      background: #0f172a;
      color: #ffffff;
      border-color: #0f172a;
      box-shadow: 0 2px 6px rgba(15, 23, 42, 0.2);
    }}

    .chip-btn.author-chip.active {{
      background: #0284c7;
      border-color: #0284c7;
      color: #ffffff;
    }}

    /* Result Info */
    .result-info-bar {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-bottom: 18px;
      font-size: 13.5px;
      color: var(--text-sub);
      font-weight: 600;
    }}

    /* Grid Layout */
    .cards-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
      gap: 22px;
    }}

    /* Prize Card */
    .prize-card {{
      background: var(--bg-surface);
      border: 1px solid var(--border-color);
      border-radius: var(--radius-lg);
      overflow: hidden;
      box-shadow: var(--shadow-sm);
      transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1);
      display: flex;
      flex-direction: column;
      position: relative;
    }}
    .prize-card:hover {{
      transform: translateY(-4px);
      box-shadow: var(--shadow-lg);
      border-color: #cbd5e1;
    }}

    /* Card Media */
    .card-media {{
      position: relative;
      width: 100%;
      height: 240px;
      background: #ffffff;
      border-bottom: 1px solid var(--border-color);
      overflow: hidden;
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 6px;
    }}
    .card-media img {{
      width: 100%;
      height: 100%;
      object-fit: contain;
      transition: transform 0.3s ease;
    }}
    .prize-card:hover .card-media img {{
      transform: scale(1.03);
    }}

    .media-count-badge {{
      position: absolute;
      bottom: 10px;
      right: 10px;
      background: rgba(15, 23, 42, 0.75);
      backdrop-filter: blur(4px);
      color: white;
      font-size: 11px;
      font-weight: 700;
      padding: 3px 8px;
      border-radius: 6px;
    }}

    .author-badge-on-card {{
      position: absolute;
      top: 10px;
      left: 10px;
      background: rgba(15, 23, 42, 0.82);
      backdrop-filter: blur(4px);
      color: #ffffff;
      font-size: 10.5px;
      font-weight: 800;
      padding: 3px 9px;
      border-radius: 6px;
      box-shadow: 0 2px 6px rgba(0,0,0,0.15);
    }}

    .no-image-placeholder {{
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      height: 100%;
      color: #94a3b8;
      font-size: 13px;
      font-weight: 600;
      gap: 6px;
    }}

    /* Card Content */
    .card-body {{
      padding: 18px;
      display: flex;
      flex-direction: column;
      flex: 1;
      gap: 12px;
    }}

    .card-meta {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 8px;
    }}

    .anime-badge {{
      background: #fef3c7;
      color: #b45309;
      font-size: 11.5px;
      font-weight: 800;
      padding: 3px 9px;
      border-radius: 6px;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
      max-width: 70%;
    }}

    .post-date {{
      font-size: 11.5px;
      color: var(--text-muted);
      font-weight: 500;
    }}

    .prize-title {{
      font-size: 15.5px;
      font-weight: 800;
      color: var(--text-main);
      line-height: 1.4;
      display: -webkit-box;
      -webkit-line-clamp: 2;
      -webkit-box-orient: vertical;
      overflow: hidden;
      min-height: 43px;
    }}

    /* Gravity Badges */
    .gravity-box {{
      background: #fffbeb;
      border: 1px solid #fef3c7;
      border-radius: var(--radius-sm);
      padding: 10px 12px;
    }}

    .gravity-title {{
      font-size: 11px;
      font-weight: 800;
      color: #d97706;
      text-transform: uppercase;
      letter-spacing: 0.04em;
      margin-bottom: 6px;
      display: flex;
      align-items: center;
      gap: 4px;
    }}

    .gravity-tags {{
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
    }}

    .gravity-pill {{
      background: #ffffff;
      color: #92400e;
      border: 1px solid #fde68a;
      font-size: 12px;
      font-weight: 700;
      padding: 3px 8px;
      border-radius: 6px;
    }}

    /* Specs List */
    .specs-grid {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 6px 12px;
      background: var(--bg-subtle);
      padding: 10px 12px;
      border-radius: var(--radius-sm);
      font-size: 11.5px;
    }}

    .spec-item {{
      display: flex;
      flex-direction: column;
    }}
    .spec-label {{
      color: var(--text-muted);
      font-weight: 600;
      font-size: 10.5px;
    }}
    .spec-value {{
      color: var(--text-main);
      font-weight: 700;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }}

    .movement-note {{
      font-size: 12px;
      color: var(--text-sub);
      background: #f8fafc;
      border-left: 3px solid #f59e0b;
      padding: 6px 10px;
      border-radius: 0 6px 6px 0;
      line-height: 1.45;
    }}

    /* Card Footer */
    .card-footer {{
      margin-top: auto;
      padding-top: 10px;
      border-top: 1px solid var(--border-light);
      display: flex;
      align-items: center;
      justify-content: space-between;
    }}

    .x-link-btn {{
      display: inline-flex;
      align-items: center;
      gap: 6px;
      font-size: 12px;
      font-weight: 700;
      color: #0284c7;
      text-decoration: none;
      transition: color 0.15s ease;
    }}
    .x-link-btn:hover {{
      color: #0369a1;
      text-decoration: underline;
    }}

    .detail-modal-btn {{
      background: none;
      border: none;
      color: var(--text-sub);
      font-size: 12px;
      font-weight: 600;
      cursor: pointer;
      padding: 4px 8px;
      border-radius: 6px;
      transition: background 0.15s ease;
    }}
    .detail-modal-btn:hover {{
      background: var(--bg-subtle);
      color: var(--text-main);
    }}

    /* Modal */
    .modal-overlay {{
      position: fixed;
      top: 0;
      left: 0;
      right: 0;
      bottom: 0;
      background: rgba(15, 23, 42, 0.6);
      backdrop-filter: blur(4px);
      display: none;
      align-items: center;
      justify-content: center;
      z-index: 100;
      padding: 20px;
    }}
    .modal-overlay.open {{
      display: flex;
    }}

    .modal-content {{
      background: var(--bg-surface);
      border-radius: var(--radius-lg);
      max-width: 760px;
      width: 100%;
      max-height: 90vh;
      overflow-y: auto;
      box-shadow: var(--shadow-lg);
      position: relative;
      display: flex;
      flex-direction: column;
    }}

    .modal-header {{
      padding: 20px 24px;
      border-bottom: 1px solid var(--border-color);
      display: flex;
      align-items: flex-start;
      justify-content: space-between;
      gap: 16px;
      position: sticky;
      top: 0;
      background: var(--bg-surface);
      z-index: 10;
    }}

    .modal-close-btn {{
      background: var(--bg-subtle);
      border: none;
      width: 34px;
      height: 34px;
      border-radius: 50%;
      font-size: 18px;
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      color: var(--text-muted);
      transition: all 0.15s ease;
    }}
    .modal-close-btn:hover {{
      background: #e2e8f0;
      color: var(--text-main);
    }}

    .modal-body {{
      padding: 24px;
      display: flex;
      flex-direction: column;
      gap: 20px;
    }}

    .modal-gallery {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
      gap: 12px;
    }}
    .modal-gallery img {{
      width: 100%;
      border-radius: var(--radius-sm);
      border: 1px solid var(--border-color);
      cursor: pointer;
      transition: transform 0.2s ease;
    }}
    .modal-gallery img:hover {{
      transform: scale(1.02);
    }}

    .modal-raw-text {{
      background: var(--bg-subtle);
      padding: 16px;
      border-radius: var(--radius-sm);
      font-size: 13px;
      white-space: pre-wrap;
      word-break: break-word;
      line-height: 1.6;
      border: 1px solid var(--border-color);
    }}

    /* Empty state */
    .empty-state {{
      text-align: center;
      padding: 60px 20px;
      background: var(--bg-surface);
      border-radius: var(--radius-lg);
      border: 1px dashed var(--border-color);
      grid-column: 1 / -1;
    }}

    @media (max-width: 768px) {{
      .header-inner {{
        flex-direction: column;
        align-items: flex-start;
      }}
      .header-stats {{
        width: 100%;
        justify-content: space-between;
      }}
      .search-row {{
        flex-direction: column;
      }}
      .select-wrapper {{
        width: 100%;
      }}
    }}
  </style>
</head>
<body>

  <!-- Header -->
  <header>
    <div class="header-inner">
      <div class="header-left">
        <div class="logo-area">
          <div class="logo-icon">⚖</div>
          <div class="logo-title">
            <h1>プライズフィギュア 重心データベース (2026年)</h1>
            <p>
              情報源：
              <a href="https://x.com/6eS8Jm4YNJpPA2D" target="_blank" rel="noopener noreferrer" class="badge-author-link">Merry✩An</a>・
              <a href="https://x.com/831suky" target="_blank" rel="noopener noreferrer" class="badge-author-link">831生活</a>・
              <a href="https://x.com/yohane150" target="_blank" rel="noopener noreferrer" class="badge-author-link">あかり</a>・
              <a href="https://x.com/mogurakurenn" target="_blank" rel="noopener noreferrer" class="badge-author-link">もぐらクレーン</a>
            </p>
          </div>
        </div>
        <div class="header-nav-links">
          <a href="index.html" class="nav-link-btn">
            📅 入荷カレンダー・横断検索 ↗
          </a>
        </div>
      </div>
      <div class="header-stats">
        <div class="stat-pill">2026年収録: <b id="totalItemsCount">{total_count}</b> 件</div>
        <div class="stat-pill">更新: <b>{updated_time}</b></div>
      </div>
    </div>
  </header>

  <!-- Main Container -->
  <main class="container">

    <!-- Controls Panel -->
    <div class="controls-panel">
      <div class="search-row">
        <div class="search-input-wrapper">
          <svg class="search-icon" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" d="m21 21-5.197-5.197m0 0A7.5 7.5 0 1 0 5.196 5.196a7.5 7.5 0 0 0 10.607 10.607Z" />
          </svg>
          <input type="text" id="searchInput" class="search-input" placeholder="景品名、作品名、重心（上/下/裏/表/動かない等）で検索...">
        </div>

        <div class="select-wrapper">
          <select id="animeSelect" class="custom-select">
            <option value="">すべての作品 ({len(anime_titles)}作品)</option>
            {''.join([f'<option value="{title}">{title}</option>' for title in anime_titles])}
          </select>
        </div>

        <div class="select-wrapper" style="max-width: 160px;">
          <select id="sortSelect" class="custom-select">
            <option value="newest">新着順</option>
            <option value="oldest">古い順</option>
            <option value="title">景品名順</option>
            <option value="anime">作品名順</option>
          </select>
        </div>
      </div>

      <!-- Filters Section -->
      <div class="filter-chips-section">
        <!-- Author filter -->
        <div class="filter-chips-row">
          <span class="filter-label">👤 投稿者:</span>
          <button class="chip-btn author-chip active" data-author="all">全員</button>
          <button class="chip-btn author-chip" data-author="Merry☆An">Merry☆An</button>
          <button class="chip-btn author-chip" data-author="831生活">831生活</button>
          <button class="chip-btn author-chip" data-author="あかり">あかり</button>
          <button class="chip-btn author-chip" data-author="もぐらクレーン">もぐらクレーン</button>
        </div>

        <!-- Gravity tags filter -->
        <div class="filter-chips-row">
          <span class="filter-label">⚖ 重心:</span>
          <button class="chip-btn grav-chip active" data-filter="all">すべて</button>
          <button class="chip-btn grav-chip" data-filter="上重心">上重心</button>
          <button class="chip-btn grav-chip" data-filter="下重心">下重心</button>
          <button class="chip-btn grav-chip" data-filter="裏重心">裏重心</button>
          <button class="chip-btn grav-chip" data-filter="表重心">表重心</button>
          <button class="chip-btn grav-chip" data-filter="左重心">左重心</button>
          <button class="chip-btn grav-chip" data-filter="右重心">右重心</button>
          <button class="chip-btn grav-chip" data-filter="ブリスター">ブリスター</button>
          <button class="chip-btn grav-chip" data-filter="固定・動かない">動かない(固定)</button>
          <button class="chip-btn grav-chip" data-filter="個体差あり">個体差注意</button>
        </div>
      </div>
    </div>

    <!-- Result info bar -->
    <div class="result-info-bar">
      <div>表示中: <span id="filteredCount" style="color: var(--text-main); font-weight: 800;">{total_count}</span> 件</div>
    </div>

    <!-- Cards Grid -->
    <div id="cardsGrid" class="cards-grid"></div>

  </main>

  <!-- Detail Modal -->
  <div id="detailModal" class="modal-overlay">
    <div class="modal-content">
      <div class="modal-header">
        <div>
          <span id="modalAuthorBadge" style="font-size: 11px; font-weight: 800; background: #e0f2fe; color: #0369a1; padding: 2px 8px; border-radius: 4px; margin-right: 6px;">投稿者</span>
          <span id="modalAnimeBadge" class="anime-badge">作品名</span>
          <h2 id="modalPrizeTitle" style="font-size: 18px; font-weight: 800; margin-top: 6px; color: var(--text-main);">景品名</h2>
        </div>
        <button id="modalCloseBtn" class="modal-close-btn">&times;</button>
      </div>
      <div class="modal-body">
        <div id="modalGallery" class="modal-gallery"></div>
        
        <div id="modalGravitySection" class="gravity-box">
          <div class="gravity-title">⚖ 重心測定データ</div>
          <div id="modalGravityTags" class="gravity-tags"></div>
        </div>

        <div class="specs-grid">
          <div class="spec-item">
            <span class="spec-label">フィギュアサイズ</span>
            <span id="modalFigSize" class="spec-value">-</span>
          </div>
          <div class="spec-item">
            <span class="spec-label">箱の重さ</span>
            <span id="modalBoxWeight" class="spec-value">-</span>
          </div>
          <div class="spec-item">
            <span class="spec-label">箱のサイズ</span>
            <span id="modalBoxSize" class="spec-value">-</span>
          </div>
          <div class="spec-item">
            <span class="spec-label">投稿日時</span>
            <span id="modalDate" class="spec-value">-</span>
          </div>
        </div>

        <div>
          <div style="font-size: 12px; font-weight: 700; color: var(--text-muted); margin-bottom: 6px;">ツイート本文</div>
          <div id="modalRawText" class="modal-raw-text"></div>
        </div>

        <div style="text-align: right;">
          <a id="modalXLink" href="#" target="_blank" rel="noopener noreferrer" class="x-link-btn" style="font-size: 13.5px; padding: 8px 16px; background: #f0f9ff; border: 1px solid #bae6fd; border-radius: 8px;">
            X（旧Twitter）でポストを見る ↗
          </a>
        </div>
      </div>
    </div>
  </div>

  <!-- Image Lightbox Modal -->
  <div id="imageLightbox" class="modal-overlay" style="background: rgba(0,0,0,0.85);">
    <div style="position: relative; max-width: 90vw; max-height: 90vh;">
      <button id="lightboxCloseBtn" class="modal-close-btn" style="position: absolute; top: -45px; right: 0; color: white; background: rgba(255,255,255,0.2);">&times;</button>
      <img id="lightboxImg" src="" alt="" style="max-width: 100%; max-height: 85vh; border-radius: 8px; object-fit: contain; box-shadow: 0 20px 40px rgba(0,0,0,0.5);">
    </div>
  </div>

  <script>
    const PRIZE_DATA = {items_json_str};

    let currentFilter = 'all';
    let currentAuthor = 'all';
    let currentAnime = '';
    let currentSearch = '';
    let currentSort = 'newest';

    const cardsGrid = document.getElementById('cardsGrid');
    const searchInput = document.getElementById('searchInput');
    const animeSelect = document.getElementById('animeSelect');
    const sortSelect = document.getElementById('sortSelect');
    const filteredCount = document.getElementById('filteredCount');
    
    const authorChips = document.querySelectorAll('.author-chip');
    const gravChips = document.querySelectorAll('.grav-chip');

    // Detail Modal Elements
    const detailModal = document.getElementById('detailModal');
    const modalCloseBtn = document.getElementById('modalCloseBtn');
    const modalAuthorBadge = document.getElementById('modalAuthorBadge');
    const modalAnimeBadge = document.getElementById('modalAnimeBadge');
    const modalPrizeTitle = document.getElementById('modalPrizeTitle');
    const modalGallery = document.getElementById('modalGallery');
    const modalGravityTags = document.getElementById('modalGravityTags');
    const modalFigSize = document.getElementById('modalFigSize');
    const modalBoxWeight = document.getElementById('modalBoxWeight');
    const modalBoxSize = document.getElementById('modalBoxSize');
    const modalDate = document.getElementById('modalDate');
    const modalRawText = document.getElementById('modalRawText');
    const modalXLink = document.getElementById('modalXLink');

    // Lightbox
    const imageLightbox = document.getElementById('imageLightbox');
    const lightboxImg = document.getElementById('lightboxImg');
    const lightboxCloseBtn = document.getElementById('lightboxCloseBtn');

    function openLightbox(url) {{
      lightboxImg.src = url;
      imageLightbox.classList.add('open');
    }}

    lightboxCloseBtn.addEventListener('click', () => imageLightbox.classList.remove('open'));
    imageLightbox.addEventListener('click', (e) => {{
      if (e.target === imageLightbox) imageLightbox.classList.remove('open');
    }});

    function openModal(item) {{
      modalAuthorBadge.textContent = item.author_name || item.user_name || '有志';
      modalAnimeBadge.textContent = item.anime_title || 'その他';
      modalPrizeTitle.textContent = item.prize_name;
      modalFigSize.textContent = item.figure_size || '記載なし';
      modalBoxWeight.textContent = item.box_weight || '記載なし';
      modalBoxSize.textContent = item.box_size || '記載なし';
      modalDate.textContent = item.created_at || '-';
      modalRawText.textContent = item.full_text || '';
      modalXLink.href = item.tweet_url;

      modalGravityTags.innerHTML = '';
      if (item.gravity_details && item.gravity_details.length > 0) {{
        item.gravity_details.forEach(g => {{
          const span = document.createElement('span');
          span.className = 'gravity-pill';
          span.textContent = g;
          modalGravityTags.appendChild(span);
        }});
      }} else {{
        modalGravityTags.innerHTML = '<span style="font-size:12px; color:var(--text-muted);">個別重心数値記載なし (本文参照)</span>';
      }}

      modalGallery.innerHTML = '';
      if (item.media && item.media.length > 0) {{
        item.media.forEach(m => {{
          const img = document.createElement('img');
          img.src = m;
          img.loading = 'lazy';
          img.addEventListener('click', () => openLightbox(m));
          modalGallery.appendChild(img);
        }});
      }}

      detailModal.classList.add('open');
    }}

    modalCloseBtn.addEventListener('click', () => detailModal.classList.remove('open'));
    detailModal.addEventListener('click', (e) => {{
      if (e.target === detailModal) detailModal.classList.remove('open');
    }});

    function filterAndRender() {{
      const query = currentSearch.toLowerCase().trim();

      let filtered = PRIZE_DATA.filter(item => {{
        // Author Filter
        if (currentAuthor !== 'all') {{
          const aName = (item.author_name || item.user_name || '');
          if (!aName.includes(currentAuthor)) return false;
        }}

        // Anime Filter
        if (currentAnime && item.anime_title !== currentAnime) {{
          return false;
        }}

        // Gravity Chip Filter
        if (currentFilter !== 'all') {{
          const tags = item.tags || [];
          const gravDetails = (item.gravity_details || []).join(' ');
          const condDetails = (item.condition_details || []).join(' ');
          const full = (item.full_text || '');
          
          const matchTag = tags.includes(currentFilter);
          const matchText = gravDetails.includes(currentFilter.replace('重心', '')) || 
                            condDetails.includes(currentFilter) ||
                            full.includes(currentFilter);
          if (!matchTag && !matchText) return false;
        }}

        // Text Search
        if (query) {{
          const searchCorpus = [
            item.prize_name,
            item.anime_title,
            item.author_name,
            item.figure_size,
            item.box_weight,
            item.box_size,
            (item.gravity_details || []).join(' '),
            (item.condition_details || []).join(' '),
            item.full_text
          ].join(' ').toLowerCase();

          if (!searchCorpus.includes(query)) return false;
        }}

        return true;
      }});

      // Sorting
      if (currentSort === 'newest') {{
        filtered.sort((a, b) => String(b.created_at).localeCompare(String(a.created_at)));
      }} else if (currentSort === 'oldest') {{
        filtered.sort((a, b) => String(a.created_at).localeCompare(String(b.created_at)));
      }} else if (currentSort === 'title') {{
        filtered.sort((a, b) => a.prize_name.localeCompare(b.prize_name, 'ja'));
      }} else if (currentSort === 'anime') {{
        filtered.sort((a, b) => a.anime_title.localeCompare(b.anime_title, 'ja'));
      }}

      filteredCount.textContent = filtered.length;
      renderCards(filtered);
    }}

    function renderCards(items) {{
      if (items.length === 0) {{
        cardsGrid.innerHTML = `
          <div class="empty-state">
            <h3 style="font-size:16px; font-weight:700; color:var(--text-main); margin-bottom:6px;">条件に一致する景品が見つかりませんでした</h3>
            <p style="font-size:13px; color:var(--text-muted);">検索キーワードやフィルター条件を変更してお試しください。</p>
          </div>
        `;
        return;
      }}

      cardsGrid.innerHTML = items.map(item => {{
        const mainImage = (item.media && item.media.length > 0) ? item.media[0] : null;
        const mediaCount = (item.media && item.media.length > 1) ? item.media.length : 0;
        const authorName = item.author_name || item.user_name || '有志';
        
        const gravBadges = (item.gravity_details && item.gravity_details.length > 0)
          ? item.gravity_details.slice(0, 3).map(g => `<span class="gravity-pill">${{escapeHtml(g)}}</span>`).join('')
          : (item.tags && item.tags.length > 0)
            ? item.tags.slice(0, 3).map(t => `<span class="gravity-pill">${{escapeHtml(t)}}</span>`).join('')
            : '<span style="font-size:11px; color:var(--text-muted);">本文記載</span>';

        const conditionNote = (item.condition_details && item.condition_details.length > 0)
          ? `<div class="movement-note">${{escapeHtml(item.condition_details[0].substring(0, 48))}}...</div>`
          : '';

        return `
          <article class="prize-card">
            <div class="card-media" onclick="viewItemDetails('${{item.tweet_id}}')">
              <span class="author-badge-on-card">${{escapeHtml(authorName)}}</span>
              ${{mainImage 
                ? `<img src="${{mainImage}}" alt="${{escapeHtml(item.prize_name)}}" loading="lazy">` 
                : `<div class="no-image-placeholder"><span>📷</span><span>No Image</span></div>`
              }}
              ${{mediaCount > 0 ? `<span class="media-count-badge">📷 ${{mediaCount}}枚</span>` : ''}}
            </div>
            <div class="card-body">
              <div class="card-meta">
                <span class="anime-badge" title="${{escapeHtml(item.anime_title)}}">${{escapeHtml(item.anime_title || 'その他')}}</span>
                <span class="post-date">${{escapeHtml(item.created_at ? item.created_at.split(' ')[0] : '')}}</span>
              </div>
              <h3 class="prize-title" title="${{escapeHtml(item.prize_name)}}">${{escapeHtml(item.prize_name)}}</h3>
              
              <div class="gravity-box">
                <div class="gravity-title">⚖ 重心データ</div>
                <div class="gravity-tags">
                  ${{gravBadges}}
                </div>
              </div>

              <div class="specs-grid">
                <div class="spec-item">
                  <span class="spec-label">フィギュア</span>
                  <span class="spec-value">${{escapeHtml(item.figure_size || '-')}}</span>
                </div>
                <div class="spec-item">
                  <span class="spec-label">箱の重さ</span>
                  <span class="spec-value">${{escapeHtml(item.box_weight || '-')}}</span>
                </div>
                <div class="spec-item" style="grid-column: 1 / -1;">
                  <span class="spec-label">箱サイズ</span>
                  <span class="spec-value">${{escapeHtml(item.box_size || '-')}}</span>
                </div>
              </div>

              ${{conditionNote}}

              <div class="card-footer">
                <a href="${{item.tweet_url}}" target="_blank" rel="noopener noreferrer" class="x-link-btn" onclick="event.stopPropagation()">
                  Xポスト ↗
                </a>
                <button class="detail-modal-btn" onclick="viewItemDetails('${{item.tweet_id}}')">
                  詳細を見る
                </button>
              </div>
            </div>
          </article>
        `;
      }}).join('');
    }}

    function escapeHtml(str) {{
      if (!str) return '';
      return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
    }}

    window.viewItemDetails = function(tweetId) {{
      const item = PRIZE_DATA.find(i => String(i.tweet_id) === String(tweetId));
      if (item) openModal(item);
    }};

    // Event Listeners
    searchInput.addEventListener('input', (e) => {{
      currentSearch = e.target.value;
      filterAndRender();
    }});

    animeSelect.addEventListener('change', (e) => {{
      currentAnime = e.target.value;
      filterAndRender();
    }});

    sortSelect.addEventListener('change', (e) => {{
      currentSort = e.target.value;
      filterAndRender();
    }});

    authorChips.forEach(btn => {{
      btn.addEventListener('click', () => {{
        authorChips.forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        currentAuthor = btn.dataset.author;
        filterAndRender();
      }});
    }});

    gravChips.forEach(btn => {{
      btn.addEventListener('click', () => {{
        gravChips.forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        currentFilter = btn.dataset.filter;
        filterAndRender();
      }});
    }});

    filterAndRender();
  </script>
</body>
</html>
"""

    with open(OUTPUT_HTML_PATH, "w", encoding="utf-8") as f:
        f.write(html_content)
    with open(PRIZE_HTML_PATH, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"HTMLビューアを生成・保存しました:\n - {OUTPUT_HTML_PATH}\n - {PRIZE_HTML_PATH}")

def main():
    print("=== プライズ重心情報（Merry✩An / 831生活 / あかり / もぐらクレーン）2026年分 収集開始 ===")
    
    limit_records = 3500
    if len(sys.argv) > 1:
        try:
            limit_records = int(sys.argv[1])
        except ValueError:
            pass

    data = collect_data(limit_records=limit_records, target_year="2026")
    generate_html(data)
    print("=== 収集・生成工程が完了しました ===")

if __name__ == "__main__":
    main()
