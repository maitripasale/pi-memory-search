import { spawn, type ChildProcessWithoutNullStreams } from "node:child_process";
import { createInterface } from "node:readline";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { randomUUID } from "node:crypto";
import { Type } from "@earendil-works/pi-ai";
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";

export default function (pi: ExtensionAPI) {
  const root = join(dirname(fileURLToPath(import.meta.url)), "..");
  let child: ChildProcessWithoutNullStreams | undefined;
  let notebook = "";
  let tail = "";
  let serial = Promise.resolve();
  const pending = new Map<string, {resolve: (v: any) => void; reject: (e: Error) => void}>();
  function start(cwd: string) {
    if (child) return;
    notebook = join(cwd, "notebooks", `pi-${randomUUID()}.ipynb`);
    child = spawn(join(root, ".venv-repl", "Scripts", "python.exe"),
      [join(root, "src", "jupyter_bridge.py"), "--cwd", cwd, "--notebook", notebook],
      { cwd, windowsHide: true, stdio: ["pipe", "pipe", "pipe"] });
    child.stderr.on("data", data => { tail = (tail + data.toString()).slice(-2000); });
    createInterface({input: child.stdout}).on("line", line => {
      try { const result = JSON.parse(line); const waiter = pending.get(result.id);
        if (waiter) { pending.delete(result.id); waiter.resolve(result); }
      } catch { /* Non-protocol output cannot be treated as a tool result. */ }
    });
    const fail = (error: Error) => { for (const p of pending.values()) p.reject(error); pending.clear(); child = undefined; };
    child.on("error", fail);
    child.on("exit", code => fail(new Error(`Jupyter bridge exited (${code}). ${tail}`)));
  }
  async function request(cwd: string, message: any, signal?: AbortSignal) {
    const previous = serial;
    let release!: () => void;
    serial = new Promise<void>(resolve => {release = resolve;});
    await previous;
    try {
      if (signal?.aborted) throw new Error("Notebook request cancelled");
      start(cwd);
      const id = randomUUID();
      const result = await new Promise<any>((resolve, reject) => {
        const timer = setTimeout(() => {pending.delete(id); reject(new Error("Jupyter bridge timeout")); child?.stdin.end();}, 110000);
        pending.set(id, {resolve: value => {clearTimeout(timer); resolve(value);}, reject: error => {clearTimeout(timer); reject(error);}});
        child!.stdin.write(JSON.stringify({...message, id}) + "\n");
      });
      if (!result.ok) throw new Error(`${result.text}\nNotebook: ${result.notebook || notebook}`);
      return {content: [{type: "text" as const, text: `${result.text}\nNotebook: ${result.notebook}`}], details: result};
    } finally {release();}
  }
  pi.registerTool({name: "python_cell", label: "Python notebook cell",
    description: "Execute Python in a persistent Jupyter kernel. Variables survive between calls in this session. Code and outputs are saved to an .ipynb notebook. Cell errors preserve state; timeouts reset it. Runs with local user permissions.",
    parameters: Type.Object({code: Type.String(), timeout: Type.Optional(Type.Number({minimum: 1, maximum: 60}))}),
    async execute(_id, params, signal, _update, ctx) {return request(ctx.cwd, {action: "execute", ...params}, signal);}});
  pi.registerTool({name: "python_history", label: "Notebook history",
    description: "Read recent notebook cells and outputs, including errors, to review previous attempts.",
    parameters: Type.Object({last: Type.Optional(Type.Number({minimum: 1, maximum: 20}))}),
    async execute(_id, params, signal, _update, ctx) {return request(ctx.cwd, {action: "history", ...params}, signal);}});
  pi.registerTool({name: "python_reset", label: "Reset notebook kernel",
    description: "Clear all Python variables by restarting the kernel. Saved notebook cells remain.", parameters: Type.Object({}),
    async execute(_id, _params, signal, _update, ctx) {return request(ctx.cwd, {action: "reset"}, signal);}});
  pi.on("session_shutdown", async () => {
    if (!child) return;
    const current = child;
    current.stdin.end();
    await new Promise<void>(resolve => {
      const timer = setTimeout(() => {current.kill(); resolve();}, 10000);
      current.once("exit", () => {clearTimeout(timer); resolve();});
    });
  });
}
