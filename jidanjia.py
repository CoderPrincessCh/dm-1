import requests
import re
import csv
from time import sleep
from html import unescape
import matplotlib.pyplot as plt
import pandas as pd

DRAMALIST_API = "https://www.missevan.com/dramaapi/filter"
SEARCH_API = "https://www.missevan.com/dramaapi/search"
headers = {
    "User-Agent": "Mozilla/5.0"
}

def clean_html(raw_html):
    # 去除 HTML 标签
    text = re.sub(r"<.*?>", "", raw_html)
    return unescape(text)

def extract_producers(abstract_html: str):
    text = clean_html(abstract_html)

    # 提取“联合出品”、“出品”、“联合制作” 等句子
    match = re.search(r"(猫耳FM.*?出品|.*?联合出品|.*?出品)", text)
    producers = match.group(0).strip() if match else ""

    has_maoer = "猫耳FM" in producers
    return producers, "是" if has_maoer else "否"

def extract_all_producers(abstract_html: str):
    text = clean_html(abstract_html)

    # 先找所有包含“出品”、“联合制作”等关键词的短句
    # 这里匹配连续不超过20个非换行字符，且包含“出品”或“制作”相关关键词
    pattern = r"([\u4e00-\u9fa5A-Za-z0-9·、，, ]{1,30}?(联合出品|联合制作|出品|制作|协作)[\u4e00-\u9fa5A-Za-z0-9·、，, ]{0,10})"
    
    matches = re.findall(pattern, text)

    # matches 是 (匹配短句, 关键词) 的元组列表，取第0个元素
    producers_list = [m[0].strip(" ,，") for m in matches]

    # 去重且保持顺序
    seen = set()
    producers = []
    for p in producers_list:
        if p not in seen:
            seen.add(p)
            producers.append(p)

    for p in producers_list:
        # 过滤包含以下词的条目
        if ("原著" in p) or ("广播剧" in p) or ("作者" in p):
            continue
        if p not in seen:
            seen.add(p)
            producers.append(p)

    # 是否含“猫耳FM”
    has_maoer = any("猫耳FM" in p for p in producers)

    # 返回所有出品方列表，和“是否猫耳FM”标识
    return producers, "是" if has_maoer else "否"


def chinese_to_arabic(cn: str) -> int:
    cn_num = {
        '零': 0, '一': 1, '二': 2, '两': 2, '三': 3, '四': 4,
        '五': 5, '六': 6, '七': 7, '八': 8, '九': 9
    }
    cn_unit = {'十': 10, '百': 100, '千': 1000}

    result = 0
    unit = 1
    num_stack = []

    for i in reversed(cn):
        if i in cn_unit:
            unit = cn_unit[i]
            if not num_stack:
                result += unit  # 处理 “十” 为 10 的情况
        elif i in cn_num:
            num = cn_num[i]
            result += num * unit
            unit = 1
        else:
            return None
    return result if result else None

def extract_episode_counts(abstract_html: str):
    text = clean_html(abstract_html)

    main_eps = None
    total_eps = None
    extra_eps = 0

    # 优先匹配：9集正剧 + 4个番外
    combo_match = re.search(
        r"(\d+)\s*[集话期]+\s*正剧\s*[,、，\s]*\s*(\d+)\s*[集话期]*\s*(番外|花絮|小剧场|福利)?",
        text
    )
    if combo_match:
        main_eps = int(combo_match.group(1))
        extra_eps = int(combo_match.group(2))
        total_eps = main_eps + extra_eps

    # 匹配：共X集正剧 / 正剧X集
    if main_eps is None:
        alt_main_match = re.search(r"(?:正剧\s*共?|共\s*)?(\d+)\s*[集话期]\s*正剧", text)
        if alt_main_match:
            main_eps = int(alt_main_match.group(1))
            total_eps = main_eps

    # 匹配：295+集正剧
    if main_eps is None:
        plus_match = re.search(r"(?:正剧\s*共|共)?\s*(\d+)\+\s*[集话期]\s*正剧", text)
        if plus_match:
            main_eps = int(plus_match.group(1))
            total_eps = None  # 不确定

    # 匹配：共X集（含番外）
    if main_eps is None:
        total_match = re.search(r"共\s*(\d+)\s*[集话期]", text)
        if total_match:
            total_eps = int(total_match.group(1))

            extra_match = re.search(r"含\s*(\d+)\s*[集话期]?.*?(番外|花絮|小剧场|福利)", text)
            extra_eps = int(extra_match.group(1)) if extra_match else 0

            main_eps = total_eps - extra_eps

    # 匹配：共X期 / 第一季X集
    if main_eps is None:
        fallback_match = re.search(r"(?:共|第一季)?\s*(\d{1,4})\s*[集期话]", text)
        if fallback_match:
            main_eps = int(fallback_match.group(1))
            total_eps = main_eps

    # 匹配：中文数字 “十六集”
    if main_eps is None:
      zh_match = re.search(r"(?:共)?([零一二三四五六七八九十百千两]+)[集期话]", text)
      if zh_match:
          cn_number = zh_match.group(1)
          main_eps = chinese_to_arabic(cn_number)
          total_eps = main_eps


    # 匹配：“包含正剧14期”
    # 新增：更宽松匹配“包含正剧14期、小剧场...”结构
    if main_eps is None:
        contain_main_match = re.search(r"包含\s*正剧\s*([0-9零一二三四五六七八九十百千两]+)[集话期]", text)
        if contain_main_match:
            raw = contain_main_match.group(1)
            main_eps = int(raw) if raw.isdigit() else chinese_to_arabic(raw)
            total_eps = main_eps  # 先假设总集数等于正剧数


    # 匹配“前X集免费”/“首X集限免”
    free_match = re.search(r"(?:前|首)\s*(\d+)\s*[集话期]?.*?(免费|限免)", text)
    free_eps = int(free_match.group(1)) if free_match else 0

    # 付费集 = 正剧 - 免费
    if main_eps is not None:
        paid_eps = max(main_eps - free_eps, 0)
    else:
        paid_eps = None

    return total_eps, main_eps, paid_eps

def fetch_drama_list_page(page: int):
    url = f"{DRAMALIST_API}?filters=0_0_0_0&page={page}&order=1&page_size=20&type=3"
    resp = requests.get(url, headers=headers, timeout=10)
    resp.raise_for_status()
    return resp.json()["info"]["Datas"]

def fetch_all_seasons_by_name(drama_name: str):
    """
    根据主剧名搜索，返回所有匹配剧（包含多季），
    返回列表，每个元素是 dict，包含价格、集数、名字、abstract
    """
    params = {"s": drama_name, "page": 1}
    resp = requests.get(SEARCH_API, headers=headers, params=params, timeout=10)
    resp.raise_for_status()
    candidates = resp.json()["info"]["Datas"]

    results = []
    for item in candidates:
        name = item.get("name", "")
        price_diamond = item.get("price", 0)

        # 只保留价格大于0的
        if price_diamond <= 0:
            continue

        # 过滤只要包含主剧名的结果
        if drama_name in name:
            abstract = item.get("abstract", "")
            producers, is_maoer = extract_all_producers(abstract)
            total_eps, main_eps, paid_eps = extract_episode_counts(abstract)
            results.append({
                "剧名": name,
                "价格钻石": price_diamond,
                "总集数": total_eps,
                "正剧集数": main_eps,
                "abstract": abstract,
                "付费集数": paid_eps,
                "备注": "；".join(producers),
                "是否猫耳FM": is_maoer
            })

    if not results:
        print(f"⚠️ 未找到匹配剧目: {drama_name}")
    return results


def clean_drama_name(name: str) -> str:
    """
    去掉“第X季”、“上季”、“下季”、“全一季”、“合集”等后缀，仅保留主剧名
    """
    return re.sub(r"[\s·]*(第[一二三四五六七八九十1234567890]+季|全[一二三四五六七八九十1234567890]+季|上季|下季|合集)$", "", name).strip()


def process_one_drama(drama):
    raw_name = drama["name"]
    drama_name = clean_drama_name(raw_name)
    drama_id = drama["id"]

    all_seasons = fetch_all_seasons_by_name(drama_name)
    results = []

    if not all_seasons:
        print(f"⚠️ {raw_name} 未找到任何季，跳过")
        return []

    for season in all_seasons:
        price_rmb = season["价格钻石"] / 10
        main_eps = season["正剧集数"]
        paid_eps = season["付费集数"]
        producers = season.get("备注", [])
        is_maoer = season.get("是否猫耳FM", "否")

        if paid_eps is None or paid_eps == 0:
            unit_price = 0
        else:
            unit_price = round(price_rmb / paid_eps, 2)

        if main_eps is None or main_eps == 0:
            avg_price = 0
            print(f"⚠️ {season['剧名']} 无法计算集均价（正剧未知或为0）")
        else:
            avg_price = round(price_rmb / main_eps, 2)

        results.append({
            "剧名": season["剧名"],
            "剧ID": drama_id,
            "总集数（含番外）": season["总集数"] if season["总集数"] else "未知",
            "正剧集数": main_eps if main_eps else "未知",
            "总价（元）": round(price_rmb, 2),
            "集均价（元）": avg_price,
            "付费集数": paid_eps if paid_eps else "未知",
            "付费集单价（元）": unit_price,
            "备注": producers,
            "是否猫耳FM": is_maoer,
        })

    return results

def main(export_csv=True):
    result = []
    page = 1
    max_pages = 100  # 最大抓取页数限制
    processed_main_titles = set()

    while True:
        if page > max_pages:
            print(f"📢 已达到最大抓取页数 {max_pages}，结束抓取。")
            break

        print(f"📦 正在抓取第 {page} 页剧列表...")
        try:
            dramas = fetch_drama_list_page(page)
        except Exception as e:
            print(f"❗ 第 {page} 页获取失败：{e}")
            break

        if not dramas:
            print("✅ 抓取完毕")
            break

        for drama in dramas:
          if drama.get("pay_type") != 2:
              continue
            
          # 获取主剧名（去掉第几季）
          raw_name = drama.get("name", "")
          main_title = clean_drama_name(raw_name)

          if main_title in processed_main_titles:
              continue  # ✅ 已处理过该主剧，跳过
          processed_main_titles.add(main_title)

          season_results = process_one_drama(drama)
          if season_results:
              result.extend(season_results)
              for data in season_results:
                  print(f"✅ 收录：{data['剧名']} | 正剧{data['正剧集数']}集 | 付费{data['付费集数']}集 | 集均价：¥{data['集均价（元）']} | 付费集单价：¥{data['付费集单价（元）']} | 备注：{data['备注']}")
          sleep(0.3)
        page += 1
        sleep(0.5)

    if export_csv:
        with open("全部付费广播剧_集均价统计.csv", "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=[
                "剧名", "剧ID", "总集数（含番外）", "正剧集数", "付费集数", "总价（元）", "集均价（元）", "付费集单价（元）", "备注", "是否猫耳FM"
            ])
            writer.writeheader()
            writer.writerows(result)
        print("📄 导出完成：全部付费广播剧_集均价统计.csv")

    return result

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib

# 设置中文字体支持（如使用微软雅黑）
matplotlib.rcParams['font.family'] = ['Microsoft YaHei']
matplotlib.rcParams['axes.unicode_minus'] = False  # 负号正常显示

# def draw_price_charts(csv_file="全部付费广播剧_集均价统计.csv"):
# # def draw_price_charts(csv_file="全部付费广播剧_集均价统计.csv", top_n=30):
#     df = pd.read_csv(csv_file)

#     # 过滤掉无法转数字的项
#     df = df[pd.to_numeric(df["集均价（元）"], errors='coerce').notna()]
#     df = df[pd.to_numeric(df["付费集单价（元）"], errors='coerce').notna()]

#     df["集均价（元）"] = df["集均价（元）"].astype(float)
#     df["付费集单价（元）"] = df["付费集单价（元）"].astype(float)

#     # 排序后取前 N 项
#     top_avg = df.sort_values("集均价（元）", ascending=False).head(top_n)
#     top_unit = df.sort_values("付费集单价（元）", ascending=False).head(top_n)

#     # ✅ 图1：集均价
#     plt.figure(figsize=(12, 8))
#     bars = plt.barh(top_avg["剧名"], top_avg["集均价（元）"], color="skyblue")
#     plt.xlabel("集均价（元）")
#     # plt.title(f"集均价 Top {top_n}")
#     plt.title(f"集均价 Top")
#     plt.gca().invert_yaxis()
#     plt.yticks(fontsize=10)
#     plt.tight_layout()
#     plt.savefig("集均价_TOP.png", dpi=200)
#     plt.close()

#     # ✅ 图2：付费集单价
#     plt.figure(figsize=(12, 8))
#     bars = plt.barh(top_unit["剧名"], top_unit["付费集单价（元）"], color="salmon")
#     plt.xlabel("付费集单价（元）")
#     plt.title(f"付费集单价 Top")
#     # plt.title(f"付费集单价 Top {top_n}")
#     plt.gca().invert_yaxis()
#     plt.yticks(fontsize=10)
#     plt.tight_layout()
#     plt.savefig("付费集单价_TOP.png", dpi=200)
#     plt.close()

#     print("📊 图表已生成：集均价_TOP.png，付费集单价_TOP.png")

def draw_price_charts(csv_file="全部付费广播剧_集均价统计.csv"):
    df = pd.read_csv(csv_file)

    # 清洗数据
    df = df[pd.to_numeric(df["集均价（元）"], errors='coerce').notna()]
    df = df[pd.to_numeric(df["付费集单价（元）"], errors='coerce').notna()]
    df["集均价（元）"] = df["集均价（元）"].astype(float)
    df["付费集单价（元）"] = df["付费集单价（元）"].astype(float)

    # 不截取前 30，直接全量绘图
    sorted_avg = df.sort_values("集均价（元）", ascending=False)
    sorted_unit = df.sort_values("付费集单价（元）", ascending=False)

    # 图1：全部集均价
    plt.figure(figsize=(12, max(6, 0.3 * len(sorted_avg))))
    plt.barh(sorted_avg["剧名"], sorted_avg["集均价（元）"], color="skyblue")
    plt.xlabel("集均价（元）")
    plt.title("全部广播剧 - 集均价")
    plt.gca().invert_yaxis()
    plt.yticks(fontsize=9)
    plt.tight_layout()
    plt.savefig("集均价_ALL.png", dpi=200)
    plt.close()

    # 图2：全部付费集单价
    plt.figure(figsize=(12, max(6, 0.3 * len(sorted_unit))))
    plt.barh(sorted_unit["剧名"], sorted_unit["付费集单价（元）"], color="salmon")
    plt.xlabel("付费集单价（元）")
    plt.title("全部广播剧 - 付费集单价")
    plt.gca().invert_yaxis()
    plt.yticks(fontsize=9)
    plt.tight_layout()
    plt.savefig("付费集单价_ALL.png", dpi=200)
    plt.close()

    print("📊 图表已生成：集均价_ALL.png，付费集单价_ALL.png")



if __name__ == "__main__":
    RUN_MAIN = True     # 改为 True 就会运行 main()
    RUN_DRAW = False      # 改为 False 就不绘图

    if RUN_MAIN:
        main()

    if RUN_DRAW:
        draw_price_charts()
