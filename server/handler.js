'use strict';

const vm = require('vm');
const path = require('path');
const { constants: cryptoConstants } = require('crypto');

const { jsdomFromUrl, jsdomFromText, logger } = require('..');
const { applyStealthPatches } = require('./stealth');
const { applyEnvConfig } = require('./env_config');

const DEFAULT_UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36';

/**
 * 远程模式 - 自动请求URL并破解瑞数
 */
async function crackUrl(url, options = {}) {
  const {
    domConfig = {},
    bomConfig = {},
    navigatorConfig = {},
    resourceMode = 'full',
    userAgent = DEFAULT_UA,
    proxy,
    timeout = 30000,
    verify = true,
    windowProxyConfig = {},
  } = options;

  return new Promise(async (resolve, reject) => {
    const timer = setTimeout(() => {
      reject({ success: false, error: 'timeout', message: `操作超时 (${timeout}ms)` });
    }, timeout);

    try {
      const dom = await jsdomFromUrl(url, {
        userAgent,
        proxy,
        strictSSL: false,
        resourceMode,
        windowProxyConfig,
        consoleConfig: { error: () => {} },
        beforeParse: (window, sdenv) => {
          applyStealthPatches(window, sdenv);
          applyEnvConfig(window, sdenv, {
            dom: domConfig,
            bom: bomConfig,
            navigator: navigatorConfig,
          });
        },
      });

      const { window, cookieJar } = dom;

      // 检测是否为瑞数网站
      if (!window.$_ts) {
        clearTimeout(timer);
        const pageContent = dom.serialize();
        try { window.close(); } catch (e) {}
        resolve({
          success: true,
          isRS: false,
          cookies: cookieJar.getCookieStringSync(url),
          data: pageContent,
          message: '非瑞数网站',
        });
        return;
      }

      logger.info(`检测到瑞数网站，等待生成cookie...`);

      // 监听退出事件（location.replace / location.assign / open）
      window.addEventListener('sdenv:exit', async (e) => {
        clearTimeout(timer);
        const cookies = cookieJar.getCookieStringSync(url);
        const eventDetail = e.detail;
        logger.debug('生成cookie：', cookies);

        try { window.close(); } catch (err) {}

        if (verify && eventDetail.url) {
          try {
            const fetchOptions = {
              headers: {
                'Cookie': cookies,
                'User-Agent': userAgent,
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7',
              },
              redirect: 'follow',
            };
            if (proxy) {
              try {
                const { ProxyAgent } = require('undici');
                fetchOptions.dispatcher = new ProxyAgent(proxy);
              } catch (e) {}
            } else if (cryptoConstants?.SSL_OP_LEGACY_SERVER_CONNECT) {
              try {
                const { Agent } = require('undici');
                fetchOptions.dispatcher = new Agent({
                  connect: {
                    rejectUnauthorized: false,
                    secureOptions: cryptoConstants.SSL_OP_LEGACY_SERVER_CONNECT,
                  },
                });
              } catch (e) {}
            }
            const res = await fetch(eventDetail.url, fetchOptions);
            const text = await res.text();
            resolve({
              success: true,
              isRS: true,
              cookies,
              status: res.status,
              headers: Object.fromEntries(res.headers.entries()),
              data: text,
              event: eventDetail,
            });
          } catch (verifyErr) {
            resolve({
              success: true,
              isRS: true,
              cookies,
              event: eventDetail,
              verifyError: verifyErr.message,
            });
          }
        } else {
          resolve({
            success: true,
            isRS: true,
            cookies,
            event: eventDetail,
          });
        }
      });
    } catch (err) {
      clearTimeout(timer);
      reject({ success: false, error: err.message, stack: err.stack });
    }
  });
}

/**
 * 本地模式 - 使用提供的HTML/JS破解
 */
async function crackLocal(url, html, js, options = {}) {
  const {
    ts,
    domConfig = {},
    bomConfig = {},
    navigatorConfig = {},
    timeout = 30000,
    windowProxyConfig = {},
  } = options;

  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => {
      reject({ success: false, error: 'timeout', message: `操作超时 (${timeout}ms)` });
    }, timeout);

    try {
      const dom = jsdomFromText(html, {
        url,
        referrer: url,
        contentType: 'text/html',
        runScripts: 'outside-only',
        windowProxyConfig,
        beforeParse: (window, sdenv) => {
          applyStealthPatches(window, sdenv);
          applyEnvConfig(window, sdenv, {
            dom: domConfig,
            bom: bomConfig,
            navigator: navigatorConfig,
          });
        },
      });

      const { window, cookieJar } = dom;

      // 设置 $_ts
      if (ts) {
        window.$_ts = typeof ts === 'string' ? JSON.parse(ts) : ts;
      }

      // 监听退出事件
      window.addEventListener('sdenv:exit', (e) => {
        clearTimeout(timer);
        const cookies = cookieJar.getCookieStringSync(url);
        logger.debug('本地模式生成cookie：', cookies);
        try { window.close(); } catch (err) {}
        resolve({
          success: true,
          isRS: true,
          cookies,
          event: e.detail,
        });
      });

      // 执行JS
      vm.runInContext(js, dom.getInternalVMContext());
    } catch (err) {
      clearTimeout(timer);
      reject({ success: false, error: err.message, stack: err.stack });
    }
  });
}

/**
 * 执行模式 - 在模拟浏览器环境中执行自定义JS并返回结果
 */
async function executeJs(url, html, jsCode, options = {}) {
  const {
    domConfig = {},
    bomConfig = {},
    navigatorConfig = {},
    timeout = 30000,
    windowProxyConfig = {},
    waitEvent,
  } = options;

  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => {
      reject({ success: false, error: 'timeout', message: `操作超时 (${timeout}ms)` });
    }, timeout);

    try {
      const dom = jsdomFromText(html || '<html><head></head><body></body></html>', {
        url: url || 'https://example.com',
        referrer: url || 'https://example.com',
        contentType: 'text/html',
        runScripts: 'outside-only',
        windowProxyConfig,
        beforeParse: (window, sdenv) => {
          applyStealthPatches(window, sdenv);
          applyEnvConfig(window, sdenv, {
            dom: domConfig,
            bom: bomConfig,
            navigator: navigatorConfig,
          });
        },
      });

      const { window, cookieJar } = dom;
      const targetUrl = url || 'https://example.com';

      if (waitEvent) {
        // 等待特定事件后返回
        window.addEventListener(waitEvent, (e) => {
          clearTimeout(timer);
          const cookies = cookieJar.getCookieStringSync(targetUrl);
          try { window.close(); } catch (err) {}
          resolve({
            success: true,
            cookies,
            event: e.detail,
          });
        });
        vm.runInContext(jsCode, dom.getInternalVMContext());
      } else {
        // 直接执行并返回结果
        const result = vm.runInContext(jsCode, dom.getInternalVMContext());
        clearTimeout(timer);
        const cookies = cookieJar.getCookieStringSync(targetUrl);

        let resultStr;
        try {
          resultStr = typeof result === 'object' ? JSON.stringify(result) : String(result ?? '');
        } catch (e) {
          resultStr = String(result);
        }

        try { window.close(); } catch (err) {}
        resolve({
          success: true,
          result: resultStr,
          cookies,
        });
      }
    } catch (err) {
      clearTimeout(timer);
      reject({ success: false, error: err.message, stack: err.stack });
    }
  });
}

module.exports = { crackUrl, crackLocal, executeJs };
