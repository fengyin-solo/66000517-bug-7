<template>
  <div class="app-container">
    <header class="app-header">
      <h1>📡 射频信号频谱分析与调制识别仪</h1>
      <p class="subtitle">FFT频谱 · 瀑布图 · 星座图 | AM/FM/BPSK/QPSK/16QAM</p>
    </header>
    <main class="app-main">
      <div class="control-card">
        <el-form :model="form" inline>
          <el-form-item label="调制方式">
            <el-select v-model="form.modulation">
              <el-option v-for="m in ['AM','FM','BPSK','QPSK','16QAM']" :key="m" :label="m" :value="m" />
            </el-select>
          </el-form-item>
          <el-form-item label="样本数">
            <el-input-number v-model="form.samples" :min="256" :max="8192" :step="256" />
          </el-form-item>
          <el-form-item label="SNR(dB)">
            <el-input-number v-model="form.snr" :min="0" :max="40" :step="5" />
          </el-form-item>
          <el-form-item>
            <el-button type="primary" @click="generate" :loading="store.loading">🔍 生成信号并分析</el-button>
          </el-form-item>
        </el-form>
      </div>

      <el-alert
        v-if="store.error"
        type="error"
        :closable="false"
        show-icon
        class="error-alert"
      >
        <template #title>
          <div class="error-line">
            <span>本次分析未成功：{{ store.error }}</span>
            <el-button type="danger" size="small" :loading="store.loading" @click="store.retry()">
              重新尝试
            </el-button>
          </div>
          <div v-if="store.result" class="error-hint">
            下方仍显示上一次成功的分析结果（{{ resultSummary }}），未被本次失败请求覆盖。
          </div>
        </template>
      </el-alert>

      <div v-if="store.result" class="results-grid">
        <SpectrumPlot />
        <ConstellationPlot />
      </div>
      <WaterfallPlot v-if="store.result" />
      <ModulationResult v-if="store.result" />

      <div v-if="!store.result && !store.loading" class="empty-state">
        点击「生成信号并分析」查看频谱图、瀑布图与星座图
      </div>
    </main>
  </div>
</template>

<script setup lang="ts">
import { computed, reactive } from 'vue'
import SpectrumPlot from './components/SpectrumPlot.vue'
import ConstellationPlot from './components/ConstellationPlot.vue'
import WaterfallPlot from './components/WaterfallPlot.vue'
import ModulationResult from './components/ModulationResult.vue'
import { useSignalStore } from './store/signal'
const store = useSignalStore()
const form = reactive({ modulation: 'QPSK', samples: 1024, snr: 20 })
function generate() { store.analyze({ ...form }) }
const resultSummary = computed(() => {
  const p = store.resultParams
  return p ? `${p.modulation} · ${p.samples} 样本 · SNR ${p.snr} dB` : '上一次成功结果'
})
</script>

<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:system-ui,sans-serif;background:#0f1923;color:#e0e0e0}
.app-container{min-height:100vh}
.app-header{background:linear-gradient(135deg,#1a2332,#2d3e50);padding:20px 40px;border-bottom:1px solid #2a3a4a}
.app-header h1{font-size:1.5rem;color:#64b5f6}
.subtitle{opacity:.7;margin-top:4px;font-size:.85rem}
.app-main{padding:16px 40px}
.control-card{background:#1a2332;border-radius:8px;padding:16px 20px;margin-bottom:16px;border:1px solid #2a3a4a}
.results-grid{display:grid;grid-template-columns:1fr 1fr;gap:16px}
.error-alert{margin-bottom:16px;align-items:center}
.error-line{display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap}
.error-hint{margin-top:4px;font-size:12px;opacity:.8}
.empty-state{background:#1a2332;border:1px dashed #2a3a4a;border-radius:8px;padding:48px;text-align:center;color:#8899aa}
</style>