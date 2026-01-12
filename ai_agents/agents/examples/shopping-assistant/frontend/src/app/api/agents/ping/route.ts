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
    const { request_id, channel_name } = body;

    const response = await axios.post(`${AGENT_SERVER_URL}/ping`, {
      request_id,
      channel_name,
    });

    return NextResponse.json(response.data, { status: response.status });
  } catch (error: any) {
    console.error("Ping agent error:", error);
    return NextResponse.json(
      { code: "1", data: null, msg: error.message || "Internal Server Error" },
      { status: 500 }
    );
  }
}
