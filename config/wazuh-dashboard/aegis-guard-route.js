"use strict";

Object.defineProperty(exports, "__esModule", {
  value: true,
});
exports.AegisGuardRoutes = AegisGuardRoutes;

const http = require("http");
const { schema } = require("@osd/config-schema");

const integrationUrl = process.env.AEGIS_GUARD_INTEGRATION_URL ||
  "http://host.docker.internal:8002";

function requestJson(method, path, payload) {
  return new Promise((resolve, reject) => {
    const target = new URL(path, integrationUrl);
    const body = payload === undefined ? "" : JSON.stringify(payload);
    const request = http.request({
      hostname: target.hostname,
      port: target.port || 80,
      path: `${target.pathname}${target.search}`,
      method,
      headers: {
        "content-type": "application/json",
        "content-length": Buffer.byteLength(body),
      },
      timeout: 15000,
    }, response => {
      let responseBody = "";
      response.setEncoding("utf8");
      response.on("data", chunk => {
        responseBody += chunk;
      });
      response.on("end", () => {
        let parsed;
        try {
          parsed = responseBody ? JSON.parse(responseBody) : {};
        } catch (error) {
          parsed = { message: responseBody || "Invalid response from Aegis Guard" };
        }

        if (response.statusCode >= 200 && response.statusCode < 300) {
          resolve(parsed);
          return;
        }

        const requestError = new Error(
          parsed.detail || parsed.message || `Aegis Guard returned ${response.statusCode}`,
        );
        requestError.statusCode = response.statusCode;
        reject(requestError);
      });
    });

    request.on("timeout", () => {
      request.destroy(new Error("Ollama analysis timed out"));
    });
    request.on("error", reject);
    if (body) {
      request.write(body);
    }
    request.end();
  });
}

function AegisGuardRoutes(router) {
  router.post({
    path: "/api/aegis-guard/analyze",
    validate: {
      body: schema.object({
        alert: schema.any(),
      }),
    },
  }, async (context, request, response) => {
    try {
      const result = await requestJson("POST", "/manual-analysis", request.body.alert);
      return response.ok({ body: result });
    } catch (error) {
      return response.customError({
        statusCode: error.statusCode || 502,
        body: {
          message: error.message || "Aegis Guard analysis failed",
        },
      });
    }
  });

  router.get({
    path: "/api/aegis-guard/analyze/{jobId}",
    validate: {
      params: schema.object({
        jobId: schema.string(),
      }),
    },
  }, async (context, request, response) => {
    try {
      const result = await requestJson(
        "GET",
        `/manual-analysis/${encodeURIComponent(request.params.jobId)}`,
      );
      return response.ok({ body: result });
    } catch (error) {
      return response.customError({
        statusCode: error.statusCode || 502,
        body: {
          message: error.message || "Unable to read Aegis Guard analysis status",
        },
      });
    }
  });
}
