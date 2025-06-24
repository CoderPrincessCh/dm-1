<template>
  <div class="p-4">
    <h1 class="text-xl font-bold mb-4">弹幕查询工具</h1>
    <div class="flex items-center gap-2 mb-4">
      <input
        v-model="soundid"
        type="text"
        placeholder="请输入视频ID"
        class="border p-2 rounded w-64"
      />
      <button @click="fetchDanmu" class="bg-blue-500 text-white px-4 py-2 rounded hover:bg-blue-600">
        查询弹幕
      </button>
    </div>
    <div v-if="loading" class="text-gray-500">加载中...</div>
    <ul v-else class="space-y-2">
      <li v-for="(item, index) in danmuList" :key="index" class="border-b pb-2">
        {{ item.content }}
      </li>
    </ul>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { parseStringPromise } from 'xml2js';

const soundid = ref('')
const danmuList = ref<any[]>([])
const loading = ref(false)

const fetchDanmu = async () => {
  if (!soundid.value.trim()) {
    alert('请输入视频ID')
    return
  }
  loading.value = true
  // try {
  //   const res = await fetch(`/sound/getdm?soundid=${soundid.value}`)
  //   // const data = await res.json()
  //   // danmuList.value = data.list || []
  // } catch (err) {
  //   console.error('请求失败', err)
  //   alert('查询失败，请检查控制台')
  // } finally {
  //   loading.value = false
  // }
  // fetch(`/sound/getdm?soundid=${soundid.value}`)
  // fetch(`/sound/getdm?soundid=1499536`)
  // .then(response => response)  // 先按文本形式获取响应数据
  // .then(data => {
  //   console.log(data);  // 打印返回的原始数据
  // })
  // .catch(error => console.error('请求失败:', error));
  // fetch(`/sound/getdm?soundid=1499536`)
  fetch(`/sound/getdm?soundid=${soundid.value}`)
  .then(response => response.text())  // 获取纯文本（XML 格式）
  .then(async xmlString => {
    console.log('xmlString', xmlString);
    

    // 使用 DOMParser 解析 XML 数据
    const parser = new DOMParser();
    const xmlDoc = parser.parseFromString(xmlString, "application/xml");

    // 从 XML 中提取 chatserver、chatid 和 source 信息
    const chatServer = xmlDoc.getElementsByTagName('chatserver')[0]?.textContent
    const chatId = xmlDoc.getElementsByTagName('chatid')[0]?.textContent
    const source = xmlDoc.getElementsByTagName('source')[0]?.textContent

    console.log('Chat Server:', chatServer)
    console.log('Chat ID:', chatId)
    console.log('Source:', source)
  })
  .catch(error => console.error('请求失败:', error));
}

// 使用 xml2js 库解析 XML 数据
async function extractUniqueDanmuIds(xmlData: string) {
  try {
    const result = await parseStringPromise(xmlData);

    // 获取所有的 <d> 标签
    const danmus = result.i.d;

    // 提取每个弹幕的 ID (倒数第二个字段)
    const ids = danmus.map((danmu: any) => {
      const p = danmu.$.p; // 获取 p 属性值
      const fields = p.split(','); // 根据逗号分割字段
      return fields[fields.length - 2]; // 获取倒数第二个字段，即 ID
    });

    // 使用 Set 去重
    const uniqueIds = [...new Set(ids)];

    // console.log("uniqueIds", uniqueIds);
    

    return uniqueIds;
  } catch (err) {
    console.error('解析 XML 错误:', err);
  }
}
</script>
