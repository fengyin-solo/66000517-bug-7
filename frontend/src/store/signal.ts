import { defineStore } from 'pinia'
import { ref } from 'vue'
import axios from 'axios'
import type { AnalysisResult } from '@/types'

interface AnalyzeParams { modulation: string; samples: number; snr: number }

function toErrorMessage(e: unknown): string {
  if (axios.isAxiosError(e)) {
    const detail = (e.response?.data as { detail?: string } | undefined)?.detail
    if (typeof detail === 'string') return `分析失败：${detail}`
    if (e.response) return `分析失败：服务器返回错误 (${e.response.status})`
    return '分析失败：无法连接后端服务，请确认后端已启动后重试'
  }
  return '分析失败：发生未知错误'
}

export const useSignalStore = defineStore('signal', () => {
  const loading = ref(false)
  const result = ref<AnalysisResult | null>(null)
  const error = ref<string | null>(null)
  const lastParams = ref<AnalyzeParams | null>(null)
  const activeView = ref('spectrum')

  async function analyze(params: AnalyzeParams) {
    loading.value = true
    error.value = null
    lastParams.value = { ...params }
    try {
      const { data } = await axios.post('/api/generate', params)
      result.value = data
    } catch (e) {
      // 保留上一次可用结果，只记录本次失败
      error.value = toErrorMessage(e)
    } finally { loading.value = false }
  }

  async function retry() {
    if (lastParams.value) await analyze(lastParams.value)
  }

  async function importCSV(formData: FormData) {
    loading.value = true
    error.value = null
    try {
      const { data } = await axios.post('/api/import', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      })
      result.value = data
    } catch (e) {
      error.value = toErrorMessage(e)
    } finally { loading.value = false }
  }

  return { loading, result, error, lastParams, activeView, analyze, retry, importCSV }
})
