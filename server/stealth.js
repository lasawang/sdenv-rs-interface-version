'use strict';

/**
 * JSDOM 指纹抹除模块 - 移除 jsdom 特征使其更接近真实浏览器
 */
function applyStealthPatches(window, sdenv) {
  const { setFuncNative } = sdenv.tools;

  // ===== 1. 清除 Node.js 全局变量泄露 =====
  const nodeGlobals = [
    'process', 'Buffer', 'setImmediate', 'clearImmediate',
    '__filename', '__dirname', 'module', 'exports'
  ];
  for (const key of nodeGlobals) {
    try { delete window[key]; } catch (e) {}
  }
  // global 需要特殊处理：RS代码可能通过 global.Math 等访问全局对象
  // 真实浏览器中 global 不存在，但删除可能不生效，所以指向 window 自身
  try {
    if ('global' in window) {
      Object.defineProperty(window, 'global', {
        get: () => window,
        configurable: true,
      });
    }
  } catch (e) {}

  // ===== 2. navigator 指纹修复 =====
  const nav = window.navigator;
  const navProto = Object.getPrototypeOf(nav) || nav.__proto__;

  // webdriver 必须为 false
  try {
    const target = navProto || nav;
    Object.defineProperty(target, 'webdriver', {
      get: () => false,
      configurable: true,
      enumerable: true,
    });
    setFuncNative(Object.getOwnPropertyDescriptor(target, 'webdriver').get, 'get');
  } catch (e) {}

  // plugins - 真实 Chrome 有 5 个 PDF 相关插件
  try {
    const pdfMime = {
      type: 'application/pdf',
      suffixes: 'pdf',
      description: 'Portable Document Format',
      enabledPlugin: null,
    };
    const pluginNames = [
      'PDF Viewer', 'Chrome PDF Viewer', 'Chromium PDF Viewer',
      'Microsoft Edge PDF Viewer', 'WebKit built-in PDF'
    ];
    const plugins = pluginNames.map(name => {
      const p = {
        name,
        filename: 'internal-pdf-viewer',
        description: 'Portable Document Format',
        length: 1,
        0: pdfMime,
        item: function (i) { return i === 0 ? pdfMime : null; },
        namedItem: function (n) { return n === pdfMime.type ? pdfMime : null; },
      };
      pdfMime.enabledPlugin = p;
      return p;
    });

    const pluginArray = { length: plugins.length, refresh: function () {} };
    plugins.forEach((p, i) => { pluginArray[i] = p; pluginArray[p.name] = p; });
    pluginArray.item = function (i) { return plugins[i] || null; };
    pluginArray.namedItem = function (n) { return pluginArray[n] || null; };

    const mimeTypeArray = { length: 1, 0: pdfMime, 'application/pdf': pdfMime };
    mimeTypeArray.item = function (i) { return i === 0 ? pdfMime : null; };
    mimeTypeArray.namedItem = function (n) { return n === 'application/pdf' ? pdfMime : null; };

    Object.defineProperty(nav, 'plugins', { get: () => pluginArray, configurable: true, enumerable: true });
    Object.defineProperty(nav, 'mimeTypes', { get: () => mimeTypeArray, configurable: true, enumerable: true });
    Object.defineProperty(nav, 'pdfViewerEnabled', { get: () => true, configurable: true, enumerable: true });
  } catch (e) {}

  // languages
  try {
    const defaultLangs = Object.freeze(['zh-CN', 'zh', 'en-US', 'en']);
    Object.defineProperty(nav, 'languages', { get: () => defaultLangs, configurable: true, enumerable: true });
    Object.defineProperty(nav, 'language', { get: () => 'zh-CN', configurable: true, enumerable: true });
  } catch (e) {}

  // 硬件相关
  try {
    Object.defineProperty(nav, 'hardwareConcurrency', { get: () => 8, configurable: true, enumerable: true });
  } catch (e) {}
  try {
    Object.defineProperty(nav, 'deviceMemory', { get: () => 8, configurable: true, enumerable: true });
  } catch (e) {}
  try {
    Object.defineProperty(nav, 'maxTouchPoints', { get: () => 0, configurable: true, enumerable: true });
  } catch (e) {}

  // 为 navigator 所有 getter 设置 native 标识
  try {
    const navProps = ['webdriver', 'plugins', 'mimeTypes', 'pdfViewerEnabled',
      'languages', 'language', 'hardwareConcurrency', 'deviceMemory', 'maxTouchPoints'];
    for (const prop of navProps) {
      const desc = Object.getOwnPropertyDescriptor(nav, prop) ||
        Object.getOwnPropertyDescriptor(navProto, prop);
      if (desc && desc.get) {
        try { setFuncNative(desc.get, 'get'); } catch (e) {}
      }
    }
  } catch (e) {}

  // ===== 3. screen 对象修复 =====
  const screenDefaults = {
    width: 1920, height: 1080,
    availWidth: 1920, availHeight: 1040,
    colorDepth: 24, pixelDepth: 24,
    availLeft: 0, availTop: 0,
  };
  for (const [k, v] of Object.entries(screenDefaults)) {
    try {
      Object.defineProperty(window.screen, k, { get: () => v, configurable: true, enumerable: true });
    } catch (e) {}
  }
  try {
    Object.defineProperty(window.screen, 'orientation', {
      get: () => ({ angle: 0, type: 'landscape-primary', onchange: null }),
      configurable: true, enumerable: true,
    });
  } catch (e) {}

  // ===== 4. window 尺寸属性 =====
  const windowDims = {
    innerWidth: 1920, innerHeight: 955,
    outerWidth: 1920, outerHeight: 1080,
    screenX: 0, screenY: 0,
    screenLeft: 0, screenTop: 0,
    devicePixelRatio: 1,
    pageXOffset: 0, pageYOffset: 0,
    scrollX: 0, scrollY: 0,
  };
  for (const [k, v] of Object.entries(windowDims)) {
    try {
      Object.defineProperty(window, k, { get: () => v, configurable: true, enumerable: true });
    } catch (e) {}
  }

  // ===== 5. document 属性修复 =====
  try {
    Object.defineProperty(window.document, 'hidden', { get: () => false, configurable: true, enumerable: true });
    Object.defineProperty(window.document, 'visibilityState', { get: () => 'visible', configurable: true, enumerable: true });
  } catch (e) {}
  try {
    window.document.hasFocus = function hasFocus() { return true; };
    setFuncNative(window.document.hasFocus, 'hasFocus', 0);
  } catch (e) {}

  // ===== 6. performance 修复 =====
  try {
    const navStart = Date.now() - Math.floor(Math.random() * 500 + 300);
    const perfTiming = {
      navigationStart: navStart,
      unloadEventStart: 0, unloadEventEnd: 0,
      redirectStart: 0, redirectEnd: 0,
      fetchStart: navStart + 1,
      domainLookupStart: navStart + 3,
      domainLookupEnd: navStart + 12,
      connectStart: navStart + 12,
      connectEnd: navStart + 45,
      secureConnectionStart: navStart + 18,
      requestStart: navStart + 50,
      responseStart: navStart + 95,
      responseEnd: navStart + 115,
      domLoading: navStart + 120,
      domInteractive: navStart + 195,
      domContentLoadedEventStart: navStart + 205,
      domContentLoadedEventEnd: navStart + 210,
      domComplete: navStart + 340,
      loadEventStart: navStart + 345,
      loadEventEnd: navStart + 350,
    };
    if (!window.performance.timing || typeof window.performance.timing.navigationStart === 'undefined') {
      Object.defineProperty(window.performance, 'timing', {
        get: () => perfTiming, configurable: true, enumerable: true,
      });
    }
    if (!window.performance.navigation) {
      Object.defineProperty(window.performance, 'navigation', {
        get: () => ({ type: 0, redirectCount: 0 }), configurable: true, enumerable: true,
      });
    }
  } catch (e) {}

  // ===== 7. 补充缺失的浏览器 API =====
  // Notification
  if (!window.Notification) {
    const Notification = function Notification() { throw new TypeError("Illegal constructor"); };
    Notification.permission = 'default';
    Notification.requestPermission = function requestPermission() { return Promise.resolve('default'); };
    Notification.maxActions = 2;
    try {
      setFuncNative(Notification, 'Notification');
      setFuncNative(Notification.requestPermission, 'requestPermission');
    } catch (e) {}
    window.Notification = Notification;
  }

  // Permissions
  if (!window.navigator.permissions) {
    const Permissions = function Permissions() { throw new TypeError("Illegal constructor"); };
    Permissions.prototype.query = function query() {
      return Promise.resolve({ state: 'prompt', onchange: null });
    };
    try { setFuncNative(Permissions, 'Permissions'); } catch (e) {}
    window.Permissions = Permissions;
    window.navigator.permissions = { __proto__: Permissions.prototype };
  }

  // CacheStorage
  if (!window.caches) {
    const CacheStorage = function CacheStorage() { throw new TypeError("Illegal constructor"); };
    CacheStorage.prototype.open = function open() { return Promise.resolve({}); };
    CacheStorage.prototype.has = function has() { return Promise.resolve(false); };
    CacheStorage.prototype.keys = function keys() { return Promise.resolve([]); };
    CacheStorage.prototype.match = function match() { return Promise.resolve(undefined); };
    CacheStorage.prototype.delete = function _delete() { return Promise.resolve(false); };
    try { setFuncNative(CacheStorage, 'CacheStorage'); } catch (e) {}
    window.CacheStorage = CacheStorage;
    window.caches = { __proto__: CacheStorage.prototype };
  }

  // SpeechSynthesis
  if (!window.speechSynthesis) {
    const SpeechSynthesis = function SpeechSynthesis() { throw new TypeError("Illegal constructor"); };
    const proto = {
      speaking: false, pending: false, paused: false, onvoiceschanged: null,
      getVoices: function getVoices() { return []; },
      speak: function speak() {}, cancel: function cancel() {},
      pause: function pause() {}, resume: function resume() {},
    };
    SpeechSynthesis.prototype = proto;
    try { setFuncNative(SpeechSynthesis, 'SpeechSynthesis'); } catch (e) {}
    window.SpeechSynthesis = SpeechSynthesis;
    window.speechSynthesis = { __proto__: proto };
  }

  // crypto.subtle
  if (window.crypto && !window.crypto.subtle) {
    try {
      window.crypto.subtle = {
        digest: function digest() { return Promise.resolve(new ArrayBuffer(0)); },
        encrypt: function encrypt() { return Promise.resolve(new ArrayBuffer(0)); },
        decrypt: function decrypt() { return Promise.resolve(new ArrayBuffer(0)); },
        generateKey: function generateKey() { return Promise.resolve({}); },
        sign: function sign() { return Promise.resolve(new ArrayBuffer(0)); },
        verify: function verify() { return Promise.resolve(false); },
      };
    } catch (e) {}
  }

  // ===== 8. Error.stack 清理 jsdom 路径 =====
  try {
    const origDescriptor = Object.getOwnPropertyDescriptor(Error.prototype, 'stack');
    if (origDescriptor && origDescriptor.get) {
      const origGet = origDescriptor.get;
      Object.defineProperty(Error.prototype, 'stack', {
        ...origDescriptor,
        get: function () {
          let stack = origGet.call(this);
          if (typeof stack === 'string') {
            stack = stack
              .replace(/[^\s(]*node_modules[/\\]+(sdenv-jsdom|jsdom|sdenv-extend)[/\\]+[^\s):]*/g, '<anonymous>')
              .replace(/[^\s(]*sdenv[/\\]+server[/\\]+[^\s):]*/g, '<anonymous>')
              .replace(/at\s+Script\.\w+\s+\((?:node:)?vm\.js[^)]*\)/g, 'at <anonymous>');
          }
          return stack;
        },
      });
    }
  } catch (e) {}

  // ===== 9. 隐藏 jsdom 内部标识 =====
  try {
    if (!Object.getOwnPropertyDescriptor(window, Symbol.toStringTag)) {
      Object.defineProperty(window, Symbol.toStringTag, { value: 'Window', configurable: true });
    }
  } catch (e) {}
  try {
    if (!Object.getOwnPropertyDescriptor(window.document, Symbol.toStringTag)) {
      Object.defineProperty(window.document, Symbol.toStringTag, { value: 'HTMLDocument', configurable: true });
    }
  } catch (e) {}

  // 确保 toString 返回正确结果
  try {
    const origToString = window.Object.prototype.toString;
    window.Object.prototype.toString = function () {
      if (this === window) return '[object Window]';
      if (this === window.document) return '[object HTMLDocument]';
      if (this === window.navigator) return '[object Navigator]';
      if (this === window.location) return '[object Location]';
      return origToString.call(this);
    };
    setFuncNative(window.Object.prototype.toString, 'toString', 0);
  } catch (e) {}
}

module.exports = { applyStealthPatches };
