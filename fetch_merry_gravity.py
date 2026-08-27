"""
プライズ重心情報（Merry✩An、831生活、あかり、もぐらクレーン）2026年分
calendar.html完全互換デザイン＆列数切替システム 収集＆HTML生成スクリプト
"""

import os
import sys
import re
import json
import time
import requests
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_JSON_PATH = os.path.join(BASE_DIR, "gravity_data.json")
SYNC_INFO_PATH = os.path.join(BASE_DIR, "gravity_sync_info.json")
OUTPUT_HTML_PATH = os.path.join(BASE_DIR, "gravity.html")
PRIZE_HTML_PATH = os.path.join(BASE_DIR, "prize_gravity_viewer.html")

SUPABASE_URL = "https://cguiwksdixdgxaebbwye.supabase.co"

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
    anime_map = {}
    try:
        r = requests.get(f"{SUPABASE_URL}/rest/v1/anime_titles?select=id,title,sub_title,reading_kana&limit=2000", headers=headers, timeout=15)
        if r.status_code == 200:
            for item in r.json():
                anime_map[item['id']] = item
    except Exception as e:
        print(f"Error fetching anime titles: {e}")
    return anime_map

def fetch_all_cog_records(headers, limit_total=None):
    all_records = []
    page_size = 1000
    offset = 0
    while True:
        url = f"{SUPABASE_URL}/rest/v1/center_of_gravity?select=*&order=id.desc&limit={page_size}&offset={offset}"
        try:
            r = requests.get(url, headers=headers, timeout=15)
            if r.status_code != 200:
                break
            items = r.json()
            if not items:
                break
            all_records.extend(items)
            if limit_total and len(all_records) >= limit_total:
                all_records = all_records[:limit_total]
                break
            if len(items) < page_size:
                break
            offset += page_size
        except Exception as e:
            break
    return all_records

def clean_url_or_text(s):
    if not s:
        return ""
    return re.sub(r'https?://t\.co/[a-zA-Z0-9]+', '', s).strip()

def parse_tweet_content(text, author_name, anime_title=""):
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

    name_candidates = []
    for line in lines:
        if any(line.startswith(prefix) for prefix in ['＃重心情報', '#重心情報', '重心情報', '#cranity', '#クレーンゲーム']):
            continue
        if any(line.startswith(prefix) for prefix in ['🔶', '【', '🟨', 'http', '※', '★', '☆', '・']):
            break
        if '重心情報:' in line or '重心情報：' in line:
            break
        cleaned = clean_url_or_text(line)
        cleaned = re.sub(r'^[『「【](.*?)[』」】]$', r'\1', cleaned)
        if cleaned:
            name_candidates.append(cleaned)

    prize_name = ' '.join(name_candidates).strip()
    if not prize_name:
        for line in lines:
            c = clean_url_or_text(line)
            if c and not any(c.startswith(p) for p in ['#', '＃', '【', '🟨', '🔶']):
                prize_name = re.sub(r'^[『「【](.*?)[』」】]$', r'\1', c)
                break
    if not prize_name:
        prize_name = anime_title or "プライズ景品"

    prize_name = clean_url_or_text(prize_name)
    prize_name = re.sub(r'[\s　]+', ' ', prize_name)

    fig_size_match = re.search(r'【Figure size】?\s*([^\n\r【🔶🟨]+)', text, re.IGNORECASE)
    if fig_size_match:
        fig_size = clean_url_or_text(fig_size_match.group(1).rstrip('】'))

    box_weight_match = re.search(r'【Box weight】?\s*([^\n\r【🔶🟨]+)', text, re.IGNORECASE) or re.search(r'重量[：:]\s*([^\n\r]+)', text)
    if box_weight_match:
        box_weight = clean_url_or_text(box_weight_match.group(1).rstrip('】'))

    box_size_match = re.search(r'【Box size】?\s*([^\n\r【🔶🟨]+)', text, re.IGNORECASE)
    if box_size_match:
        box_size = clean_url_or_text(box_size_match.group(1).rstrip('】'))

    for line in lines:
        if line.startswith('🟨'):
            c = clean_url_or_text(line.replace('🟨', '').strip())
            if c and c not in gravity_details:
                gravity_details.append(c)

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

    for i, line in enumerate(lines):
        if '重心情報:' in line or '重心情報：' in line:
            part = line.split(':', 1)[-1].split('：', 1)[-1].strip()
            if part:
                c = clean_url_or_text(part)
                if c and c not in gravity_details:
                    gravity_details.append(c)
            elif i + 1 < len(lines):
                c = clean_url_or_text(lines[i+1])
                if c and c not in gravity_details and not c.startswith('http'):
                    gravity_details.append(c)

    for line in lines:
        if any(w in line for w in ['重心', '側重', '裏面', '表面', '上側', '下側', '頭側', '足側']):
            if not line.startswith('🔶') and not line.startswith('＃') and not line.startswith('#') and '【獲得' not in line:
                c = clean_url_or_text(line.lstrip('・- ').strip())
                if c and c not in gravity_details and len(c) <= 60 and not c.startswith('http'):
                    gravity_details.append(c)

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

def collect_data(limit_records=3500, target_year="2026"):
    anon_key = get_supabase_key()
    headers = {
        "apikey": anon_key,
        "Authorization": f"Bearer {anon_key}",
        "Content-Type": "application/json"
    }
    
    # 前回の同期情報を読み込み
    prev_sync_info = {}
    if os.path.exists(SYNC_INFO_PATH):
        try:
            with open(SYNC_INFO_PATH, "r", encoding="utf-8") as f:
                prev_sync_info = json.load(f)
        except Exception:
            pass

    prev_time = prev_sync_info.get("last_sync_time", "2026-08-23 09:17")
    prev_total = prev_sync_info.get("total_records", 0)
    prev_authors = prev_sync_info.get("author_counts", {})

    anime_map = fetch_anime_titles(headers)
    cog_records = fetch_all_cog_records(headers, limit_total=limit_records)
    
    existing_items = {}
    if os.path.exists(DATA_JSON_PATH):
        try:
            with open(DATA_JSON_PATH, "r", encoding="utf-8") as f:
                old_list = json.load(f)
                for item in old_list:
                    c_date = str(item.get('created_at', ''))
                    if not target_year or c_date.startswith(target_year):
                        existing_items[item['tweet_id']] = item
        except Exception:
            pass

    unique_items = []
    seen_ids = set()
    for rec in cog_records:
        tid = str(rec.get('tweet_id', '')).strip()
        if tid and tid not in seen_ids:
            seen_ids.add(tid)
            unique_items.append(rec)
            
    to_fetch = [item for item in unique_items if item['tweet_id'] not in existing_items]
    
    new_count = 0
    new_items_by_author = {}
    if to_fetch:
        with ThreadPoolExecutor(max_workers=15) as executor:
            future_to_item = {executor.submit(fetch_single_tweet, item['tweet_id']): item for item in to_fetch}
            for future in as_completed(future_to_item):
                item = future_to_item[future]
                tid, tweet_data = future.result()
                if not tweet_data:
                    continue
                
                user = tweet_data.get('user') or {}
                screen_name = user.get('screen_name', '')
                user_name = user.get('name', '')
                
                author_display_name = identify_author(user_name, screen_name)
                if not author_display_name:
                    continue
                
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

                if target_year and not formatted_date.startswith(target_year):
                    continue

                anime_info = anime_map.get(item.get('anime_title_id'), {})
                anime_title = anime_info.get('title', '')
                text = tweet_data.get('text', '')
                
                parsed = parse_tweet_content(text, author_display_name, anime_title)
                
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
                new_items_by_author[author_display_name] = new_items_by_author.get(author_display_name, 0) + 1

    final_dict = {}
    for tid, item in existing_items.items():
        c_date = str(item.get('created_at', ''))
        if target_year and not c_date.startswith(target_year):
            continue
        
        auth_name = item.get('author_name') or identify_author(item.get('user_name', ''), item.get('screen_name', '')) or item.get('user_name', '')
        item['author_name'] = auth_name
        
        parsed = parse_tweet_content(item.get('full_text', ''), auth_name, item.get('anime_title', ''))
        item['prize_name'] = parsed.get('prize_name', item.get('prize_name', ''))
        item['figure_size'] = parsed.get('figure_size', item.get('figure_size', ''))
        item['box_weight'] = parsed.get('box_weight', item.get('box_weight', ''))
        item['box_size'] = parsed.get('box_size', item.get('box_size', ''))
        item['gravity_details'] = parsed.get('gravity_details', [])
        item['condition_details'] = parsed.get('condition_details', [])
        item['tags'] = parsed.get('tags', [])
        final_dict[tid] = item

    final_list = list(final_dict.values())
    final_list.sort(key=lambda x: str(x.get('created_at', '')), reverse=True)
    
    with open(DATA_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(final_list, f, ensure_ascii=False, indent=2)

    # 投稿者別集計
    current_authors = {}
    for item in final_list:
        a_name = item.get('author_name', 'その他')
        current_authors[a_name] = current_authors.get(a_name, 0) + 1

    current_time_str = datetime.now().strftime('%Y-%m-%d %H:%M')
    history = prev_sync_info.get("history", [])
    
    if new_count > 0 or not history:
        history.insert(0, {
            "timestamp": current_time_str,
            "total": len(final_list),
            "new_added": new_count
        })
        history = history[:30] # 直近30回分を保持

    sync_info = {
        "last_sync_time": current_time_str,
        "previous_sync_time": prev_time,
        "total_records": len(final_list),
        "new_records_count": new_count,
        "author_counts": current_authors,
        "author_new_counts": new_items_by_author,
        "history": history
    }

    with open(SYNC_INFO_PATH, "w", encoding="utf-8") as f:
        json.dump(sync_info, f, ensure_ascii=False, indent=2)

    print("\n" + "=" * 60)
    print("📊 プライズ重心情報 収集・同期レポート")
    print("=" * 60)
    print(f"🕒 前回更新日時 : {prev_time}")
    print(f"🕒 今回更新日時 : {current_time_str}")
    print(f"📦 今回追加件数 : +{new_count} 件")
    print(f"🎯 2026年総件数 : {len(final_list):,} 件")
    print("-" * 60)
    print("👤 投稿者別内訳:")
    for a_name, count in sorted(current_authors.items(), key=lambda x: x[1], reverse=True):
        diff = new_items_by_author.get(a_name, 0)
        diff_str = f" (+{diff})" if diff > 0 else ""
        print(f"  - {a_name:<10} : {count:>4} 件{diff_str}")
    print("=" * 60 + "\n")
    
    return final_list, sync_info

def generate_html(gravity_items, sync_info=None):
    total_count = len(gravity_items)
    anime_titles = sorted(list({item.get('anime_title', 'その他') for item in gravity_items if item.get('anime_title')}))
    updated_time = datetime.now().strftime('%Y年%m月%d日 %H:%M')
    
    diff_badge = ""
    if sync_info and sync_info.get("new_records_count", 0) > 0:
        new_cnt = sync_info["new_records_count"]
        diff_badge = f' <span style="background: rgba(255,255,255,0.25); padding: 1px 7px; border-radius: 10px; font-size: 11px; margin-left: 4px; font-weight: 700;">+{new_cnt}件追加</span>'

    items_json_str = json.dumps(gravity_items, ensure_ascii=False)

    html_content = f"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
<title>プライズフィギュア 重心情報データベース - 2026年</title>
<style>
    :root {{
        --primary: #e63946;
        --primary-dark: #c1121f;
        --mercari: #ff0211;
        --mercari-dark: #d6000e;
        --bg-body: #f1f5f9;
        --card-bg: #ffffff;
        --text-main: #0f172a;
        --text-sub: #64748b;
        --border-color: #e2e8f0;
    }}
    * {{
        box-sizing: border-box;
    }}
    body {{
        margin: 0;
        padding: 16px 8px;
        font-family: 'Helvetica Neue', Arial, 'Hiragino Kaku Gothic ProN', 'Hiragino Sans', Meiryo, sans-serif;
        background-color: var(--bg-body);
        display: flex;
        justify-content: center;
        color: var(--text-main);
    }}
    .container {{
        width: 100%;
        max-width: 1680px;
        background-color: #ffffff;
        border-radius: 12px;
        overflow: hidden;
        box-shadow: 0 4px 20px rgba(0,0,0,0.06);
        border: 1px solid #e2e8f0;
    }}
    .header {{
        background: linear-gradient(135deg, #e63946 0%, #ba181b 100%);
        color: #fff;
        padding: 12px 16px;
        display: flex;
        flex-direction: column;
        gap: 10px;
    }}
    .header-top {{
        display: flex;
        justify-content: space-between;
        align-items: center;
        flex-wrap: wrap;
        gap: 8px;
    }}
    .header-left {{
        display: flex;
        align-items: center;
        gap: 8px;
        flex-wrap: wrap;
    }}
    .nav-top-btn {{
        color: #fff;
        text-decoration: none;
        font-size: 12px;
        font-weight: 700;
        background: rgba(0,0,0,0.25);
        padding: 5px 12px;
        border-radius: 20px;
        display: inline-flex;
        align-items: center;
        gap: 4px;
        transition: background 0.2s ease;
    }}
    .nav-top-btn:hover {{
        background: rgba(0,0,0,0.4);
    }}
    .header h1 {{
        margin: 0;
        font-size: 18px;
        font-weight: 800;
        letter-spacing: 0.5px;
    }}

    /* コントロールツールバー */
    .header-toolbar {{
        display: flex;
        align-items: center;
        justify-content: space-between;
        background: rgba(0, 0, 0, 0.22);
        padding: 8px 12px;
        border-radius: 8px;
        flex-wrap: wrap;
        gap: 8px;
        backdrop-filter: blur(4px);
    }}
    .toolbar-group {{
        display: flex;
        align-items: center;
        gap: 6px;
        flex-wrap: wrap;
    }}
    .toolbar-label {{
        font-size: 12px;
        font-weight: 700;
        color: #ffffff;
        display: flex;
        align-items: center;
        gap: 3px;
    }}

    /* モード切替ボタングループ */
    .mode-btn-group {{
        display: inline-flex;
        background: rgba(0,0,0,0.25);
        padding: 2px;
        border-radius: 6px;
        border: 1px solid rgba(255,255,255,0.2);
    }}
    .mode-btn {{
        padding: 4px 10px;
        border: none;
        background: transparent;
        color: rgba(255,255,255,0.85);
        font-size: 11.5px;
        font-weight: 700;
        cursor: pointer;
        border-radius: 4px;
        transition: all 0.15s ease;
        display: flex;
        align-items: center;
        gap: 4px;
    }}
    .mode-btn.active {{
        background: #ffffff;
        color: var(--primary-dark);
        box-shadow: 0 2px 5px rgba(0,0,0,0.2);
    }}
    .mode-btn.active.mercari-mode {{
        background: var(--mercari);
        color: #ffffff;
    }}

    /* 検索バー */
    .search-input-box {{
        padding: 5px 12px;
        font-size: 12.5px;
        border-radius: 20px;
        border: 1px solid rgba(255,255,255,0.4);
        background: #ffffff;
        color: #0f172a;
        font-weight: 600;
        outline: none;
        min-width: 200px;
    }}
    .search-input-box:focus {{
        border-color: #ffffff;
        box-shadow: 0 0 0 2px rgba(255,255,255,0.4);
    }}

    .anime-dropdown {{
        padding: 5px 10px;
        font-size: 12px;
        border-radius: 20px;
        border: 1px solid rgba(255,255,255,0.4);
        background: #ffffff;
        color: #0f172a;
        font-weight: 700;
        outline: none;
        cursor: pointer;
        max-width: 170px;
    }}

    /* 列数切替ボタン */
    .col-btn-group {{
        display: inline-flex;
        background: rgba(0,0,0,0.25);
        padding: 2px;
        border-radius: 6px;
        border: 1px solid rgba(255,255,255,0.2);
    }}
    .col-btn {{
        padding: 3px 7px;
        border: none;
        background: transparent;
        color: rgba(255,255,255,0.85);
        font-size: 11px;
        font-weight: 700;
        cursor: pointer;
        border-radius: 4px;
        transition: all 0.15s ease;
    }}
    .col-btn.active {{
        background: #ffffff;
        color: #0f172a;
    }}

    /* サブフィルターバー */
    .filter-bar {{
        background: #ffffff;
        border-bottom: 1px solid #e2e8f0;
        padding: 10px 14px;
        display: flex;
        flex-direction: column;
        gap: 8px;
    }}
    .filter-row {{
        display: flex;
        align-items: center;
        gap: 6px;
        flex-wrap: wrap;
    }}
    .filter-row-label {{
        font-size: 11.5px;
        font-weight: 700;
        color: #475569;
        min-width: 54px;
    }}
    .chip-btn {{
        padding: 3px 9px;
        border: 1px solid #e2e8f0;
        background: #f1f5f9;
        color: #334155;
        font-size: 11.5px;
        font-weight: 700;
        border-radius: 6px;
        cursor: pointer;
        transition: all 0.15s ease;
    }}
    .chip-btn:hover {{
        background: #e2e8f0;
        border-color: #cbd5e1;
    }}
    .chip-btn.active {{
        background: var(--primary);
        color: #ffffff;
        border-color: var(--primary-dark);
        box-shadow: 0 2px 6px rgba(230, 57, 70, 0.25);
    }}
    .chip-btn.author-chip.active {{
        background: #0284c7;
        border-color: #0369a1;
        box-shadow: 0 2px 6px rgba(2, 132, 199, 0.25);
    }}

    /* グリッドレイアウト（PC・大画面は7列） */
    .grid {{
        display: grid;
        grid-template-columns: repeat(7, 1fr);
        gap: 8px;
        padding: 12px;
        background-color: #f8fafc;
    }}
    @media (max-width: 1200px) {{
        .grid {{
            grid-template-columns: repeat(5, 1fr);
        }}
    }}
    @media (max-width: 900px) {{
        .grid {{
            grid-template-columns: repeat(4, 1fr);
            gap: 6px;
            padding: 8px;
        }}
    }}

    /* スマホ・小型端末（デフォルト3列表示で一画面に多数表示） */
    @media (max-width: 650px) {{
        body {{
            padding: 4px 2px;
        }}
        .container {{
            border-radius: 6px;
        }}
        .header {{
            padding: 10px 10px;
            gap: 8px;
        }}
        .header h1 {{
            font-size: 15px;
        }}
        .header-toolbar {{
            padding: 6px 8px;
            gap: 6px;
        }}
        .grid {{
            grid-template-columns: repeat(3, 1fr);
            gap: 5px;
            padding: 5px;
        }}
        .info-wrap {{
            padding: 4px 4px 6px !important;
            gap: 3px !important;
        }}
        .item-name {{
            font-size: 9.5px !important;
            line-height: 1.25 !important;
        }}
        .gravity-pill {{
            font-size: 8.5px !important;
            padding: 1px 4px !important;
        }}
    }}

    /* ユーザーが列数を手動で切り替えた時の上書きクラス */
    .grid.cols-2 {{ grid-template-columns: repeat(2, 1fr) !important; }}
    .grid.cols-3 {{ grid-template-columns: repeat(3, 1fr) !important; }}
    .grid.cols-4 {{ grid-template-columns: repeat(4, 1fr) !important; }}
    .grid.cols-5 {{ grid-template-columns: repeat(5, 1fr) !important; }}
    .grid.cols-6 {{ grid-template-columns: repeat(6, 1fr) !important; }}
    .grid.cols-7 {{ grid-template-columns: repeat(7, 1fr) !important; }}
    .grid.cols-8 {{ grid-template-columns: repeat(8, 1fr) !important; }}
    
    /* アイテムカード */
    .item-card {{
        background: var(--card-bg);
        border: 1px solid var(--border-color);
        border-radius: 8px;
        overflow: hidden;
        display: flex;
        flex-direction: column;
        box-shadow: 0 2px 5px rgba(0,0,0,0.03);
        cursor: pointer;
        position: relative;
        transition: transform 0.15s ease, box-shadow 0.15s ease, border-color 0.15s ease;
    }}
    .item-card:hover {{
        transform: translateY(-2px);
        box-shadow: 0 8px 18px rgba(0,0,0,0.09);
        border-color: var(--primary);
    }}
    .item-card:active {{
        transform: scale(0.98);
    }}
    
    /* 画像ラッパー */
    .img-wrap {{
        width: 100%;
        aspect-ratio: 1 / 1;
        background-color: #ffffff;
        position: relative;
        overflow: hidden;
        display: flex;
        align-items: center;
        justify-content: center;
        border-bottom: 1px solid #f1f5f9;
    }}
    .img-wrap img {{
        width: 100%;
        height: 100%;
        object-fit: contain;
        padding: 3px;
        transition: transform 0.2s ease;
    }}
    .item-card:hover .img-wrap img {{
        transform: scale(1.04);
    }}

    .card-author-badge {{
        position: absolute;
        top: 4px;
        left: 4px;
        background: rgba(15, 23, 42, 0.85);
        color: #ffffff;
        font-size: 8.5px;
        font-weight: 800;
        padding: 2px 6px;
        border-radius: 4px;
        letter-spacing: 0.2px;
        z-index: 2;
        backdrop-filter: blur(4px);
    }}

    .card-photo-count {{
        position: absolute;
        bottom: 4px;
        right: 4px;
        background: rgba(0, 0, 0, 0.65);
        color: #ffffff;
        font-size: 8.5px;
        font-weight: 700;
        padding: 1px 5px;
        border-radius: 4px;
        z-index: 2;
    }}

    .no-img-text {{
        font-size: 11px;
        color: #94a3b8;
        font-weight: 700;
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 2px;
    }}
    
    /* 情報ブロック */
    .info-wrap {{
        padding: 6px 6px 8px;
        display: flex;
        flex-direction: column;
        gap: 4px;
        flex-grow: 1;
        justify-content: space-between;
        background: #ffffff;
    }}
    .info-top {{
        display: flex;
        flex-direction: column;
        gap: 3px;
    }}
    
    .anime-tag {{
        font-size: 9px;
        font-weight: 800;
        padding: 1px 5px;
        border-radius: 4px;
        display: inline-block;
        width: fit-content;
        letter-spacing: 0.2px;
        background-color: #fef3c7;
        color: #b45309;
        border: 1px solid #fde68a;
        max-width: 100%;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }}
    
    .item-name {{
        font-size: 10.5px;
        font-weight: 700;
        line-height: 1.35;
        color: #0f172a;
        word-break: break-word;
        margin: 0;
        display: -webkit-box;
        -webkit-line-clamp: 2;
        -webkit-box-orient: vertical;
        overflow: hidden;
        min-height: 28px;
    }}

    /* 重心バッジ */
    .gravity-badge-wrap {{
        display: flex;
        flex-wrap: wrap;
        gap: 3px;
        margin-top: 2px;
    }}
    .gravity-pill {{
        background: #fffbeb;
        color: #92400e;
        border: 1px solid #fde68a;
        font-size: 9px;
        font-weight: 800;
        padding: 1.5px 5px;
        border-radius: 4px;
        line-height: 1.2;
    }}
    
    /* スペック */
    .item-specs {{
        font-size: 9px;
        color: #64748b;
        font-weight: 600;
        line-height: 1.3;
        display: flex;
        flex-direction: column;
        gap: 1px;
        padding-top: 2px;
        border-top: 1px dashed #f1f5f9;
    }}

    .card-bottom-bar {{
        display: flex;
        align-items: center;
        justify-content: space-between;
        font-size: 9.5px;
        color: #94a3b8;
        font-weight: 600;
        margin-top: 2px;
    }}
    .card-x-link {{
        color: #0284c7;
        text-decoration: none;
        font-weight: 700;
    }}
    .card-x-link:hover {{
        text-decoration: underline;
    }}

    /* トースト通知 */
    #toast {{
        position: fixed;
        bottom: 24px;
        left: 50%;
        transform: translateX(-50%) translateY(100px);
        background: rgba(15, 23, 42, 0.92);
        color: #ffffff;
        padding: 8px 16px;
        border-radius: 25px;
        font-size: 12px;
        font-weight: 600;
        box-shadow: 0 10px 25px rgba(0,0,0,0.3);
        display: flex;
        align-items: center;
        gap: 6px;
        backdrop-filter: blur(8px);
        pointer-events: none;
        z-index: 99999;
        transition: transform 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275), opacity 0.3s ease;
        opacity: 0;
        max-width: 90%;
        text-align: center;
    }}
    #toast.show {{
        transform: translateX(-50%) translateY(0);
        opacity: 1;
    }}
    #toast .toast-icon {{
        color: #4ade80;
        font-size: 14px;
    }}

    /* モーダル */
    .modal-overlay {{
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: rgba(15, 23, 42, 0.65);
        backdrop-filter: blur(4px);
        display: none;
        align-items: center;
        justify-content: center;
        z-index: 99999;
        padding: 16px;
    }}
    .modal-overlay.open {{
        display: flex;
    }}
    .modal-content {{
        background: #ffffff;
        border-radius: 12px;
        max-width: 680px;
        width: 100%;
        max-height: 90vh;
        overflow-y: auto;
        box-shadow: 0 10px 30px rgba(0,0,0,0.25);
        position: relative;
        display: flex;
        flex-direction: column;
    }}
    .modal-header {{
        padding: 14px 18px;
        border-bottom: 1px solid #e2e8f0;
        display: flex;
        align-items: flex-start;
        justify-content: space-between;
        gap: 12px;
        position: sticky;
        top: 0;
        background: #ffffff;
        z-index: 10;
    }}
    .modal-close-btn {{
        background: #f1f5f9;
        border: none;
        width: 32px;
        height: 32px;
        border-radius: 50%;
        font-size: 18px;
        cursor: pointer;
        display: flex;
        align-items: center;
        justify-content: center;
        color: #64748b;
        transition: all 0.15s ease;
    }}
    .modal-close-btn:hover {{
        background: #e2e8f0;
        color: #0f172a;
    }}
    .modal-body {{
        padding: 18px;
        display: flex;
        flex-direction: column;
        gap: 14px;
    }}
    .modal-gallery {{
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
        gap: 8px;
    }}
    .modal-gallery img {{
        width: 100%;
        border-radius: 6px;
        border: 1px solid #e2e8f0;
        cursor: pointer;
        transition: transform 0.2s ease;
    }}
    .modal-gallery img:hover {{
        transform: scale(1.02);
    }}
    .modal-raw-text {{
        background: #f8fafc;
        padding: 12px;
        border-radius: 6px;
        font-size: 12.5px;
        white-space: pre-wrap;
        word-break: break-word;
        line-height: 1.6;
        border: 1px solid #e2e8f0;
    }}
</style>
</head>
<body>
<div class="container">

    <!-- ヘッダー（calendar.htmlデザイン） -->
    <div class="header">
        <div class="header-top">
            <div class="header-left">
                <a href="index.html" class="nav-top-btn">
                    <span>🏠</span><span>トップへ</span>
                </a>
                <a href="index.html" class="nav-top-btn" style="background: rgba(255,255,255,0.35); color: #ffffff;">
                    <span>🔍</span><span>全月検索</span>
                </a>
                <h1>プライズフィギュア 重心情報データベース (2026年)</h1>
            </div>
            <div style="font-size: 12px; font-weight: 700; color: rgba(255,255,255,0.9); text-align: right;">
                収録: <b id="totalItemsCount" style="color: #fff; font-size: 14px;">{total_count}</b> 件 ({updated_time} 更新){diff_badge}
            </div>
        </div>

        <!-- ツールバー -->
        <div class="header-toolbar">
            <div class="toolbar-group">
                <span class="toolbar-label">クリック:</span>
                <div class="mode-btn-group">
                    <button type="button" class="mode-btn active" id="modeBtnDetail" onclick="setClickMode('detail')">
                        <span>🔍</span> 詳細・重心
                    </button>
                    <button type="button" class="mode-btn" id="modeBtnMercari" onclick="setClickMode('mercari')">
                        <span>🔴</span> メルカリ
                    </button>
                </div>
            </div>

            <!-- 表示列数ボタングループ（calendar.html完全互換 2列〜8列） -->
            <div class="toolbar-group">
                <span class="toolbar-label">表示列数:</span>
                <div class="col-btn-group">
                    <button type="button" class="col-btn" id="colBtn2" onclick="setGridColumns(2)">2列</button>
                    <button type="button" class="col-btn" id="colBtn3" onclick="setGridColumns(3)">3列</button>
                    <button type="button" class="col-btn" id="colBtn4" onclick="setGridColumns(4)">4列</button>
                    <button type="button" class="col-btn" id="colBtn5" onclick="setGridColumns(5)">5列</button>
                    <button type="button" class="col-btn" id="colBtn6" onclick="setGridColumns(6)">6列</button>
                    <button type="button" class="col-btn" id="colBtn7" onclick="setGridColumns(7)">7列</button>
                    <button type="button" class="col-btn" id="colBtn8" onclick="setGridColumns(8)">8列</button>
                </div>
            </div>

            <div class="toolbar-group" style="flex: 1; min-width: 200px; justify-content: flex-end;">
                <input type="text" id="searchInput" class="search-input-box" placeholder="景品名、作品名、重心で検索...">
                <select id="animeSelect" class="anime-dropdown">
                    <option value="">全作品 ({len(anime_titles)}作品)</option>
                    {''.join([f'<option value="{title}">{title}</option>' for title in anime_titles])}
                </select>
            </div>
        </div>
    </div>

    <!-- サブフィルターバー -->
    <div class="filter-bar">
        <!-- 投稿者別フィルター -->
        <div class="filter-row">
            <span class="filter-row-label">👤 投稿者:</span>
            <button class="chip-btn author-chip active" data-author="all">全員</button>
            <button class="chip-btn author-chip" data-author="Merry☆An">Merry☆An</button>
            <button class="chip-btn author-chip" data-author="831生活">831生活</button>
            <button class="chip-btn author-chip" data-author="あかり">あかり</button>
            <button class="chip-btn author-chip" data-author="もぐらクレーン">もぐらクレーン</button>
        </div>

        <!-- 重心別フィルター -->
        <div class="filter-row">
            <span class="filter-row-label">⚖ 重心:</span>
            <button class="chip-btn grav-chip active" data-filter="all">すべて</button>
            <button class="chip-btn grav-chip" data-filter="上重心">上重心</button>
            <button class="chip-btn grav-chip" data-filter="下重心">下重心</button>
            <button class="chip-btn grav-chip" data-filter="裏重心">裏重心</button>
            <button class="chip-btn grav-chip" data-filter="表重心">表重心</button>
            <button class="chip-btn grav-chip" data-filter="左重心">左重心</button>
            <button class="chip-btn grav-chip" data-filter="右重心">右重心</button>
            <button class="chip-btn grav-chip" data-filter="ブリスター">ブリスター</button>
            <button class="chip-btn grav-chip" data-filter="固定・動かない">動かない</button>
            <button class="chip-btn grav-chip" data-filter="個体差あり">個体差注意</button>
        </div>
    </div>

    <!-- 景品カードグリッド -->
    <div id="mainGrid" class="grid"></div>

</div>

<!-- トースト通知 -->
<div id="toast">
    <span class="toast-icon">✓</span>
    <span id="toastMsg">列数を切り替えました</span>
</div>

<!-- 詳細モーダル -->
<div id="detailModal" class="modal-overlay">
    <div class="modal-content">
        <div class="modal-header">
            <div>
                <span id="modalAuthorBadge" style="font-size: 10px; font-weight: 800; background: #e0f2fe; color: #0369a1; padding: 2px 7px; border-radius: 4px; margin-right: 4px;">投稿者</span>
                <span id="modalAnimeBadge" class="anime-tag">作品名</span>
                <h2 id="modalPrizeTitle" style="font-size: 16px; font-weight: 800; margin-top: 6px; color: #0f172a;">景品名</h2>
            </div>
            <button id="modalCloseBtn" class="modal-close-btn">&times;</button>
        </div>
        <div class="modal-body">
            <div id="modalGallery" class="modal-gallery"></div>
            
            <div style="background: #fffbeb; border: 1px solid #fde68a; border-radius: 6px; padding: 10px 12px;">
                <div style="font-size: 11px; font-weight: 800; color: #d97706; margin-bottom: 6px;">⚖ 重心測定データ</div>
                <div id="modalGravityTags" style="display: flex; flex-wrap: wrap; gap: 4px;"></div>
            </div>

            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 6px 12px; background: #f8fafc; padding: 10px 12px; border-radius: 6px; font-size: 11.5px;">
                <div><span style="color:#64748b;">フィギュアサイズ:</span> <b id="modalFigSize" style="color:#0f172a;">-</b></div>
                <div><span style="color:#64748b;">箱の重さ:</span> <b id="modalBoxWeight" style="color:#0f172a;">-</b></div>
                <div style="grid-column: 1 / -1;"><span style="color:#64748b;">箱サイズ:</span> <b id="modalBoxSize" style="color:#0f172a;">-</b></div>
                <div style="grid-column: 1 / -1;"><span style="color:#64748b;">投稿日時:</span> <b id="modalDate" style="color:#0f172a;">-</b></div>
            </div>

            <div>
                <div style="font-size: 11.5px; font-weight: 700; color: #64748b; margin-bottom: 4px;">ツイート本文</div>
                <div id="modalRawText" class="modal-raw-text"></div>
            </div>

            <div style="display: flex; justify-content: space-between; align-items: center;">
                <button type="button" id="modalMercariBtn" style="font-size: 12.5px; font-weight: 700; color: #fff; background: var(--mercari); border: none; border-radius: 6px; padding: 6px 14px; cursor: pointer;">
                    🔴 メルカリ検索 ↗
                </button>
                <a id="modalXLink" href="#" target="_blank" rel="noopener noreferrer" style="font-size: 12.5px; font-weight: 700; color: #0284c7; text-decoration: none; padding: 6px 14px; background: #f0f9ff; border: 1px solid #bae6fd; border-radius: 6px;">
                    Xで元のポストを見る ↗
                </a>
            </div>
        </div>
    </div>
</div>

<!-- ライトボックス -->
<div id="imageLightbox" class="modal-overlay" style="background: rgba(0,0,0,0.88);">
    <div style="position: relative; max-width: 90vw; max-height: 90vh;">
        <button id="lightboxCloseBtn" class="modal-close-btn" style="position: absolute; top: -40px; right: 0; color: white; background: rgba(255,255,255,0.2);">&times;</button>
        <img id="lightboxImg" src="" alt="" style="max-width: 100%; max-height: 85vh; border-radius: 8px; object-fit: contain; box-shadow: 0 10px 30px rgba(0,0,0,0.5);">
    </div>
</div>

<script>
    const PRIZE_DATA = {items_json_str};

    let toastTimeout = null;
    let currentClickMode = localStorage.getItem('prize_gravity_mode') || 'detail';
    let currentFilter = 'all';
    let currentAuthor = 'all';
    let currentAnime = '';
    let currentSearch = '';

    const cardsGrid = document.getElementById('mainGrid');
    const searchInput = document.getElementById('searchInput');
    const animeSelect = document.getElementById('animeSelect');
    
    const authorChips = document.querySelectorAll('.author-chip');
    const gravChips = document.querySelectorAll('.grav-chip');

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
    const modalMercariBtn = document.getElementById('modalMercariBtn');

    const imageLightbox = document.getElementById('imageLightbox');
    const lightboxImg = document.getElementById('lightboxImg');
    const lightboxCloseBtn = document.getElementById('lightboxCloseBtn');

    function showToast(text) {{
        const toast = document.getElementById('toast');
        const toastMsg = document.getElementById('toastMsg');
        toastMsg.innerText = text;
        toast.classList.add('show');
        if (toastTimeout) clearTimeout(toastTimeout);
        toastTimeout = setTimeout(() => {{
            toast.classList.remove('show');
        }}, 2000);
    }}

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

        modalMercariBtn.onclick = () => {{
            const url = `https://jp.mercari.com/search?keyword=${{encodeURIComponent(item.prize_name)}}&status=sold_out&sort=created_time&order=desc`;
            window.open(url, '_blank');
        }};

        modalGravityTags.innerHTML = '';
        if (item.gravity_details && item.gravity_details.length > 0) {{
            item.gravity_details.forEach(g => {{
                const span = document.createElement('span');
                span.className = 'gravity-pill';
                span.textContent = g;
                modalGravityTags.appendChild(span);
            }});
        }} else {{
            modalGravityTags.innerHTML = '<span style="font-size:11px; color:#64748b;">個別重心数値記載なし (本文参照)</span>';
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

    function setClickMode(mode) {{
        currentClickMode = mode;
        localStorage.setItem('prize_gravity_mode', mode);
        updateModeButtons();
        if (mode === 'mercari') {{
            showToast('カードタップ時の動作を【メルカリ直接検索】に設定しました');
        }} else {{
            showToast('カードタップ時の動作を【詳細・重心プレビュー】に設定しました');
        }}
    }}

    function updateModeButtons() {{
        const btnDetail = document.getElementById('modeBtnDetail');
        const btnMercari = document.getElementById('modeBtnMercari');
        if (currentClickMode === 'mercari') {{
            btnMercari.className = 'mode-btn active mercari-mode';
            btnDetail.className = 'mode-btn';
        }} else {{
            btnDetail.className = 'mode-btn active';
            btnMercari.className = 'mode-btn';
        }}
    }}

    // 表示列数切替（calendar.html完全互換）
    function setGridColumns(cols, save = true) {{
        const grid = document.getElementById('mainGrid');
        if (!grid) return;
        grid.classList.remove('cols-2', 'cols-3', 'cols-4', 'cols-5', 'cols-6', 'cols-7', 'cols-8');
        grid.classList.add('cols-' + cols);
        
        document.querySelectorAll('.col-btn').forEach(btn => btn.classList.remove('active'));
        const activeBtn = document.getElementById('colBtn' + cols);
        if (activeBtn) activeBtn.classList.add('active');
        
        if (save) {{
            localStorage.setItem('prize_gravity_cols', cols);
            showToast(cols + '列表示に切り替えました');
        }}
    }}

    // 初期設定ロード
    (function initSettings() {{
        updateModeButtons();
        const storedCols = localStorage.getItem('prize_gravity_cols');
        if (storedCols) {{
            setGridColumns(parseInt(storedCols, 10), false);
        }} else {{
            const defaultCol = (window.innerWidth <= 650) ? 3 : 7;
            setGridColumns(defaultCol, false);
        }}
    }})();

    function handleCardClick(tweetId, prizeName) {{
        if (currentClickMode === 'mercari') {{
            const url = `https://jp.mercari.com/search?keyword=${{encodeURIComponent(prizeName)}}&status=sold_out&sort=created_time&order=desc`;
            window.open(url, '_blank');
            showToast('メルカリ検索を開きました: ' + prizeName);
        }} else {{
            const item = PRIZE_DATA.find(i => String(i.tweet_id) === String(tweetId));
            if (item) openModal(item);
        }}
    }}

    function filterAndRender() {{
        const query = currentSearch.toLowerCase().trim();

        let filtered = PRIZE_DATA.filter(item => {{
            if (currentAuthor !== 'all') {{
                const aName = (item.author_name || item.user_name || '');
                if (!aName.includes(currentAuthor)) return false;
            }}

            if (currentAnime && item.anime_title !== currentAnime) {{
                return false;
            }}

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

        filtered.sort((a, b) => String(b.created_at).localeCompare(String(a.created_at)));
        renderCards(filtered);
    }}

    function renderCards(items) {{
        if (items.length === 0) {{
            cardsGrid.innerHTML = `
                <div style="grid-column: 1 / -1; padding: 40px 20px; text-align: center; color: #64748b; background: #ffffff; border-radius: 8px; border: 1px dashed #cbd5e1;">
                    <p style="font-size: 14px; font-weight: 700;">条件に一致する景品が見つかりませんでした</p>
                    <p style="font-size: 12px; margin-top: 4px;">検索キーワードやフィルター条件を変更してお試しください。</p>
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
                    : '<span style="font-size:8.5px; color:#94a3b8;">本文記載</span>';

            const specs = [];
            if (item.figure_size) specs.push(`📏 ${{escapeHtml(item.figure_size)}}`);
            if (item.box_weight) specs.push(`⚖ ${{escapeHtml(item.box_weight)}}`);
            if (item.box_size) specs.push(`📦 ${{escapeHtml(item.box_size)}}`);

            const specsHtml = specs.length > 0
                ? `<div class="item-specs">${{specs.map(s => `<span>${{s}}</span>`).join('')}}</div>`
                : '';

            return `
                <div class="item-card" onclick="handleCardClick('${{item.tweet_id}}', '${{escapeHtml(item.prize_name)}}')">
                    <div class="img-wrap">
                        <span class="card-author-badge">${{escapeHtml(authorName)}}</span>
                        ${{mainImage 
                            ? `<img src="${{mainImage}}" alt="${{escapeHtml(item.prize_name)}}" loading="lazy">` 
                            : `<div class="no-img-text"><span>📷</span><span>No Image</span></div>`
                        }}
                        ${{mediaCount > 0 ? `<span class="card-photo-count">📷 ${{mediaCount}}</span>` : ''}}
                    </div>
                    <div class="info-wrap">
                        <div class="info-top">
                            <span class="anime-tag">${{escapeHtml(item.anime_title || 'その他')}}</span>
                            <div class="item-name" title="${{escapeHtml(item.prize_name)}}">${{escapeHtml(item.prize_name)}}</div>
                            <div class="gravity-badge-wrap">
                                ${{gravBadges}}
                            </div>
                        </div>
                        ${{specsHtml}}
                        <div class="card-bottom-bar">
                            <span>${{escapeHtml(item.created_at ? item.created_at.split(' ')[0] : '')}}</span>
                            <a href="${{item.tweet_url}}" target="_blank" rel="noopener noreferrer" class="card-x-link" onclick="event.stopPropagation()">
                                X ↗
                            </a>
                        </div>
                    </div>
                </div>
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

    searchInput.addEventListener('input', (e) => {{
        currentSearch = e.target.value;
        filterAndRender();
    }});

    animeSelect.addEventListener('change', (e) => {{
        currentAnime = e.target.value;
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
    limit_records = 3500
    if len(sys.argv) > 1:
        try:
            limit_records = int(sys.argv[1])
        except ValueError:
            pass

    data, sync_info = collect_data(limit_records=limit_records, target_year="2026")
    generate_html(data, sync_info=sync_info)

if __name__ == "__main__":
    main()
