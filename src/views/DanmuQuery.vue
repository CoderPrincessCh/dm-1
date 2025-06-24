<template>
  <div class="p-4">
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
    <div v-if="uniqueUserCount >= 0">
      <p>去重后的用户ID个数：{{ uniqueUserCount }}</p>
      计算的付费集：<p v-for="item in dramaList">{{ item }}</p>
      <p>用户ID第一次发的弹幕内容：
        <button @click="exportExcel" class="bg-blue-500 text-white px-4 py-2 rounded hover:bg-blue-600">
          导出excel
        </button>
      </p>
      <p style="margin-top: 20px;">当前时间：{{ new Date() }}</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue';
import * as XLSX from 'xlsx';

const soundid = ref('');
const userDanmuData = ref<{ userId: string, content: string }[]>([]);
const loading = ref(false);
const uniqueUserCount = ref(0);
const allId = ref<number[]>([]);
const userSet = new Set<string>();
const dramaList = ref<string[]>()

watch(soundid, () => {
  // Clear previous data when soundid changes
  userDanmuData.value = [];
  userSet.clear();
  uniqueUserCount.value = 0;
  dramaList.value = []
});

const fetchDanmu = async () => {
  if (!soundid.value.trim()) {
    alert('请输入剧名');
    return;
  }
  loading.value = true;

  // Fetch allId first
  fetch(`/sound/getsearch?s=${soundid.value}&p=1&type=3&page_size=400`)
    .then(response => response.json())
    .then(async data => {
      const filteredIds = data.info.Datas.filter(item => item.pay_type === "2").map(item => item.id);
      allId.value = filteredIds;
      dramaList.value = data.info.Datas.filter(item => item.pay_type === "2").map(item => item.soundstr)

      // Now iterate over the filtered sound IDs
      for (let soundid of filteredIds) {
        try {
          const response = await fetch(`/sound/getdm?soundid=${soundid}`);
          const xmlString = await response.text();

          // Use DOMParser to parse XML
          const parser = new DOMParser();
          const xmlDoc = parser.parseFromString(xmlString, "application/xml");

          // Extract danmu data
          const danmuNodes = xmlDoc.getElementsByTagName('d');

          // Loop through danmu nodes and collect unique user IDs
          for (let i = 0; i < danmuNodes.length; i++) {
            const danmu = danmuNodes[i];
            const pValue = danmu.getAttribute('p') || "";
            const userId = pValue.split(',')[6];  // Extract user ID from p attribute

            // If this user ID hasn't appeared before, save the danmu
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

      // Update the unique user count after processing all the data
      uniqueUserCount.value = userSet.size;
      console.log('去重后的用户ID个数:', userSet.size);
    })
    .catch(error => console.error('请求失败:', error))
    .finally(() => {
      loading.value = false; // Reset loading state
    });
}

// Export to Excel
const exportExcel = () => {
  if (userDanmuData.value.length === 0) {
    alert('没有弹幕数据可导出');
    return;
  }

  // Prepare data for Excel export
  const sheetData = [
    ['用户ID', '弹幕内容'], // Header
    ...userDanmuData.value.map(item => [item.userId, item.content])
  ];

  // Create worksheet and workbook
  const ws = XLSX.utils.aoa_to_sheet(sheetData);
  const wb = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(wb, ws, '弹幕数据');

  // Write the Excel file
  XLSX.writeFile(wb, 'danmu_data.xlsx');
}
</script>
