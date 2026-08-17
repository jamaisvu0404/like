import os
import re
import json
import hashlib
import time

def generate_search_index(output_dir=None):
    if output_dir is None:
        output_dir = os.path.dirname(os.path.abspath(__file__))
        
    t0 = time.time()
    
    # 高速読み込みのため、ローカルSSD (C:\Users\pande\prize-calendar) があればそこから読み込み
    local_dir = r"C:\Users\pande\prize-calendar"
    read_dir = local_dir if os.path.exists(local_dir) else output_dir
    
    months = sorted([d for d in os.listdir(read_dir) if d.isdigit() and len(d) == 6])
    
    all_items = []
    
    month_names_map = {
        "202601": "2026年 1月",
        "202602": "2026年 2月",
        "202603": "2026年 3月",
        "202604": "2026年 4月",
        "202605": "2026年 5月",
        "202606": "2026年 6月",
        "202607": "2026年 7月",
        "202608": "2026年 8月",
        "202609": "2026年 9月",
        "202610": "2026年 10月",
        "202611": "2026年 11月",
    }
    
    month_counts = {}

    for m in months:
        cal_path = os.path.join(read_dir, m, "calendar.html")
        if not os.path.exists(cal_path):
            continue
            
        m_dir = os.path.join(read_dir, m)
        img_hashes = {}
        if os.path.exists(m_dir):
            for f in os.listdir(m_dir):
                if f.lower().endswith(('.webp', '.jpg', '.jpeg', '.png')):
                    fp = os.path.join(m_dir, f)
                    try:
                        with open(fp, "rb") as img_f:
                            h = hashlib.md5(img_f.read()).hexdigest()
                            img_hashes[h] = f
                    except Exception:
                        pass
        
        m_items = []
        current_date = ""
        
        with open(cal_path, "r", encoding="utf-8") as f:
            in_date = False
            day_str = ""
            weekday_str = ""
            
            in_card = False
            card_div_depth = 0
            card_lines = []
            
            for line in f:
                line_s = line.strip()
                
                if '<div class="date-cell' in line:
                    in_date = True
                    day_str = ""
                    weekday_str = ""
                    continue
                if in_date:
                    if '<div class="day">' in line:
                        day_str = re.sub(r'</?div[^>]*>', '', line).replace('<br>', ' ').strip()
                    elif '<div class="weekday">' in line:
                        weekday_str = re.sub(r'</?div[^>]*>', '', line).strip()
                    elif line_s.startswith('</div>'):
                        current_date = f"{day_str} {weekday_str}".strip()
                        in_date = False
                    continue
                    
                if '<div class="item-card"' in line:
                    in_card = True
                    card_div_depth = 1
                    card_lines = [line]
                    continue
                    
                if in_card:
                    card_lines.append(line)
                    card_div_depth += line.count('<div')
                    card_div_depth -= line.count('</div')
                    
                    if card_div_depth <= 0:
                        full_card = "".join(card_lines)
                        
                        click_m = re.search(r'handleCardClick\(this,\s*(.*?)\)', full_card)
                        raw_mercari = click_m.group(1).strip() if click_m else ""
                        try:
                            mercari_name = json.loads(raw_mercari)
                        except Exception:
                            mercari_name = raw_mercari.strip("'\"")
                            
                        title_m = re.search(r'title="([^"]*)"', full_card)
                        raw_title = title_m.group(1) if title_m else ""
                        
                        name_m = re.search(r'<p class="item-name">([^<]+)</p>', full_card)
                        title = name_m.group(1).strip() if name_m else raw_title
                        
                        maker_m = re.search(r'<span class="maker-tag [^"]*">([^<]+)</span>', full_card)
                        maker = maker_m.group(1).strip() if maker_m else ""
                        
                        size_m = re.search(r'<div class="item-size">[\s\S]*?<span>([^<]+)</span>', full_card)
                        size = size_m.group(1).strip() if size_m else ""
                        
                        img_file = ""
                        b64_m = re.search(r'<img src="data:[^;]+;base64,([^"]+)"', full_card)
                        if b64_m:
                            import base64
                            try:
                                raw_bytes = base64.b64decode(b64_m.group(1))
                                img_h = hashlib.md5(raw_bytes).hexdigest()
                                if img_h in img_hashes:
                                    img_file = f"{m}/{img_hashes[img_h]}"
                            except Exception:
                                pass
                        elif '<img src="' in full_card:
                            # Relative path case
                            rel_m = re.search(r'<img src="([^"]+)"', full_card)
                            if rel_m and not rel_m.group(1).startswith('http'):
                                img_file = f"{m}/{rel_m.group(1)}"
                        
                        month_label = month_names_map.get(m, f"{m[:4]}年{int(m[4:])}月")
                        
                        m_items.append({
                            "id": len(all_items) + len(m_items) + 1,
                            "month": m,
                            "monthName": month_label,
                            "date": current_date,
                            "title": title,
                            "mercari": mercari_name,
                            "maker": maker,
                            "size": size,
                            "img": img_file,
                            "calUrl": f"{m}/calendar.html"
                        })
                        
                        in_card = False
                        card_lines = []

        print(f"[{m}] {len(m_items)} 件抽出完了", flush=True)
        month_counts[m] = len(m_items)
        all_items.extend(m_items)

    print(f"\n合計 {len(all_items)} 件の商品データを {time.time() - t0:.2f} 秒で集約しました。", flush=True)
    
    # search_data.js (ブラウザで script タグとして読み込める形式)
    js_content = f"// 自動生成されたプライズフィギュア検索インデックスデータ ({len(all_items)}件)\nconst PRIZE_ITEMS = " + json.dumps(all_items, ensure_ascii=False) + ";\n"
    js_path = os.path.join(output_dir, "search_data.js")
    with open(js_path, "w", encoding="utf-8") as f:
        f.write(js_content)
        
    # search_data.json
    json_path = os.path.join(output_dir, "search_data.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(all_items, f, ensure_ascii=False, indent=2)
        
    print(f"出力完了: {js_path} ({os.path.getsize(js_path) // 1024} KB)")
    print(f"出力完了: {json_path} ({os.path.getsize(json_path) // 1024} KB)")
    
    # C:\Users\pande\prize-calendar への同期
    dst_dir = r"C:\Users\pande\prize-calendar"
    if os.path.exists(dst_dir) and dst_dir != output_dir:
        import shutil
        for fn in ["search_data.js", "search_data.json", "update_search_index.py"]:
            sp = os.path.join(output_dir, fn)
            dp = os.path.join(dst_dir, fn)
            if os.path.exists(sp):
                shutil.copy2(sp, dp)
        print(f"[同期] {dst_dir} へ検索データを同期しました。")
        
    return all_items, month_counts

if __name__ == "__main__":
    generate_search_index()

