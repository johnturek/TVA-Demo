/**
 * dataverse.js — Shared Dataverse REST API helpers
 *
 * HTTP GET, PATCH, POST against Dataverse OData v4.0 API.
 * Used by clone, push, publish, and list scripts.
 */

const https = require("https");

function request(method, url, accessToken, body) {
  return new Promise((resolve, reject) => {
    const urlObj = new URL(url);
    const options = {
      hostname: urlObj.hostname,
      port: urlObj.port || 443,
      path: urlObj.pathname + urlObj.search,
      method,
      headers: {
        Authorization: `Bearer ${accessToken}`,
        Accept: "application/json",
        "OData-MaxVersion": "4.0",
        "OData-Version": "4.0",
      },
    };

    if (body) {
      options.headers["Content-Type"] = "application/json";
    }

    const req = https.request(options, (res) => {
      let data = "";
      res.on("data", (chunk) => (data += chunk));
      res.on("end", () => {
        if (res.statusCode >= 400) {
          reject(new Error(`HTTP ${res.statusCode}: ${data}`));
        } else {
          try {
            resolve(data ? JSON.parse(data) : {});
          } catch {
            resolve({});
          }
        }
      });
    });

    req.on("error", reject);
    if (body) req.write(JSON.stringify(body));
    req.end();
  });
}

const httpGet = (url, token) => request("GET", url, token);
const httpPatch = (url, token, body) => request("PATCH", url, token, body);
const httpPost = (url, token, body) => request("POST", url, token, body);

module.exports = { httpGet, httpPatch, httpPost };
