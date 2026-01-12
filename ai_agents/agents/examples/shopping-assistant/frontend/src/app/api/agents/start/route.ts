import axios from "axios";
import { type NextRequest, NextResponse } from "next/server";

export async function POST(request: NextRequest) {
  try {
    const AGENT_SERVER_URL = process.env.AGENT_SERVER_URL;

    if (!AGENT_SERVER_URL) {
      return NextResponse.json(
        { code: "1", data: null, msg: "AGENT_SERVER_URL not configured" },
        { status: 500 }
      );
    }

    const body = await request.json();
    const {
      request_id,
      channel_name,
      user_uid,
      graph_name,
      language,
      voice_type,
      properties,
    } = body;

    const response = await axios.post(`${AGENT_SERVER_URL}/start`, {
      request_id,
      channel_name,
      user_uid,
      graph_name,
      properties,
    });

    return NextResponse.json(response.data, { status: response.status });
  } catch (error: any) {
    console.error("Start agent error:", error);
    return NextResponse.json(
      { code: "1", data: null, msg: error.message || "Internal Server Error" },
      { status: 500 }
    );
  }
}
