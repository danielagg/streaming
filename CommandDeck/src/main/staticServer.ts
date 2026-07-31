import fs from "node:fs";
import http from "node:http";
import path from "node:path";
import { app } from "electron";

export interface RendererServer {
  url: string;
  close(): void;
}

const CONTENT_TYPES: Record<string, string> = {
  ".css": "text/css; charset=utf-8",
  ".html": "text/html; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".png": "image/png",
  ".svg": "image/svg+xml",
};

export async function startRendererServer(): Promise<RendererServer> {
  const root = path.resolve(app.getAppPath(), "dist");
  const server = http.createServer((request, response) => {
    let pathname = "/";
    try {
      pathname = decodeURIComponent(
        new URL(request.url ?? "/", "http://localhost").pathname,
      );
    } catch {
      response.writeHead(400).end();
      return;
    }
    const requested = pathname === "/" ? "index.html" : pathname.slice(1);
    const filePath = path.resolve(root, requested);
    if (filePath !== root && !filePath.startsWith(`${root}${path.sep}`)) {
      response.writeHead(403).end();
      return;
    }
    const target = fs.existsSync(filePath) && fs.statSync(filePath).isFile()
      ? filePath
      : path.join(root, "index.html");
    response.setHeader(
      "Content-Type",
      CONTENT_TYPES[path.extname(target).toLowerCase()] ??
        "application/octet-stream",
    );
    fs.createReadStream(target).pipe(response);
  });

  await new Promise<void>((resolve, reject) => {
    server.once("error", reject);
    server.listen(0, "localhost", resolve);
  });
  const address = server.address();
  if (!address || typeof address === "string") {
    server.close();
    throw new Error("Could not start the Command Deck renderer server.");
  }
  return {
    url: `http://localhost:${address.port}`,
    close: () => server.close(),
  };
}
