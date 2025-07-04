import requests
import xml.etree.ElementTree as ET
from collections import OrderedDict
from openpyxl import Workbook
from openpyxl.styles import Font
from datetime import datetime

SEARCH_API = "https://www.missevan.com/sound/getsearch"
DANMU_API = "https://www.missevan.com/sound/getdm"


def search_drama(keyword: str):
    page = 1
    page_size = 30
    collected = []
    keyword_lower = keyword.strip().lower()

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

            # 👇 过滤
            filtered = [
                (item["id"], item["soundstr"])
                for item in datas
                if item.get("pay_type") == "2"
                and keyword_lower in item.get("soundstr", "").lower()
            ]
            collected.extend(filtered)

            print(f"📄 第 {page} 页，获取 {len(datas)} 条，总计符合条件 {len(filtered)} 条")

            if len(datas) < page_size:
                break
            page += 1

        except Exception as e:
            print(f"❌ 请求第 {page} 页失败:", e)
            break

    return collected

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

def main():
    keyword = input("请输入剧名关键词：").strip()
    if not keyword:
        print("⚠️ 关键词不能为空")
        return

    print("🔍 正在搜索剧集...")
    drama_list = search_drama(keyword)
    if not drama_list:
        print("未找到符合条件的剧集")
        return

    print(f"\n🎬 找到 {len(drama_list)} 个付费剧集：")
    for _, name in drama_list:
        print(" -", name)

    user_danmu_dict = OrderedDict()
    total_danmu = 0

    print("\n📥 正在获取弹幕...")
    for soundid, name in drama_list:
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

    choice = input("\n是否导出去重后的实时付费弹幕 Excel？(Y/N)：").strip().lower()
    if choice == 'y':
        export_to_excel(user_danmu_dict)
    else:
        print("✅ 已取消导出")

    input("\n按回车键退出...")

if __name__ == "__main__":
    main()