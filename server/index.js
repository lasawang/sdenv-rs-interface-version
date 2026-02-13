#!/usr/bin/env node
'use strict';

process.env.NODE_TLS_REJECT_UNAUTHORIZED = "0";
process.env.OPENSSL_LEGACY_RENEGOTIATION = '1';

// 防止第三方页面脚本的未捕获异常导致进程崩溃
process.on('uncaughtException', (err) => {
  const logger = require('../utils/logger');
  logger.warn('未捕获异常（已拦截，不影响服务）:', err.message);
});
process.on('unhandledRejection', (reason) => {
  const logger = require('../utils/logger');
  logger.warn('未处理的Promise拒绝（已拦截）:', reason?.message || reason);
});

const http = require('http');
const path = require('path');

const { crackUrl, crackLocal, executeJs } = require('./handler');
const logger = require('../utils/logger');
const version = require('../package.json').version;

const PORT = parseInt(process.env.SDENV_PORT || '3000', 10);
const HOST = process.env.SDENV_HOST || '0.0.0.0';
const MAX_BODY_SIZE = parseInt(process.env.SDENV_MAX_BODY || '52428800', 10); // 50MB

function parseBody(req) {
  return new Promise((resolve, reject) => {
    let body = '';
    let size = 0;
    req.on('data', chunk => {
      size += chunk.length;
      if (size > MAX_BODY_SIZE) {
        reject(new Error('请求体过大'));
        req.destroy();
        return;
      }
      body += chunk;
    });
    req.on('end', () => {
      try {
        resolve(body ? JSON.parse(body) : {});
      } catch (e) {
        reject(new Error('无效的JSON格式'));
      }
    });
    req.on('error', reject);
  });
}

function sendJson(res, statusCode, data) {
  const json = JSON.stringify(data, null, 0);
  res.writeHead(statusCode, {
    'Content-Type': 'application/json; charset=utf-8',
    'Content-Length': Buffer.byteLength(json),
  });
  res.end(json);
}

async function handleCrack(body) {
  const {
    mode = 'remote',
    url,
    html,
    js,
    ts,
    jsCode,
    waitEvent,
    apiUrls,
    methods,
    domConfig,
    bomConfig,
    navigatorConfig,
    resourceMode,
    userAgent,
    proxy,
    timeout = 30000,
    verify = true,
    windowProxyConfig,
  } = body;

  if (!url && mode !== 'execute') {
    throw new Error('url 参数为必填项');
  }

  const commonOpts = { domConfig, bomConfig, navigatorConfig, resourceMode, timeout, windowProxyConfig };

  switch (mode) {
    case 'remote':
      return await crackUrl(url, { ...commonOpts, userAgent, proxy, verify });

    case 'local':
      if (!html || !js) throw new Error('本地模式需要 html 和 js 参数');
      return await crackLocal(url, html, js, { ...commonOpts, ts });

    case 'execute':
      if (!jsCode) throw new Error('执行模式需要 jsCode 参数');
      return await executeJs(url, html, jsCode, { ...commonOpts, waitEvent });

    default:
      throw new Error(`不支持的模式: ${mode}，可选: remote, local, execute`);
  }
}

const server = http.createServer(async (req, res) => {
  // CORS
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'POST, GET, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');

  if (req.method === 'OPTIONS') {
    res.writeHead(204);
    return res.end();
  }

  const urlPath = req.url.split('?')[0];

  // GET /api/health
  if (req.method === 'GET' && urlPath === '/api/health') {
    return sendJson(res, 200, { status: 'ok', version });
  }

  // POST /api/crack
  if (req.method === 'POST' && urlPath === '/api/crack') {
    try {
      const body = await parseBody(req);
      logger.info(`收到请求: mode=${body.mode || 'remote'}, url=${body.url || 'N/A'}`);
      const result = await handleCrack(body);
      logger.info(`请求完成: success=${result.success}, isRS=${result.isRS}`);
      return sendJson(res, 200, result);
    } catch (err) {
      const errObj = typeof err === 'object' && err !== null ? err : { error: String(err) };
      logger.error('请求处理失败:', errObj.error || errObj.message || err);
      return sendJson(res, 500, {
        success: false,
        error: errObj.error || errObj.message || '内部错误',
      });
    }
  }

  sendJson(res, 404, { error: '接口不存在' });
});

server.listen(PORT, HOST, () => {
  logger.info(`sdenv API 服务已启动: http://${HOST}:${PORT}`);
  logger.info(`版本: v${version}`);
  logger.info('接口:');
  logger.info('  GET  /api/health  - 健康检查');
  logger.info('  POST /api/crack   - 瑞数破解');
  logger.info('模式:');
  logger.info('  remote  - 远程请求URL自动破解');
  logger.info('  local   - 本地HTML/JS破解');
  logger.info('  execute - 自定义JS执行');
});

server.on('error', (err) => {
  if (err.code === 'EADDRINUSE') {
    logger.error(`端口 ${PORT} 已被占用，请设置 SDENV_PORT 环境变量使用其他端口`);
  } else {
    logger.error('服务器错误:', err.message);
  }
  process.exit(1);
});
