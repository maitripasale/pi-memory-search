import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";
import { appendFileSync } from "node:fs";
import { join } from "node:path";
export default function(pi: ExtensionAPI) {
 let requests=0, tools=0;
 pi.on("tool_call", () => {
   tools++;
   if(tools>18) return {block:true, reason:"Research tool-call budget exhausted. Return your best supported answer."};
 });
 pi.on("before_provider_request", (event,ctx) => {
   requests++;
   const payload={...event.payload as any,temperature:0,max_tokens:4096};
   const bytes=Buffer.byteLength(JSON.stringify(payload));
   appendFileSync(join(ctx.cwd,"budget.jsonl"),JSON.stringify({requests,tools,input_bytes:bytes,temperature:0,max_tokens:4096})+"\n");
   if(requests>10 || bytes>100000) throw new Error("Research request/input budget exhausted");
   return payload;
 });
}
