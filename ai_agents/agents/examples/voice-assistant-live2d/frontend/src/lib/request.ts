import axios from 'axios';

// Generate a simple UUID-like string
function genUUID(): string {
    return Math.random().toString(36).substring(2, 15) + Math.random().toString(36).substring(2, 15);
}

interface StartRequestConfig {
    channel: string;
    userId: number;
    graphName: string;
    language: string;
    voiceType: "male" | "female";
    properties?: Record<string, unknown>;
}

export const apiStartService = async (config: StartRequestConfig): Promise<any> => {
    const base = (process.env.NEXT_PUBLIC_API_BASE_URL || '').replace(/\/$/, '');
    const primary = base ? `${base}/start` : `/api/agents/start`;
    const { channel, userId, graphName, language, voiceType, properties } = config;
    const data: Record<string, unknown> = {
        request_id: genUUID(),
        channel_name: channel,
        user_uid: userId,
        graph_name: graphName,
        language,
        voice_type: voiceType
    };
    if (properties) {
        data.properties = properties;
    }
    let resp: any;
    try {
        resp = await axios.post(primary, data);
    } catch {
        const fallback = `/api/agents/start`;
        resp = await axios.post(fallback, data);
    }
    resp = (resp.data) || {};
    return resp;
};

export const apiStopService = async (channel: string) => {
    const base = (process.env.NEXT_PUBLIC_API_BASE_URL || '').replace(/\/$/, '');
    const primary = base ? `${base}/stop` : `/api/agents/stop`;
    const data = {
        request_id: genUUID(),
        channel_name: channel
    };
    let resp: any;
    try {
        resp = await axios.post(primary, data);
    } catch {
        const fallback = `/api/agents/stop`;
        resp = await axios.post(fallback, data);
    }
    resp = (resp.data) || {};
    return resp;
};

// ping/pong
export const apiPing = async (channel: string) => {
    const base = (process.env.NEXT_PUBLIC_API_BASE_URL || '').replace(/\/$/, '');
    const primary = base ? `${base}/ping` : `/api/agents/ping`;
    const data = {
        request_id: genUUID(),
        channel_name: channel
    };
    let resp: any;
    try {
        resp = await axios.post(primary, data);
    } catch {
        const fallback = `/api/agents/ping`;
        resp = await axios.post(fallback, data);
    }
    resp = (resp.data) || {};
    return resp;
};
