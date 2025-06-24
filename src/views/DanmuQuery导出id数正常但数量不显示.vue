<template>
  <div class="p-4">
    <!-- <h1 class="text-xl font-bold mb-4">弹幕查询</h1> -->
    <div class="flex items-center gap-2 mb-4">
      <input
        v-model="soundid"
        type="text"
        placeholder="请输入剧名"
        class="border p-2 rounded w-64"
      />
      <button @click="fetchDanmu" class="bg-blue-500 text-white px-4 py-2 rounded hover:bg-blue-600">
        查询
      </button>
    </div>
    <div v-if="loading" class="text-gray-500">加载中...</div>
    <!-- <ul v-else class="space-y-2">
      <li v-for="(item, index) in danmuList" :key="index" class="border-b pb-2">
        {{ item.content }}
      </li>
    </ul> -->
    <div v-if="uniqueUserCount >= 0">
      <p>去重后的用户ID个数：{{ uniqueUserCount }}</p>
      <!-- <p>用户ID第一次发的弹幕内容：{{ firstUserDanmu }}</p> -->
      <p>用户ID第一次发的弹幕内容：
        <button @click="exportExcel" class="bg-blue-500 text-white px-4 py-2 rounded hover:bg-blue-600">
          导出excel
        </button>
      </p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch  } from 'vue'
import * as XLSX from 'xlsx' 

const soundid = ref('')
const danmuList = ref<any[]>([])
const loading = ref(false)
const uniqueUserCount = ref(0)
const firstUserDanmu = ref("")
const allId = ref(0)

// 存储去重后的用户ID
const userSet = new Set<string>();

// 用来记录第一次发的弹幕
let firstDanmu: string | null = null;

// 用来存储用户ID和弹幕内容
const userDanmuData = ref<{ userId: string, content: string }[]>([]);

watch(soundid, () => {
  // 每次输入新的 soundid 时清空数据
  userDanmuData.value = [];
  userSet.clear();
  uniqueUserCount.value = 0;
});

const fetchDanmu = async () => {
  if (!soundid.value.trim()) {
    alert('请输入剧名')
    return
  }
  loading.value = true

  // https://www.missevan.com/sound/getsearch?s=%E7%AB%B9%E6%9C%A8%E7%8B%BC%E9%A9%AC&p=1&type=3&page_size=30
  // fetch(`http://127.0.0.1:3000/sound/getsearch?s=${soundid.value}&p=1&type=3&page_size=30`)
  // fetch(`http://localhost:3000/sound/getsearch?s=${soundid.value}&p=1&type=3&page_size=30`)
  fetch(`/sound/getsearch?s=${soundid.value}&p=1&type=3&page_size=100`)
    .then(response => response.json())
    .then(async data => {
      // console.log('data', data.info.Datas);
      // allId.value = data.info.Datas.filter(item => item.pay_type === "2").map(item => item.id)
      console.log('allId.value', data.info.Datas.filter(item => item.pay_type === "2").map(item => item.id));
        // 遍历所有 soundid 请求
      for (let soundid of data.info.Datas.filter(item => item.pay_type === "2").map(item => item.id)) {
        try {
          const response = await fetch(`/sound/getdm?soundid=${soundid}`);
          const xmlString = await response.text();
        
          // 使用 DOMParser 解析 XML 数据
          const parser = new DOMParser();
          const xmlDoc = parser.parseFromString(xmlString, "application/xml");
        
          // 提取弹幕数据
          const danmuNodes = xmlDoc.getElementsByTagName('d');
        
          // 遍历所有弹幕并提取信息
          for (let i = 0; i < danmuNodes.length; i++) {
            const danmu = danmuNodes[i];
            const pValue = danmu.getAttribute('p') || ""; // 获取 p 属性值
            const userId = pValue.split(',')[6];  // 用户ID是 p 属性的第7个值
          
            // 如果这个用户ID第一次出现，保存弹幕
            if (!userSet.has(userId)) {
              userSet.add(userId);
              userDanmuData.value.push({
                userId,
                content: danmu.textContent || ""
              });
            }
          }
        
        } catch (error) {
          console.error('请求失败:', error);
        }
      }
    })
  // 更新去重后的用户ID个数
  uniqueUserCount.value = userSet.size;
  console.log('userSet.size', userSet.size);
  
  loading.value = false;  // 请求完成，加载状态改为 false

  // fetch(`/sound/getdm?soundid=${soundid.value}`)
  //   .then(response => response.text())  // 获取纯文本（XML 格式）
  //   .then(async xmlString => {
  //     // 使用 DOMParser 解析 XML 数据
  //     const parser = new DOMParser();
  //     const xmlDoc = parser.parseFromString(xmlString, "application/xml");

  //     // 提取弹幕数据
  //     const danmuNodes = xmlDoc.getElementsByTagName('d');

  //     // 遍历所有弹幕并提取信息
  //     for (let i = 0; i < danmuNodes.length; i++) {
  //       const danmu = danmuNodes[i];
  //       const pValue = danmu.getAttribute('p') || ""; // 获取 p 属性值
  //       const userId = pValue.split(',')[6];  // 用户ID是 p 属性的第7个值

  //       // 如果这个用户ID第一次出现，保存弹幕
  //       if (!userSet.has(userId)) {
  //         userSet.add(userId);
  //         userDanmuData.value.push({
  //           userId,
  //           content: danmu.textContent || ""
  //         });
  //       }
  //     }

  //     // 更新去重后的用户ID个数
  //     uniqueUserCount.value = userSet.size;
  //   })
  //   .catch(error => console.error('请求失败:', error))
  //   .finally(() => {
  //     loading.value = false;
  //   });
}

// 导出为 Excel 文件
const exportExcel = () => {
  // 校验是否有去重后的弹幕数据
  if (userDanmuData.value.length === 0) {
    alert('没有弹幕数据可导出');
    return;
  }
  // 构建数据：添加表头
  const sheetData = [
    ['用户ID', '弹幕内容'], // 表头
    ...userDanmuData.value.map(item => [item.userId, item.content])
  ];

  // 创建工作簿
  const ws = XLSX.utils.aoa_to_sheet(sheetData);

  // 创建工作簿对象
  const wb = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(wb, ws, '弹幕数据');

  // 导出 Excel 文件
  XLSX.writeFile(wb, 'danmu_data.xlsx');
}

</script>
