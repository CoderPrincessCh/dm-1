import requests
import xml.etree.ElementTree as ET
from collections import OrderedDict, defaultdict
from openpyxl import Workbook
from openpyxl.styles import Font
from datetime import datetime
import re

SEARCH_API = "https://www.missevan.com/sound/getsearch"
DANMU_API = "https://www.missevan.com/sound/getdm"

# 中文数字映射
CN_NUM_MAP = {
    "一": 1, "二": 2, "三": 3, "四": 4, "五": 5,
    "六": 6, "七": 7, "八": 8, "九": 9, "十": 10
}

def to_arabic_number(text: str) -> int:
    """支持输入阿拉伯数字或中文数字，统一转换为 int"""
    text = text.strip()
    if text.isdigit():
        return int(text)
    return CN_NUM_MAP.get(text, -1)

def match_season(name: str, season_number: int):
    chinese_nums = {v: k for k, v in CN_NUM_MAP.items()}
    chinese_num = chinese_nums.get(season_number, "")
    season_patterns = [
        rf"第\s*{season_number}\s*季",
        rf"第{season_number}季",
        rf"第\s*{chinese_num}\s*季",
        rf"第{chinese_num}季",
        rf"Season\s*{season_number}",
    ]
    for pat in season_patterns:
        if re.search(pat, name, re.IGNORECASE):
            return True
    return False

def search_drama(keyword: str):
    page = 1
    page_size = 30
    keyword_lower = keyword.strip().lower()
    season_grouped = defaultdict(list)  # 季号 -> [(id, name)]

    while True:
        params = {
            "s": keyword,
            "p": page,
            "type": 3,
            "page_size": page_size
        }
        try:
            response = requests.get(SEARCH_API, params=params)
            response.raise_for_status()
            data = response.json()
            datas = data.get("info", {}).get("Datas", [])

            for item in datas:
                name = item.get("soundstr", "")
                if item.get("pay_type") != "2":
                    continue
                if keyword_lower not in name.lower():
                    continue

                # 尝试提取“第X季”或“Season X”
                matched = False
                for season in range(1, 11):  # 假设最多到第十季
                    if match_season(name, season):
                        season_grouped[season].append((item["id"], name))
                        matched = True
                        break
                if not matched:
                    season_grouped[1].append((item["id"], name))  # 把未识别季归为“第一季”


            print(f"📄 第 {page} 页，共 {len(datas)} 条数据，已匹配季数：{len(season_grouped)}")

            if len(datas) < page_size:
                break
            page += 1

        except Exception as e:
            print(f"❌ 请求第 {page} 页失败:", e)
            break

    return season_grouped

def fetch_danmu(soundid: str):
    try:
        response = requests.get(DANMU_API, params={"soundid": soundid})
        response.raise_for_status()
        return response.text
    except Exception as e:
        print(f"❌ 获取弹幕失败（soundid={soundid}）:", e)
        return None

def parse_danmu(xml_text: str, user_danmu_dict: OrderedDict):
    total_count = 0
    try:
        root = ET.fromstring(xml_text)
        for d in root.findall("d"):
            total_count += 1
            p_attr = d.attrib.get("p", "")
            parts = p_attr.split(",")
            if len(parts) >= 7:
                user_id = parts[6]
                if user_id not in user_danmu_dict:
                    user_danmu_dict[user_id] = d.text or ""
        return total_count
    except Exception as e:
        print("❌ 解析 XML 失败:", e)
        return 0

def export_to_excel(data: OrderedDict, filename="danmu_data.xlsx"):
    wb = Workbook()
    ws = wb.active
    ws.title = "弹幕数据"
    ws.append(["用户ID", "首次弹幕内容"])
    for cell in ws[1]:
        cell.font = Font(bold=True)

    for uid, content in data.items():
        ws.append([uid, content])

    wb.save(filename)
    print(f"✅ 已导出 Excel，共 {len(data)} 条记录 → {filename}")

def to_index(input_str: str) -> int:
    """将用户输入的中文数字或数字字符串转为索引（从1开始）"""
    cn_to_num = {
        '一': 1, '二': 2, '三': 3, '四': 4, '五': 5,
        '六': 6, '七': 7, '八': 8, '九': 9, '十': 10
    }
    input_str = input_str.strip()
    if input_str.isdigit():
        return int(input_str)
    return cn_to_num.get(input_str, -1)

def main():
    keyword = input("请输入剧名关键词：").strip()
    if not keyword:
        print("⚠️ 关键词不能为空")
        return

    print("🔍 正在搜索剧集...")
    season_grouped = search_drama(keyword)
    if not season_grouped:
        print("❌ 未找到符合条件的剧集")
        return

    sorted_seasons = sorted(season_grouped.keys())  # 例：[1, 2, 3] 或 [0, 1, 2]
    print(f"\n🎬 找到以下季数：")
    for idx, season in enumerate(sorted_seasons):
        label = f"第{season}季"
        # 尝试提取剧名前缀：取每一季第一个 soundstr 的前缀（去除“第X季”等）
        sample_title = season_grouped[season][0][1]
        # 去掉常见“第X季”描述
        clean_title = re.sub(r"第[\d一二三四五六七八九十]+季", "", sample_title)
        clean_title = clean_title.strip(" -【】「」[]")
        print(f"{idx + 1}. {clean_title} - {label}（共 {len(season_grouped[season])} 集）")


    input_str = input("\n请选择要处理的季（输入序号或中文数字）：").strip()
    choice = to_index(input_str)

    if not (1 <= choice <= len(sorted_seasons)):
        print("❌ 无效选择，程序终止。")
        return

    selected_season = sorted_seasons[choice - 1]
    selected_sounds = season_grouped[selected_season]
    label = f"第{selected_season}季" if selected_season > 0 else "未识别季"

    print(f"\n📥 正在获取弹幕：{label}（共 {len(selected_sounds)} 集）")
    user_danmu_dict = OrderedDict()
    total_danmu = 0

    for soundid, name in selected_sounds:
        print(f"→ 获取：{name} (ID: {soundid})")
        xml_text = fetch_danmu(soundid)
        if xml_text:
            count = parse_danmu(xml_text, user_danmu_dict)
            total_danmu += count

    print("\n📊 统计结果：")
    print(f"🔹 实时付费弹幕总条数：{total_danmu}")
    print(f"🔹 实时付费弹幕去重后id数：{len(user_danmu_dict)}")
    print(f"🕒 当前时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"♣ 娱乐分享，请勿作为依据☺")

    export_choice = input("\n是否导出去重后的实时付费弹幕 Excel？(Y/N)：").strip().lower()
    if export_choice == 'y':
        clean_title = re.sub(r"第[\d一二三四五六七八九十]+季", "", selected_sounds[0][1])
        clean_title = clean_title.strip(" -【】「」[]")
        export_to_excel(user_danmu_dict, filename=f"{clean_title}_{label}_弹幕.xlsx")

    else:
        print("✅ 已取消导出")

    input("\n按回车键退出...")

if __name__ == "__main__":
    main()
