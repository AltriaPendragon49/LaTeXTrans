const DEFAULT_API_ORIGIN = "https://api.latextrans.online"

function normalizeOrigin(value: string | undefined): string {
  const candidate = String(value ?? "").trim()
  if (!candidate) {
    return DEFAULT_API_ORIGIN
  }

  return candidate.replace(/\/+$/, "")
}

export async function onRequest(context: {
  env?: { API_ORIGIN?: string; API_HOST_HEADER?: string }
  request: Request
}): Promise<Response> {
  const origin = normalizeOrigin(context.env?.API_ORIGIN)
  const incomingUrl = new URL(context.request.url)
  const upstreamUrl = new URL(`${origin}${incomingUrl.pathname}${incomingUrl.search}`)
  const upstreamHeaders = new Headers(context.request.headers)

  const hostHeader = String(context.env?.API_HOST_HEADER ?? "").trim()
  if (hostHeader) {
    upstreamHeaders.set("host", hostHeader)
  } else {
    upstreamHeaders.delete("host")
  }
  upstreamHeaders.set("x-forwarded-host", incomingUrl.host)
  upstreamHeaders.set("x-forwarded-proto", incomingUrl.protocol.replace(":", ""))

  return fetch(
    new Request(upstreamUrl.toString(), {
      method: context.request.method,
      headers: upstreamHeaders,
      body: context.request.body,
      redirect: "manual",
    }),
  )
}
