import os
import requests
import csv
import re
import sys
import argparse
import base64
import mimetypes
import html
import json
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from collections import defaultdict

# 作品名マッピング辞書
SERIES_CLEAN_MAP = [
    (r'初音ミク|初音ミクシリーズ|ピアプロキャラクターズ|プロジェクトセカイ|プロセカ', '初音ミク'),
    (r'トイ・ストーリー|トイストーリー', 'トイストーリー'),
    (r'ワンピース|ONE PIECE', 'ワンピース'),
    (r'HUNTER[×xX]HUNTER|ハンターハンター', 'HUNTER×HUNTER'),
    (r'僕のヒーローアカデミア|ヒロアカ', 'ヒロアカ'),
    (r'チェンソーマン', 'チェンソーマン'),
    (r'鬼滅の刃', '鬼滅の刃'),
    (r'呪術廻戦', '呪術廻戦'),
    (r'ドラゴンボールZ|ドラゴンボールGT|ドラゴンボール超|ドラゴンボール', 'ドラゴンボール'),
    (r'BORUTO|NARUTO|ナルト', 'NARUTO'),
    (r'Re:ゼロ|Re:ゼロから始める異世界生活|リゼロ', 'リゼロ'),
    (r'ウマ娘|ウマ娘 プリティーダービー|ウマ娘 シンデレラグレイ', 'ウマ娘'),
    (r'葬送のフリーレン|フリーレン', 'フリーレン'),
    (r'魔法少女まどか☆マギカ|まどか☆マギカ|まどマギ', 'まどマギ'),
    (r'To LOVEる|とらぶる', 'To LOVEる'),
    (r'ブルーアーカイブ|ブルアカ', 'ブルアカ'),
    (r'ダンダダン', 'ダンダダン'),
    (r'ジョジョの奇妙な冒険|ジョジョ', 'ジョジョ'),
    (r'BLEACH|ブリーチ', 'BLEACH'),
    (r'機動戦士ガンダムUC|ガンダムUC', 'ガンダムUC'),
    (r'機動戦士ガンダム|ガンダム|Gundam', 'ガンダム'),
    (r'ホロライブ|hololive', 'ホロライブ'),
    (r'BanG Dream!|バンドリ|Ave Mujica', 'バンドリ'),
    (r'負けヒロインが多すぎる！|マケイン', 'マケイン'),
    (r'薬屋のひとりごと', '薬屋のひとりごと'),
    (r'その着せ替え人形は恋をする|着せ恋', '着せ恋'),
    (r'オーバーロード', 'オーバーロード'),
    (r'リトル・マーメイド|ディズニー|Disney', 'ディズニー'),
    (r'デジモン|デジモンアドベンチャー', 'デジモン'),
    (r'キン肉マン', 'キン肉マン'),
    (r'ルパン三世|LUPIN', 'ルパン三世'),
    (r'ローゼンメイデン', 'ローゼンメイデン'),
    (r'いちご100％|いちご100%', 'いちご100%'),
    (r'けいおん|けいおん！|けいおん!!', 'けいおん'),
    (r'魔都精兵のスレイブ', '魔都精兵のスレイブ'),
    (r'無職転生', '無職転生'),
    (r'涼宮ハルヒの憂鬱|涼宮ハルヒ', '涼宮ハルヒ'),
    (r'ドラゴンクエスト|ドラクエ', 'ドラクエ'),
    (r'春夏秋冬代行者', '春夏秋冬代行者'),
    (r'NEEDY GIRL OVERDOSE', 'NEEDY GIRL OVERDOSE'),
    (r'TinyTAN|タイニータン', 'TinyTAN'),
    (r'重音テト', '重音テト'),
    (r'千歳くんはラムネ瓶のなか', '千歳くんはラムネ瓶のなか'),
    (r'ばっどがーる', 'ばっどがーる'),
    (r'あの日見た花の名前を僕達はまだ知らない。|あの花', 'あの花'),
    (r'UNDERTALE|アンダーテール', 'UNDERTALE'),
    (r'エスターバニー', 'エスターバニー'),
    (r'クレヨンしんちゃん', 'クレヨンしんちゃん'),
    (r'都市伝説解体センター', '都市伝説解体センター'),
    (r'サンリオ|Sanrio', 'サンリオ'),
    (r'刃牙|刃牙道|グラップラー刃牙|バキ', '刃牙'),
    (r'ぶいすぽっ！|ぶいすぽ', 'ぶいすぽ'),
    (r'この素晴らしい世界に祝福を！|このすば', 'このすば'),
    (r'宇宙刑事ギャバン|ギャバン', 'ギャバン'),
    (r'テッド|ted2|ted', 'テッド'),
    (r'俺の妹がこんなに可愛いわけがない。|俺の妹', '俺の妹'),
    (r'デート・ア・ライブ', 'デート・ア・ライブ'),
    (r'貞子', '貞子'),
    (r'PANTY & STOCKING|パンティ＆ストッキング', 'パンティ ストッキング'),
    (r'ボンバーガール', 'ボンバーガール'),
    (r'カグラバチ', 'カグラバチ'),
    (r'ムーミン', 'ムーミン'),
    (r'ウルトラセブン|ウルトラマン', 'ウルトラセブン'),
    (r'ドットハック|\.hack', 'ドットハック'),
    (r'よふかしのうた', 'よふかしのうた'),
    (r'勝利の女神|NIKKE|ニケ', 'NIKKE'),
    (r'ちいかわ', 'ちいかわ'),
    (r'らき☆すた|らきすた', 'らきすた'),
    (r'東宝怪獣|ゴジラ|モスラ', 'モスラ'),
    (r'犬夜叉', '犬夜叉'),
    (r'ギャグマンガ日和', 'ギャグマンガ日和'),
    (r'トリコ', 'トリコ'),
    (r'おジャ魔女どれみ', 'おジャ魔女どれみ'),
    (r'魔女の旅々', '魔女の旅々'),
    (r'カイジ|逆境無頼カイジ', 'カイジ'),
    (r'ケロロ軍曹', 'ケロロ軍曹'),
]

# メルカリ検索で邪魔になるマイナーシリーズ・接頭語
NOISE_TERMS = [
    r'BANPRESTO\s*EVOLVE',
    r'HUNTING\s*ARCHIVES',
    r'THE\s*AMAZING\s*HEROES(?:-DX)?',
    r'Classical\s*tuning',
    r'組曲',
    r'より',
    r'DNA\s*モニタートップフィギュア',
    r'DNA\s*モニタートップ',
    r'モニタートップフィギュア',
    r'Fascinity\s*Figure',
    r'MeloDoll\s*Figure',
    r'Vivitフィギュア',
    r'Mometria',
    r'XStellar',
    r'Figuno',
    r'フィギュアコレクション',
    r'ポージングBIGソフビフィギュア',
    r'胸像センサーライト',
    r'のろいの胸像フィギュア',
    r'感知して動く',
    r'完璧超人始祖編リアルフィギュア',
    r'リアルフィギュア',
    r'ビッグアクションフィギュア',
    r'プレミアムフィギュアAve\s*Mujica',
    r'超宇宙刑事',
    r'Clearluxe',
    r'Flower\s*Fairy',
    r'Yumemirize',
    r'T-most',
    r'Trio-Try-iT(?:\s*Figure)?',
    r'Desktop\s*Cute',
    r'Aqua\s*Float\s*Girls',
    r'#hololive\s*IF',
    r'Break\s*time\s*collection(?:\s*vol\.\d+)?',
    r'History\s*Box',
    r'BLOOD\s*OF\s*SAIYANS',
    r'VIBRATION\s*STARS',
    r'GLITTER&GLAMOURS',
    r'CROSS\s*POSING',
    r'ESPRESTO(?:-Excite\s*Motions)?',
    r'FIGURIZMα',
    r'フィグライフ!?',
    r'きゅむころ',
    r'あみこっと',
    r'くれーんぽっぷ',
    r'ふぃぐきゅーぶ',
    r'にゃーるずこれくしょん',
    r'きゃらごん',
    r'デジヴァイスタンド!?',
    r'プチっと灯りマス',
    r'むにっとハートライト',
]

TERM_REPLACEMENTS = [
    (r'MONKEY\.?D\.?LUFFY', 'モンキー D ルフィ'),
    (r'MARSHALL\.?D\.?TEACH', 'マーシャル D ティーチ'),
    (r'GEAR\s*5|GEAR5', 'ギア5'),
    (r'ENEL', 'エネル'),
    (r'UZUMAKI\s*NARUTO', 'うずまきナルト'),
    (r'UCHIHA\s*ITACHI', 'うちはイタチ'),
    (r'IZUKU\s*MIDORIYA', '緑谷出久'),
    (r'TORU\s*HAGAKURE', '葉隠透'),
    (r'MINA\s*ASHIDO', '芦戸三奈'),
    (r'TSUYU\s*ASUI', '蛙吹梅雨'),
    (r'KYOKA\s*JIRO', '耳郎響香'),
    (r'TANJIRO\s*KAMADO', '竈門炭治郎'),
    (r'NEZUKO\s*KAMADO', '竈門禰豆子'),
    (r'YUJI\s*ITADORI', '虎杖悠仁'),
    (r'MEGUMI\s*FUSHIGURO', '伏黒恵'),
    (r'HANMA\s*BAKI', '範馬刃牙'),
    (r'(?:ZARAKI\s*KENPACHI|KENPACHI\s*ZARAKI)', '更木剣八'),
    (r'GOGETA', 'ゴジータ'),
    (r'POWER', 'パワー'),
    (r'PANTY', 'パンティ'),
    (r'STOCKING', 'ストッキング'),
    (r'Scanty', 'スキャンティ'),
    (r'Kneesocks', 'ニーソックス'),
    (r'ted2|ted', 'テッド'),
]

ROMAN_NUMS = [
    (r'Ⅰ', '1'), (r'Ⅱ', '2'), (r'Ⅲ', '3'), (r'Ⅳ', '4'), (r'Ⅴ', '5'),
    (r'Ⅵ', '6'), (r'Ⅶ', '7'), (r'Ⅷ', '8'), (r'Ⅸ', '9'), (r'Ⅹ', '10')
]

def generate_mercari_search_title(full_title):
    raw = full_title.strip()
    
    # 1. 作品名の特定
    series_name = ""
    m_bracket = re.search(r'[『【「［\[（〈(]([^』】」］\]）〉)]+)[』】」］\]）〉)]', raw)
    bracket_content = m_bracket.group(1) if m_bracket else ""
    
    if bracket_content:
        for pat, s_name in SERIES_CLEAN_MAP:
            if re.search(pat, bracket_content, re.IGNORECASE):
                series_name = s_name
                break
    if not series_name:
        for pat, s_name in SERIES_CLEAN_MAP:
            if re.search(pat, raw, re.IGNORECASE):
                series_name = s_name
                break

    # 2. 景品名部分の切り出し（先頭括弧の除去）
    t = raw
    t = re.sub(r'^(?:劇場版|TVアニメ|アニメ|映画)?\s*[『【「［\[（〈(][^』】」］\]）〉)]+[』】」］\]）〉)]\s*', '', t).strip()
    t = re.sub(r'^[『【「［\[（〈(][^』】」］\]）〉)]+[』】」］\]）〉)]\s*', '', t).strip()
    
    if '。' in t:
        parts = t.split('。', 1)
        if len(parts) > 1 and parts[1].strip():
            t = parts[1].strip()
            
    t = re.sub(r'^(?:劇場版|TVアニメ|映画)?\s*[^〈<]+[〈<][^〉>]+[〉>]\s*', '', t).strip()
    
    m_naruto = re.search(r'(?:GENERATIONS|BORUTO|NARUTO)\s*(.*)', t)
    if m_naruto:
        t = m_naruto.group(1).strip()
        
    m_jojo = re.search(r'ダイヤモンドは砕けない\s*(.*)', t)
    if m_jojo:
        t = m_jojo.group(1).strip()
        
    m_class = re.search(r'友だちになった\s*(.*)', t)
    if m_class:
        t = m_class.group(1).strip()

    # 3. 英語・用語のカナ変換
    for pat, rep in TERM_REPLACEMENTS:
        t = re.sub(pat, rep, t, flags=re.IGNORECASE)

    # 4. ローマ数字の変換
    for r_num, a_num in ROMAN_NUMS:
        t = t.replace(r_num, a_num)

    # 5. ノイズシリーズ名の除去（長い順に置換）
    for noise in sorted(NOISE_TERMS, key=len, reverse=True):
        t = re.sub(noise, ' ', t, flags=re.IGNORECASE)

    # 6. 「フィギュアー」「ムチュートフィギュアー」等の語尾処理
    t = re.sub(r'ムチュート(?:フィギュア|フィギュアー)?ー*', 'ムチュート ', t)
    t = re.sub(r'(?:フィギュア|Figure|figure)ー+', 'フィギュア ', t)
    t = re.sub(r'ッッ+', ' ', t)

    # 7. 全記号のスペース置換
    t = re.sub(r'[^\u4e00-\u9fff\u3040-\u309f\u30a1-\u30fa\u30fca-zA-Z0-9\s]', ' ', t)
    # カタカナ直後以外の長音符のみ除去（サニー号などのカタカナ＋長音符は保護）
    t = re.sub(r'(?<![ぁ-んァ-ヶ])ー+', ' ', t)
    t = re.sub(r'(?<![ぁ-んァ-ヶ])ー+(?=[一-龥a-zA-Z0-9])', ' ', t)
    t = re.sub(r'\s+ー+\s*|^ー+\s*', ' ', t)

    # 景品名単語の重複除去
    t_words = []
    for w in t.split():
        w = w.strip()
        if w and w not in t_words:
            t_words.append(w)
    t_clean = " ".join(t_words)

    # 8. 「フィギュア」補完判定
    has_type_keyword = any(k in (series_name + " " + t_clean) for k in ['フィギュア', 'ソフビ', 'スピーカー', 'ライト', '提灯', 'スタンド', 'タオル', 'ワーコレ', 'リモコンカー', 'ぬいぐるみ', 'マスコット'])

    # 9. キーワードの合成
    tokens = []
    if series_name:
        tokens.append(series_name)
    if t_clean:
        tokens.append(t_clean)
    if not has_type_keyword:
        tokens.append('フィギュア')

    result = " ".join(tokens)
    return re.sub(r'\s+', ' ', result).strip()

def main():
    parser = argparse.ArgumentParser(description="URLからプライズフィギュア情報を抽出し、カレンダーHTMLを自動生成します")
    parser.add_argument("url", help="対象のURL (例: https://tokutame.net/prize-matome-202608/)")
    args = parser.parse_args()
    
    url = args.url
    
    # URLから年月を抽出
    m_url = re.search(r'matome-(\d{6})', url)
    if m_url:
        target_month_str = m_url.group(1)
        target_month_display = f"{target_month_str[:4]}年{int(target_month_str[4:])}月"
    else:
        target_month_str = "latest"
        target_month_display = "今月"
        
    base_dir = os.path.dirname(os.path.abspath(__file__))
    output_dir = os.path.join(base_dir, target_month_str)
    os.makedirs(output_dir, exist_ok=True)
    
    print(f"[{target_month_display}] Fetching HTML from {url}...")
    response = requests.get(url)
    response.raise_for_status()
    response.encoding = response.apparent_encoding
    soup = BeautifulSoup(response.text, "html.parser")
    
    # --- データ抽出 ---
    data = []
    headings = soup.find_all(['h3', 'h4'])
    for h in headings:
        title = h.text.strip()
        if any(x in title for x in ['関連リンク', '人気記事', '注目記事', 'まとめ', 'プライズ予約', 'オンラインクレーンゲーム特典']):
            continue
            
        sibling = h.find_next_sibling()
        img_url = ""
        details_text = ""
        desc_text = ""
        
        for _ in range(4):
            if not sibling: break
            if sibling.name in ['figure', 'div']:
                img = sibling.find('img')
                if img and img.get('src'):
                    img_url = img.get('src')
            elif sibling.name == 'p':
                t = sibling.text.strip()
                if '●メーカー' in t or '●予定' in t or '●種類' in t:
                    details_text += t
                else:
                    if '購入・相場' not in t and '出典' not in t:
                        desc_text += t + " "
            sibling = sibling.find_next_sibling()

        if not img_url and not details_text:
            continue
            
        maker = ""
        size = ""
        date = ""
        
        m = re.search(r'●メーカー[：:]\s*([^●]+)', details_text)
        if m: maker = m.group(1).strip()
            
        m = re.search(r'●種類[、・]サイズ[：:]\s*([^●]+)', details_text)
        if m: size = m.group(1).strip()
            
        m = re.search(r'●予定[：:]\s*([^●]+)', details_text)
        if m: date = m.group(1).strip()
            
        local_img_filename = ""
        if img_url:
            parsed_url = urlparse(img_url)
            filename = os.path.basename(parsed_url.path)
            if not filename: filename = "image.jpg"
            local_img_path = os.path.join(output_dir, filename)
            
            # キャッシュ確認（既に存在する場合はダウンロードをスキップ）
            if os.path.exists(local_img_path) and os.path.getsize(local_img_path) > 0:
                local_img_filename = filename
            else:
                try:
                    img_resp = requests.get(img_url, timeout=15)
                    img_resp.raise_for_status()
                    with open(local_img_path, 'wb') as f:
                        f.write(img_resp.content)
                    local_img_filename = filename
                except Exception as e:
                    print(f"Failed to download {img_url}: {e}")
                
        data.append({
            "商品名": title,
            "メルカリ検索名": generate_mercari_search_title(title),
            "メーカー": maker,
            "種類・サイズ": size,
            "予定日": date,
            "説明": desc_text.strip(),
            "画像ファイル": local_img_filename,
            "画像URL": img_url
        })

    # --- カレンダー生成 ---
    data_by_date = defaultdict(list)
    for row in data:
        date_str = row["予定日"].strip()
        data_by_date[date_str].append(row)

    def parse_date_key(d_str):
        m1 = re.search(r'(\d+)日', d_str)
        if m1: return int(m1.group(1))
        m2 = re.search(r'(\d+)週', d_str)
        if m2: return 100 + int(m2.group(1))
        return 999

    sorted_dates = sorted(data_by_date.keys(), key=parse_date_key)
    
    # 月選択プルダウンのオプション生成
    available_months = [
        ("202601", "2026年 1月"),
        ("202602", "2026年 2月"),
        ("202603", "2026年 3月"),
        ("202604", "2026年 4月"),
        ("202605", "2026年 5月"),
        ("202606", "2026年 6月"),
        ("202607", "2026年 7月"),
        ("202608", "2026年 8月"),
        ("202609", "2026年 9月"),
        ("202610", "2026年 10月"),
        ("202611", "2026年 11月"),
    ]
    month_options_html = ""
    for m_val, m_lbl in available_months:
        sel = "selected" if m_val == target_month_str else ""
        month_options_html += f'<option value="{m_val}" {sel}>{m_lbl}</option>'

    calendar_html_path = os.path.join(output_dir, "calendar.html")
    html_content = f"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
<title>プライズ景品 入荷情報 フィギュア - {target_month_display}</title>
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
    .month-select-wrap {{
        display: inline-flex;
        align-items: center;
        background: #ffffff;
        border-radius: 20px;
        padding: 2px 10px 2px 8px;
        box-shadow: 0 2px 6px rgba(0,0,0,0.15);
        gap: 4px;
    }}
    .month-select-wrap .month-icon {{
        font-size: 13px;
    }}
    .month-dropdown {{
        border: none;
        background: transparent;
        color: var(--primary-dark);
        font-size: 13px;
        font-weight: 800;
        cursor: pointer;
        outline: none;
        padding: 3px 0;
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

    .suffix-control-wrap {{
        display: flex;
        align-items: center;
        gap: 6px;
        flex-wrap: wrap;
    }}
    .suffix-toggle-label {{
        display: flex;
        align-items: center;
        gap: 4px;
        cursor: pointer;
        font-size: 12px;
        font-weight: 600;
        user-select: none;
    }}
    .suffix-toggle-label input[type="checkbox"] {{
        width: 15px;
        height: 15px;
        cursor: pointer;
        accent-color: #ffffff;
    }}
    .suffix-input-box {{
        padding: 4px 8px;
        font-size: 12px;
        border-radius: 5px;
        border: 1px solid rgba(255,255,255,0.4);
        background: #ffffff;
        color: #0f172a;
        font-weight: 600;
        outline: none;
        width: 90px;
    }}
    .quick-tag-btn {{
        background: rgba(255,255,255,0.2);
        color: #fff;
        border: 1px solid rgba(255,255,255,0.4);
        padding: 3px 8px;
        border-radius: 4px;
        font-size: 11px;
        font-weight: 600;
        cursor: pointer;
    }}
    .quick-tag-btn.active {{
        background: #ffffff;
        color: var(--primary-dark);
        border-color: #ffffff;
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
        .date-cell {{
            min-height: 70px !important;
            padding: 6px 2px !important;
            border-radius: 6px !important;
        }}
        .date-cell .day {{
            font-size: 22px !important;
        }}
        .date-cell .weekday {{
            font-size: 11px !important;
            padding: 1px 4px !important;
            margin-top: 2px !important;
        }}
        .info-wrap {{
            padding: 4px 4px 6px !important;
            gap: 3px !important;
        }}
        .maker-tag {{
            font-size: 8.5px !important;
            padding: 1px 4px !important;
        }}
        .item-name {{
            font-size: 9.5px !important;
            line-height: 1.25 !important;
            display: -webkit-box;
            -webkit-line-clamp: 3;
            -webkit-box-orient: vertical;
            overflow: hidden;
        }}
        .item-size {{
            font-size: 8.5px !important;
            margin-top: 1px !important;
            padding-top: 2px !important;
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
    
    /* 日付セル */
    .date-cell {{
        border-radius: 8px;
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        color: #fff;
        font-weight: bold;
        padding: 12px 6px;
        box-shadow: 0 2px 6px rgba(0,0,0,0.12);
        min-height: 110px;
        text-align: center;
    }}
    .date-color-1 {{ background: linear-gradient(135deg, #d4a373 0%, #bc6c25 100%); }}
    .date-color-2 {{ background: linear-gradient(135deg, #6c757d 0%, #495057 100%); }}
    .date-color-3 {{ background: linear-gradient(135deg, #2a9d8f 0%, #264653 100%); }}
    .date-color-4 {{ background: linear-gradient(135deg, #e76f51 0%, #f4a261 100%); }}
    .date-color-5 {{ background: linear-gradient(135deg, #457b9d 0%, #1d3557 100%); }}
    
    .date-cell .day {{
        font-size: 32px;
        line-height: 1.1;
        font-weight: 800;
        text-shadow: 0 2px 4px rgba(0,0,0,0.2);
    }}
    .date-cell .weekday {{
        font-size: 14px;
        margin-top: 4px;
        background: rgba(255,255,255,0.25);
        padding: 2px 6px;
        border-radius: 10px;
    }}
    
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
    .item-card.copied-flash {{
        animation: flashHighlight 0.4s ease;
    }}
    @keyframes flashHighlight {{
        0% {{ box-shadow: 0 0 0 3px #22c55e; border-color: #22c55e; }}
        100% {{ box-shadow: 0 2px 5px rgba(0,0,0,0.03); border-color: var(--border-color); }}
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
        transform: scale(1.03);
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
    
    /* メーカータグ */
    .maker-tag {{
        font-size: 9.5px;
        font-weight: 700;
        padding: 1px 5px;
        border-radius: 4px;
        display: inline-block;
        width: fit-content;
        letter-spacing: 0.2px;
    }}
    .maker-banpresto {{ background-color: #e0f2fe; color: #0369a1; border: 1px solid #bae6fd; }}
    .maker-sega {{ background-color: #dbeafe; color: #1d4ed8; border: 1px solid #bfdbfe; }}
    .maker-furyu {{ background-color: #fce7f3; color: #be185d; border: 1px solid #fbcfe8; }}
    .maker-taito {{ background-color: #dcfce7; color: #15803d; border: 1px solid #bbf7d0; }}
    .maker-bushiroad {{ background-color: #ffedd5; color: #c2410c; border: 1px solid #fed7aa; }}
    .maker-konami {{ background-color: #fee2e2; color: #b91c1c; border: 1px solid #fecaca; }}
    .maker-other {{ background-color: #f1f5f9; color: #475569; border: 1px solid #e2e8f0; }}
    
    /* タイトル */
    .item-name {{
        font-size: 10.5px;
        font-weight: 700;
        line-height: 1.35;
        color: #0f172a;
        word-break: break-word;
        margin: 0;
    }}
    
    /* サイズ・種類 */
    .item-size {{
        font-size: 9.5px;
        color: #64748b;
        font-weight: 500;
        line-height: 1.25;
        display: flex;
        align-items: flex-start;
        gap: 2px;
        margin-top: 1px;
        padding-top: 3px;
        border-top: 1px dashed #f1f5f9;
    }}
    .item-size .size-icon {{
        font-size: 9px;
        color: #94a3b8;
        flex-shrink: 0;
    }}

    /* トースト通知 */
    #toast {{
        position: fixed;
        bottom: 20px;
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
</style>
</head>
<body>
<div class="container">
    <div class="header">
        <div class="header-top">
            <div class="header-left">
                <a href="../index.html" class="nav-top-btn">
                    <span>🏠</span><span>トップへ</span>
                </a>
                <div class="month-select-wrap">
                    <span class="month-icon">📅</span>
                    <select id="monthSelect" class="month-dropdown" onchange="if(this.value) location.href='../' + this.value + '/calendar.html'">
                        {month_options_html}
                    </select>
                </div>
                <h1>プライズ景品 入荷情報 フィギュア</h1>
            </div>
        </div>
        
        <!-- コントロールツールバー -->
        <div class="header-toolbar">
            <div class="toolbar-group">
                <span class="toolbar-label">クリック:</span>
                <div class="mode-btn-group">
                    <button type="button" class="mode-btn active mercari-mode" id="modeBtnMercari" onclick="setClickMode('mercari')">
                        <span>🔴</span> メルカリ検索
                    </button>
                    <button type="button" class="mode-btn" id="modeBtnCopy" onclick="setClickMode('copy')">
                        <span>📋</span> コピー
                    </button>
                </div>
            </div>

            <div class="toolbar-group">
                <span class="toolbar-label">表示列数:</span>
                <div class="col-btn-group">
                    <button type="button" class="col-btn" id="colBtn2" onclick="setGridColumns(2)">2列</button>
                    <button type="button" class="col-btn active" id="colBtn3" onclick="setGridColumns(3)">3列</button>
                    <button type="button" class="col-btn" id="colBtn4" onclick="setGridColumns(4)">4列</button>
                    <button type="button" class="col-btn" id="colBtn5" onclick="setGridColumns(5)">5列</button>
                    <button type="button" class="col-btn" id="colBtn6" onclick="setGridColumns(6)">6列</button>
                    <button type="button" class="col-btn" id="colBtn7" onclick="setGridColumns(7)">7列</button>
                    <button type="button" class="col-btn" id="colBtn8" onclick="setGridColumns(8)">8列</button>
                </div>
            </div>
            
            <div class="suffix-control-wrap">
                <label class="suffix-toggle-label">
                    <input type="checkbox" id="suffixCheckbox" checked>
                    <span>追加:</span>
                </label>
                <input type="text" id="suffixInput" class="suffix-input-box" value="箱無し" placeholder="追加テキスト">
                <button type="button" class="quick-tag-btn active" id="tagBtnHakonashi" onclick="setSuffixTag('箱無し')">箱無し</button>
                <button type="button" class="quick-tag-btn" id="tagBtnMikaifu" onclick="setSuffixTag('未開封')">未開封</button>
                <button type="button" class="quick-tag-btn" id="tagBtnClear" onclick="clearSuffixTag()">なし</button>
            </div>
        </div>
    </div>
    <div class="grid" id="mainGrid">
"""

    def get_maker_class(m_text):
        if not m_text: return "maker-other"
        if "バンプレスト" in m_text or "BANDAI" in m_text: return "maker-banpresto"
        if "セガ" in m_text or "SEGA" in m_text: return "maker-sega"
        if "フリュー" in m_text or "FuRyu" in m_text: return "maker-furyu"
        if "タイトー" in m_text or "TAITO" in m_text: return "maker-taito"
        if "ブシロード" in m_text: return "maker-bushiroad"
        if "コナミ" in m_text or "KONAMI" in m_text: return "maker-konami"
        return "maker-other"

    color_idx = 1
    for date_str in sorted_dates:
        items = data_by_date[date_str]
        
        day_display = date_str
        weekday_display = ""
        m_day = re.search(r'(\d+)日\((.)\)', date_str)
        if m_day:
            day_display = m_day.group(1)
            weekday_display = f"({m_day.group(2)})"
        else:
            m_week = re.search(r'(\d+)週', date_str)
            if m_week:
                day_display = f"第\n{m_week.group(1)}\n週"
        
        day_html = day_display.replace('\n', '<br>')
        
        html_content += f"""
        <div class="date-cell date-color-{color_idx}">
            <div class="day">{day_html}</div>
            <div class="weekday">{weekday_display}</div>
        </div>
        """
        
        color_idx = (color_idx % 5) + 1
        
        for item in items:
            img_src = item["画像ファイル"]
            if not img_src:
                img_src_data = "https://via.placeholder.com/200?text=No+Image"
            else:
                img_path = os.path.join(output_dir, img_src)
                if os.path.exists(img_path):
                    with open(img_path, "rb") as f:
                        b64_data = base64.b64encode(f.read()).decode("utf-8")
                        mime_type = mimetypes.guess_type(img_path)[0] or "image/jpeg"
                        img_src_data = f"data:{mime_type};base64,{b64_data}"
                else:
                    img_src_data = img_src
                    
            title = item["商品名"]
            mercari_title = item["メルカリ検索名"]
            maker = item["メーカー"] if item["メーカー"] else "メーカー未記載"
            size = item["種類・サイズ"] if item["種類・サイズ"] else "サイズ未記載"
            
            maker_class = get_maker_class(maker)
            title_escaped = html.escape(title)
            maker_escaped = html.escape(maker)
            size_escaped = html.escape(size)
            mercari_title_json = json.dumps(mercari_title)
            
            html_content += f"""
        <div class="item-card" onclick='handleCardClick(this, {mercari_title_json})' title="{title_escaped}">
            <div class="img-wrap">
                <img src="{img_src_data}" alt="{title_escaped}">
            </div>
            <div class="info-wrap">
                <div class="info-top">
                    <span class="maker-tag {maker_class}">{maker_escaped}</span>
                    <p class="item-name">{title_escaped}</p>
                </div>
                <div class="item-size">
                    <span class="size-icon">📏</span>
                    <span>{size_escaped}</span>
                </div>
            </div>
        </div>
            """

    html_content += f"""
    </div>
</div>

<div id="toast">
    <span class="toast-icon">✓</span>
    <span id="toastMsg">キーワードをコピーしました</span>
</div>

<script>
    let toastTimeout = null;
    let currentClickMode = localStorage.getItem('prize_calendar_mode') || 'mercari';

    // ローカルストレージ復元
    const storedSuffix = localStorage.getItem('prize_calendar_suffix');
    const storedEnabled = localStorage.getItem('prize_calendar_suffix_enabled');
    if (storedSuffix !== null) {{
        document.getElementById('suffixInput').value = storedSuffix;
    }}
    if (storedEnabled !== null) {{
        document.getElementById('suffixCheckbox').checked = (storedEnabled === 'true');
    }}
    updateTagButtons();
    updateModeButtons();

    // 列数設定復元
    const storedCols = localStorage.getItem('prize_calendar_cols');
    if (storedCols) {{
        setGridColumns(parseInt(storedCols, 10), false);
    }}

    document.getElementById('suffixInput').addEventListener('input', function() {{
        localStorage.setItem('prize_calendar_suffix', this.value);
        updateTagButtons();
    }});

    document.getElementById('suffixCheckbox').addEventListener('change', function() {{
        localStorage.setItem('prize_calendar_suffix_enabled', this.checked);
        updateTagButtons();
    }});

    function setGridColumns(cols, save = true) {{
        const grid = document.getElementById('mainGrid');
        if (!grid) return;
        grid.classList.remove('cols-2', 'cols-3', 'cols-4', 'cols-5', 'cols-6', 'cols-7', 'cols-8');
        grid.classList.add('cols-' + cols);
        
        document.querySelectorAll('.col-btn').forEach(btn => btn.classList.remove('active'));
        const activeBtn = document.getElementById('colBtn' + cols);
        if (activeBtn) activeBtn.classList.add('active');
        
        if (save) {{
            localStorage.setItem('prize_calendar_cols', cols);
            showToast(cols + '列表示に切り替えました');
        }}
    }}

    function setClickMode(mode) {{
        currentClickMode = mode;
        localStorage.setItem('prize_calendar_mode', mode);
        updateModeButtons();
        if (mode === 'mercari') {{
            showToast('カードタップ時の動作を【メルカリ直接検索】に設定しました');
        }} else {{
            showToast('カードタップ時の動作を【名前コピー】に設定しました');
        }}
    }}

    function updateModeButtons() {{
        const btnMercari = document.getElementById('modeBtnMercari');
        const btnCopy = document.getElementById('modeBtnCopy');
        if (currentClickMode === 'mercari') {{
            btnMercari.className = 'mode-btn active mercari-mode';
            btnCopy.className = 'mode-btn';
        }} else {{
            btnMercari.className = 'mode-btn';
            btnCopy.className = 'mode-btn active';
        }}
    }}

    function setSuffixTag(text) {{
        const input = document.getElementById('suffixInput');
        const checkbox = document.getElementById('suffixCheckbox');
        input.value = text;
        checkbox.checked = true;
        localStorage.setItem('prize_calendar_suffix', text);
        localStorage.setItem('prize_calendar_suffix_enabled', 'true');
        updateTagButtons();
    }}

    function clearSuffixTag() {{
        const checkbox = document.getElementById('suffixCheckbox');
        checkbox.checked = false;
        localStorage.setItem('prize_calendar_suffix_enabled', 'false');
        updateTagButtons();
    }}

    function updateTagButtons() {{
        const inputVal = document.getElementById('suffixInput').value.trim();
        const isChecked = document.getElementById('suffixCheckbox').checked;
        
        document.querySelectorAll('.quick-tag-btn').forEach(btn => btn.classList.remove('active'));
        if (!isChecked) {{
            const clearBtn = document.getElementById('tagBtnClear');
            if (clearBtn) clearBtn.classList.add('active');
        }} else {{
            if (inputVal === '箱無し') document.getElementById('tagBtnHakonashi')?.classList.add('active');
            else if (inputVal === '未開封') document.getElementById('tagBtnMikaifu')?.classList.add('active');
        }}
    }}

    function getSuffixText() {{
        const checkbox = document.getElementById('suffixCheckbox');
        const input = document.getElementById('suffixInput');
        if (checkbox && checkbox.checked && input) {{
            const val = input.value.trim();
            if (val.length > 0) {{
                return ' ' + val;
            }}
        }}
        return '';
    }}

    function showToast(text) {{
        const toast = document.getElementById('toast');
        const toastMsg = document.getElementById('toastMsg');
        toastMsg.innerText = text;
        toast.classList.add('show');
        
        if (toastTimeout) clearTimeout(toastTimeout);
        toastTimeout = setTimeout(() => {{
            toast.classList.remove('show');
        }}, 2200);
    }}

    function openMercariSearch(baseName, event) {{
        if (event) event.stopPropagation();
        const fullText = baseName + getSuffixText();
        const url = `https://jp.mercari.com/search?keyword=${{encodeURIComponent(fullText)}}&status=sold_out&sort=created_time&order=desc`;
        window.open(url, '_blank');
        showToast('メルカリ検索を開きました: ' + fullText);
    }}

    function copyItemName(cardEl, baseName, event) {{
        if (event) event.stopPropagation();
        const fullText = baseName + getSuffixText();
        
        if (navigator.clipboard && window.isSecureContext) {{
            navigator.clipboard.writeText(fullText).then(() => {{
                showToast('コピーしました: ' + fullText);
            }}).catch(() => {{
                fallbackCopy(fullText);
            }});
        }} else {{
            fallbackCopy(fullText);
        }}
        
        if (cardEl) {{
            cardEl.classList.remove('copied-flash');
            void cardEl.offsetWidth; // reflow
            cardEl.classList.add('copied-flash');
        }}
    }}

    function handleCardClick(cardEl, baseName) {{
        if (currentClickMode === 'mercari') {{
            openMercariSearch(baseName);
            if (cardEl) {{
                cardEl.classList.remove('copied-flash');
                void cardEl.offsetWidth;
                cardEl.classList.add('copied-flash');
            }}
        }} else {{
            copyItemName(cardEl, baseName);
        }}
    }}

    function fallbackCopy(name) {{
        const textArea = document.createElement("textarea");
        textArea.value = name;
        textArea.style.position = "fixed";
        textArea.style.opacity = "0";
        document.body.appendChild(textArea);
        textArea.focus();
        textArea.select();
        try {{
            document.execCommand('copy');
            showToast('コピーしました: ' + name);
        }} catch (err) {{
            alert("コピーに失敗しました: " + name);
        }}
        document.body.removeChild(textArea);
    }}
</script>
</body>
</html>
"""

    with open(calendar_html_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    print(f"成功: {target_month_display} のカレンダーHTMLと画像データを {output_dir} に出力しました。")

    # --- GitHub への自動同期 ＆ プッシュ ---
    sync_and_push_to_github(base_dir, target_month_str)

def sync_and_push_to_github(src_dir, target_month_str):
    import shutil
    import subprocess
    
    dst_dir = r"C:\Users\pande\prize-calendar"
    if not os.path.exists(dst_dir):
        os.makedirs(dst_dir, exist_ok=True)
        
    print(f"\n[GitHub自動同期] {dst_dir} へ最新ファイルを同期中...")
    
    # 必要ファイル・フォルダの同期
    items = ['index.html', 'auto_generate_calendar.py', 'generate_calendar.py', 'instructions_for_ai.md', '.gitignore', '.nojekyll']
    for it in items:
        s = os.path.join(src_dir, it)
        d = os.path.join(dst_dir, it)
    # 全月フォルダの同期（存在する月フォルダすべて）
    for entry in os.listdir(src_dir):
        if entry.isdigit() and len(entry) == 6:
            s_m = os.path.join(src_dir, entry)
            d_m = os.path.join(dst_dir, entry)
            if os.path.isdir(s_m):
                s_cal = os.path.join(s_m, 'calendar.html')
                d_cal = os.path.join(d_m, 'calendar.html')
                if os.path.exists(s_cal):
                    os.makedirs(d_m, exist_ok=True)
                    for _ in range(5):
                        try:
                            shutil.copy2(s_cal, d_cal)
                            break
                        except Exception:
                            import time
                            time.sleep(0.5)

    # Git Commit & Push
    try:
        subprocess.run(["git", "add", "."], cwd=dst_dir, capture_output=True, check=True)
        commit_res = subprocess.run(["git", "commit", "-m", f"Auto update calendar for {target_month_str}"], cwd=dst_dir, capture_output=True, text=True)
        print(f"[GitHub自動同期] コミット完了: {commit_res.stdout.strip() if commit_res.stdout else '変更なし'}")
        push_res = subprocess.run(["git", "push", "origin", "main"], cwd=dst_dir, capture_output=True, text=True)
        print(f"[GitHub自動同期] GitHubへプッシュ完了！\n公開URL: https://jamaisvu0404.github.io/like/")
    except Exception as e:
        print(f"[GitHub自動同期] プッシュスキップまたはエラー: {e}")

if __name__ == "__main__":
    main()
