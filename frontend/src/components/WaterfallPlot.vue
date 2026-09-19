<template>
  <div class="panel" style="margin-top:16px">
    <h3>🌊 瀑布图 (Spectrogram)</h3>
    <div class="wf-wrap">
      <canvas ref="cvs" width="800" height="200" class="waterfall-canvas"></canvas>
      <div v-if="isEmpty" class="empty-tip">
        ⚠️ 本次结果没有瀑布图数据：样本数太少，不足以切分出哪怕一段（每段至少 16 个样本）做 FFT。
        请增大样本数后重新分析。
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { useSignalStore } from '../store/signal'
const store = useSignalStore()
const cvs = ref<HTMLCanvasElement>()

const isEmpty = computed(() => !!store.result && !(store.result.waterfall?.length))

function draw() {
  const c = cvs.value
  if (!c) return
  const ctx = c.getContext('2d')!; const W = c.width, H = c.height
  // 无论本次有没有数据都先清屏，避免残留上一次分析的图形
  ctx.fillStyle = '#0d1520'; ctx.fillRect(0, 0, W, H)
  const rows = store.result?.waterfall || []
  if (!rows.length) return
  const rowH = H / rows.length
  for (let r = 0; r < rows.length; r++) {
    const vals = rows[r].values, n = vals.length
    if (!n) continue
    const valsMin = Math.min(...vals), valsMax = Math.max(...vals)
    const vRange = valsMax - valsMin || 1
    for (let i = 0; i < n; i++) {
      const t = (vals[i] - valsMin) / vRange
      const rv = Math.round(t * 200)
      const gv = Math.round(t * 100 + (1-t) * 50)
      const bv = Math.round((1-t) * 200 + 30)
      ctx.fillStyle = `rgb(${rv},${gv},${bv})`
      ctx.fillRect(i * W / n, r * rowH, W / n + 1, rowH + 1)
    }
  }
}

onMounted(draw)
watch(() => store.result, draw)
</script>

<style scoped>
.panel { background:#1a2332; border-radius:8px; padding:16px; border:1px solid #2a3a4a }
.panel h3 { margin-bottom:8px; color:#90caf9; font-size:14px }
.wf-wrap { position:relative }
.waterfall-canvas { display:block; width:100%; border-radius:4px }
.empty-tip {
  position:absolute; inset:0; display:flex; align-items:center; justify-content:center;
  padding:0 24px; text-align:center; font-size:13px; line-height:1.6; color:#ffb74d;
  background:rgba(13,21,32,.85); border-radius:4px
}
</style>
