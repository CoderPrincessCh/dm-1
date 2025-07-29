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
    season_grouped = {
        "广播剧": defaultdict(list),
        "有声剧": defaultdict(list)
    }

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
                pay_type = item.get("pay_type")
                catalog_id = item.get("catalog_id")

                # 只保留付费内容
                if pay_type != "2":
                    continue

                # 只识别有声剧(17) 和广播剧(19)
                if catalog_id == "19":
                    drama_type = "广播剧"
                elif catalog_id == "17":
                    drama_type = "有声剧"
                else:
                    continue  # 其他类型不要

                # 判断季数
                matched = False
                for season in range(1, 11):  # 最多到第十季
                    if match_season(name, season):
                        season_grouped[drama_type][season].append((item["id"], name))
                        matched = True
                        break
                if not matched:
                    season_grouped[drama_type][1].append((item["id"], name))  # 没识别到季归入第一季

            print(f"📄 第 {page} 页，共 {len(datas)} 条数据")

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
    all_grouped = search_drama(keyword)
    if not all_grouped or not any(all_grouped.values()):
        print("❌ 未找到符合条件的剧集")
        return

    # Step 1: 选择类型
    drama_types = [k for k in all_grouped.keys() if all_grouped[k]]
    print("\n🎭 找到以下剧集类型：")
    for idx, dtype in enumerate(drama_types, 1):
        season_count = len(all_grouped[dtype])
        print(f"{idx}. {dtype}（共 {season_count} 季）")

    input_type = input("请选择类型编号：").strip()
    if not input_type.isdigit() or not (1 <= int(input_type) <= len(drama_types)):
        print("❌ 类型选择无效，程序终止。")
        return
    selected_type = drama_types[int(input_type) - 1]

    # Step 2: 选择季数
    selected_seasons = all_grouped[selected_type]
    sorted_seasons = sorted(selected_seasons.keys())

    print(f"\n📺 类型：{selected_type}，共 {len(sorted_seasons)} 季：")
    for idx, season in enumerate(sorted_seasons, 1):
        sample_title = selected_seasons[season][0][1]
        clean_title = re.sub(r"第[\d一二三四五六七八九十]+季", "", sample_title)
        clean_title = clean_title.strip(" -【】「」[]")
        print(f"{idx}. {clean_title} - 第{season}季（共 {len(selected_seasons[season])} 集）")

    input_season = input("\n请选择要处理的季（输入序号或中文数字）：").strip()
    choice = to_index(input_season)
    if not (1 <= choice <= len(sorted_seasons)):
        print("❌ 季数选择无效，程序终止。")
        return

    season = sorted_seasons[choice - 1]
    selected_sounds = selected_seasons[season]
    label = f"第{season}季"

    print(f"\n📥 正在获取弹幕：{selected_type} - {label}（共 {len(selected_sounds)} 集）")
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
    print(f"🔹 去重后用户数：{len(user_danmu_dict)}")
    print(f"🕒 当前时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"♣ 数据仅供娱乐参考 ☺")

    export_choice = input("\n是否导出去重后的实时弹幕 Excel？(Y/N)：").strip().lower()
    if export_choice == 'y':
        clean_title = re.sub(r"第[\d一二三四五六七八九十]+季", "", selected_sounds[0][1])
        clean_title = clean_title.strip(" -【】「」[]")
        filename = f"{clean_title}_{selected_type}_{label}_弹幕.xlsx"
        export_to_excel(user_danmu_dict, filename=filename)
    else:
        print("✅ 已取消导出")

    input("\n按回车键退出...")

if __name__ == "__main__":
    main()
