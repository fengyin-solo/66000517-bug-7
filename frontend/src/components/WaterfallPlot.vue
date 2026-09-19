<template>
  <div class="panel" style="margin-top:16px">
    <h3>🌊 瀑布图 (Spectrogram)</h3>
    <canvas ref="cvs" width="800" height="230" class="waterfall-canvas"></canvas>
    <div v-if="rows.length" class="wf-caption">
      共 {{ rows.length }} 行，每行 FFT 段长 {{ segmentSamples }} 个样本（约 {{ segmentSeconds }} ms）
      · 频率范围 −{{ halfFs }} ~ {{ halfFs }} Hz（与频谱图一致，最新时间在下方）
    </div>
    <el-alert
      v-else
      type="warning"
      :closable="false"
      show-icon
      title="样本数过少，无法绘制瀑布图"
      :description="`瀑布图每个时间段至少需要 ${minFft} 个样本才能做 FFT，当前样本数不足。请增大「样本数」后重新分析。`"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, watch, onMounted, computed, nextTick } from 'vue'
import { useSignalStore } from '../store/signal'
const store = useSignalStore()
const cvs = ref<HTMLCanvasElement>()

const rows = computed(() => store.result?.waterfall ?? [])
const segmentSamples = computed(() => store.result?.waterfallMeta?.segmentSamples ?? 0)
const minFft = computed(() => store.result?.waterfallMeta?.fftMinSamples ?? 32)
const fs = computed(() => store.result?.sampleRate ?? store.result?.waterfallMeta?.sampleRate ?? 1000)
const halfFs = computed(() => fs.value / 2)
const segmentSeconds = computed(() =>
  fs.value ? ((segmentSamples.value / fs.value) * 1000).toFixed(1) : '-'
)

function draw() {
  const c = cvs.value
  if (!c) return
  const ctx = c.getContext('2d')!
  const W = c.width, H = c.height
  const padBottom = 26
  const plotH = H - padBottom

  // Always repaint the whole canvas so rows from a previous run
  // (possibly with more rows / more bins) can never remain visible.
  ctx.fillStyle = '#0d1520'
  ctx.fillRect(0, 0, W, H)

  const data = rows.value
  if (!data.length) return

  // Normalize against the global min/max of this result so colors stay
  // comparable between rows and between runs with different sample sizes.
  let vMin = Infinity, vMax = -Infinity
  for (const row of data) {
    for (const v of row.values) {
      if (v < vMin) vMin = v
      if (v > vMax) vMax = v
    }
  }
  if (!isFinite(vMin) || !isFinite(vMax) || vMax - vMin < 1e-6) { vMin = -80; vMax = 0 }

  const rowH = plotH / data.length
  for (let r = 0; r < data.length; r++) {
    const vals = data[r].values
    const n = vals.length
    if (!n) continue
    for (let i = 0; i < n; i++) {
      const t = Math.min(1, Math.max(0, (vals[i] - vMin) / (vMax - vMin)))
      const rv = Math.round(t * 200)
      const gv = Math.round(t * 100 + (1 - t) * 50)
      const bv = Math.round((1 - t) * 200 + 30)
      ctx.fillStyle = `rgb(${rv},${gv},${bv})`
      ctx.fillRect((i * W) / n, r * rowH, W / n + 1, rowH + 1)
    }
  }

  // Frequency axis: full shifted spectrum, same scale as the FFT panel.
  ctx.fillStyle = '#8899aa'
  ctx.font = '11px system-ui'
  ctx.textAlign = 'center'
  ctx.fillText(`-${halfFs.value}`, 30, H - 8)
  ctx.fillText('0', W / 2, H - 8)
  ctx.fillText(`${halfFs.value}`, W - 30, H - 8)
  ctx.textAlign = 'left'
  ctx.fillText('频率 (Hz) →', 4, H - 8)
}

function scheduleDraw() { nextTick(draw) }

onMounted(scheduleDraw)
watch(() => store.result, scheduleDraw)
</script>

<style scoped>
.panel { background:#1a2332; border-radius:8px; padding:16px; border:1px solid #2a3a4a }
.panel h3 { margin-bottom:8px; color:#90caf9; font-size:14px }
.waterfall-canvas { display:block; width:100%; border-radius:4px }
.wf-caption { margin-top:6px; font-size:12px; color:#8899aa }
</style>
