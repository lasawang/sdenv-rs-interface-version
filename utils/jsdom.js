const jsdom = require('sdenv-jsdom');
const { constants: cryptoConstants } = require('crypto');
const Request = require('sdenv-jsdom/lib/jsdom/living/helpers/http-request');
const agentFactory = require('sdenv-jsdom/lib/jsdom/living/helpers/agent-factory');

const logger = require('./logger');
const paths = require('./paths');
const { JSDOM, CookieJar } = jsdom;
const browser = require('../browser/');
const version = require(paths.package).version.split('-')[0];

const LEGACY_RENEGOTIATION_OPTION = cryptoConstants?.SSL_OP_LEGACY_SERVER_CONNECT || 0;
const NON_ESSENTIAL_RESOURCE_EXTENSIONS = new Set([
  '.png', '.jpg', '.jpeg', '.gif', '.webp', '.svg', '.ico',
  '.css', '.woff', '.woff2', '.ttf', '.otf', '.eot',
  '.mp4', '.mp3', '.wav', '.webm', '.avi', '.mov', '.m3u8',
  '.zip', '.rar', '.7z', '.pdf',
]);

function shouldSkipNonEssentialResource(urlString) {
  try {
    const parsed = new URL(urlString);
    const pathname = (parsed.pathname || '').toLowerCase();
    const dotIndex = pathname.lastIndexOf('.');
    if (dotIndex < 0) {
      return false;
    }
    const extension = pathname.slice(dotIndex);
    return NON_ESSENTIAL_RESOURCE_EXTENSIONS.has(extension);
  } catch (error) {
    return false;
  }
}

function applyLegacyRenegotiationOption(agent) {
  if (!agent || !LEGACY_RENEGOTIATION_OPTION) {
    return;
  }

  if (agent.options && typeof agent.options === 'object') {
    const secureOptions = Number(agent.options.secureOptions || 0);
    agent.options.secureOptions = secureOptions | LEGACY_RENEGOTIATION_OPTION;
  }

  if (agent.connectOpts && typeof agent.connectOpts === 'object') {
    const secureOptions = Number(agent.connectOpts.secureOptions || 0);
    agent.connectOpts.secureOptions = secureOptions | LEGACY_RENEGOTIATION_OPTION;
  }
}

function createAgents(proxy, strictSSL, allowUnsafeLegacyRenegotiation) {
  const agents = agentFactory(proxy, strictSSL);
  if (allowUnsafeLegacyRenegotiation) {
    applyLegacyRenegotiationOption(agents?.https);
  }
  return agents;
}

class ResourceLoaderWithLegacyRenegotiation extends jsdom.ResourceLoader {
  constructor({ allowUnsafeLegacyRenegotiation = true, skipNonEssential = false, ...options } = {}) {
    super(options);
    this._allowUnsafeLegacyRenegotiation = allowUnsafeLegacyRenegotiation;
    this._skipNonEssential = skipNonEssential;
  }

  fetch(urlString, { accept, cookieJar, referrer } = {}) {
    let protocol;
    try {
      protocol = new URL(urlString).protocol;
    } catch (error) {
      return super.fetch(urlString, { accept, cookieJar, referrer });
    }

    if (protocol !== 'http:' && protocol !== 'https:') {
      return super.fetch(urlString, { accept, cookieJar, referrer });
    }

    if (this._skipNonEssential && shouldSkipNonEssentialResource(urlString)) {
      return null;
    }

    const headers = {
      'User-Agent': this._userAgent,
      'Accept-Language': 'en',
      'Accept-Encoding': 'gzip',
      Accept: accept || '*/*',
    };
    if (referrer) {
      headers.Referer = referrer;
    }

    const agents = createAgents(this._proxy, this._strictSSL, this._allowUnsafeLegacyRenegotiation);
    const requestClient = new Request(
      urlString,
      { followRedirects: true, cookieJar, agents },
      { headers },
    );

    const promise = new Promise((resolve, reject) => {
      const accumulated = [];
      requestClient.once('response', (res) => {
        promise.response = res;
      });
      requestClient.on('data', (chunk) => {
        accumulated.push(chunk);
      });
      requestClient.on('end', () => resolve(Buffer.concat(accumulated)));
      requestClient.on('error', reject);
    });

    requestClient.on('end', () => {
      promise.href = requestClient.currentURL;
    });
    promise.abort = requestClient.abort.bind(requestClient);
    promise.getHeader = (name) => headers[name] || requestClient.getHeader(name);
    requestClient.end();

    return promise;
  }
}

function wrap(func) {
  return (urlOrHtml, {
    // logger event handlers for jsdom virtual console
    consoleConfig = {},
    browserType = 'chrome',
    windowProxyConfig = {},
    beforeParse,
    ...config
  } = {}) => {
    if (!browser.isSupport(browserType)) {
      throw new Error(`Unsupported browser type: ${browserType}`);
    }

    const options = {
      pretendToBeVisual: true,
      cookieJar: new CookieJar(),
      beforeParse(window) {
        const sdenv = browser(window, browserType);
        sdenv.getHandle('window')(windowProxyConfig);
        beforeParse?.(window, sdenv);
      },
      ...config,
    };

    if (typeof consoleConfig === 'object') {
      const virtualConsole = new jsdom.VirtualConsole();
      virtualConsole.on('log', consoleConfig.log || logger.log.bind(logger));
      virtualConsole.on('warn', consoleConfig.warn || logger.warn.bind(logger));
      virtualConsole.on('error', consoleConfig.error || logger.error.bind(logger));
      virtualConsole.on('info', consoleConfig.info || logger.info.bind(logger));
      virtualConsole.on('table', consoleConfig.table || logger.log.bind(logger));
      virtualConsole.on('jsdomError', consoleConfig.error || logger.error.bind(logger));
      options.virtualConsole = virtualConsole;
    }

    return func(urlOrHtml, options);
  };
}

exports.jsdomFromUrl = wrap(async (url, {
  strictSSL = false,
  proxy,
  userAgent = `sdenv/${version}`,
  resourceMode = 'full',
  allowUnsafeLegacyRenegotiation = true,
  resources,
  ...options
}) => {
  const resourceLoader = resources || new ResourceLoaderWithLegacyRenegotiation({
    strictSSL,
    proxy,
    userAgent,
    allowUnsafeLegacyRenegotiation,
    skipNonEssential: resourceMode === 'fast',
  });

  return JSDOM.fromURL(url, {
    runScripts: 'dangerously',
    resources: resourceLoader,
    ...options,
  });
});

exports.jsdomFromText = wrap((html, options) => {
  return new JSDOM(html, options);
});
