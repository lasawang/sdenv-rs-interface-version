'use strict';

/**
 * 动态 DOM/BOM 环境配置模块
 * 允许用户针对不同网站动态调整浏览器环境参数
 */
function applyEnvConfig(window, sdenv, config = {}) {
  const { dom = {}, bom = {}, navigator: navConfig = {}, custom = {} } = config;

  // ===== Navigator 配置覆盖 =====
  const nav = window.navigator;
  const navProto = Object.getPrototypeOf(nav) || nav.__proto__;

  // 辅助函数：在原型或实例上定义 getter 属性
  function defineNavProp(propName, value) {
    const getter = () => value;
    // 优先在实例上定义（实例属性会遮蔽原型 getter）
    const targets = [nav, navProto];
    for (const target of targets) {
      if (!target) continue;
      try {
        Object.defineProperty(target, propName, {
          get: getter, configurable: true, enumerable: true,
        });
        sdenv.tools.setFuncNative(getter, 'get');
        return;
      } catch (e) {}
    }
  }

  if (navConfig.userAgent) {
    const ua = navConfig.userAgent;
    defineNavProp('userAgent', ua);
    defineNavProp('appVersion', ua.replace(/^Mozilla\//, ''));
  }

  if (navConfig.platform) {
    defineNavProp('platform', navConfig.platform);
  }

  if (navConfig.vendor) {
    defineNavProp('vendor', navConfig.vendor);
  }

  if (navConfig.languages) {
    try {
      const langs = Object.freeze([...navConfig.languages]);
      Object.defineProperty(nav, 'languages', { get: () => langs, configurable: true, enumerable: true });
      Object.defineProperty(nav, 'language', { get: () => langs[0], configurable: true, enumerable: true });
    } catch (e) {}
  }

  if (navConfig.hardwareConcurrency !== undefined) {
    try {
      Object.defineProperty(nav, 'hardwareConcurrency', {
        get: () => navConfig.hardwareConcurrency, configurable: true, enumerable: true,
      });
    } catch (e) {}
  }

  if (navConfig.deviceMemory !== undefined) {
    try {
      Object.defineProperty(nav, 'deviceMemory', {
        get: () => navConfig.deviceMemory, configurable: true, enumerable: true,
      });
    } catch (e) {}
  }

  if (navConfig.maxTouchPoints !== undefined) {
    try {
      Object.defineProperty(nav, 'maxTouchPoints', {
        get: () => navConfig.maxTouchPoints, configurable: true, enumerable: true,
      });
    } catch (e) {}
  }

  // ===== Screen 配置覆盖 =====
  if (dom.screen) {
    for (const [k, v] of Object.entries(dom.screen)) {
      try {
        Object.defineProperty(window.screen, k, { get: () => v, configurable: true, enumerable: true });
      } catch (e) {}
    }
  }

  // ===== Window 尺寸配置覆盖 =====
  const dimKeys = [
    'innerWidth', 'innerHeight', 'outerWidth', 'outerHeight',
    'screenX', 'screenY', 'screenLeft', 'screenTop', 'devicePixelRatio'
  ];
  for (const k of dimKeys) {
    if (bom[k] !== undefined) {
      try {
        Object.defineProperty(window, k, { get: () => bom[k], configurable: true, enumerable: true });
      } catch (e) {}
    }
  }

  // 同步更新 visualViewport
  try {
    if (bom.innerWidth !== undefined) {
      Object.defineProperty(window.visualViewport, 'width', {
        get: () => bom.innerWidth, configurable: true, enumerable: true,
      });
    }
    if (bom.innerHeight !== undefined) {
      Object.defineProperty(window.visualViewport, 'height', {
        get: () => bom.innerHeight, configurable: true, enumerable: true,
      });
    }
  } catch (e) {}

  // ===== Document 配置覆盖 =====
  if (dom.referrer !== undefined) {
    try {
      Object.defineProperty(window.document, 'referrer', {
        get: () => dom.referrer, configurable: true, enumerable: true,
      });
    } catch (e) {}
  }
  if (dom.title !== undefined) {
    try { window.document.title = dom.title; } catch (e) {}
  }

  // ===== 自定义属性配置 =====
  // 支持通过点号路径设置任意属性，如 "navigator.connection.downlink": 10
  if (custom && typeof custom === 'object') {
    for (const [dotPath, value] of Object.entries(custom)) {
      try {
        const parts = dotPath.split('.');
        let obj = window;
        for (let i = 0; i < parts.length - 1; i++) {
          if (obj[parts[i]] === undefined || obj[parts[i]] === null) break;
          obj = obj[parts[i]];
        }
        const lastKey = parts[parts.length - 1];
        if (typeof value === 'object' && value !== null && !Array.isArray(value)) {
          if (!obj[lastKey]) obj[lastKey] = {};
          Object.assign(obj[lastKey], value);
        } else {
          Object.defineProperty(obj, lastKey, {
            get: () => value, configurable: true, enumerable: true,
          });
        }
      } catch (e) {}
    }
  }
}

module.exports = { applyEnvConfig };
