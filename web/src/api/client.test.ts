import { afterEach, describe, expect, it, vi } from "vitest";
import { ApiError, predict } from "./client";

const jpegFile = () => new File([new Uint8Array([1, 2, 3])], "leaf.jpg", { type: "image/jpeg" });

describe("predict", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("returns the parsed response on success", async () => {
    const body = { status: "ok", top: null, alternatives: [], message: null };
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify(body), { status: 200 })));

    await expect(predict(jpegFile())).resolves.toEqual(body);
  });

  it("throws the server's detail message on a non-200 response", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(new Response(JSON.stringify({ detail: "model unavailable" }), { status: 503 })),
    );

    await expect(predict(jpegFile())).rejects.toThrow("model unavailable");
    await expect(predict(jpegFile())).rejects.toBeInstanceOf(ApiError);
  });

  it("throws a friendly message when the network request itself fails", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("Failed to fetch")));

    await expect(predict(jpegFile())).rejects.toThrow(/could not reach/i);
  });
});
