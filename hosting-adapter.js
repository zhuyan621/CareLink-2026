// Connect only project API calls to the original running application.
(() => {
  const apiOrigin = "https://savings-functions-diverse-separate.trycloudflare.com";
  const originalFetch = window.fetch.bind(window);
  window.fetch = (input, options) => {
    const raw = input instanceof Request ? input.url : String(input);
    const url = new URL(raw, location.href);
    if (url.origin === location.origin && /^\/(?:site|mapfm|screening|risk|engineering|competition)(?:\/|$)/.test(url.pathname)) {
      if (input instanceof Request) return originalFetch(new Request(apiOrigin + url.pathname + url.search, input), {...options, credentials:'omit', mode:'cors'});
      return originalFetch(apiOrigin + url.pathname + url.search, {...options, credentials:'omit', mode:'cors'});
    }
    return originalFetch(input, options);
  };
})();
