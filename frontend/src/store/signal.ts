import { defineStore } from 'pinia'
import { ref } from 'vue'
import axios from 'axios'
import type { AnalysisResult } from '@/types'

export interface AnalyzeParams {
  modulation: string
  samples: number
  snr: number
}

export const useSignalStore = defineStore('signal', () => {
  const loading = ref(false)
  const result = ref<AnalysisResult | null>(null)
  const error = ref<string | null>(null)
  const lastParams = ref<AnalyzeParams | null>(null)
  const resultParams = ref<AnalyzeParams | null>(null)
  const activeView = ref('spectrum')

  // Monotonic token: a late response from an older request must never
  // overwrite the result (or clear the error) of a newer request.
  let requestSeq = 0

  function errorMessage(e: unknown, fallback: string): string {
    if (axios.isAxiosError(e)) {
      if (e.response) {
        const detail = (e.response.data as { detail?: unknown })?.detail
        return `请求失败（HTTP ${e.response.status}）${detail ? '：' + detail : ''}`
      }
      if (e.request) return '无法连接到分析服务，请确认后端已启动后重试'
    }
    return e instanceof Error ? e.message : fallback
  }

  async function analyze(params: AnalyzeParams) {
    const seq = ++requestSeq
    lastParams.value = params
    loading.value = true
    error.value = null
    try {
      const { data } = await axios.post<AnalysisResult>('/api/generate', params)
      if (seq !== requestSeq) return
      // Replace the whole result atomically; every panel redraws from
      // this single response so they can never belong to different runs.
      result.value = data
      resultParams.value = params
    } catch (e) {
      if (seq !== requestSeq) return
      // Keep the previous good result visible; only record the failure.
      error.value = errorMessage(e, '分析失败，请重试')
    } finally {
      if (seq === requestSeq) loading.value = false
    }
  }

  // Re-run the analysis with the parameters of the failed attempt.
  function retry() {
    if (lastParams.value && !loading.value) return analyze(lastParams.value)
  }

  async function importCSV(formData: FormData) {
    const seq = ++requestSeq
    loading.value = true
    error.value = null
    try {
      const { data } = await axios.post('/api/import', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      })
      if (seq !== requestSeq) return
      result.value = data
      resultParams.value = lastParams.value
    } catch (e) {
      if (seq !== requestSeq) return
      error.value = errorMessage(e, '导入失败，请重试')
    } finally {
      if (seq === requestSeq) loading.value = false
    }
  }

  return { loading, result, error, lastParams, resultParams, activeView, analyze, retry, importCSV }
})
