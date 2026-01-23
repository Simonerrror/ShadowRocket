/**
 * Clash Verge Rev script profile (mirrors shadowrocket.conf)
 * - Filters proxies: VLESS only, exclude Russia/Belarus/Ukraine
 * - GOOGLE group: Netherlands(R) or UAE, fallback to all clean proxies
 * - Rules: QUIC blocks, google/gemini/youtube, microsoft, community, domain_ips, voice_ports, telegram, RU bypass, final PROXY
 */

module.exports.main = async function (config) {
  // -------- System baseline (close to shadowrocket.conf) --------
  config.port = 7890;
  config['socks-port'] = 7891;
  config['allow-lan'] = false;
  config.mode = 'rule';
  config['log-level'] = 'info';
  config.ipv6 = false;

  config.tun = {
    enable: true,
    stack: 'system',
    'dns-hijack': ['any:53'],
    'auto-route': true,
    'auto-detect-interface': true
  };

  config.dns = {
    enable: true,
    listen: '0.0.0.0:1053',
    ipv6: false,
    'enhanced-mode': 'fake-ip',
    'fake-ip-range': '198.18.0.1/16',
    'fake-ip-filter': ['*', '+.lan', '+.local'],
    nameserver: ['https://1.1.1.1/dns-query', 'https://8.8.8.8/dns-query'],
    fallback: ['https://8.8.8.8/dns-query', 'https://94.140.14.14/dns-query']
  };

  // -------- Rule providers (exact URLs from shadowrocket.conf) --------
  config['rule-providers'] = {
    whitelist_direct: {
      type: 'http',
      behavior: 'classical',
      url: 'https://raw.githubusercontent.com/Simonerrror/ShadowRocket/main/rules/whitelist_direct.list',
      path: './rules/whitelist.yaml',
      interval: 86400
    },
    greylist_proxy: {
      type: 'http',
      behavior: 'classical',
      url: 'https://raw.githubusercontent.com/Simonerrror/ShadowRocket/main/rules/greylist_proxy.list',
      path: './rules/greylist.yaml',
      interval: 86400
    },
    google_gemini: {
      type: 'http',
      behavior: 'classical',
      url: 'https://raw.githubusercontent.com/Simonerrror/ShadowRocket/main/rules/google-gemini.list',
      path: './rules/google_gemini.yaml',
      interval: 86400
    },
    google_full: {
      type: 'http',
      behavior: 'classical',
      url: 'https://raw.githubusercontent.com/Simonerrror/ShadowRocket/main/rules/google.list',
      path: './rules/google.yaml',
      interval: 86400
    },
    gemini_ip: {
      type: 'http',
      behavior: 'classical',
      url: 'https://raw.githubusercontent.com/Simonerrror/ShadowRocket/main/rules/gemini_ip.list',
      path: './rules/gemini_ip.yaml',
      interval: 86400
    },
    youtube: {
      type: 'http',
      behavior: 'classical',
      url: 'https://raw.githubusercontent.com/Simonerrror/ShadowRocket/main/rules/youtube.list',
      path: './rules/youtube.yaml',
      interval: 86400
    },
    youtubemusic: {
      type: 'http',
      behavior: 'classical',
      url: 'https://raw.githubusercontent.com/Simonerrror/ShadowRocket/main/rules/youtubemusic.list',
      path: './rules/youtubemusic.yaml',
      interval: 86400
    },
    microsoft: {
      type: 'http',
      behavior: 'classical',
      url: 'https://raw.githubusercontent.com/Simonerrror/ShadowRocket/main/rules/microsoft.list',
      path: './rules/microsoft.yaml',
      interval: 86400
    },
    domains_community: {
      type: 'http',
      behavior: 'classical',
      url: 'https://raw.githubusercontent.com/Simonerrror/ShadowRocket/main/rules/domains_community.list',
      path: './rules/domains_community.yaml',
      interval: 86400
    },
    domain_ips: {
      type: 'http',
      behavior: 'classical',
      url: 'https://raw.githubusercontent.com/Simonerrror/ShadowRocket/main/rules/domain_ips.list',
      path: './rules/domain_ips.yaml',
      interval: 86400
    },
    voice_ports: {
      type: 'http',
      behavior: 'classical',
      url: 'https://raw.githubusercontent.com/Simonerrror/ShadowRocket/main/rules/voice_ports.list',
      path: './rules/voice_ports.yaml',
      interval: 86400
    },
    telegram: {
      type: 'http',
      behavior: 'classical',
      url: 'https://raw.githubusercontent.com/Simonerrror/ShadowRocket/main/rules/telegram.list',
      path: './rules/telegram.yaml',
      interval: 86400
    }
  };

  // -------- Proxy filtering (VLESS only, exclude RU/BY/UA) --------
  const rawProxies = Array.isArray(config.proxies) ? config.proxies : [];
  const cleanProxies = rawProxies.filter(p => {
    const n = p.name || '';
    return /Vless/i.test(n) && !/(Russia|Belarus|Ukraine)/i.test(n);
  });

  const allNames = cleanProxies.map(p => p.name);
  const googleNames = allNames.filter(n => /(Netherlands\(R\)|UAE)/i.test(n));
  const finalGoogleNames = googleNames.length ? googleNames : allNames;

  // Provider fallback (when proxies come from provider at runtime)
  const providerNames = Object.keys(config['proxy-providers'] || {});
  const mainProvider = providerNames[0];

  const googleGroup = finalGoogleNames.length
    ? {
        name: 'GOOGLE',
        type: 'url-test',
        url: 'http://www.gstatic.com/generate_204',
        interval: 300,
        tolerance: 50,
        proxies: finalGoogleNames
      }
    : {
        name: 'GOOGLE',
        type: 'url-test',
        url: 'http://www.gstatic.com/generate_204',
        interval: 300,
        tolerance: 50,
        use: mainProvider ? [mainProvider] : [],
        filter: '(?i)(Netherlands\\(R\\)|UAE).*Vless'
      };

  const autoMainGroup = allNames.length
    ? {
        name: 'AUTO-MAIN',
        type: 'url-test',
        url: 'http://www.gstatic.com/generate_204',
        interval: 600,
        tolerance: 100,
        proxies: allNames
      }
    : {
        name: 'AUTO-MAIN',
        type: 'url-test',
        url: 'http://www.gstatic.com/generate_204',
        interval: 600,
        tolerance: 100,
        use: mainProvider ? [mainProvider] : [],
        filter: '(?i)^(?!.*(Russia|Belarus|Ukraine)).*Vless.*$'
      };

  // Keep filtered proxies if already present; otherwise provider will supply them
  if (cleanProxies.length) {
    config.proxies = cleanProxies;
  }

  config['proxy-groups'] = [
    { name: 'PROXY', type: 'select', proxies: ['AUTO-MAIN', 'GOOGLE', 'DIRECT'] },
    googleGroup,
    autoMainGroup
  ];

  // -------- Rules (order matches shadowrocket.conf) --------
  config.rules = [
    'AND,((NETWORK,UDP),(DST-PORT,443)),REJECT',
    'AND,((NETWORK,UDP),(DST-PORT,853)),REJECT',
    'RULE-SET,whitelist_direct,DIRECT',
    'RULE-SET,greylist_proxy,PROXY',
    'RULE-SET,google_gemini,GOOGLE',
    'RULE-SET,google_full,GOOGLE',
    'RULE-SET,gemini_ip,GOOGLE,no-resolve',
    'RULE-SET,youtube,GOOGLE',
    'RULE-SET,youtubemusic,GOOGLE',
    'RULE-SET,microsoft,PROXY',
    'RULE-SET,domains_community,PROXY',
    'RULE-SET,domain_ips,PROXY,no-resolve',
    'RULE-SET,voice_ports,PROXY',
    'RULE-SET,telegram,PROXY',
    'DOMAIN-SUFFIX,ru,DIRECT',
    'DOMAIN-SUFFIX,рф,DIRECT',
    'DOMAIN-SUFFIX,su,DIRECT',
    'GEOIP,RU,DIRECT',
    'MATCH,PROXY'
  ];

  return config;
};
