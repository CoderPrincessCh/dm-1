import requests
import xml.etree.ElementTree as ET
from wordcloud import WordCloud
import jieba
import matplotlib.pyplot as plt

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
            filtered = [
                (item["id"], item["soundstr"])
                for item in datas
                # if item.get("pay_type") == "2"
                # and keyword_lower in item.get("soundstr", "").lower()
                if keyword_lower in item.get("soundstr", "").lower()
            ]
            collected.extend(filtered)

            if len(datas) < page_size:
                break
            page += 1
        except Exception as e:
            print(f"❌ 请求失败：{e}")
            break
    return collected

def fetch_all_danmu_text(drama_list):
    all_texts = []
    for soundid, name in drama_list:
        print(f"→ 获取：{name} (ID: {soundid})")
        try:
            response = requests.get(DANMU_API, params={"soundid": soundid})
            response.raise_for_status()
            xml_text = response.text
            root = ET.fromstring(xml_text)
            for d in root.findall("d"):
                all_texts.append(d.text or "")
        except Exception as e:
            print(f"❌ 获取失败（ID={soundid}）：{e}")
    return all_texts

def generate_wordcloud(danmu_list, filename="danmu_wordcloud.png"):
    if not danmu_list:
        print("⚠️ 没有弹幕内容")
        return

    print("🎨 正在生成词云...")
    text = " ".join(jieba.cut(" ".join(danmu_list)))
    wc = WordCloud(
        font_path="msyh.ttc",  # 替换为系统的中文字体路径
        width=1000,
        height=600,
        background_color="white",
        max_words=300
    ).generate(text)

    wc.to_file(filename)
    print(f"✅ 词云已保存为 → {filename}")
    plt.imshow(wc, interpolation="bilinear")
    plt.axis("off")
    plt.show()

def main():
    keyword = input("请输入剧名关键词：").strip()
    if not keyword:
        print("⚠️ 关键词不能为空")
        return

    print("🔍 正在搜索剧集...")
    drama_list = search_drama(keyword)
    if not drama_list:
        print("❌ 未找到符合条件的剧集")
        return

    print(f"\n🎬 共找到 {len(drama_list)} 个付费剧集：")
    for _, name in drama_list:
        print(" -", name)

    print("\n📥 正在获取所有实时弹幕...")
    all_text = fetch_all_danmu_text(drama_list)
    print(f"🔹 共收集 {len(all_text)} 条弹幕")

    generate_wordcloud(all_text)

    input("\n✅ 操作完成，按回车退出...")

if __name__ == "__main__":
    main()
