"""
Lightweight OpenAI-compatible HTTP mock server for offline smoke testing.
Allows testing the Pi coding agent CLI, tool calling, event streaming, and trajectory capture
without external API costs, rate limits, or network dependencies.
"""

import http.server
import json
import socketserver
import sys
import threading
import time
from typing import Optional


class MockOpenAIHandler(http.server.BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        sys.stderr.write(f"[MOCK HTTP] {format % args}\n")
        sys.stderr.flush()

    def do_GET(self):
        sys.stderr.write(f"[MOCK GET] {self.path}\n")
        sys.stderr.flush()
        if self.path == "/v1/models" or self.path == "/models":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            data = {
                "object": "list",
                "data": [
                    {
                        "id": "frozen-baseline-model",
                        "object": "model",
                        "created": 1700000000,
                        "owned_by": "pi-memory-research",
                    }
                ],
            }
            self.wfile.write(json.dumps(data).encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        sys.stderr.write(f"[MOCK POST] {self.path}\n")
        sys.stderr.flush()
        if self.path in ("/v1/chat/completions", "/chat/completions"):
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode("utf-8")
            try:
                payload = json.loads(body)
            except Exception:
                payload = {}

            messages = payload.get("messages", [])
            stream = payload.get("stream", True)

            # Analyze last message to determine whether to call tool or respond
            has_tool_result = False
            user_prompt = ""
            for msg in reversed(messages):
                role = msg.get("role")
                if role == "tool":
                    has_tool_result = True
                    break
                elif role == "user":
                    content = msg.get("content", "")
                    if isinstance(content, list):
                        user_prompt = " ".join(
                            p.get("text", "") for p in content if isinstance(p, dict)
                        )
                    else:
                        user_prompt = str(content)
                    break

            self.send_response(200)
            if stream:
                self.send_header("Content-Type", "text/event-stream")
                self.send_header("Cache-Control", "no-cache")
                self.send_header("Connection", "keep-alive")
                self.end_headers()

                # If tool result already arrived, return final completion text
                if has_tool_result:
                    chunks = [
                        {
                            "id": "chatcmpl-smoke-final",
                            "object": "chat.completion.chunk",
                            "created": int(time.time()),
                            "model": "frozen-baseline-model",
                            "choices": [
                                {
                                    "index": 0,
                                    "delta": {"content": "File smoke_output.txt created successfully with SMOKE_TEST_PASSED."},
                                    "finish_reason": None,
                                }
                            ],
                        },
                        {
                            "id": "chatcmpl-smoke-final",
                            "object": "chat.completion.chunk",
                            "created": int(time.time()),
                            "model": "frozen-baseline-model",
                            "choices": [
                                {
                                    "index": 0,
                                    "delta": {},
                                    "finish_reason": "stop",
                                }
                            ],
                            "usage": {
                                "prompt_tokens": 120,
                                "completion_tokens": 20,
                                "total_tokens": 140,
                            },
                        },
                    ]
                    for chunk in chunks:
                        self.wfile.write(f"data: {json.dumps(chunk)}\n\n".encode("utf-8"))
                        self.wfile.flush()
                    self.wfile.write(b"data: [DONE]\n\n")
                    self.wfile.flush()
                else:
                    # Issue tool call to write smoke_output.txt
                    args = json.dumps({
                        "path": "smoke_output.txt",
                        "content": "SMOKE_TEST_PASSED\n"
                    })
                    chunks = [
                        {
                            "id": "chatcmpl-smoke-tool",
                            "object": "chat.completion.chunk",
                            "created": int(time.time()),
                            "model": "frozen-baseline-model",
                            "choices": [
                                {
                                    "index": 0,
                                    "delta": {
                                        "tool_calls": [
                                            {
                                                "index": 0,
                                                "id": "call_write_smoke_001",
                                                "type": "function",
                                                "function": {
                                                    "name": "write",
                                                    "arguments": args,
                                                },
                                            }
                                        ]
                                    },
                                    "finish_reason": None,
                                }
                            ],
                        },
                        {
                            "id": "chatcmpl-smoke-tool",
                            "object": "chat.completion.chunk",
                            "created": int(time.time()),
                            "model": "frozen-baseline-model",
                            "choices": [
                                {
                                    "index": 0,
                                    "delta": {},
                                    "finish_reason": "tool_calls",
                                }
                            ],
                            "usage": {
                                "prompt_tokens": 80,
                                "completion_tokens": 40,
                                "total_tokens": 120,
                            },
                        },
                    ]
                    for chunk in chunks:
                        self.wfile.write(f"data: {json.dumps(chunk)}\n\n".encode("utf-8"))
                        self.wfile.flush()
                    self.wfile.write(b"data: [DONE]\n\n")
                    self.wfile.flush()
            else:
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                resp = {
                    "id": "chatcmpl-mock",
                    "object": "chat.completion",
                    "created": int(time.time()),
                    "model": "frozen-baseline-model",
                    "choices": [
                        {
                            "index": 0,
                            "message": {"role": "assistant", "content": "OK"},
                            "finish_reason": "stop",
                        }
                    ],
                    "usage": {"prompt_tokens": 50, "completion_tokens": 10, "total_tokens": 60},
                }
                self.wfile.write(json.dumps(resp).encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()


class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    allow_reuse_address = True


def start_mock_server(port: int = 8765) -> socketserver.TCPServer:
    server = ThreadedTCPServer(("127.0.0.1", port), MockOpenAIHandler)
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()
    return server


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8765
    server = start_mock_server(port)
    print(f"Mock OpenAI server listening on http://127.0.0.1:{port}")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        server.shutdown()
        server.server_close()
