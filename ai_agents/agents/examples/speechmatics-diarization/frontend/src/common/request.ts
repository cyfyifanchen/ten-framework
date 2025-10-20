import axios from 'axios'

const genUUID = () => crypto.randomUUID()

const isRecord = (value: unknown): value is Record<string, unknown> =>
  typeof value === 'object' && value !== null

export type NormalizedApiResponse<T = unknown> = {
  ok: boolean
  code: string | number | undefined
  msg: string | undefined
  data: T
}

export const normalizeApiResponse = <T = unknown>(resp: unknown): NormalizedApiResponse<T> => {
  const raw = isRecord(resp) && 'data' in resp ? (resp as { data?: unknown }).data : resp
  const payload = isRecord(raw) ? raw : {}
  const successFlag = payload['success'] === true
  const codeValue =
    (payload['code'] as string | number | undefined) ??
    (payload['status'] as string | number | undefined) ??
    (successFlag ? 0 : 1)
  const ok =
    codeValue === 0 ||
    codeValue === '0' ||
    codeValue === 'success' ||
    successFlag
  const msgValue =
    (payload['msg'] as string | undefined) ??
    (payload['message'] as string | undefined) ??
    (payload['status'] as string | undefined) ??
    (ok ? 'ok' : 'error')
  return {
    ok,
    code: codeValue as string | number | undefined,
    msg: msgValue,
    data: (payload['data'] ?? undefined) as T,
  }
}

export const apiGenAgoraData = async (config: { userId: number; channel: string }) => {
  const url = '/api/token/generate'
  const data = { request_id: genUUID(), uid: config.userId, channel_name: config.channel }
  const resp = await axios.post(url, data)
  return normalizeApiResponse(resp)
}

export const apiStartService = async (config: { channel: string; userId: number; graphName?: string }) => {
  const url = '/api/agents/start'
  const data = {
    request_id: genUUID(),
    channel_name: config.channel,
    user_uid: config.userId,
    graph_name: config.graphName || 'diarization_demo',
  }
  const resp = await axios.post(url, data)
  return normalizeApiResponse(resp)
}

export const apiStopService = async (channel: string) => {
  const url = '/api/agents/stop'
  const data = {
    request_id: genUUID(),
    channel_name: channel,
  }
  const resp = await axios.post(url, data)
  return normalizeApiResponse(resp)
}

export const apiPing = async (channel: string) => {
  const url = '/api/agents/ping'
  const data = {
    request_id: genUUID(),
    channel_name: channel,
  }
  const resp = await axios.post(url, data)
  return normalizeApiResponse(resp)
}
